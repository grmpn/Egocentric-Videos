"""Render a saved gripper mapping onto its synchronized source RGB video."""

import argparse
from pathlib import Path

from egocentric_pipeline.gripper_overlay import render_gripper_overlay


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mapping_directory", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="New .mp4 output path")
    parser.add_argument("--opacity", type=float, default=.7)
    args = parser.parse_args()
    print(render_gripper_overlay(args.mapping_directory, args.output, opacity=args.opacity))


if __name__ == "__main__":
    main()
