"""Review saved fixed-base episodes and verified IK with camera and timeline controls."""

import argparse
from pathlib import Path

from egocentric_pipeline.retargeting_visualization import view_retargeting


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("retargeting_directory", type=Path)
    parser.add_argument("--asset-root", type=Path)
    parser.add_argument("--open-browser", action="store_true")
    args = parser.parse_args()
    viewer = view_retargeting(args.retargeting_directory, asset_root=args.asset_root, open_browser=args.open_browser)
    try:
        viewer.wait_until_close()
    finally:
        viewer.close()


if __name__ == "__main__":
    main()
