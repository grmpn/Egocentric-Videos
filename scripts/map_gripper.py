"""Map original MANO hands to detached gripper poses/opening, without arm IK."""

import argparse
from pathlib import Path

from egocentric_pipeline.gripper_mapping import prepare_gripper_mapping
from egocentric_pipeline.run_metadata import read_json


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alignment-directory", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True, help="New directory")
    parser.add_argument("--asset-root", type=Path, default=root / "data/models/purdue-alex-assets")
    parser.add_argument("--config", type=Path, default=root / "configs/gripper_mapping.json")
    parser.add_argument("--robot-config", type=Path, default=root / "configs/robot_workspace.json")
    parser.add_argument("--frame-start", type=int, default=0)
    parser.add_argument("--frame-stop", type=int, required=True, help="Exclusive source frame index")
    parser.add_argument("--mano-models", nargs=2, type=Path, metavar=("LEFT", "RIGHT"))
    args = parser.parse_args()
    report = prepare_gripper_mapping(args.alignment_directory, args.output_directory, read_json(args.config),
        read_json(args.robot_config), args.asset_root, args.frame_start, args.frame_stop, args.mano_models)
    print(f"Saved direct mapping: {args.output_directory}\n{report['summary']}")


if __name__ == "__main__":
    main()
