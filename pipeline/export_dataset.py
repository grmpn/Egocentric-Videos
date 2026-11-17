"""Create/append human reconstruction or region-based robot LeRobot datasets."""

import argparse
import json
from pathlib import Path

from egocentric_pipeline.datasets.lerobot_export import append_human_episode, append_robot_regions
from egocentric_pipeline.datasets.human_episode import materialize_human_alignment
from egocentric_pipeline.run_metadata import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='mode', required=True)
    human = commands.add_parser('human', help='Full-video human export, before robot processing')
    human.add_argument('--alignment-directory', type=Path, required=True)
    human.add_argument('--repo-id', default='local/egocentric-human')
    robot = commands.add_parser('robot', help='Export independently evaluated fixed-base regions')
    robot.add_argument('--human-dataset-root', type=Path, required=True)
    robot.add_argument('--source-episode-index', type=int, required=True)
    robot.add_argument('--trajectory-directory', type=Path, action='append', required=True)
    robot.add_argument('--evaluation-directory', type=Path, action='append')
    robot.add_argument('--min-episode-valid-ratio', type=float, default=.85,
                       help='Minimum fraction of finite solved, collision-free frames within all joint limits')
    robot.add_argument('--include-rejected-regions', action='store_true',
                       help='Test dataset only: export failed regions and record gate failures and overrides')
    robot.add_argument('--diagnostics', type=Path, required=True, help='Processing-run report, outside the dataset')
    robot.add_argument('--repo-id', default='local/egocentric-robot')
    restore = commands.add_parser('restore-human', help='Start new retargeting from a standalone human episode')
    restore.add_argument('--human-dataset-root', type=Path, required=True)
    restore.add_argument('--source-episode-index', type=int, required=True)
    restore.add_argument('--output-directory', type=Path, required=True)
    restore.add_argument('--mano-models', nargs=2, type=Path, required=True, metavar=('LEFT', 'RIGHT'))
    for command in (human, robot):
        command.add_argument('--dataset-root', type=Path, required=True)
        command.add_argument('--task', required=True)
        command.add_argument('--result', type=Path)
    args = parser.parse_args()
    if getattr(args, 'result', None) is not None and args.result.exists():
        parser.error('Result already exists; choose a new run path')
    if args.mode == 'human':
        result = append_human_episode(args.alignment_directory, args.dataset_root, task=args.task, repo_id=args.repo_id)
    elif args.mode == 'robot':
        result = append_robot_regions(args.human_dataset_root, args.source_episode_index, args.trajectory_directory,
            args.dataset_root, task=args.task, repo_id=args.repo_id, diagnostic_path=args.diagnostics,
            evaluation_directories=args.evaluation_directory, min_episode_valid_ratio=args.min_episode_valid_ratio,
            include_rejected_regions=args.include_rejected_regions)
    else:
        result = materialize_human_alignment(args.human_dataset_root, args.source_episode_index,
                                            args.output_directory, args.mano_models)
    if getattr(args, 'result', None) is not None:
        write_json(args.result, result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
