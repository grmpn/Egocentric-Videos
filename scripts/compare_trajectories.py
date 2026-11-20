#!/usr/bin/env python3
"""Controlled three-backend comparison; stages run in their own environments."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from egocentric_pipeline.run_metadata import read_json, utc_now, write_json


def prepare(settings, output):
    """Use the existing working MP4, preserving and checking every source timestamp."""
    output.mkdir(parents=True, exist_ok=True)
    if (output / "input.json").exists():
        if read_json(output / "settings.json") != settings:
            raise ValueError("Settings changed; choose a new output directory")
        return
    def probe(path):
        command = [str(ROOT / ".conda/envs/hawor/bin/ffprobe"), "-v", "error", "-select_streams", "v:0",
                   "-show_entries", "stream=width,height:frame=best_effort_timestamp_time", "-of", "json", path]
        return json.loads(subprocess.check_output(command))
    working, source = probe(settings["video"]), probe(settings["source_video"])
    times = [float(f["best_effort_timestamp_time"]) for f in working["frames"]]
    source_times = [float(f["best_effort_timestamp_time"]) for f in source["frames"]]
    if len(times) != settings["expected_frames"] or len(times) != len(source_times):
        raise ValueError("Source and working video frame counts differ")
    if any(abs((a - times[0]) - (b - source_times[0])) > 1e-5 for a, b in zip(times, source_times)):
        raise ValueError("Working video timestamp mapping differs from source")
    if any(abs((t - times[0]) - i / settings["fps"]) > 1e-5 for i, t in enumerate(times)):
        raise ValueError("Input must have the agreed uniform frame rate")
    (output / "input").mkdir()
    (output / "input/rgb.mp4").symlink_to(settings["video"])
    write_json(output / "settings.json", settings)
    write_json(output / "input.json", {**working["streams"][0], "frame_count": len(times),
               "frame_index": list(range(len(times))), "timestamp_s": [t - times[0] for t in times],
               "source_timestamp_s": source_times, "video": settings["video"], "source_video": settings["source_video"]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/experiments/trajectory_comparison.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage", choices=["prepare", "hands", "gravity", "hawor", "metric_depth", "lingbot", "amb3r", "scale", "evaluate", "all"], default="all")
    args = parser.parse_args()
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("OMP_NUM_THREADS", "4")
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    os.environ["PATH"] = str(ROOT / ".conda/envs/hawor/bin") + os.pathsep + os.environ["PATH"]
    settings = read_json(args.config)
    for key in list(settings):
        if key.endswith("_python"):
            # Resolving a venv's symlink selects its base interpreter and loses
            # the venv packages. Preserve the configured executable path.
            settings[key] = str((ROOT / settings[key]).absolute())
        elif key.endswith(("_root", "_checkpoint")) or key in ("video", "source_video"):
            settings[key] = str((ROOT / settings[key]).resolve())
    output = args.output.resolve()
    prepare(settings, output)
    if args.stage == "prepare":
        return
    if args.stage == "all":
        for stage in ("hands", "gravity", "hawor", "metric_depth", "lingbot", "amb3r", "scale", "evaluate"):
            state = output / f"{stage}_timing.json"
            if state.exists() and read_json(state)["status"] == "completed":
                print(f"Reuse completed {stage}", flush=True)
                continue
            python_key = "hawor_python" if stage in ("hands", "hawor", "metric_depth", "scale") else "amb3r_python" if stage == "amb3r" else "mapping_python"
            with (output / f"{stage}.log").open("x") as log:
                subprocess.run([settings[python_key], str(Path(__file__).resolve()), "--config", str(args.config.resolve()),
                                "--output", str(output), "--stage", stage], stdout=log, stderr=subprocess.STDOUT, check=True)
        return
    report_path = output / f"{args.stage}_timing.json"
    if report_path.exists():
        raise ValueError(f"Stage already attempted; preserve evidence before retrying: {report_path}")
    report = {"stage": args.stage, "status": "running", "started_at": utc_now(), "python": sys.executable}
    write_json(report_path, report)
    started = time.perf_counter()
    try:
        import torch
        cuda = torch.cuda.is_available()
        if not cuda and args.stage not in ("scale", "evaluate"):
            raise RuntimeError("GPU unavailable; run outside the restricted sandbox")
        torch.set_num_threads(4)
        torch.manual_seed(42)
        if cuda:
            torch.cuda.reset_peak_memory_stats()
            report["gpu"] = torch.cuda.get_device_name()
        backend = "hawor" if args.stage in ("hands", "hawor", "metric_depth", "scale") else args.stage
        if backend in ("hawor", "lingbot", "amb3r"):
            revision = subprocess.check_output(["git", "-C", settings[f"{backend}_root"], "rev-parse", "HEAD"], text=True).strip()
            from egocentric_pipeline.tracking.hawor_runner import HAWOR_REVISION
            expected = HAWOR_REVISION if backend == "hawor" else settings[f"{backend}_revision"]
            if revision != expected:
                raise ValueError(f"Unexpected {backend} revision: {revision}")
            report["upstream_revision"] = revision
        from egocentric_pipeline.tracking.comparison_inference import STAGES
        STAGES[args.stage](settings, output, report)
        if cuda:
            torch.cuda.synchronize()
            report.update(peak_gpu_allocated_bytes=torch.cuda.max_memory_allocated(),
                          peak_gpu_reserved_bytes=torch.cuda.max_memory_reserved())
        report["status"] = "completed"
    except BaseException as error:
        report.update(status="failed", error=str(error), traceback=traceback.format_exc())
        raise
    finally:
        report.update(wall_time_s=time.perf_counter() - started, finished_at=utc_now())
        write_json(report_path, report, overwrite=True)


if __name__ == "__main__":
    main()
