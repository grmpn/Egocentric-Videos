#!/usr/bin/env python3
"""Prepare and evaluate the TACO hand-trajectory benchmark."""

import argparse
import os
from pathlib import Path
import subprocess
import sys
import time

PROCESS_STARTED = time.monotonic()

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from egocentric_pipeline.datasets.taco import download_sequences, prepare_reference
from egocentric_pipeline.run_metadata import read_json, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/experiments/taco_benchmark.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage", choices=("download", "prepare", "inspect", "evaluate", "run"), required=True)
    parser.add_argument("--method", choices=("hawor", "stablehand", "handflow"))
    parser.add_argument("--sequence")
    args = parser.parse_args()
    settings = read_json(args.config)
    settings["source_root"] = str((ROOT / settings["source_root"]).resolve())
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    os.environ["PATH"] = str(ROOT / ".conda/envs/hawor/bin") + os.pathsep + os.environ["PATH"]
    if args.stage == "run":
        if not args.method or not args.sequence:
            parser.error("run requires --method and --sequence; launch one fresh process per trial")
        from egocentric_pipeline.tracking.hand_benchmark import run_method
        run_method(args.method, args.sequence, output, settings, ROOT, started=PROCESS_STARTED)
        return
    if args.stage == "download":
        report = download_sequences(settings["clips"], settings["source_root"], settings["dataset_revision"])
        write_json(output / "download.json", report)
        return
    if args.stage == "inspect":
        from egocentric_pipeline.visualization.hand_benchmark import reference_overlays
        clips = read_json(output / "clips.json")["clips"]
        if args.sequence:
            clips = [clip for clip in clips if clip["clip"]["sequence_id"] == args.sequence]
            if not clips:
                parser.error("Sequence is not part of the frozen benchmark")
        print(reference_overlays(clips, output, prediction_method=args.method))
        return
    if args.stage == "evaluate":
        from egocentric_pipeline.evaluation.hand_benchmark import evaluate_benchmark
        evaluate_benchmark(output, settings)
        print(output / "comparison.md")
        return
    taco_root = ROOT / "external/TACO-Instructions"
    revision = subprocess.check_output(["git", "-C", str(taco_root), "rev-parse", "HEAD"], text=True).strip()
    if revision != settings["taco_source_revision"]:
        raise ValueError("TACO loader revision differs from the configured reference")
    model_paths = [ROOT / "external/HaWoR/_DATA/data_left/mano_left/MANO_LEFT.pkl",
                   ROOT / "external/HaWoR/_DATA/data/mano/MANO_RIGHT.pkl"]
    clips = []
    for clip in settings["clips"]:
        info = prepare_reference(settings, clip, output / "prepared", output / "reference", taco_root, model_paths)
        clips.append(info)
        print(f"Prepared {clip['sequence_id']}: {info['frame_count']} frames; {info['camera_motion']}", flush=True)
    write_json(output / "settings.json", settings)
    write_json(output / "clips.json", {"clips": clips, "plot_sequence_id": settings["plot_sequence_id"]})


if __name__ == "__main__":
    main()
