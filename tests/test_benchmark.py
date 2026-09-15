"""Per-run reporting and the actual single-clip command's failure behavior."""

import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from egocentric_pipeline.benchmark import build_benchmark
from egocentric_pipeline.run_metadata import artifact_record, new_manifest, new_run_directory, read_json, utc_now, write_json


ROOT = Path(__file__).resolve().parents[1]


def finalized_run(tmp_path, status="completed"):
    directory = new_run_directory(tmp_path)
    manifest = new_manifest(directory, {"source": {"path": "fixture.mp4"}, "license_reference": "synthetic test"}, ROOT)
    manifest.update(status=status, finished_at=utc_now(), clip_id="fixture", wall_time_s=2.0,
                    source={"path": "fixture.mp4", "dataset": "synthetic"})
    manifest["stages"] = [{"name": "preparation", "status": "completed"},
                          {"name": "inference", "status": status}]
    if status == "completed":
        manifest["stages"].append({"name": "visualization", "status": "completed"})
        manifest["preparation"] = {"prepared": {"frame_count": 6},
                                   "hawor_camera": {"focal_length_px": 600.0, "provenance": "hawor_default"}}
        export = directory / "trajectory_world.npz"
        direct = np.ones((6, 2), dtype=bool)
        direct[1:4, 0] = False
        direct[4:6, 1] = False
        infilled = ~direct
        infilled[5, 1] = False
        valid = direct | infilled
        np.savez(export, direct_detection=direct, motion_infilled=infilled,
                 hawor_valid=valid, export_valid=valid)
        overlay = directory / "overlay.mp4"
        overlay.write_bytes(b"report fixture; not used as rendering validation")
        manifest["artifacts"] = {"trajectory_world": artifact_record(export), "overlay": artifact_record(overlay)}
    else:
        manifest["failure"] = {"stage": "inference", "type": "RuntimeError", "message": "synthetic failure"}
    path = directory / "run_manifest.json"
    write_json(path, manifest)
    return path


def test_success_metrics_review_and_report_identity(tmp_path):
    manifest = finalized_run(tmp_path)
    files = build_benchmark(manifest, "other_test", review_status="complete",
                            failure_labels=["temporal jitter"], notes="Reviewed synthetic evidence")
    result = read_json(files["benchmark"])
    assert result["run_id"] == manifest.parent.name
    assert result["metrics"]["effective_fps"]["value"] == 3
    assert result["manual_review"]["status"] == "complete"
    coverage = result["metrics"]["trajectory_coverage"]["value"]
    assert coverage["left"]["longest_infilled_s"] == pytest.approx(3 / 30)
    assert coverage["right"]["export_invalid_frames"] == 1
    assert coverage["right"]["valid_provenance_coverage_fraction"] == 1
    assert result["metrics"]["peak_process_gpu_memory_bytes"]["value"] is None
    assert result["metrics"]["peak_process_gpu_memory_bytes"]["unavailable_reason"]
    report = Path(files["report"]).read_text()
    assert "temporal jitter" in report and "Reviewed synthetic evidence" in report
    assert manifest.parent.name in report


def test_failed_attempt_and_no_cross_run_overwrite(tmp_path):
    success = finalized_run(tmp_path)
    files = build_benchmark(success, "setup_smoke")
    original = Path(files["benchmark"]).read_bytes()
    failed = finalized_run(tmp_path, "failed")
    failure_files = build_benchmark(failed, "ego4d")
    result = read_json(failure_files["benchmark"])
    assert result["run_id"] == failed.parent.name
    assert result["failure"]["stage"] == "inference"
    assert result["manual_review"]["status"] == "not_possible"
    assert result["metrics"]["trajectory_coverage"]["value"] is None
    assert result["metrics"]["trajectory_coverage"]["unavailable_reason"]
    assert Path(files["benchmark"]).read_bytes() == original
    with pytest.raises(FileExistsError):
        build_benchmark(success, "setup_smoke")


def test_review_update_is_explicit_and_retains_execution(tmp_path):
    manifest = finalized_run(tmp_path)
    build_benchmark(manifest, "other_test")
    paths = build_benchmark(manifest, "other_test", review_status="complete", notes="Reviewed", overwrite=True)
    result = read_json(paths["benchmark"])
    assert result["status"] == "completed"
    assert result["manual_review"]["status"] == "complete"


def test_reject_unfinalized_or_foreign_artifact(tmp_path):
    first, second = finalized_run(tmp_path), finalized_run(tmp_path)
    manifest = read_json(first)
    manifest["artifacts"]["trajectory_world"] = read_json(second)["artifacts"]["trajectory_world"]
    write_json(first, manifest, overwrite=True)
    with pytest.raises(ValueError, match="outside this run"):
        build_benchmark(first, "other_test")
    manifest.update(status="running", finished_at=None)
    write_json(first, manifest, overwrite=True)
    with pytest.raises(ValueError, match="finalized"):
        build_benchmark(first, "other_test")


def test_tampered_export_is_a_contract_violation(tmp_path):
    manifest = finalized_run(tmp_path)
    (manifest.parent / "trajectory_world.npz").write_bytes(b"tampered")
    paths = build_benchmark(manifest, "other_test")
    result = read_json(paths["benchmark"])
    assert result["structural_violations"]
    assert result["metrics"]["trajectory_coverage"]["value"] is None


@pytest.mark.parametrize("fault", ["float_masks", "wrong_shape", "partial_npz", "tampered_overlay", "foreign_overlay", "partial_render"])
def test_malformed_evidence_still_produces_honest_report(tmp_path, fault):
    path = finalized_run(tmp_path)
    manifest = read_json(path)
    if fault in ("float_masks", "wrong_shape"):
        array = np.ones((6, 2) if fault == "float_masks" else (5, 2), dtype=float if fault == "float_masks" else bool)
        export = path.parent / "trajectory_world.npz"
        np.savez(export, **{key: array for key in ("direct_detection", "motion_infilled", "export_valid", "hawor_valid")})
        manifest["artifacts"]["trajectory_world"] = artifact_record(export)
    elif fault == "partial_npz":
        export = path.parent / "trajectory_world.npz"
        export.write_bytes(b"PK\x03\x04partial-npz")
        manifest["artifacts"]["trajectory_world"] = artifact_record(export)
        manifest["status"] = "failed"
        manifest["failure"] = {"stage": "export", "message": "interrupted"}
    elif fault == "tampered_overlay":
        (path.parent / "overlay.mp4").write_bytes(b"tampered")
    elif fault == "foreign_overlay":
        other = finalized_run(tmp_path)
        manifest["artifacts"]["overlay"] = read_json(other)["artifacts"]["overlay"]
    else:
        manifest["status"] = "failed"
        manifest["stages"][-1]["status"] = "failed"
        manifest["failure"] = {"stage": "visualization", "message": "interrupted"}
    write_json(path, manifest, overwrite=True)
    report = build_benchmark(path, "other_test", review_status="complete")
    result = read_json(report["benchmark"])
    assert Path(report["report"]).is_file()
    if fault in ("float_masks", "wrong_shape", "partial_npz"):
        assert result["metrics"]["trajectory_coverage"]["value"] is None
    else:
        assert result["manual_review"]["status"] == "not_possible"
    if fault != "partial_render":
        assert result["structural_violations"]


def test_milestone_cli_reports_each_failed_attempt_without_other_clips(tmp_path):
    command = [sys.executable, str(ROOT / "scripts/run_milestone1_baseline.py"),
               "--video", str(tmp_path / "missing.mp4"), "--output-root", str(tmp_path / "runs"),
               "--prepared-root", str(tmp_path / "prepared"), "--dataset", "ego4d"]
    environment = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    for _ in range(2):
        process = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True)
        assert process.returncode == 1, process.stdout + process.stderr
    manifests = list((tmp_path / "runs").glob("*/run_manifest.json"))
    assert len(manifests) == 2
    for path in manifests:
        manifest = read_json(path)
        assert manifest["status"] == "failed" and manifest["failure"]["stage"] == "preparation"
        assert manifest["stages"][1]["status"] == "not_run"
        result = read_json(path.parent / "benchmark.json")
        assert result["run_id"] == path.parent.name and result["role"] == "ego4d"
        assert (path.parent / "benchmark_report.md").is_file()


def test_invalid_request_syntax_allocates_no_run(tmp_path):
    process = subprocess.run([sys.executable, str(ROOT / "scripts/run_milestone1_baseline.py"),
                              "--video", str(tmp_path / "unsupported.avi"), "--output-root", str(tmp_path / "runs")],
                             cwd=ROOT, env=dict(os.environ, PYTHONPATH=str(ROOT / "src")), capture_output=True, text=True)
    assert process.returncode == 2
    assert not (tmp_path / "runs").exists()
