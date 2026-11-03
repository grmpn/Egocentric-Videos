"""Create/append a local LeRobot v3.1 episode from an MP4 or completed HaWoR run."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

# Legacy libtorch on LD_LIBRARY_PATH can segfault modern Torch before Python
# can report an error. Re-exec the dataset CLI cleanly; configure only its HaWoR
# subprocess below. The environments and installed libraries stay unchanged.
if __name__ == "__main__" and os.environ.get("LD_LIBRARY_PATH"):
    clean_environment = dict(os.environ)
    clean_environment.pop("LD_LIBRARY_PATH")
    os.execve(sys.executable, [sys.executable, *sys.argv], clean_environment)

from egocentric_pipeline.benchmark import build_benchmark
from egocentric_pipeline.clip_request import ClipRequest
from egocentric_pipeline.lerobot_export import append_run
from egocentric_pipeline.run_metadata import new_run_directory, read_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--video", type=Path)
    source.add_argument("--run-manifest", type=Path, help="Reuse a completed run without rerunning inference")
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--repo-id", default="local/egocentric-pilot")
    parser.add_argument("--source-metadata", type=Path, help="JSON recording source revision, attribution, camera evidence, etc.")
    parser.add_argument("--hawor-python", type=Path, help="Python in the existing HaWoR environment; required with --video")
    parser.add_argument("--start-s", type=float)
    parser.add_argument("--end-s", type=float)
    parser.add_argument("--focal-length-px", type=float)
    parser.add_argument("--source-dataset")
    parser.add_argument("--video-id")
    parser.add_argument("--license-reference")
    parser.add_argument("--output-root", type=Path, default=Path("outputs/hawor/milestone-2"))
    args = parser.parse_args()
    try:
        extra = read_json(args.source_metadata) if args.source_metadata else None
        if args.video:
            if not args.hawor_python:
                parser.error("--video requires --hawor-python pointing to the separate HaWoR environment")
            if (args.start_s is None) != (args.end_s is None):
                parser.error("Supply --start-s and --end-s together")
            interval = None if args.start_s is None else (args.start_s, args.end_s)
            ClipRequest.from_video(args.video, interval=interval, task_label=args.task,
                                   focal_length_px=args.focal_length_px)
            root = Path(__file__).resolve().parents[1]
            attempt = new_run_directory(args.output_root)
            command = [str(args.hawor_python.expanduser().absolute()), str(root / "scripts/run_hawor_pipeline.py"),
                       "--video", str(args.video.resolve()), "--task-label", args.task,
                       "--output-root", str(attempt)]
            for option, value in (("start-s", args.start_s), ("end-s", args.end_s),
                                  ("focal-length-px", args.focal_length_px), ("dataset", args.source_dataset),
                                  ("video-id", args.video_id), ("license-reference", args.license_reference)):
                if value is not None:
                    command += [f"--{option}", str(value)]
            environment = {**os.environ, "PYTHONPATH": str(root / "src"), "PYTHONUNBUFFERED": "1"}
            prefix = args.hawor_python.expanduser().absolute().parent.parent
            # Conda can expose python3.10 through a python3.1 compatibility symlink.
            torch_libraries = sorted({path.resolve() for path in prefix.glob("lib/python*/site-packages/torch/lib")})
            if len(torch_libraries) != 1:
                raise ValueError("--hawor-python must point to the installed HaWoR environment's interpreter")
            environment["PATH"] = str(prefix / "bin") + os.pathsep + environment.get("PATH", "")
            environment["LD_LIBRARY_PATH"] = os.pathsep.join([
                "/usr/lib/wsl/lib", "/usr/local/cuda-11.7/lib64",
                str(prefix / "lib"), str(torch_libraries[0])])
            result = subprocess.run(command, env=environment, cwd=root)
            manifests = list(attempt.glob("*/run_manifest.json"))
            if len(manifests) != 1:
                raise RuntimeError(f"HaWoR did not produce one manifest; inspect {attempt}")
            args.run_manifest = manifests[0]
            build_benchmark(args.run_manifest, "other_test")
            if result.returncode:
                raise RuntimeError(f"HaWoR failed; dataset unchanged. Inspect {args.run_manifest}")
        elif any(v is not None for v in (args.start_s, args.end_s, args.focal_length_px,
                                          args.source_dataset, args.video_id, args.license_reference, args.hawor_python)):
            parser.error("--run-manifest uses the saved run's source/camera settings; omit video execution options")
        print(json.dumps(append_run(args.run_manifest, args.dataset_root, task=args.task,
                                    repo_id=args.repo_id, source_metadata=extra), indent=2))
    except (ValueError, FileNotFoundError, RuntimeError) as error:
        print(f"Dataset addition failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
