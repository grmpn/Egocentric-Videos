"""Run one local MP4 or verified prepared clip through the reusable pipeline."""

import argparse
from pathlib import Path

from egocentric_pipeline.clip_request import add_request_arguments, request_from_arguments
from egocentric_pipeline.pipeline import run_clip


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--video", type=Path)
    source.add_argument("--prepared", type=Path, help="Existing clip_metadata.json")
    add_request_arguments(parser)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--prepared-root", type=Path)
    parser.add_argument("--hawor-root", type=Path)
    parser.add_argument("--sample-interval-s", type=float, default=0.5)
    args = parser.parse_args()
    if args.prepared and any(getattr(args, field) is not None for field in (
        "start_s", "end_s", "clip_id", "dataset", "video_id", "task_label", "license_reference", "focal_length_px")):
        parser.error("Existing prepared metadata owns clip intent; omit new-video request options")
    try:
        request = None if args.prepared else request_from_arguments(args)
        result = run_clip(request, prepared_metadata=args.prepared, output_root=args.output_root,
                          prepared_root=args.prepared_root, hawor_root=args.hawor_root,
                          sample_interval_s=args.sample_interval_s)
    except (TypeError, ValueError) as error:
        parser.error(str(error))
    print(f"Run directory: {result.run_directory}")
    print(f"Status: {result.status}")
    return 0 if result.status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
