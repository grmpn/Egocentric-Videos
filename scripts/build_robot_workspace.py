"""Build and verify sampled left/right Purdue Alex workspaces in the base frame."""

import argparse
from pathlib import Path

from egocentric_pipeline.robot_workspace import build_workspace
from egocentric_pipeline.run_metadata import read_json


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path, default=root / "data/models/purdue-alex-assets")
    parser.add_argument("--config", type=Path, default=root / "configs/robot_workspace.json")
    parser.add_argument("--output-directory", type=Path, required=True, help="New directory; existing outputs are never overwritten")
    parser.add_argument("--samples-per-arm", type=int, help="Override the configured count, up to 10,000,000")
    args = parser.parse_args()
    settings = read_json(args.config)
    if args.samples_per_arm is not None:
        settings["samples_per_arm"] = args.samples_per_arm
    report = build_workspace(args.asset_root, args.output_directory, settings)
    print(f"Status: {report['status']}\nReview: {args.output_directory}/workspace_report.json")


if __name__ == "__main__":
    main()
