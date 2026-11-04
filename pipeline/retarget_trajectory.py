"""Jointly fit each retained region's base and poses, then refine with fixed bases."""

import argparse
from pathlib import Path

from egocentric_pipeline.retargeting.joint_retargeting import joint_retarget_trajectory
from egocentric_pipeline.run_metadata import read_json


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alignment-directory', type=Path, required=True)
    parser.add_argument('--gripper-mapping-directory', type=Path, required=True)
    parser.add_argument('--regions', type=Path, help='Saved full-video candidate-region proposal')
    parser.add_argument('--output-directory', type=Path, required=True)
    parser.add_argument('--config', type=Path, default=root / 'configs/defaults/retargeting.json')
    parser.add_argument('--robot-config', type=Path, default=root / 'configs/defaults/robot_workspace.json')
    parser.add_argument('--asset-root', type=Path, default=root / 'data/models/purdue-alex-assets')
    parser.add_argument('--solver-backend', choices=('cpu', 'cuda'))
    args = parser.parse_args()
    settings = read_json(args.config)
    if args.solver_backend:
        settings['solver_backend'] = args.solver_backend
    report = joint_retarget_trajectory(args.alignment_directory, args.output_directory,
        settings, read_json(args.robot_config), args.asset_root,
        mapping_directory=args.gripper_mapping_directory, region_proposal_path=args.regions)
    print(f"Completed; pose demonstration acceptance: {report['demo_accepted']}")
    print(f"Review: {args.output_directory}/retargeting_report.json")
    # Completed fitting with failed feasibility remains exportable evidence.
    # Exceptions and interrupted/incomplete stages still propagate a failure.


if __name__ == '__main__':
    main()
