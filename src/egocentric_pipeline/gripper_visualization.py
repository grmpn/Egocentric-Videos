"""Interactive direct gripper review with source RGB and original MANO meshes."""

import copy
from pathlib import Path
import subprocess
import threading
import time
import webbrowser

import numpy as np
from scipy.spatial.transform import Rotation

from .gripper_mapping import (grasp_forward_segment, load_mapping, map_grasp_landmarks, reconstruct_grasp_geometry,
                              save_mapping, validate_settings)
from .gripper_model import load_grippers
from .run_metadata import utc_now


def review_rgb(report, frame_indices):
    """Decode exactly the selected source frames, downscaled only for display."""
    first, last = int(frame_indices[0]), int(frame_indices[-1])
    if not np.array_equal(frame_indices, np.arange(first, last + 1)):
        raise ValueError("Review requires a contiguous source frame interval")
    width = min(480, report["video_size"][0])
    height = round(report["video_size"][1] * width / report["video_size"][0])
    command = ["ffmpeg", "-v", "error", "-nostdin", "-i", report["prepared_video"],
               "-vf", f"select=between(n\\,{first}\\,{last}),scale={width}:{height}",
               "-vsync", "0", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.check_output(command)
    expected = len(frame_indices) * width * height * 3
    if len(raw) != expected:
        raise ValueError("Decoded RGB frame count differs from selected trajectory interval")
    return np.frombuffer(raw, np.uint8).reshape(len(frame_indices), height, width, 3)


class GripperMappingViewer:
    """One synchronized review session; tuning exports new directories only."""

    def __init__(self, directory, *, port=8080, asset_root=None, mano_models=None):
        import torch
        import viser

        torch.set_num_threads(4)
        self.directory = Path(directory).resolve()
        self.arrays, self.report = load_mapping(directory)
        self.settings = copy.deepcopy(self.report["settings"])
        self.exact_tips = self.settings.get("mapping_mode") == "fingertip_correspondence"
        self.mcp_plane = self.settings.get("mapping_mode") == "mcp_plane"
        self.kinematic_opening = self.exact_tips or self.mcp_plane
        self.report["mano_models"] = [str(Path(p).resolve()) for p in (mano_models or self.report["mano_models"])]
        self.report["asset_root"] = str(Path(asset_root or self.report["asset_root"]).resolve())
        point_count = self.arrays["landmarks_aligned_m"].shape[2]
        landmarks, self.meshes = reconstruct_grasp_geometry(self.arrays, self.report["mano_models"], landmark_count=point_count)
        forward_axis = self.settings.get("forward_axis", "wrist_to_thumb_mcp")
        self.midpoint_forward = forward_axis == "wrist_to_mcp_midpoint"
        forward_label = {"wrist_to_thumb_mcp": "wrist → thumb MCP",
                         "thumb_mcp_to_ip": "thumb MCP → thumb IP",
                         "index_mcp_to_pip": "index MCP → index PIP",
                         "wrist_to_mcp_midpoint": "thumb-side wrist → thumb/index MCP midpoint"}[forward_axis]
        if not np.allclose(landmarks, self.arrays["landmarks_aligned_m"], atol=1e-6, rtol=0, equal_nan=True):
            raise ValueError("Saved landmarks disagree with MANO reconstruction; use the original model assets")
        self.grippers = load_grippers(self.report["asset_root"], self.report["robot_settings"])
        for hand, gripper in enumerate(self.grippers):
            if not np.allclose(gripper.transform_palm_from_tcp, self.arrays["transform_palm_from_tcp"][hand], atol=1e-10):
                raise ValueError("Saved nominal TCP differs from current gripper assets")
        self.rgb = review_rgb(self.report, self.arrays["frame_index"])
        self.mapping = map_grasp_landmarks(landmarks, self.arrays["export_valid"] & ~self.arrays["motion_infilled"], self.settings, self.grippers)
        for key, values in self.mapping.items():
            if not np.allclose(values, self.arrays[key], atol=1e-6, rtol=0, equal_nan=True):
                raise ValueError(f"Saved {key} disagrees with this mapping/configuration; regenerate into a new directory")
        preview_indices = np.flatnonzero(self.mapping["mapping_valid"].all(axis=1))
        if not len(preview_indices):
            preview_indices = np.flatnonzero(self.mapping["mapping_valid"].any(axis=1))
        initial_index = int(preview_indices[0]) if len(preview_indices) else 0
        self.lock = threading.RLock()
        self.server = viser.ViserServer(host="0.0.0.0", port=port)
        self.server.scene.set_up_direction("+z")
        self.server.scene.set_background_image(np.full((1, 1, 3), [27, 32, 43], np.uint8))
        self.server.gui.configure_theme(dark_mode=True, show_logo=False, show_share_button=False)
        self.server.gui.main_panel.dock_right()
        gui = self.server.gui
        gui.add_markdown("## Hand → gripper\nDirect mapping · original MANO · no IK\n\n"
                         "Blue: left hand · Orange: right hand · Gray: grippers\n\nOpening: 0 closed · 1 open")
        priority = self.settings.get("orientation_priority", "closing")
        rule = "Forward preserved; closing made perpendicular." if priority == "forward" else "Closing preserved; forward made perpendicular."
        if self.exact_tips:
            forward_label = "true wrist → thumb MCP"
            rule = "Both tips matched. Fingertip line preserved; wrist direction resolves twist."
        if self.mcp_plane:
            forward_label = "index MCP → index PIP, projected in MCP plane"
            rule = "Jaw: thumb MCP → index MCP. Tip midpoint matched."
        gui.add_markdown(f"Forward direction: **{forward_label}**\n\n{rule}")
        first, last = self.arrays["frame_index"][[0, -1]]
        self.frame = gui.add_slider("Source frame", min=int(first), max=int(last), step=1,
                                    initial_value=int(self.arrays["frame_index"][initial_index]))
        self.play = gui.add_checkbox("Play", initial_value=False)
        self.speed = gui.add_slider("Playback speed", min=.1, max=1., step=.1, initial_value=1.)
        self.views = gui.add_button_group("Camera", ("Both hands", "Left closeup", "Right closeup"))
        self.image = gui.add_image(self.rgb[0], label="Synchronized source RGB", format="jpeg")
        self.status = gui.add_markdown("")
        with gui.add_folder("Display", expand_by_default=False):
            self.side_visible = [gui.add_checkbox(f"{side} hand and gripper", initial_value=True) for side in ("Left", "Right")]
            self.show_hands = gui.add_checkbox("MANO hands", initial_value=True)
            self.show_grippers = gui.add_checkbox("Mapped grippers", initial_value=True)
            self.hand_opacity = gui.add_slider("Hand opacity", min=.1, max=1., step=.05, initial_value=.55)
            self.gripper_opacity = gui.add_slider("Gripper opacity", min=.1, max=1., step=.05, initial_value=1.)
            self.show_landmarks = gui.add_checkbox("Landmarks", initial_value=True)
            self.show_axes = gui.add_checkbox("Grasp and TCP axes", initial_value=True)
            gui.add_markdown("Axes: X red (forward), Y green (closing), Z blue.\n\n"
                             "Landmarks: wrist white, MCPs yellow, thumbtip pink, index tip green; thumb IP orange and index PIP purple when present. "
                             "Small cyan sphere: nominal gripper TCP. " +
                             ("Yellow triangle: thumb MCP / index MCP / index PIP plane. Cyan spheres: gripper tips; individual offsets are expected." if self.mcp_plane else
                              "Cyan tip spheres: gripper tip markers, coincident with human fingertips." if self.exact_tips else
                              "White sphere: shifted wrist construction point."))
        with gui.add_folder("Mapping adjustments", expand_by_default=False):
            gui.add_markdown("Jaw follows the MCP line; forward lies in the MCP/index-PIP plane. "
                             "Tip midpoint and separation follow the fingertips." if self.mcp_plane else
                             "Opening and pose are solved from both fingertips. "
                             "Tip markers are the centers of the distal mesh edges." if self.exact_tips else
                             "Offsets are relative to each human grasp frame. "
                             "Opening: 0 closed, 1 open. Distance thresholds are adjustable.")
            self.closed = gui.add_number("Closed distance (m)", initial_value=self.settings.get("closed_distance_m", 0.), min=0., step=.005, visible=not self.kinematic_opening)
            self.opened = gui.add_number("Open distance (m)", initial_value=self.settings.get("open_distance_m", .1), min=.001, step=.005, visible=not self.kinematic_opening)
            self.wrist_offset = gui.add_number("Wrist shift toward thumb (m)", initial_value=self.settings.get("wrist_thumb_offset_m", 0.),
                                               min=0., step=.005, visible=self.midpoint_forward)
            self.offsets, self.rotations = [], []
            for hand, side in enumerate(("Left", "Right")):
                self.offsets.append(gui.add_vector3(f"{side} TCP offset (m)", initial_value=self.settings.get("tcp_offset_grasp_m", np.zeros((2,3)))[hand], step=.005, visible=not self.kinematic_opening))
                self.rotations.append(gui.add_vector3(f"{side} TCP rotation (deg)", initial_value=np.rad2deg(self.settings.get("tcp_rotation_grasp_xyz_rad", np.zeros((2,3)))[hand]), step=5., visible=not self.kinematic_opening))
            self.reset = gui.add_button("Reset to saved settings", visible=not self.kinematic_opening)
            self.save = gui.add_button("Save mapping snapshot")
            self.save_status = gui.add_markdown("Snapshots preserve the current settings and all mapped frames in a new directory.")
        with gui.add_folder("Detached gripper controls", expand_by_default=False):
            self.manual = gui.add_checkbox("Manual grippers", initial_value=False)
            gui.add_markdown("Pause the mapping and move either nominal TCP freely. "
                             "Drag its gizmo or edit position/rotation; test opening independently. "
                             "Manual poses are a preview and are not saved as a hand mapping.")
            self.manual_positions, self.manual_rotations, self.manual_actions = [], [], []
            for hand, side in enumerate(("Left", "Right")):
                eligible = np.flatnonzero(self.mapping["mapping_valid"][:, hand])
                seed = initial_index if self.mapping["mapping_valid"][initial_index, hand] else (eligible[0] if len(eligible) else None)
                pose = self.mapping["transform_aligned_from_tcp"][seed, hand] if seed is not None else np.eye(4)
                self.manual_positions.append(gui.add_vector3(f"{side} position (m)", initial_value=pose[:3, 3], step=.01, disabled=True))
                self.manual_rotations.append(gui.add_vector3(f"{side} rotation (deg)", initial_value=Rotation.from_matrix(pose[:3, :3]).as_euler("xyz", degrees=True), step=5., disabled=True))
                self.manual_actions.append(gui.add_slider(f"{side} opening", min=0., max=1., step=.01, initial_value=1., disabled=True))
        gui.add_markdown(("Tip markers use the gripper mesh. " if self.kinematic_opening else "Nominal TCP and opening scale are uncalibrated. ") +
                         "Missing/infilled hands are hidden. "
                         "Physical grasp accuracy remains unverified.")
        self.hand_handles, self.robot_handles, self.grasp_axes, self.tcp_axes = [], [], [], []
        self.landmarks, self.lines, self.tcp_markers, self.gizmos, self.wrist_markers = [], [], [], [], []
        self.tip_markers, self.plane_handles = [], []
        for hand, side in enumerate(("left", "right")):
            verts, faces = self.meshes[hand]
            self.hand_handles.append(self.server.scene.add_mesh_simple(f"/{side}/mano", vertices=np.zeros_like(verts[0]), faces=faces,
                color=(70, 145, 245) if hand == 0 else (245, 155, 60), opacity=.55, side="double", visible=False))
            handles = []
            for link in self.grippers[hand].model.link_list:
                mesh = link.concatenated_visual_mesh
                if mesh is not None:
                    handle = self.server.scene.add_mesh_simple(f"/{side}/gripper/{link.name}", vertices=mesh.vertices,
                        faces=mesh.faces, color=(185, 194, 205), side="double", visible=False)
                    handles.append((link, handle))
            self.robot_handles.append(handles)
            self.plane_handles.append(self.server.scene.add_mesh_simple(f"/{side}/mcp_plane",
                vertices=np.zeros((3, 3), np.float32), faces=np.array([[0, 1, 2]]),
                color=(255, 220, 70), opacity=.22, side="double", visible=False))
            self.grasp_axes.append(self.server.scene.add_frame(f"/{side}/grasp", axes_length=.045, axes_radius=.0015, visible=False))
            self.tcp_axes.append(self.server.scene.add_frame(f"/{side}/tcp", axes_length=.025, axes_radius=.001, visible=False))
            self.tcp_markers.append(self.server.scene.add_icosphere(f"/{side}/tcp_marker", radius=.004, color=(70, 240, 230), visible=False))
            self.tip_markers.append([self.server.scene.add_icosphere(f"/{side}/tip_{finger}", radius=.0025,
                color=(70, 240, 230), visible=False) for finger in ("thumb", "index")])
            self.wrist_markers.append(self.server.scene.add_icosphere(f"/{side}/shifted_wrist", radius=.003, color=(255, 255, 255), visible=False))
            self.landmarks.append(self.server.scene.add_point_cloud(f"/{side}/landmarks", points=np.zeros((point_count, 3), np.float32),
                colors=np.array([[255,255,255],[255,220,70],[255,220,70],[255,90,170],[80,255,130],[255,140,30],[180,110,255]], np.uint8)[:point_count], point_size=.008, visible=False))
            self.lines.append(self.server.scene.add_line_segments(f"/{side}/landmark_lines", points=np.zeros((4, 2, 3), np.float32),
                colors=(240, 215, 95), line_width=2, visible=False))
            gizmo = self.server.scene.add_transform_controls(f"/{side}/manual_tcp", scale=.15, visible=False)
            self.gizmos.append(gizmo)
            def drag(event, hand=hand):
                if event.client is not None and self.manual.value:
                    self.manual_positions[hand].value = tuple(event.target.position)
                    self.manual_rotations[hand].value = tuple(Rotation.from_quat(event.target.wxyz, scalar_first=True).as_euler("xyz", degrees=True))
            gizmo.on_update(drag)
        def scrub(event):
            if event.client is not None:
                self.play.value = False
            bounded = int(np.clip(self.frame.value, first, last))
            if bounded != self.frame.value:
                self.frame.value = bounded
                return
            self.render()
        self.frame.on_update(scrub)
        for control in (self.show_hands, self.show_grippers, self.hand_opacity, self.gripper_opacity,
                        self.show_landmarks, self.show_axes, *self.side_visible,
                        *self.manual_positions, *self.manual_rotations, *self.manual_actions):
            control.on_update(lambda _: self.render())
        for control in (self.closed, self.opened, self.wrist_offset, *self.offsets, *self.rotations):
            control.on_update(lambda _: self.remap())
        self.reset.on_click(lambda _: self.reset_settings())
        self.save.on_click(lambda _: self.save_snapshot())
        self.manual.on_update(lambda _: self.change_mode())
        self.views.on_click(lambda event: self.focus(event.target.value))
        self.server.on_client_connect(lambda event: self.focus("Both hands", event))
        self.render()

    def focus(self, view, client=None):
        i = self.frame_index()
        hand = {"Left closeup": 0, "Right closeup": 1}.get(view)
        if hand is not None:
            if self.manual.value:
                center = np.asarray(self.manual_positions[hand].value)
                rotation = Rotation.from_euler("xyz", self.manual_rotations[hand].value, degrees=True).as_matrix()
            else:
                valid = self.mapping["mapping_valid"][:, hand]
                indices = np.flatnonzero(valid)
                if not len(indices):
                    return
                nearest = i if valid[i] else indices[np.argmin(abs(indices - i))]
                pose = self.mapping["transform_aligned_from_tcp"][nearest, hand]
                center, rotation = pose[:3, 3], pose[:3, :3]
            position, up = center + rotation @ np.array([-.12, 0., .45]), rotation[:, 0]
        else:
            points = np.array([c.value for c in self.manual_positions]) if self.manual.value else self.arrays["landmarks_aligned_m"][i]
            points = points[np.isfinite(points).all(axis=-1)]
            if not len(points):
                points = self.arrays["landmarks_aligned_m"][np.isfinite(self.arrays["landmarks_aligned_m"]).all(axis=-1)]
            center = points.mean(axis=0) if len(points) else np.zeros(3)
            position, up = center + [.55, -.65, .5], [0, 0, 1]
        clients = [client] if client is not None else self.server.get_clients().values()
        for connected in clients:
            connected.camera.position = position
            connected.camera.look_at = center
            connected.camera.up_direction = up

    def remap(self):
        with self.lock:
            if self.kinematic_opening:
                self.save.disabled = self.manual.value
                self.render()
                return
            settings = {**self.settings, "closed_distance_m": float(self.closed.value), "open_distance_m": float(self.opened.value),
                        "wrist_thumb_offset_m": float(self.wrist_offset.value),
                        "tcp_offset_grasp_m": [list(c.value) for c in self.offsets],
                        "tcp_rotation_grasp_xyz_rad": [np.deg2rad(c.value).tolist() for c in self.rotations]}
            try:
                validate_settings(settings)
            except ValueError as error:
                self.save.disabled = True
                self.save_status.content = f"**Invalid settings:** {error}. Preview retains the last valid mapping."
                return
            self.settings = settings
            self.mapping = map_grasp_landmarks(self.arrays["landmarks_aligned_m"], self.mapping["observation_valid"], settings)
            self.save.disabled = self.manual.value
            self.save_status.content = "Current settings applied. Save a snapshot to preserve this mapping."
            self.render()

    def reset_settings(self):
        settings = self.report["settings"]
        self.closed.value, self.opened.value = settings["closed_distance_m"], settings["open_distance_m"]
        self.wrist_offset.value = settings.get("wrist_thumb_offset_m", 0.)
        for hand in range(2):
            self.offsets[hand].value = tuple(settings["tcp_offset_grasp_m"][hand])
            self.rotations[hand].value = tuple(np.rad2deg(settings["tcp_rotation_grasp_xyz_rad"][hand]))
        self.remap()

    def save_snapshot(self):
        with self.lock:
            if self.manual.value or self.save.disabled:
                return
            name = "tuning-" + utc_now().replace(":", "").replace(".", "")
            output = self.directory / name
            save_mapping(output, self.arrays, {**self.report, "parent_mapping": str(self.directory)}, self.settings, self.grippers)
            for gripper in self.grippers:
                (output / f"{gripper.side}_gripper.urdf").write_text(gripper.xml)
            self.save_status.content = f"Saved settings and all mapped frames to `{output}`."
            self.render()

    def change_mode(self):
        self.play.value = False
        self.play.disabled = self.manual.value
        # The installed Viser slider's companion text box ignores disabled;
        # hide the entire control while manual poses freeze the source frame.
        self.frame.visible = not self.manual.value
        if self.manual.value:
            i = self.frame_index()
            for hand in range(2):
                if self.mapping["mapping_valid"][i, hand]:
                    pose = self.mapping["transform_aligned_from_tcp"][i, hand]
                    self.manual_positions[hand].value = tuple(pose[:3, 3])
                    self.manual_rotations[hand].value = tuple(Rotation.from_matrix(pose[:3, :3]).as_euler("xyz", degrees=True))
                    self.manual_actions[hand].value = float(self.mapping["gripper_action"][i, hand])
        for control in (*self.manual_positions, *self.manual_rotations, *self.manual_actions):
            control.disabled = not self.manual.value
        self.remap()
        self.render()

    def frame_index(self):
        # Numeric edits can briefly exceed slider bounds before the GUI clamps.
        return int(np.clip(self.frame.value - self.arrays["frame_index"][0], 0, len(self.rgb) - 1))

    def render(self):
        with self.lock, self.server.atomic():
            i = self.frame_index()
            self.image.image = self.rgb[i]
            details = []
            for hand, side in enumerate(("Left", "Right")):
                observed = bool(self.mapping["observation_valid"][i, hand])
                valid = bool(self.mapping["mapping_valid"][i, hand])
                mesh = self.hand_handles[hand]
                enabled = self.side_visible[hand].value
                mesh.visible = enabled and observed and self.show_hands.value
                if mesh.visible:
                    mesh.vertices = self.meshes[hand][0][i]
                mesh.opacity = self.hand_opacity.value
                if self.manual.value:
                    pose = np.eye(4)
                    pose[:3, 3] = self.manual_positions[hand].value
                    pose[:3, :3] = Rotation.from_euler("xyz", self.manual_rotations[hand].value, degrees=True).as_matrix()
                    action = self.manual_actions[hand].value
                else:
                    pose, action = self.mapping["transform_aligned_from_tcp"][i, hand], self.mapping["gripper_action"][i, hand]
                visible = enabled and self.show_grippers.value and (valid or self.manual.value)
                if valid or self.manual.value:
                    self.grippers[hand].set_opening(action)
                    self.grippers[hand].place_tcp(pose)
                for link, handle in self.robot_handles[hand]:
                    handle.visible = visible
                    handle.opacity = self.gripper_opacity.value
                    if visible:
                        handle.position = link.worldpos()
                        handle.wxyz = Rotation.from_matrix(link.worldrot()).as_quat(scalar_first=True)
                self.gizmos[hand].visible = visible and self.manual.value
                if self.manual.value:
                    self.gizmos[hand].position = pose[:3, 3]
                    self.gizmos[hand].wxyz = Rotation.from_matrix(pose[:3, :3]).as_quat(scalar_first=True)
                for axes, transform, show in ((self.grasp_axes[hand], self.mapping["transform_aligned_from_grasp"][i, hand], valid),
                                               (self.tcp_axes[hand], pose, visible)):
                    axes.visible = enabled and self.show_axes.value and show
                    if axes.visible:
                        axes.position = transform[:3, 3]
                        axes.wxyz = Rotation.from_matrix(transform[:3, :3]).as_quat(scalar_first=True)
                self.tcp_markers[hand].visible = visible and self.show_axes.value
                if visible:
                    self.tcp_markers[hand].position = pose[:3, 3]
                for tip, marker in enumerate(self.tip_markers[hand]):
                    marker.visible = visible and self.kinematic_opening and self.show_landmarks.value
                    if marker.visible:
                        marker.position = self.grippers[hand].tip_positions(self.settings["distal_tip_local_m"])[tip]
                self.landmarks[hand].visible = self.lines[hand].visible = enabled and observed and self.show_landmarks.value
                self.wrist_markers[hand].visible = self.landmarks[hand].visible and self.midpoint_forward and self.settings.get("wrist_thumb_offset_m", 0.) > 0
                self.plane_handles[hand].visible = self.landmarks[hand].visible and self.mcp_plane
                if observed:
                    points = self.arrays["landmarks_aligned_m"][i, hand]
                    self.landmarks[hand].points = points
                    if self.mcp_plane:
                        self.plane_handles[hand].vertices = points[[1, 2, 6]]
                    start, end = grasp_forward_segment(points, self.settings)
                    segments = np.array([[start, end], points[[1, 2]], points[[3, 4]], [points[0], start]])
                    if self.mcp_plane:
                        segments[3] = points[[1, 6]]
                    elif not self.midpoint_forward:
                        segments[3] = [points[0], points[0]]
                    self.lines[hand].points = segments
                    self.wrist_markers[hand].position = start
                if self.manual.value:
                    detail = f"manual opening **{action:.3f}**"
                elif valid:
                    distance = self.mapping["fingertip_distance_m"][i, hand]
                    detail = f"{distance * 100:.2f} cm · action **{action:.3f}**" + (" · fully open (clipped)" if action == 1 else "")
                    if self.kinematic_opening:
                        error = self.mapping["tip_error_m"][i, hand].max() * 1000
                        if self.mcp_plane:
                            center = self.mapping["gripper_tips_aligned_m"][i, hand].mean(axis=0)
                            target = self.mapping["transform_aligned_from_grasp"][i, hand, :3, 3]
                            detail += f" · center error **{np.linalg.norm(center - target) * 1000:.4f} mm** · tip offset **{error:.2f} mm**"
                        else:
                            detail += f" · tip error **{error:.4f} mm**"
                else:
                    detail = "missing/infilled" if not observed else "invalid landmark geometry"
                    if observed and self.kinematic_opening and not self.mapping["opening_reachable"][i, hand]:
                        detail = "fingertip separation outside gripper range"
                details.append(f"{side}: {detail}")
            mode = "Manual gripper preview" if self.manual.value else "Direct hand mapping"
            self.status.content = (f"**Frame {int(self.arrays['frame_index'][i])} · {self.arrays['timestamp_s'][i]:.3f} s**\n\n"
                                   f"Source time: {self.arrays['source_timestamp_s'][i]:.3f} s · {mode}\n\n" + "\n\n".join(details))

    def run(self, open_browser=False):
        url = f"http://localhost:{self.server.get_port()}"
        print(f"Direct gripper viewer: {url}", flush=True)
        if open_browser:
            webbrowser.open(url)
        try:
            while True:
                i = self.frame_index()
                times = self.arrays["timestamp_s"]
                delay = times[i + 1] - times[i] if i + 1 < len(times) else (np.median(np.diff(times)) if len(times) > 1 else 1/30)
                time.sleep(float(delay) / self.speed.value)
                with self.lock:
                    if self.play.value and not self.manual.value:
                        current = self.frame_index()
                        self.frame.value = int(self.arrays["frame_index"][(current + 1) % len(times)])
        finally:
            self.server.stop()
