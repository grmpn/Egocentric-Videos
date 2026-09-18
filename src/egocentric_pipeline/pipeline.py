"""One clip attempt with a finalized manifest on success or stage failure."""

from dataclasses import dataclass
from datetime import datetime
import math
from pathlib import Path
import time

from .clip_request import ClipRequest
from .hawor_runner import run_hawor
from .run_metadata import ResourceMonitor, artifact_record, new_manifest, new_run_directory, redact, stage_record, utc_now, write_json


@dataclass(frozen=True)
class RunResult:
    run_directory: Path
    manifest_path: Path
    status: str


def run_clip(request=None, *, prepared_metadata=None, output_root=None, prepared_root=None,
             hawor_root=None, preparation_policy=None, sample_interval_s=0.5):
    """Prepare/load one MP4, invoke HaWoR, package unchanged coordinates, render.

    Invalid request syntax fails before allocation. Once allocated, stage failures
    are returned as RunResult(status='failed') with their finalized manifest.
    """
    if (request is None) == (prepared_metadata is None):
        raise ValueError("Supply exactly one ClipRequest or prepared metadata path")
    if request is not None and not isinstance(request, ClipRequest):
        raise TypeError("request must be a normalized ClipRequest")
    if not math.isfinite(sample_interval_s) or sample_interval_s <= 0:
        raise ValueError("Resource sampling interval must be positive")
    repository_root = Path(__file__).resolve().parents[2]
    output_root = Path(output_root) if output_root is not None else repository_root / "outputs/hawor"
    prepared_root = Path(prepared_root) if prepared_root is not None else repository_root / "data/prepared"
    hawor_root = Path(hawor_root) if hawor_root is not None else repository_root / "external/HaWoR"
    run_directory = new_run_directory(output_root)
    manifest_path = run_directory / "run_manifest.json"
    snapshot = request.to_dict() if request is not None else {"prepared_metadata": str(Path(prepared_metadata).resolve())}
    manifest = new_manifest(run_directory, snapshot, repository_root)
    manifest["source"] = snapshot.get("source")
    manifest["stages"] = [stage_record(name) for name in ("preparation", "inference", "export", "visualization", "validation")]
    start = time.monotonic()
    current_stage = None
    clip_directory = None
    monitor = ResourceMonitor(sample_interval_s)
    write_json(manifest_path, manifest)

    def stage(name, operation):
        nonlocal current_stage
        current_stage = next(item for item in manifest["stages"] if item["name"] == name)
        current_stage.update(status="running", started_at=utc_now())
        print(f"Run {run_directory.name}: {name}", flush=True)
        write_json(manifest_path, manifest, overwrite=True)
        stage_start = time.monotonic()
        try:
            result = operation()
        except (Exception, KeyboardInterrupt) as error:
            current_stage.update(status="failed", error=redact(str(error)), finished_at=utc_now(),
                                 wall_time_s=time.monotonic() - stage_start)
            print(f"{name}: failed after {current_stage['wall_time_s']:.3f} s", flush=True)
            raise
        current_stage.update(status="completed", finished_at=utc_now(), wall_time_s=time.monotonic() - stage_start)
        print(f"{name}: completed in {current_stage['wall_time_s']:.3f} s", flush=True)
        return result

    try:
        monitor.start()
        # Lazy imports keep an allocated run reportable if a stage dependency fails.
        def prepare():
            from .video_preparation import load_prepared_clip, prepare_clip
            if prepared_metadata is not None:
                return load_prepared_clip(Path(prepared_metadata), policy=preparation_policy)
            return prepare_clip(request, prepared_root, policy=preparation_policy)

        prepared = stage("preparation", prepare)
        manifest["request"] = prepared.metadata.request
        manifest["source"] = prepared.metadata.source
        manifest["clip_id"] = prepared.video_path.parent.name
        manifest["preparation"] = prepared.metadata.to_dict()
        manifest["artifacts"]["clip_metadata"] = artifact_record(prepared.metadata_path)
        manifest["artifacts"]["prepared_video"] = artifact_record(prepared.video_path)
        clip_directory = run_directory / "clips" / manifest["clip_id"]
        clip_directory.mkdir(parents=True)

        def infer():
            result = run_hawor(prepared, clip_directory / "native", hawor_root, sample_interval_s,
                               resource_monitor=monitor)
            manifest["inference"] = result
            manifest["commands"].append({"command": result["command"], "cwd": result["cwd"], "environment": result["environment"]})
            manifest["artifacts"]["inference_log"] = artifact_record(result["log"])
            if result["status"] != "completed":
                raise RuntimeError(f"HaWoR failed (exit {result['returncode']}); adapter error: {result.get('failure')}; missing artifacts: {result['missing_artifacts']}; see {result['log']}")
            return result

        inference = stage("inference", infer)
        native_directory = Path(inference["native_directory"])

        def export():
            from .world_export import export_world
            return export_world(native_directory, prepared, clip_directory,
                                upstream_stages_completed=inference["upstream_stages_completed"])

        exported = stage("export", export)
        for key in ("trajectory_world", "trajectory_metadata"):
            manifest["artifacts"][key] = artifact_record(exported[key])
        manifest["validation"]["trajectory"] = exported["validation"]

        def render():
            from .visualization import visualize
            return visualize(native_directory, prepared, Path(exported["trajectory_world"]), clip_directory, hawor_root)

        rendered = stage("visualization", render)
        for key in ("overlay", "trajectory_preview", "render_log"):
            if key in rendered:
                manifest["artifacts"][key] = artifact_record(rendered[key])
        manifest["validation"]["visualization"] = rendered.get("validation", {})

        def validate_artifacts():
            for name, evidence in manifest["artifacts"].items():
                if artifact_record(evidence["path"]) != evidence:
                    raise ValueError(f"Artifact changed during the run: {name}")
            return {"artifact_hashes_match": True,
                    "manual_review": "pending", "world_coordinates_transformed": False}

        manifest["validation"]["final"] = stage("validation", validate_artifacts)
        manifest["status"] = "completed"
    except (Exception, KeyboardInterrupt) as error:
        manifest["status"] = "failed"
        if current_stage is not None and current_stage["status"] != "failed":
            current_stage.update(status="failed", error=redact(str(error)), finished_at=utc_now())
        manifest["failure"] = {"stage": current_stage["name"] if current_stage else "initialization",
                               "type": type(error).__name__, "message": redact(str(error))}
        for item in manifest["stages"]:
            if item["status"] == "pending":
                item["status"] = "not_run"
    finally:
        manifest["resources"] = monitor.stop()
        manifest["resources"]["scope"] = "Whole pipeline: preparation, engine verification/inference, export, visualization, and validation"
        # Retain useful partial output on failure without calling it validated.
        if clip_directory is not None:
            for name, relative in (("inference_log", "native/console.log"),
                                   ("trajectory_world", "trajectory_world.npz"),
                                   ("trajectory_metadata", "trajectory_metadata.json"),
                                   ("overlay", "overlay.mp4"),
                                   ("trajectory_preview", "trajectory_preview.png"),
                                   ("render_log", "visualization.log")):
                path = clip_directory / relative
                if name not in manifest["artifacts"] and path.is_file():
                    try:
                        manifest["artifacts"][name] = artifact_record(path)
                    except OSError as error:
                        manifest["warnings"].append(f"Could not record partial {name}: {error}")
        manifest["finished_at"] = utc_now()
        manifest["wall_time_s"] = time.monotonic() - start
        utc_span = (datetime.fromisoformat(manifest["finished_at"].replace("Z", "+00:00"))
                    - datetime.fromisoformat(manifest["started_at"].replace("Z", "+00:00"))).total_seconds()
        manifest["timing"] = {
            "elapsed_clock": "time.monotonic (CLOCK_MONOTONIC)",
            "timestamp_clock": "UTC system realtime; subject to clock corrections",
            "utc_span_s": utc_span,
            "utc_minus_elapsed_s": utc_span - manifest["wall_time_s"],
            "scope_note": "UTC start precedes environment capture; elapsed timing starts afterward. UTC clock corrections do not alter measured elapsed durations.",
        }
        write_json(manifest_path, redact(manifest), overwrite=True)
        print(f"Total pipeline time: {manifest['wall_time_s']:.3f} s ({manifest['status']}; "
              "includes validation and bookkeeping)", flush=True)
    return RunResult(run_directory, manifest_path, manifest["status"])
