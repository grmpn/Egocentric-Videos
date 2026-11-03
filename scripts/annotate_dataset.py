"""Generate plans and subtasks for later review using the official lerobot-annotate CLI."""

import argparse
import json
import os
from pathlib import Path
import sys

# Keep the dataset runtime isolated when invoked from an active HaWoR shell.
if __name__ == "__main__" and os.environ.get("LD_LIBRARY_PATH"):
    clean_environment = dict(os.environ)
    clean_environment.pop("LD_LIBRARY_PATH")
    os.execve(sys.executable, [sys.executable, *sys.argv], clean_environment)

from egocentric_pipeline.annotations import annotate_dataset


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--model", required=True, help="Model ID served by the selected VLM endpoint")
    parser.add_argument("--api-base", default="http://localhost:8000/v1")
    parser.add_argument("--episodes", type=int, nargs="+", help="Default: all episodes without existing language annotations")
    args = parser.parse_args()
    result = annotate_dataset(args.dataset_root, model=args.model, api_base=args.api_base, episodes=args.episodes)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
