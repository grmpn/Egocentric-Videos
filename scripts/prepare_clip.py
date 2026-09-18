"""Prepare one local MP4 without a per-clip configuration file."""

import argparse
from pathlib import Path

from egocentric_pipeline.clip_request import add_request_arguments, request_from_arguments
from egocentric_pipeline.video_preparation import prepare_clip


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--prepared-root", type=Path, default=Path("data/prepared"))
    add_request_arguments(parser)
    args = parser.parse_args()
    try:
        prepared = prepare_clip(request_from_arguments(args), prepared_root=args.prepared_root)
    except (ValueError, OSError, RuntimeError) as error:
        parser.exit(1, f"Preparation failed: {error}\n")
    print(prepared.metadata_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
