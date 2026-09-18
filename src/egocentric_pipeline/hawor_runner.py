"""Run the pinned, unchanged HaWoR demo in an isolated per-clip workspace."""

import math
import os
from pathlib import Path
import queue
import shutil
import signal
import subprocess
import sys
import threading
import time

from .run_metadata import ResourceMonitor, artifact_record, redact, stage_record, utc_now


HAWOR_REVISION = "66c7d4108d58a716deccd192cb7645170cdc7bd7"
WEIGHTS = (
    "weights/external/droid.pth", "weights/external/detector.pt",
    "weights/hawor/checkpoints/hawor.ckpt", "weights/hawor/checkpoints/infiller.pt",
    "weights/hawor/model_config.yaml",
    "thirdparty/Metric3D/weights/metric_depth_vit_large_800k.pth",
)
MANO = ("_DATA/data/mano/MANO_RIGHT.pkl", "_DATA/data_left/mano_left/MANO_LEFT.pkl")


def inspect_engine(hawor_root):
    hawor_root = Path(hawor_root).resolve()
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=hawor_root,
                              check=True, capture_output=True, text=True).stdout.strip()
    if revision != HAWOR_REVISION:
        raise ValueError(f"HaWoR must be pinned to {HAWOR_REVISION}; found {revision}")
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"],
                           cwd=hawor_root, check=True, capture_output=True, text=True).stdout
    if dirty.strip():
        raise ValueError("HaWoR source has tracked changes; restore or review them before running the unchanged baseline")
    nested = subprocess.run(["git", "submodule", "status", "--recursive"], cwd=hawor_root,
                            check=True, capture_output=True, text=True).stdout
    if len(nested.splitlines()) < 3 or any(line.startswith(("-", "+", "U")) for line in nested.splitlines()):
        raise ValueError("Initialize HaWoR's pinned nested submodules with git submodule update --init --recursive")
    return {"revision": revision, "nested_submodules": nested.splitlines(),
            "assets": {relative: artifact_record(hawor_root / relative) for relative in WEIGHTS + MANO}}


def run_hawor(prepared, native_root, hawor_root, sample_interval_s=0.5, *, resource_monitor=None):
    """Return native artifacts and execution evidence, including failed processes.

    RAM is sampled summed RSS of the process tree (shared pages may be counted
    more than once). GPU memory samples are device-wide, not process-exclusive;
    WSL does not consistently expose per-process GPU accounting.
    """
    if not math.isfinite(sample_interval_s) or sample_interval_s <= 0:
        raise ValueError("Resource sampling interval must be positive")
    from .video_preparation import load_prepared_clip

    native_root = Path(native_root).resolve()
    native_root.mkdir(parents=True, exist_ok=False)
    staged = native_root / "rgb.mp4"
    native_directory = native_root / "rgb"
    log_path = native_root / "console.log"
    focal = prepared.metadata.hawor_camera["focal_length_px"]
    command = [sys.executable, "demo.py", "--video_path", str(staged),
               "--img_focal", str(focal), "--vis_mode", "none"]
    environment = os.environ.copy()
    environment["PYTHONUNBUFFERED"] = "1"
    if Path("/usr/lib/wsl/lib").is_dir():
        environment["LD_LIBRARY_PATH"] = "/usr/lib/wsl/lib:" + environment.get("LD_LIBRARY_PATH", "")
    stages = [stage_record(name) for name in (
        "initialization", "detection_tracking", "hand_estimation", "slam_metric_scale", "infilling")]
    current_stage = 0
    stages[0].update(status="running", started_at=utc_now())
    stage_started = started = time.monotonic()
    engine = None
    failure = None
    monitor = resource_monitor or ResourceMonitor(sample_interval_s)
    process = None
    returncode = None
    lines = queue.Queue()

    def read_output(stream):
        try:
            for line in stream:
                lines.put(line)
        finally:
            stream.close()
            lines.put(None)

    with log_path.open("x", encoding="utf-8") as log:
        try:
            if resource_monitor is None:
                monitor.start()
            verified = load_prepared_clip(prepared.metadata_path)
            if (verified.metadata.to_dict() != prepared.metadata.to_dict()
                    or verified.video_path.resolve() != prepared.video_path.resolve()):
                raise ValueError("PreparedClip differs from its verified persisted metadata; reload it before inference")
            engine = inspect_engine(hawor_root)
            shutil.copyfile(verified.video_path, staged)
            if artifact_record(staged)["sha256"] != verified.metadata.prepared["sha256"]:
                raise ValueError("Staged video differs from the verified prepared clip")
            process = subprocess.Popen(command, cwd=hawor_root, env=environment,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, errors="replace", bufsize=1, start_new_session=True)
            reader = threading.Thread(target=read_output, args=(process.stdout,), daemon=True)
            reader.start()
            output_done = False
            while not output_done or process.poll() is None:
                try:
                    line = lines.get(timeout=min(sample_interval_s, 0.1))
                    if line is None:
                        output_done = True
                    else:
                        output = redact(line)
                        log.write(output)
                        log.flush()
                        print(output, end="", flush=True)
                        marker = None
                        for phrase, index in (("Running detect_track on", 1), ("Running hawor on", 2),
                                              ("Running slam on", 3), ("run infiller on", 4)):
                            if phrase in line:
                                marker = index
                                break
                        if marker is not None and marker > current_stage:
                            now = time.monotonic()
                            stages[current_stage].update(status="completed", finished_at=utc_now(),
                                                         wall_time_s=now - stage_started)
                            current_stage = marker
                            stages[current_stage].update(status="running", started_at=utc_now())
                            stage_started = now
                except queue.Empty:
                    pass
            returncode = process.wait()
            reader.join(timeout=2)
        except (Exception, KeyboardInterrupt) as error:
            failure = {"type": type(error).__name__, "message": redact(str(error))}
            output = f"\nAdapter failure: {failure['type']}: {failure['message']}\n"
            log.write(output)
            log.flush()
            print(output, end="", flush=True)
            if process is not None and process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
            returncode = process.returncode if process is not None else None
        finally:
            resources = monitor.stop() if resource_monitor is None else {"scope": "Shared whole-pipeline monitor; see run_manifest.resources"}
    stages[current_stage].update(status="completed" if returncode == 0 and failure is None else "failed", finished_at=utc_now(),
                                 wall_time_s=time.monotonic() - stage_started,
                                 error=failure["message"] if failure else None if returncode == 0 else f"HaWoR exited with status {returncode}; see {log_path}")
    for stage in stages:
        if stage["status"] == "pending":
            stage["status"] = "not_run"
    count = prepared.metadata.prepared["frame_count"]
    required = {
        "tracks": native_directory / f"tracks_0_{count}/model_tracks.npy",
        "chunks": native_directory / f"tracks_0_{count}/frame_chunks_all.npy",
        "masks": native_directory / f"tracks_0_{count}/model_masks.npy",
        "slam": native_directory / f"SLAM/hawor_slam_w_scale_0_{count}.npz",
        "world": native_directory / "world_space_res.pth",
    }
    missing = [str(path) for path in required.values() if not path.is_file()]
    completed = failure is None and returncode == 0 and not missing and all(stage["status"] == "completed" for stage in stages)
    return {"status": "completed" if completed else "failed", "returncode": returncode,
            "native_directory": str(native_directory), "log": str(log_path), "command": redact(command),
            "cwd": str(Path(hawor_root).resolve()), "engine": engine,
            "environment": {"PYTHONUNBUFFERED": "1", "LD_LIBRARY_PATH": environment.get("LD_LIBRARY_PATH")},
            "stages": stages, "wall_time_s": time.monotonic() - started, "missing_artifacts": missing,
            "upstream_stages_completed": completed, "failure": failure,
            "artifacts": {name: artifact_record(path) for name, path in required.items() if path.is_file()},
            "resources": resources,
            "timing_method": "time.monotonic elapsed time between received upstream stdout stage markers; initialization overhead may be charged to the preceding stage"}
