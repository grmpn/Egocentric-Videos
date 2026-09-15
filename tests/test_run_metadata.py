"""Exercise provenance publication and redaction used by real pipeline runs."""

import hashlib
import math
from pathlib import Path
import shutil
import subprocess
import sys
import threading

import numpy as np
import pytest

from egocentric_pipeline.clip_request import ClipRequest
from egocentric_pipeline import hawor_runner, pipeline, run_metadata, visualization
from egocentric_pipeline.run_metadata import (
    ResourceMonitor, capture_environment, new_manifest, new_run_directory, read_json, redact, sha256_file, write_json,
)
from egocentric_pipeline.video_preparation import PreparedClip, prepare_clip
from test_world_export import native_fixture


def test_hash_and_non_overwriting_json(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"unchanged input\x00\xff")
    assert sha256_file(source) == hashlib.sha256(source.read_bytes()).hexdigest()
    target = tmp_path / "evidence.json"
    write_json(target, {"source_sha256": sha256_file(source)})
    original = target.read_bytes()
    with pytest.raises(FileExistsError):
        write_json(target, {"replaced": True})
    assert target.read_bytes() == original
    with pytest.raises(ValueError):
        write_json(target, {"bad": math.nan}, overwrite=True)
    assert target.read_bytes() == original
    write_json(target, {"finalized": True}, overwrite=True)
    assert read_json(target) == {"finalized": True}
    assert not list(tmp_path.glob(".evidence.json-*"))


def test_run_ids_preserve_prior_runs(tmp_path):
    first = new_run_directory(tmp_path)
    write_json(first / "run_manifest.json", {"evidence": "keep"})
    second = new_run_directory(tmp_path)
    assert first != second
    assert read_json(first / "run_manifest.json") == {"evidence": "keep"}


def test_named_secrets_and_command_arguments_are_redacted():
    value = {"AWS_SECRET_ACCESS_KEY": "private", "nested": {"Authorization": "Bearer private"},
             "command": ["program", "--token", "private", "--api-key=private", "--input", "video.mp4"],
             "download": "https://user:private@example.com/model"}
    result = redact(value)
    assert "private" not in str(result)
    assert result["command"][-1] == "video.mp4"
    assert value["AWS_SECRET_ACCESS_KEY"] == "private"


def test_initial_manifest_has_explicit_missing_evidence(tmp_path):
    root = Path(__file__).resolve().parents[1]
    manifest = new_manifest(new_run_directory(tmp_path), {"source": "fixture.mp4"}, root)
    assert manifest["run_id"]
    assert manifest["status"] == "running"
    assert manifest["finished_at"] is None
    assert manifest["failure"] is None
    assert manifest["artifacts"] == {}
    assert manifest["environment"]["python"]


@pytest.mark.parametrize("gpu_response", ["unavailable", "unsupported", "available"])
def test_resource_monitor_reports_real_ram_and_honest_gpu_evidence(monkeypatch, gpu_response):
    queried = threading.Event()
    calls = []

    def gpu_query(command, **kwargs):
        calls.append((command, kwargs))
        queried.set()
        if gpu_response == "unavailable":
            raise FileNotFoundError("Synthetic nvidia-smi is unavailable")
        metrics = "4096, N/A, [Not Supported]" if gpu_response == "unsupported" else "4096, 1024, 34"
        return subprocess.CompletedProcess(command, 0, stdout=f"Synthetic GPU, test-driver, {metrics}\n", stderr="")

    monkeypatch.setattr(run_metadata.subprocess, "run", gpu_query)
    monitor = ResourceMonitor(sample_interval_s=0.5)
    assert monitor.start() is monitor
    try:
        assert queried.wait(timeout=2), "The resource monitor did not attempt its first sample"
    finally:
        resources = monitor.stop()
    assert monitor._thread is not None and not monitor._thread.is_alive()
    assert resources["sample_interval_s"] == 0.5
    assert resources["started_at"] and resources["finished_at"] and resources["duration_s"] >= 0
    assert resources["samples"]
    assert resources["peak_process_tree_rss_bytes"] > 0
    assert resources["process_tree_rss_unavailable_reason"] is None
    assert resources["peak_process_gpu_memory_bytes"] is None
    assert resources["process_gpu_memory_unavailable_reason"]
    assert "other applications" in resources["gpu_scope"]
    assert resources["sampling_error"] is None
    for command, arguments in calls:
        assert command == ["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.used,utilization.gpu",
                           "--format=csv,noheader,nounits"]
        assert arguments == {"capture_output": True, "text": True,
                             "timeout": run_metadata.GPU_QUERY_TIMEOUT_S, "check": False}
    for sample in resources["samples"]:
        assert sample["process_tree_rss_bytes"] > 0
        assert sample["observed_at"] and sample["elapsed_s"] >= 0 and sample["sample_duration_s"] >= 0
        if gpu_response == "available":
            assert sample["device_gpu_memory_used_bytes"] == [1024 * 1024**2]
            assert sample["device_gpu_utilization_percent"] == [34.0]
            assert sample["gpu_unavailable_reason"] is None
        else:
            expected = None if gpu_response == "unavailable" else [None]
            assert sample["device_gpu_memory_used_bytes"] == expected
            assert sample["device_gpu_utilization_percent"] == expected
            assert sample["gpu_unavailable_reason"]
    if gpu_response == "available":
        assert resources["peak_device_gpu_memory_bytes"] == 1024 * 1024**2
        assert resources["peak_device_gpu_utilization_percent"] == 34.0
        assert resources["gpu_sampling_error"] is None
    else:
        assert resources["peak_device_gpu_memory_bytes"] is None
        assert resources["peak_device_gpu_utilization_percent"] is None
        assert resources["gpu_sampling_error"]
    if gpu_response == "unavailable":
        assert resources["gpu_identity"] is None
    else:
        assert resources["gpu_identity"] == [{"name": "Synthetic GPU", "driver_version": "test-driver",
                                               "memory_total_bytes": 4096 * 1024**2}]
    # Final snapshots are stable, and nested sample dictionaries are detached.
    assert monitor.stop() == resources == monitor.snapshot()
    resources["samples"][0]["process_tree_rss_bytes"] = -1
    assert monitor.snapshot()["samples"][0]["process_tree_rss_bytes"] > 0
    with pytest.raises(RuntimeError, match="only be started once"):
        monitor.start()


@pytest.mark.parametrize("interval", [0, -0.5, math.nan, math.inf, True])
def test_resource_monitor_rejects_invalid_sampling_intervals(interval):
    with pytest.raises(ValueError, match="positive finite"):
        ResourceMonitor(sample_interval_s=interval)


@pytest.mark.parametrize("startup", ["never-started", "missing-psutil", "thread-start-failure"])
def test_resource_monitor_stop_finalizes_unstarted_or_failed_startup(monkeypatch, startup):
    monitor = ResourceMonitor()
    if startup == "missing-psutil":
        monkeypatch.setitem(sys.modules, "psutil", None)
        with pytest.raises(ModuleNotFoundError, match="psutil"):
            monitor.start()
    elif startup == "thread-start-failure":
        def fail_start(thread):
            raise RuntimeError("Synthetic thread startup failure")

        monkeypatch.setattr(run_metadata.threading.Thread, "start", fail_start)
        with pytest.raises(RuntimeError, match="Synthetic thread startup failure"):
            monitor.start()
    result = monitor.stop()
    assert result["finished_at"]
    assert result["samples"] == []
    assert result["peak_process_tree_rss_bytes"] is None
    assert result["peak_device_gpu_memory_bytes"] is None
    assert result["peak_device_gpu_utilization_percent"] is None
    assert result["sampling_error"] == result["process_tree_rss_unavailable_reason"] == result["gpu_sampling_error"]
    assert result["sampling_error"]
    if startup == "thread-start-failure":
        assert result["started_at"] and result["duration_s"] >= 0
        assert "Synthetic thread startup failure" in result["sampling_error"]
    else:
        assert result["started_at"] is None and result["duration_s"] is None
    assert monitor.stop() == result == monitor.snapshot()


def test_environment_provenance_tracks_dirty_source_and_environment_changes(tmp_path, monkeypatch):
    source = tmp_path / "src/egocentric_pipeline/example.py"
    specification = tmp_path / "environment/hawor.yml"
    source.parent.mkdir(parents=True)
    specification.parent.mkdir()
    source.write_text("VALUE = 1\n")
    specification.write_text("name: synthetic-test-environment\n")
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(["git", "add", "src", "environment"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "-c", "user.name=Test Fixture", "-c", "user.email=fixture@example.invalid",
                    "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "--quiet",
                    "-m", "Synthetic provenance fixture"], cwd=tmp_path, check=True, capture_output=True)
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "synthetic-device-visibility")

    clean = capture_environment(tmp_path)
    assert clean["repository_commit"]
    assert clean["repository_dirty"] is False
    assert clean["repository_status"] == []
    assert clean["repository_state_unavailable_reason"] is None
    assert clean["project_file_sha256"] == {"src/egocentric_pipeline/example.py": sha256_file(source),
                                             "environment/hawor.yml": sha256_file(specification)}
    assert clean["environment_specification"] == {"path": str(specification), "sha256": sha256_file(specification)}
    assert clean["variables"]["CUDA_VISIBLE_DEVICES"] == "synthetic-device-visibility"

    source.write_text("VALUE = 2\n")
    specification.write_text("name: changed-synthetic-test-environment\n")
    added = source.parent / "untracked.py"
    added.write_text("ADDED = True\n")
    excluded = source.parent / "api_token.py"
    excluded.write_text("SYNTHETIC_ONLY = True\n")
    dirty = capture_environment(tmp_path)
    assert dirty["repository_commit"] == clean["repository_commit"]
    assert dirty["repository_dirty"] is True
    assert set(dirty["repository_status"]) == {
        " M environment/hawor.yml", " M src/egocentric_pipeline/example.py", "?? src/egocentric_pipeline/untracked.py"}
    assert dirty["project_file_sha256"] == {"src/egocentric_pipeline/example.py": sha256_file(source),
                                             "environment/hawor.yml": sha256_file(specification),
                                             "src/egocentric_pipeline/untracked.py": sha256_file(added)}
    assert dirty["project_file_sha256"]["src/egocentric_pipeline/example.py"] != clean["project_file_sha256"]["src/egocentric_pipeline/example.py"]
    assert dirty["environment_specification"] == {"path": str(specification), "sha256": sha256_file(specification)}
    assert dirty["environment_specification"]["sha256"] != clean["environment_specification"]["sha256"]
    assert "api_token.py" not in str(dirty)


def test_environment_provenance_marks_missing_git_state_unknown(tmp_path):
    evidence = capture_environment(tmp_path)
    assert evidence["repository_commit"] is None
    assert evidence["repository_dirty"] is None
    assert evidence["repository_status"] == []
    assert evidence["repository_state_unavailable_reason"]
    assert evidence["project_file_sha256"] == {}
    assert evidence["environment_specification"] is None


def _workflow_video(path, frame_count=6):
    subprocess.run(["ffmpeg", "-v", "error", "-n", "-f", "lavfi", "-i", "testsrc2=size=32x24:rate=30",
                    "-frames:v", str(frame_count), "-c:v", "libx264", "-threads", "1", "-pix_fmt", "yuv420p",
                    str(path)], check=True, capture_output=True)
    return path


@pytest.mark.parametrize("failure_mode", ["changed-focal", "engine-inspection", "process-launch"])
def test_hawor_prelaunch_failures_retain_evidence_without_inference(tmp_path, monkeypatch, failure_mode):
    source = _workflow_video(tmp_path / "source.mp4")
    prepared = prepare_clip(ClipRequest.from_video(source, clip_id="prelaunch-failure"), tmp_path / "prepared")
    persisted_focal = prepared.metadata.hawor_camera["focal_length_px"]
    if failure_mode == "changed-focal":
        prepared.metadata.hawor_camera["focal_length_px"] = persisted_focal + 100
    inspections, launches = [], []

    def inspect_engine(path):
        inspections.append(path)
        if failure_mode == "engine-inspection":
            raise ValueError("Synthetic engine inspection failure")
        return {"revision": hawor_runner.HAWOR_REVISION, "nested_submodules": [], "assets": {}}

    real_popen = subprocess.Popen

    def launch(command, *args, **kwargs):
        # Prepared-clip verification still invokes real ffprobe/ffmpeg. Only the
        # engine launch is replaced, so the actual runner boundary is exercised.
        if len(command) > 1 and command[1] == "demo.py":
            launches.append((command, kwargs))
            raise OSError("Synthetic engine process launch failure")
        return real_popen(command, *args, **kwargs)

    monkeypatch.setattr(hawor_runner, "inspect_engine", inspect_engine)
    monkeypatch.setattr(hawor_runner.subprocess, "Popen", launch)
    native_root = tmp_path / "run/native"
    engine_root = tmp_path / "synthetic-engine"
    result = hawor_runner.run_hawor(prepared, native_root, engine_root, resource_monitor=object())
    assert result["status"] == "failed"
    assert result["returncode"] is None
    assert result["upstream_stages_completed"] is False
    assert result["wall_time_s"] > 0
    assert result["artifacts"] == {}
    assert len(result["missing_artifacts"]) == 5
    assert result["native_directory"] == str(native_root / "rgb")
    assert result["cwd"] == str(engine_root)
    assert result["command"][1:] == ["demo.py", "--video_path", str(native_root / "rgb.mp4"),
                                      "--img_focal", str(prepared.metadata.hawor_camera["focal_length_px"]),
                                      "--vis_mode", "none"]
    log = Path(result["log"])
    assert log == native_root / "console.log" and log.is_file()
    assert result["failure"]["message"] in log.read_text()
    assert [(stage["name"], stage["status"]) for stage in result["stages"]] == [
        ("initialization", "failed"), ("detection_tracking", "not_run"), ("hand_estimation", "not_run"),
        ("slam_metric_scale", "not_run"), ("infilling", "not_run")]
    initial = result["stages"][0]
    assert initial["started_at"] and initial["finished_at"] and initial["wall_time_s"] >= 0
    assert initial["error"] == result["failure"]["message"]
    if failure_mode == "changed-focal":
        assert "differs from its verified persisted metadata" in result["failure"]["message"]
        assert result["failure"]["type"] == "ValueError"
        assert inspections == launches == []
        assert not (native_root / "rgb.mp4").exists()
    elif failure_mode == "engine-inspection":
        assert result["failure"] == {"type": "ValueError", "message": "Synthetic engine inspection failure"}
        assert inspections == [engine_root] and launches == []
        assert not (native_root / "rgb.mp4").exists()
    else:
        assert result["failure"] == {"type": "OSError", "message": "Synthetic engine process launch failure"}
        assert inspections == [engine_root] and len(launches) == 1
        assert launches[0][0] == result["command"]
        assert launches[0][1]["cwd"] == engine_root
        assert sha256_file(native_root / "rgb.mp4") == prepared.metadata.prepared["sha256"]
    assert read_json(prepared.metadata_path)["hawor_camera"]["focal_length_px"] == persisted_focal


@pytest.mark.parametrize("run_mode", ["fresh-mp4", "reloaded-prepared", "renderer-failure"])
def test_pipeline_prepares_runs_real_export_and_finalizes_manifest(tmp_path, monkeypatch, native_fixture, run_mode):
    """Only inference/rendering are substituted; preparation/export are production."""
    native_template, _, _, native_arrays = native_fixture
    source = _workflow_video(tmp_path / "source.mp4", native_arrays[0].shape[1])
    source_hash = sha256_file(source)
    request = ClipRequest.from_video(source, clip_id="workflow-clip", dataset="synthetic",
                                     video_id="six-frames", task_label="generated test pattern",
                                     license_reference="synthetic fixture")
    engine_calls = []
    renderer_calls = []

    def engine(prepared, native_root, hawor_root, sample_interval_s, *, resource_monitor=None):
        assert isinstance(prepared, PreparedClip)
        assert prepared.metadata.prepared["frame_count"] == 6
        assert prepared.metadata.source["sha256"] == source_hash
        assert prepared.metadata.hawor_camera["focal_length_px"] == 600
        assert isinstance(resource_monitor, ResourceMonitor)
        assert resource_monitor.snapshot()["started_at"]
        assert resource_monitor.snapshot()["finished_at"] is None
        engine_calls.append((prepared, native_root, hawor_root, sample_interval_s, resource_monitor))
        # The fixture is copied into the exact native workspace supplied by the
        # production orchestrator; the real exporter reads these files itself.
        native_directory = native_root / "rgb"
        shutil.copytree(native_template, native_directory)
        log = native_root / "console.log"
        log.write_text("Synthetic CPU inference fixture; no neural network executed.\n")
        return {"status": "completed", "returncode": 0, "native_directory": str(native_directory),
                "log": str(log), "command": ["synthetic-engine", "--img_focal", "600.0"],
                "cwd": str(hawor_root), "environment": {}, "missing_artifacts": [],
                "resources": {"sample_interval_s": sample_interval_s, "peak_device_gpu_memory_bytes": None},
                "upstream_stages_completed": True}

    def renderer(native_directory, prepared, trajectory_path, output_directory, hawor_root):
        assert trajectory_path == output_directory / "trajectory_world.npz"
        assert native_directory == output_directory / "native/rgb"
        assert engine_calls[0][4].snapshot()["finished_at"] is None
        # Reading the real export here checks that orchestration handed the
        # renderer the completed export and the same prepared-clip contract.
        with np.load(trajectory_path, allow_pickle=False) as exported:
            assert exported["frame_index"].size == prepared.metadata.prepared["frame_count"]
            assert exported["export_valid"].sum() == 11
        renderer_calls.append((prepared, trajectory_path, hawor_root))
        overlay = output_directory / "overlay.mp4"
        preview = output_directory / "trajectory_preview.png"
        log = output_directory / "visualization.log"
        if run_mode == "renderer-failure":
            log.write_text("Synthetic renderer failed before producing a complete video.\n")
            raise RuntimeError("Synthetic renderer failed; see visualization.log")
        shutil.copyfile(prepared.video_path, overlay)
        subprocess.run(["ffmpeg", "-v", "error", "-n", "-i", str(prepared.video_path), "-frames:v", "1",
                        str(preview)], check=True, capture_output=True)
        log.write_text("Synthetic CPU renderer fixture; no mesh projection verified.\n")
        return {"overlay": str(overlay), "trajectory_preview": str(preview), "render_log": str(log),
                "validation": {"frame_count": 6, "renderer": "synthetic CPU fixture"}}

    monkeypatch.setattr(pipeline, "run_hawor", engine)
    monkeypatch.setattr(visualization, "visualize", renderer)
    prepared_root, output_root = tmp_path / "prepared", tmp_path / "runs"
    arguments = {"prepared_root": prepared_root, "output_root": output_root,
                 "hawor_root": tmp_path / "synthetic-engine", "sample_interval_s": 0.25}
    if run_mode == "reloaded-prepared":
        existing = prepare_clip(request, prepared_root)
        result = pipeline.run_clip(prepared_metadata=existing.metadata_path, **arguments)
    else:
        result = pipeline.run_clip(request, **arguments)

    manifest = read_json(result.manifest_path)
    assert manifest["resources"]["started_at"] and manifest["resources"]["finished_at"]
    assert manifest["resources"]["samples"]
    assert "Whole pipeline" in manifest["resources"]["scope"]
    assert manifest["resources"]["duration_s"] > 0
    assert not engine_calls[0][4]._thread.is_alive()
    if run_mode == "renderer-failure":
        assert result.status == manifest["status"] == "failed"
        assert len(engine_calls) == len(renderer_calls) == 1
        assert manifest["finished_at"] and manifest["wall_time_s"] > 0
        assert manifest["failure"]["stage"] == "visualization"
        assert "Synthetic renderer failed" in manifest["failure"]["message"]
        assert [(stage["name"], stage["status"]) for stage in manifest["stages"]] == [
            ("preparation", "completed"), ("inference", "completed"), ("export", "completed"),
            ("visualization", "failed"), ("validation", "not_run")]
        assert set(manifest["artifacts"]) == {
            "clip_metadata", "prepared_video", "inference_log", "trajectory_world", "trajectory_metadata", "render_log"}
        log_evidence = manifest["artifacts"]["render_log"]
        assert "Synthetic renderer failed" in Path(log_evidence["path"]).read_text()
        assert log_evidence["sha256"] == sha256_file(log_evidence["path"])
        assert manifest["validation"]["trajectory"]["export_valid_count_by_hand"] == [6, 5]
        assert "visualization" not in manifest["validation"]
        assert "final" not in manifest["validation"]
        assert not list(result.run_directory.rglob("overlay.mp4"))
        assert sha256_file(source) == source_hash
        return
    assert result.status == "completed", manifest["failure"]
    assert len(engine_calls) == len(renderer_calls) == 1
    assert engine_calls[0][0].metadata == renderer_calls[0][0].metadata
    assert engine_calls[0][3] == 0.25
    assert list(output_root.iterdir()) == [result.run_directory]
    assert result.manifest_path == result.run_directory / "run_manifest.json"
    assert manifest["schema_version"] == "1.0"
    assert manifest["run_id"] == result.run_directory.name
    assert manifest["run_directory"] == str(result.run_directory)
    assert manifest["clip_id"] == "workflow-clip"
    assert manifest["request"] == request.to_dict()
    assert manifest["source"]["dataset"] == "synthetic"
    assert manifest["source"]["video_id"] == "six-frames"
    assert manifest["source"]["sha256"] == source_hash == sha256_file(source)
    assert manifest["started_at"] and manifest["finished_at"]
    assert manifest["wall_time_s"] > 0
    assert manifest["failure"] is None
    assert [(stage["name"], stage["status"]) for stage in manifest["stages"]] == [
        (name, "completed") for name in ("preparation", "inference", "export", "visualization", "validation")]
    assert all(stage["started_at"] and stage["finished_at"] and stage["wall_time_s"] >= 0
               for stage in manifest["stages"])
    assert manifest["inference"]["upstream_stages_completed"] is True
    assert manifest["commands"][0]["command"] == ["synthetic-engine", "--img_focal", "600.0"]
    assert manifest["resources"]["sample_interval_s"] == 0.25
    assert manifest["validation"]["trajectory"]["native_float32_values_bitwise_preserved"] is True
    assert manifest["validation"]["trajectory"]["export_valid_count_by_hand"] == [6, 5]
    assert manifest["validation"]["final"] == {
        "artifact_hashes_match": True, "manual_review": "pending", "world_coordinates_transformed": False}
    assert set(manifest["artifacts"]) == {
        "clip_metadata", "prepared_video", "inference_log", "trajectory_world", "trajectory_metadata",
        "overlay", "trajectory_preview", "render_log"}
    for evidence in manifest["artifacts"].values():
        path = Path(evidence["path"])
        assert path.is_file()
        assert evidence["sha256"] == sha256_file(path)
        assert evidence["size_bytes"] == path.stat().st_size
    with np.load(manifest["artifacts"]["trajectory_world"]["path"], allow_pickle=False) as exported:
        assert exported["root_translation_world_m"].transpose(1, 0, 2).tobytes() == native_arrays[0].tobytes()
        np.testing.assert_array_equal(exported["source_timestamp_s"], np.arange(6) / 30)
        assert not exported["export_valid"][-1, 1]


def test_pipeline_engine_failure_finalizes_evidence_without_downstream_artifacts(tmp_path, monkeypatch):
    source = _workflow_video(tmp_path / "source.mp4")
    source_hash = sha256_file(source)
    request = ClipRequest.from_video(source, clip_id="failed-workflow", dataset="synthetic")
    engine_calls = []

    def failing_engine(prepared, native_root, hawor_root, sample_interval_s, *, resource_monitor=None):
        assert isinstance(prepared, PreparedClip)
        engine_calls.append(prepared)
        native_root.mkdir()
        log = native_root / "console.log"
        log.write_text("Synthetic upstream failure before world export.\n")
        return {"status": "failed", "returncode": 9, "native_directory": str(native_root / "rgb"),
                "log": str(log), "command": ["synthetic-engine"], "cwd": str(hawor_root),
                "environment": {}, "resources": {}, "missing_artifacts": ["world_space_res.pth"],
                "upstream_stages_completed": False}

    def unexpected_renderer(*args, **kwargs):
        pytest.fail("Renderer must not run after an engine failure")

    monkeypatch.setattr(pipeline, "run_hawor", failing_engine)
    monkeypatch.setattr(visualization, "visualize", unexpected_renderer)
    result = pipeline.run_clip(request, prepared_root=tmp_path / "prepared", output_root=tmp_path / "runs",
                               hawor_root=tmp_path / "synthetic-engine")
    manifest = read_json(result.manifest_path)
    assert result.status == manifest["status"] == "failed"
    assert len(engine_calls) == 1
    assert manifest["run_id"] == result.run_directory.name
    assert manifest["clip_id"] == "failed-workflow"
    assert manifest["request"] == request.to_dict()
    assert manifest["finished_at"] and manifest["wall_time_s"] > 0
    assert manifest["resources"]["finished_at"]
    assert manifest["failure"]["stage"] == "inference"
    assert manifest["failure"]["type"] == "RuntimeError"
    assert "exit 9" in manifest["failure"]["message"]
    assert [(stage["name"], stage["status"]) for stage in manifest["stages"]] == [
        ("preparation", "completed"), ("inference", "failed"), ("export", "not_run"),
        ("visualization", "not_run"), ("validation", "not_run")]
    assert set(manifest["artifacts"]) == {"clip_metadata", "prepared_video", "inference_log"}
    assert manifest["validation"] == {}
    assert manifest["inference"]["upstream_stages_completed"] is False
    assert not list(result.run_directory.rglob("trajectory_world.npz"))
    assert not list(result.run_directory.rglob("trajectory_metadata.json"))
    assert not list(result.run_directory.rglob("overlay.mp4"))
    assert not list(result.run_directory.rglob("trajectory_preview.png"))
    assert sha256_file(source) == source_hash


def test_pipeline_rejects_corrupt_prepared_metadata_before_engine_execution(tmp_path, monkeypatch):
    source = _workflow_video(tmp_path / "source.mp4")
    prepared = prepare_clip(ClipRequest.from_video(source, clip_id="corrupt-metadata"), tmp_path / "prepared")
    metadata = read_json(prepared.metadata_path)
    metadata["prepared"]["sha256"] = metadata["artifacts"]["prepared"]["sha256"] = "0" * 64
    write_json(prepared.metadata_path, metadata, overwrite=True)

    def unexpected_engine(*args, **kwargs):
        pytest.fail("The engine must not receive an unverified prepared clip")

    monkeypatch.setattr(pipeline, "run_hawor", unexpected_engine)
    result = pipeline.run_clip(prepared_metadata=prepared.metadata_path, output_root=tmp_path / "runs")
    manifest = read_json(result.manifest_path)
    assert result.status == manifest["status"] == "failed"
    assert manifest["run_id"] == result.run_directory.name
    assert manifest["finished_at"] and manifest["wall_time_s"] > 0
    assert manifest["resources"]["finished_at"]
    assert manifest["request"] == {"prepared_metadata": str(prepared.metadata_path)}
    assert manifest["failure"]["stage"] == "preparation"
    assert "hash" in manifest["failure"]["message"]
    assert [(stage["name"], stage["status"]) for stage in manifest["stages"]] == [
        ("preparation", "failed"), ("inference", "not_run"), ("export", "not_run"),
        ("visualization", "not_run"), ("validation", "not_run")]
    assert "inference" not in manifest
    assert "trajectory_world" not in manifest["artifacts"]
    assert "overlay" not in manifest["artifacts"]
