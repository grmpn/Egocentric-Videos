"""Segment aligned motion, fit fixed robot bases, verify IK and annotate the video."""

import argparse
from pathlib import Path

from egocentric_pipeline.retargeting import retarget_trajectory
from egocentric_pipeline.run_metadata import read_json


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alignment-directory", type=Path, required=True)
    parser.add_argument("--method", choices=("workspace", "joint"), default="workspace")
    parser.add_argument("--workspace-directory", type=Path, help="Required for the workspace baseline")
    parser.add_argument("--output-directory", type=Path, required=True, help="New directory; existing outputs are preserved")
    parser.add_argument("--config", type=Path, help="Defaults to the selected method's configuration")
    parser.add_argument("--robot-config", type=Path, default=root / "configs/robot_workspace.json")
    parser.add_argument("--regions-only", action="store_true", help="Baseline comparison on unexpanded heuristic regions")
    parser.add_argument("--asset-root", type=Path, help="Override the location of the same pinned robot assets")
    args = parser.parse_args()
    if args.method == "joint":
        from egocentric_pipeline.joint_retargeting import joint_retarget_trajectory
        if args.asset_root is None:
            parser.error("--asset-root is required for joint fitting")
        report = joint_retarget_trajectory(args.alignment_directory, args.output_directory,
            read_json(args.config or root / "configs/joint_retargeting.json"),
            read_json(args.robot_config), args.asset_root)
    else:
        if args.workspace_directory is None:
            parser.error("--workspace-directory is required for workspace fitting")
        report = retarget_trajectory(args.alignment_directory, args.workspace_directory, args.output_directory,
            read_json(args.config or root / "configs/trajectory_retargeting.json"), args.asset_root,
            regions_only=args.regions_only)
    print(f"Completed; demonstration accepted: {report['demo_accepted']}\nReview: {args.output_directory}/retargeting_report.json")
    return 0 if report["demo_accepted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
