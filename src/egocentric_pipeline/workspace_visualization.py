"""Movable-camera review of saved FK clouds and actual 2 cm voxel cells."""

from pathlib import Path

import numpy as np

from .robot_workspace import HAND_ORDER, load_robot, verify_asset_source
from .run_metadata import read_json
from .workspace import WorkspaceGrid


def view_workspace(directory, *, asset_root=None, open_browser=False):
    """Serve a read-only robot/workspace scene using scikit-robot's Viser viewer.

    Point display can be reduced for responsiveness. Every occupied voxel is
    rendered as an instanced cube; source exports are never edited.
    """
    import trimesh
    from skrobot.viewers import ViserViewer

    directory = Path(directory)
    report = read_json(directory / "workspace_report.json")
    if report["status"] != "completed":
        raise ValueError("View a completed workspace run; inspect workspace_report.json")
    settings = report["settings"]
    grid = WorkspaceGrid.load(directory / "workspace_grid.npz")
    assets = Path(asset_root or report["asset_root"])
    robot = load_robot(verify_asset_source(assets, settings), settings["base_frame"])
    viewer = ViserViewer(draw_grid=False, enable_ik=False, enable_motion_planning=False)
    # This server extension is used in scikit-robot's reachability-map example.
    server = viewer._server
    server.scene.set_up_direction("+z")
    # Add individual links to keep the robot in its reference pose. Moving it
    # with joint sliders would visually misrepresent the saved workspace.
    for link in robot.link_list:
        viewer.add(link)
    server.scene.add_frame("/base", axes_length=.2, axes_radius=.004)
    server.scene.add_label("/base/label", settings["base_frame"], position=(0, 0, .05))
    server.gui.add_markdown("## Purdue Alex workspace\nBlue: left · Orange: right\n\nDrag to orbit · Right-drag to pan · Scroll to zoom\n\n"
                           f"Endpoints: {', '.join(settings.get('target_frames', settings['tool_frames']))}\n\n"
                           "Sampled position coverage; collisions and tool orientations are unchecked.")
    colors = [(60, 150, 245), (245, 145, 55)]
    box = trimesh.creation.box(extents=[grid.spacing_m] * 3)
    for hand, name in enumerate(HAND_ORDER):
        with np.load(directory / f"samples_{name}.npz", allow_pickle=False) as data:
            points = data["positions_base_m"]
        count = min(len(points), settings["viewer_max_points_per_arm"])
        chosen = np.linspace(0, len(points) - 1, count, dtype=int)
        point_handle = server.scene.add_point_cloud(f"/{name}/points", points=points[chosen].astype(np.float32),
                                                    colors=colors[hand], point_size=.002)
        indices = np.argwhere(grid.occupancy[hand])
        # Alternating brightness exposes the actual cube boundaries without
        # shrinking the cells or changing the underlying workspace geometry.
        brightness = np.where(indices.sum(axis=1) % 2 == 0, 1., .78)
        voxel_colors = np.asarray(colors[hand])[None] * brightness[:, None]
        voxel_handle = server.scene.add_batched_meshes_simple(
            f"/{name}/voxels", vertices=box.vertices.astype(np.float32), faces=box.faces.astype(np.uint32),
            batched_wxyzs=np.tile([1., 0, 0, 0], (len(indices), 1)).astype(np.float32),
            batched_positions=grid.centers(indices).astype(np.float32),
            batched_colors=voxel_colors.astype(np.uint8), visible=False, lod="off",
            cast_shadow=False, receive_shadow=False)
        with server.gui.add_folder(f"{name.title()} workspace"):
            server.gui.add_markdown(f"{len(points):,} FK samples · {len(indices):,} occupied voxels\n\nDisplaying {count:,} points; all occupied cells available.")
            for label, handle, visible in ((f"{name.title()} points", point_handle, True),
                                           (f"{name.title()} voxels", voxel_handle, False)):
                control = server.gui.add_checkbox(label, initial_value=visible)

                @control.on_update
                def toggle(event, target=handle):
                    target.visible = event.target.value
    center = grid.origin_m + grid.shape * grid.spacing_m / 2
    viewer.set_camera(angles=[np.pi / 3, 0, 3 * np.pi / 4], distance=3.5, center=center)
    viewer.show(open_browser=open_browser)
    return viewer
