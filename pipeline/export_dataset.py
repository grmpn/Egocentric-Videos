"""Create/append one full-video robot episode using the official LeRobot writer."""

import argparse
import json
from pathlib import Path

from egocentric_pipeline.datasets.lerobot_export import append_robot_episode
from egocentric_pipeline.run_metadata import read_json, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-manifest", type=Path, required=True)
    parser.add_argument("--trajectory-directory", type=Path, required=True, action="append",
                        help="Completed evaluated trajectory; repeat only for disjoint regions of this same video")
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--repo-id", default="local/egocentric-pilot")
    parser.add_argument("--source-metadata", type=Path)
    parser.add_argument("--result", type=Path, help="Save the added episode index for downstream annotation")
    args = parser.parse_args()
    if args.result is not None and args.result.exists():
        parser.error(f"Result file already exists: {args.result}; choose a new path")
    result = append_robot_episode(args.run_manifest, args.trajectory_directory, args.dataset_root,
                                  task=args.task, repo_id=args.repo_id,
                                  source_metadata=read_json(args.source_metadata) if args.source_metadata else None)
    if args.result is not None:
        write_json(args.result, result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
