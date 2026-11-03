"""Align a completed HaWoR run to a shared Z-up frame without changing its inputs."""

import argparse
import os
from pathlib import Path
import sys


def main():
    # The modern Torch runtime must not inherit HaWoR's legacy CUDA libraries.
    if "LD_LIBRARY_PATH" in os.environ:
        environment = dict(os.environ)
        environment.pop("LD_LIBRARY_PATH")
        os.execve(sys.executable, [sys.executable, *sys.argv], environment)
    from egocentric_pipeline.gravity_pipeline import align_run
    from egocentric_pipeline.run_metadata import read_json

    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-manifest", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True, help="New directory; existing outputs are never overwritten")
    parser.add_argument("--config", type=Path, default=root / "configs/gravity_alignment.json")
    parser.add_argument("--checkpoint", type=Path, default=root / "data/models/geocalib/geocalib-pinhole-v1.0.tar")
    parser.add_argument("--hawor-root", type=Path, default=root / "external/HaWoR", help="Owns the existing licensed MANO model files")
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    args = parser.parse_args()
    try:
        report = align_run(args.run_manifest, args.output_directory, args.checkpoint, args.hawor_root,
                           read_json(args.config), device=args.device)
    except (Exception, KeyboardInterrupt) as error:
        print(f"Gravity alignment failed: {error}\nInspect {args.output_directory}/alignment_report.json if allocated.", file=sys.stderr)
        return 1
    print(f"Status: {report['status']}\nReview: {args.output_directory}/alignment_report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
