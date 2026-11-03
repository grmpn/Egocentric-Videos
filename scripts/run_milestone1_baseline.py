"""Run exactly one Milestone 1 clip and automatically report that attempt."""

import argparse
from pathlib import Path

from egocentric_pipeline.benchmark import FAILURE_LABELS, ROLES, build_benchmark
from egocentric_pipeline.clip_request import add_request_arguments, request_from_arguments
from egocentric_pipeline.pipeline import run_clip
from egocentric_pipeline.run_metadata import read_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--example", action="store_true", help="Use the bundled HaWoR example")
    source.add_argument("--video", type=Path)
    source.add_argument("--prepared", type=Path, help="Existing clip_metadata.json")
    add_request_arguments(parser)
    parser.add_argument("--role", choices=ROLES, help="Default: setup_smoke for the example; ego4d for that dataset; otherwise other_test")
    parser.add_argument("--output-root", type=Path,
                        default=Path(__file__).resolve().parents[1] / "outputs/hawor/milestone-1")
    parser.add_argument("--prepared-root", type=Path)
    parser.add_argument("--hawor-root", type=Path)
    parser.add_argument("--sample-interval-s", type=float, default=0.5)
    parser.add_argument("--review-status", choices=("pending", "complete", "not_possible"), default="pending")
    parser.add_argument("--failure-label", choices=FAILURE_LABELS, action="append", default=[])
    parser.add_argument("--review-notes", default="")
    args = parser.parse_args()
    if args.prepared and any(getattr(args, field) is not None for field in (
        "start_s", "end_s", "clip_id", "dataset", "video_id", "task_label", "license_reference", "focal_length_px")):
        parser.error("Existing prepared metadata owns clip intent; omit new-video request options")
    if args.example:
        root = args.hawor_root or Path(__file__).resolve().parents[1] / "external/HaWoR"
        args.video = root / "example/video_0.mp4"
        if args.dataset not in (None, "hawor_bundled") or args.video_id not in (None, "video_0"):
            parser.error("The bundled example has fixed hawor_bundled/video_0 source identity")
        args.dataset, args.video_id = "hawor_bundled", "video_0"
    try:
        request = None if args.prepared else request_from_arguments(args, constructor="milestone1_baseline")
        result = run_clip(request, prepared_metadata=args.prepared, output_root=args.output_root,
                          prepared_root=args.prepared_root, hawor_root=args.hawor_root,
                          sample_interval_s=args.sample_interval_s)
    except (TypeError, ValueError) as error:
        parser.error(str(error))
    manifest = read_json(result.manifest_path)
    dataset = (manifest.get("source") or manifest.get("request", {}).get("source") or {}).get("dataset")
    role = args.role or ("setup_smoke" if args.example or dataset == "hawor_bundled" else "ego4d" if dataset == "ego4d" else "other_test")
    report = build_benchmark(result.manifest_path, role, review_status=args.review_status,
                             failure_labels=args.failure_label, notes=args.review_notes)
    print(f"Run directory: {result.run_directory}")
    print(f"Status: {result.status}")
    print(f"Benchmark: {report['report']}")
    return 0 if result.status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
