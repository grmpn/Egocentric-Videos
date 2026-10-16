"""Segment aligned motion, fit fixed robot bases, verify IK and annotate the video."""

import argparse
from pathlib import Path

from egocentric_pipeline.retargeting import retarget_trajectory
from egocentric_pipeline.run_metadata import read_json


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alignment-directory", type=Path, required=True)
    parser.add_argument("--workspace-directory", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True, help="New directory; existing outputs are preserved")
    parser.add_argument("--config", type=Path, default=root / "configs/trajectory_retargeting.json")
    parser.add_argument("--asset-root", type=Path, help="Override the location of the same pinned robot assets")
    args = parser.parse_args()
    report = retarget_trajectory(args.alignment_directory, args.workspace_directory, args.output_directory,
                                read_json(args.config), args.asset_root)
    print(f"Completed; demonstration accepted: {report['demo_accepted']}\nReview: {args.output_directory}/retargeting_report.json")
    return 0 if report["demo_accepted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
