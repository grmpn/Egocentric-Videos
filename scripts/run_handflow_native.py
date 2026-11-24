#!/usr/bin/env python3
"""Internal isolated-environment worker for benchmark_hands.py."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from egocentric_pipeline.tracking.handflow_runner import run_native

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--intrinsics", type=float, nargs=4, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--frame-count", type=int, required=True)
    args = parser.parse_args()
    run_native(args.video, args.intrinsics, args.output, ROOT, args.seed, args.frame_count)
