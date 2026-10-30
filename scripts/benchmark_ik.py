"""Run one preserved IK experiment and update the common 100-point scoreboard."""

import argparse
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import re
import traceback

from egocentric_pipeline.gripper_mapping import load_mapping
from egocentric_pipeline.ik_benchmark import evaluate_run, update_report, validate_settings as validate_benchmark_settings
from egocentric_pipeline.joint_retargeting import joint_retarget_trajectory, validate_settings
from egocentric_pipeline.run_metadata import read_json, utc_now, write_json


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--mapping-directory", type=Path, required=True)
    parser.add_argument("--benchmark-directory", type=Path, default=root / "outputs/ik-benchmark")
    parser.add_argument("--benchmark-config", type=Path, default=root / "configs/ik_benchmark.json")
    parser.add_argument("--run-id", required=True, help="Unique directory name; existing experiments are preserved")
    parser.add_argument("--name", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--skip-video", action="store_true",
                        help="Skip annotated video export during tuning; preserve trajectory and interactive viewer inputs")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", args.run_id):
        parser.error("run-id must be an ordinary directory name containing letters, digits, hyphens or underscores")
    settings, benchmark = read_json(args.config), read_json(args.benchmark_config)
    validate_settings(settings)
    validate_benchmark_settings(benchmark)
    for key in ("hand_position_window_s", "hand_orientation_window_s", "hand_filter_polyorder"):
        if settings.get(key) != benchmark[key]:
            parser.error(f"IK and benchmark must share {key}")
    if min(benchmark["hand_position_window_s"], benchmark["hand_orientation_window_s"]) <= 0:
        parser.error("This benchmark requires smoothed position and orientation targets")
    _, mapping_report = load_mapping(args.mapping_directory)
    output = args.benchmark_directory.resolve()
    output.mkdir(parents=True, exist_ok=True)
    common = output / "benchmark_settings.json"
    if common.exists() and read_json(common) != benchmark:
        parser.error("Benchmark settings changed; use a new benchmark directory")
    if not common.exists():
        write_json(common, benchmark)
    run = output / args.run_id
    run.mkdir(exist_ok=False)
    write_json(run / "config.json", settings)
    write_json(run / "mapping_report.json", mapping_report)
    experiment = {"name": args.name, "description": args.description, "status": "running", "started_at": utc_now(),
                  "mapping_directory": str(args.mapping_directory.resolve()),
                  "render_video": not args.skip_video}
    write_json(run / "experiment.json", experiment)
    update_report(output)
    print(f"Running {args.name}; log: {run / 'run.log'}", flush=True)
    try:
        with (run / "run.log").open("x", buffering=1) as log, redirect_stdout(log), redirect_stderr(log):
            try:
                joint_retarget_trajectory(mapping_report["alignment_directory"], run / "trajectory", settings,
                    mapping_report["robot_settings"], mapping_report["asset_root"],
                    mapping_directory=args.mapping_directory, render_video=not args.skip_video,
                    region_limit=benchmark.get("region_limit"), selection=benchmark.get("selection"))
                score = evaluate_run(run, args.mapping_directory, benchmark, args.name, args.description)
            except (Exception, KeyboardInterrupt):
                traceback.print_exc()
                raise
        experiment["status"] = "completed"
        print(f"Completed {args.name}: {score['score']} /100. Report: {output / 'REPORT.md'}", flush=True)
    except (Exception, KeyboardInterrupt) as error:
        experiment.update(status="failed", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        experiment["finished_at"] = utc_now()
        write_json(run / "experiment.json", experiment, overwrite=True)
        update_report(output)


if __name__ == "__main__":
    main()
