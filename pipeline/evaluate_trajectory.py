"""Evaluate tracking, robot limits and discrete self-collision for every retained region."""

import argparse
from pathlib import Path

from egocentric_pipeline.evaluation.ik_benchmark import evaluate_run
from egocentric_pipeline.run_metadata import read_json


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trajectory-directory', type=Path, required=True)
    parser.add_argument('--mapping-directory', type=Path, required=True)
    parser.add_argument('--config', type=Path, default=root / 'configs/defaults/evaluation.json')
    args = parser.parse_args()
    output = args.trajectory_directory.parent
    if any((output / name).exists() for name in ('score.json', 'benchmark_frame_metrics.npz')):
        parser.error('Evaluation already exists; preserve it or evaluate a new run directory')
    settings = read_json(args.config)
    if settings.get('selection') is not None or settings.get('region_limit') is not None:
        parser.error('Pipeline evaluation must cover every retained region; benchmark selections belong in scripts/benchmark_ik.py')
    result = evaluate_run(output, args.mapping_directory, settings, 'Full-video trajectory',
                          'All retained regions; failures retained as dataset validity and diagnostics',
                          trajectory_directory=args.trajectory_directory, compare=False)
    print(f"Completed evaluation: {result['score']} / 100; {len(result['collision_frames'])} collision frames")
    print(f'Review: {output}/score.json')


if __name__ == '__main__':
    main()
