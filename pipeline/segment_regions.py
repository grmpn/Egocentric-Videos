"""Save full-video candidate manipulation regions; this does not certify IK feasibility."""

import argparse
from pathlib import Path

from egocentric_pipeline.retargeting.manipulation_regions import camera_segments, retained_regions, SEGMENTATION_SETTINGS
from egocentric_pipeline.retargeting.trajectory import load_alignment
from egocentric_pipeline.run_metadata import read_json, write_json


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alignment-directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--config', type=Path, default=root / 'configs/defaults/retargeting.json')
    args = parser.parse_args()
    settings = read_json(args.config)
    arrays, alignment, _ = load_alignment(args.alignment_directory)
    _, seeds = camera_segments(arrays['camera_position_aligned_m'], arrays['timestamp_s'], settings)
    regions = retained_regions(seeds, arrays['timestamp_s'], settings['merge_adjacent_regions'])
    write_json(args.output, {'schema_version': 1, 'source_run_id': alignment['source_run_id'],
        'timestamp_s': arrays['timestamp_s'].tolist(), 'source_timestamp_s': arrays['source_timestamp_s'].tolist(),
        'settings': {k: settings[k] for k in SEGMENTATION_SETTINGS}, 'seeds': seeds, 'regions': regions,
        'feasibility': 'candidate camera-motion intervals only; requires joint fitting and independent evaluation'})
    print(f'Saved {len(regions)} retained candidate regions: {args.output}')


if __name__ == '__main__':
    main()
