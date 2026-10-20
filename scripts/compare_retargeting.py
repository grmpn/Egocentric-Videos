"""Compare three joint/base and workspace solves on identical heuristic regions."""

import argparse
from pathlib import Path

from egocentric_pipeline.retargeting_comparison import compare_retargeting
from egocentric_pipeline.run_metadata import read_json


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alignment-directory", type=Path, required=True)
    parser.add_argument("--workspace-directory", type=Path, required=True)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--joint-config", type=Path, default=root / "configs/joint_retargeting.json")
    parser.add_argument("--workspace-config", type=Path, default=root / "configs/trajectory_retargeting.json")
    parser.add_argument("--robot-config", type=Path, default=root / "configs/robot_workspace.json")
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    report = compare_retargeting(args.alignment_directory, args.workspace_directory, args.output_directory,
        read_json(args.joint_config), read_json(args.workspace_config), read_json(args.robot_config),
        args.asset_root, args.repeats)
    print(f"Solve times: {report['solve_time_s']}\nReview: {args.output_directory}/comparison_report.json")


if __name__ == "__main__":
    main()
