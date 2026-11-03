"""Open a saved workspace in a local browser with orbit/pan/zoom and layer controls."""

import argparse
from pathlib import Path

from egocentric_pipeline.workspace_visualization import view_workspace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace_directory", type=Path)
    parser.add_argument("--asset-root", type=Path, help="Override the asset location if the same pinned model was moved")
    parser.add_argument("--open-browser", action="store_true")
    args = parser.parse_args()
    viewer = view_workspace(args.workspace_directory, asset_root=args.asset_root, open_browser=args.open_browser)
    try:
        viewer.wait_until_close()
    finally:
        viewer.close()


if __name__ == "__main__":
    main()
