"""Review original MANO hands and directly mapped grippers; no arm IK."""

import argparse
from pathlib import Path

from egocentric_pipeline.gripper_visualization import GripperMappingViewer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mapping_directory", type=Path)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--asset-root", type=Path)
    parser.add_argument("--mano-models", nargs=2, type=Path, metavar=("LEFT", "RIGHT"))
    parser.add_argument("--open-browser", action="store_true")
    args = parser.parse_args()
    viewer = GripperMappingViewer(args.mapping_directory, port=args.port, asset_root=args.asset_root, mano_models=args.mano_models)
    try:
        viewer.run(open_browser=args.open_browser)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
