"""Source-video annotations and read-only interactive positional IK playback."""

from fractions import Fraction
import json
from pathlib import Path
import subprocess
import threading
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .base_placement import transform_points
from .robot_workspace import load_robot, verify_asset_source
from .run_metadata import read_json


COLORS = {"feasible": (70, 195, 130), "infeasible": (240, 95, 90),
          "unknown": (150, 155, 168), "ik_failed": (205, 115, 240)}


def episode_region(episode):
    return episode["region"] if "region" in episode else episode["sdf"]


def frame_state(frame, arrays, report):
    """Classification under the selected interval; unassigned is not infeasible."""
    eid = int(arrays["episode_id"][frame])
    if not arrays["export_valid"][frame].any():
        return "unknown", "No valid hand estimates"
    if eid < 0:
        return "unknown", "No retained episode"
    episode = report["episodes"][eid]
    cid = episode["candidate_id"]
    if report.get("method") == "joint_base":
        if not (arrays["ik_success"][frame] | ~arrays["export_valid"][frame]).all():
            return "ik_failed", f"Region {eid}: wrist position/orientation gate failed"
        return "feasible", f"Region {eid}: available wrists pass position and orientation"
    if not (arrays["ik_success"][frame] | ~arrays["export_valid"][frame]).all():
        suffix = "; workspace margin failed" if not arrays["candidate_frame_passed"][cid, frame] else ""
        return "ik_failed", f"Episode {eid}: IK unverified{suffix}"
    if not arrays["candidate_frame_passed"][cid, frame]:
        return "infeasible", f"Episode {eid}: workspace margin failed"
    return "feasible", f"Episode {eid}: available hands pass SDF and IK"


def draw_timeline(image, arrays, report, top, current_frame=None):
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=16)
    x0, x1, n = 140, image.width - 18, len(arrays["timestamp_s"])
    width = x1 - x0
    draw.text((12, top), "Camera seeds", fill="white", font=font)
    for i, seed in enumerate(report["seeds"]):
        a, b = x0 + width * seed["start"] / n, x0 + width * seed["stop"] / n
        color = (70, 120, 205) if seed["retained"] else (65, 70, 85)
        draw.rectangle((a, top, b - 1, top + 20), fill=color)
        if b - a > 24:
            draw.text((a + 3, top), str(i), font=font, fill="white")
    draw.text((12, top + 28), "Final regions", fill="white", font=font)
    for frame in range(n):
        state, _ = frame_state(frame, arrays, report)
        a, b = x0 + width * frame / n, x0 + width * (frame + 1) / n
        draw.rectangle((a, top + 28, b, top + 48), fill=COLORS[state])
    for episode in report["episodes"]:
        a = x0 + width * episode_region(episode)["start"] / n
        draw.line((a, top + 24, a, top + 50), fill="white", width=2)
        draw.text((a + 3, top + 49), f"E{episode['episode_id']}", fill="white", font=font)
    if current_frame is not None:
        x = x0 + width * (current_frame + .5) / n
        draw.line((x, top - 3, x, top + 50), fill="yellow", width=2)


def annotate_video(output, arrays, report, clip):
    """Use existing ffmpeg/Pillow; retain every prepared frame at source cadence."""
    output = Path(output)
    pose_fitting = report.get("method") == "joint_base"
    n, fps = len(arrays["timestamp_s"]), Fraction(clip["prepared"]["fps"])
    if not np.allclose(np.diff(arrays["timestamp_s"]), float(1 / fps), atol=1e-7, rtol=0):
        raise ValueError("Annotated video requires uniform prepared timestamps matching its FPS")
    width = min(960, clip["prepared"]["width"])
    width -= width % 2
    height = int(round(clip["prepared"]["height"] * width / clip["prepared"]["width"] / 2)) * 2
    font = ImageFont.load_default(size=17)
    review_frames = {0, n // 2, n - 1}
    review_frames.update(episode_region(e)["start"] for e in report["episodes"])
    for mask in ((arrays["export_valid"] & ~arrays["ik_success"]).any(axis=1), arrays["joint_jump"].any(axis=1)):
        indices = np.flatnonzero(mask)
        if len(indices):
            review_frames.add(int(indices[0]))
    decode_command = ["ffmpeg", "-v", "error", "-nostdin", "-i", report["prepared_video"],
                      "-vf", f"scale={width}:{height}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    encode_command = ["ffmpeg", "-v", "error", "-nostdin", "-n", "-f", "rawvideo", "-pix_fmt", "rgb24",
                      "-s", f"{width}x{height + 196}", "-r", str(fps), "-i", "-", "-an", "-c:v", "libx264",
                      "-crf", "18", "-pix_fmt", "yuv420p", str(output / "annotated_video.mp4")]
    with (output / "video-decode.log").open("w") as decode_log, (output / "video-encode.log").open("w") as encode_log:
        decoder = subprocess.Popen(decode_command, stdout=subprocess.PIPE, stderr=decode_log)
        encoder = subprocess.Popen(encode_command, stdin=subprocess.PIPE, stderr=encode_log)
        try:
            for frame in range(n):
                raw = decoder.stdout.read(width * height * 3)
                if len(raw) != width * height * 3:
                    raise ValueError(f"Prepared video ended before trajectory frame {frame}; inspect video-decode.log")
                image = Image.new("RGB", (width, height + 196), (22, 27, 38))
                image.paste(Image.frombytes("RGB", (width, height), raw), (0, 0))
                draw = ImageDraw.Draw(image)
                state, label = frame_state(frame, arrays, report)
                if arrays["joint_jump"][frame].any():
                    label += " | Large joint change flagged"
                draw.text((12, height + 8), f"Frame {frame} | clip {arrays['timestamp_s'][frame]:.3f}s | source {arrays['source_timestamp_s'][frame]:.3f}s", fill="white", font=font)
                draw.text((12, height + 32), label, fill=COLORS[state], font=font)
                missing = [name for hand, name in enumerate(("left", "right")) if not arrays["export_valid"][frame, hand]]
                detail = "Missing/unverified: " + ", ".join(missing) if missing else "Both hand estimates available"
                mode = "Pose fitting" if pose_fitting else "Position-only"
                draw.text((12, height + 55), detail + f" | {mode}; collisions/dynamics unchecked", fill=(200, 205, 218), font=font)
                draw_timeline(image, arrays, report, height + 86, frame)
                legend = ("Green: pose pass   Purple: pose fail   Gray: unknown/outside regions" if pose_fitting
                          else "Green: pass   Red: SDF fail   Purple: IK fail   Gray: unknown/unassigned")
                draw.text((12, height + 164), legend, fill=(210, 215, 228), font=font)
                encoder.stdin.write(image.tobytes())
                if frame in review_frames:
                    image.save(output / f"review-frame-{frame:04d}.png")
            if decoder.stdout.read(1):
                raise ValueError("Prepared video has more frames than the trajectory")
            encoder.stdin.close()
            if decoder.wait() or encoder.wait():
                raise RuntimeError("Video annotation failed; inspect video-decode.log and video-encode.log")
        finally:
            decoder.stdout.close()
            for process in (decoder, encoder):
                if process.poll() is None:
                    process.kill()
                    process.wait()
    probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                        "-show_entries", "stream=nb_read_frames,avg_frame_rate,width,height,duration", "-of", "json",
                        str(output / "annotated_video.mp4")], text=True))["streams"][0]
    if int(probe["nb_read_frames"]) != n or Fraction(probe["avg_frame_rate"]) != fps:
        raise ValueError("Annotated video frame count or cadence changed")
    timeline = Image.new("RGB", (1100, 135 + 32 * len(report["candidates"])), (22, 27, 38))
    draw_timeline(timeline, arrays, report, 12)
    draw = ImageDraw.Draw(timeline)
    for cid in range(len(report["candidates"])):
        y = 90 + cid * 32
        draw.text((12, y), f"Base {cid} {'pose' if pose_fitting else 'SDF'}", fill="white", font=font)
        for frame in range(n):
            outside = pose_fitting and arrays["episode_id"][frame] != cid
            state = "unknown" if outside or not arrays["export_valid"][frame].any() else (
                "feasible" if arrays["candidate_frame_passed"][cid, frame] else "ik_failed" if pose_fitting else "infeasible")
            draw.rectangle((140 + 942 * frame / n, y, 140 + 942 * (frame + 1) / n, y + 20), fill=COLORS[state])
    timeline.save(output / "feasibility_timeline.png")
    report["video"] = {"decode_command": decode_command, "encode_command": encode_command, "probe": probe,
                       "review_frames": sorted(review_frames)}


def base_hand_meshes(arrays, report, model_paths):
    """Original MANO vertices in each frame's episode base; no IK deformation.

    Returns left/right (vertices [T,778,3] metres, faces [F,3]). Missing hands
    and frames without a retained base stay NaN, independently of IK success.
    """
    from .hand_geometry import load_mano_model, reconstruct_mano

    meshes = []
    for hand, path in enumerate(model_paths):
        if not Path(path).is_file():
            raise FileNotFoundError(f"MANO asset missing: {path}; supply --mano-models LEFT RIGHT or use --no-mano")
        model = load_mano_model(path, hand)
        vertices = np.full((len(arrays["episode_id"]), len(model.v_template), 3), np.nan, np.float32)
        for episode in report["episodes"]:
            indices = np.flatnonzero((arrays["episode_id"] == episode["episode_id"]) & arrays["export_valid"][:, hand])
            if not len(indices):
                continue
            joints, world_vertices = reconstruct_mano(
                model, arrays["root_translation_world_m"][indices, hand],
                arrays["root_orientation_world_axis_angle"][indices, hand],
                arrays["hand_pose_axis_angle"][indices, hand], arrays["mano_betas"][indices, hand])
            transform = arrays["transform_base_from_world"][episode["candidate_id"]]
            # Catch incorrect assets/hand conventions before showing a misleading overlay.
            if not np.allclose(transform_points(joints[:, 0], transform),
                               arrays["wrist_position_base_m"][indices, hand], atol=1e-5, rtol=0):
                raise ValueError("MANO wrists disagree with saved base-frame targets; check model assets and hand order")
            vertices[indices] = transform_points(world_vertices, transform)
        meshes.append((vertices, model.faces))
    return meshes


def view_retargeting(directory, *, asset_root=None, open_browser=False, mano_models=None, show_mano=True):
    """Orbit/pan/zoom and source-timed playback; failed arm poses are hidden."""
    from scipy.spatial.transform import Rotation
    from skrobot.coordinates import Coordinates
    from skrobot.viewers import ViserViewer

    directory = Path(directory)
    report = read_json(directory / "retargeting_report.json")
    if report["status"] != "completed":
        raise ValueError("View a completed run; inspect retargeting_report.json")
    with np.load(directory / "trajectory_retargeted.npz", allow_pickle=False) as data:
        arrays = {key: data[key] for key in data.files}
    if not report["episodes"]:
        raise ValueError("No retained episodes to animate; review annotated_video.mp4 and candidate diagnostics")
    meshes = []
    if show_mano:
        if mano_models is None:
            alignment = read_json(Path(report["alignment_directory"]) / "alignment_report.json")
            mano_models = [alignment["inputs"][f"mano_{name}"]["path"] for name in ("left", "right")]
        meshes = base_hand_meshes(arrays, report, mano_models)
    settings = report["robot_settings"]
    pose_fitting = report.get("method") == "joint_base"
    target_frames = settings.get("target_frames", settings["tool_frames"])
    wrist_matching = target_frames != settings["tool_frames"]
    endpoint_positions = arrays.get("target_position_base_m", arrays["tcp_position_base_m"])
    if wrist_matching and "target_position_base_m" not in arrays:
        raise ValueError("Wrist-target run has no saved target positions; regenerate the retargeting output")
    robot = load_robot(verify_asset_source(asset_root or report["asset_root"], settings), settings["base_frame"])
    viewer = ViserViewer(draw_grid=False, enable_ik=False, enable_motion_planning=False)
    server = viewer._server
    server.scene.set_up_direction("+z")
    server.scene.set_background_image(np.full((1, 1, 3), [28, 33, 45], dtype=np.uint8))
    for link in robot.link_list:
        viewer.add(link)
    base_axes = server.scene.add_frame("/base", axes_length=.2, axes_radius=.004)
    mesh_handles = [server.scene.add_mesh_simple(
        f"/base/mano_{name}", vertices=np.zeros_like(vertices[0]), faces=faces,
        color=(70, 145, 245) if hand == 0 else (245, 155, 60), opacity=.65,
        side="double", visible=False) for hand, (name, (vertices, faces))
        in enumerate(zip(("left", "right"), meshes))]
    server.scene.add_label("/base/label", "Fixed robot base", position=(0, 0, -.06))
    server.scene.add_frame("/aligned", axes_length=.25, axes_radius=.003)
    server.scene.add_label("/aligned/label", "Aligned origin", position=(0, 0, -.06))
    camera = arrays["camera_position_aligned_m"]
    camera_points = server.scene.add_point_cloud("/camera", points=camera.astype(np.float32), colors=(160, 165, 178), point_size=.012)
    wrists = arrays["wrist_position_aligned_m"]
    targets, endpoint_markers, tcp_markers, paths = [], [], [], []
    for hand, name in enumerate(("left", "right")):
        valid = arrays["export_valid"][:, hand]
        colors = np.array([COLORS[frame_state(i, arrays, report)[0]] for i in np.flatnonzero(valid)], np.uint8)
        paths.append(server.scene.add_point_cloud(f"/{name}/path", points=wrists[valid, hand].astype(np.float32), colors=colors, point_size=.018))
        targets.append(server.scene.add_icosphere(f"/{name}/wrist", radius=.023, color=(70, 145, 245) if hand == 0 else (245, 155, 60)))
        endpoint_markers.append(server.scene.add_icosphere(f"/{name}/ik_target", radius=.012, color=(245, 245, 245)))
        tcp_markers.append(server.scene.add_icosphere(f"/{name}/tcp", radius=.009, color=(90, 235, 220)))
    endpoint_label = "robot wrist" if wrist_matching else "TCP (legacy alignment)"
    explanation = (
        "Saved joint/base pose fit and fixed-base smoothing; no live solve. Camera position was used only "
        "for initialization. Axes compare target and fitted orientations. Unverified poses are hidden unless enabled."
        if pose_fitting else
        "Saved per-frame position-only IK; no live solve. Missing/failed robot arms are hidden; MANO retains "
        "the original hand orientation and articulation.")
    server.gui.add_markdown(
        "## Fixed-base trajectory review\nDrag to orbit · Right-drag to pan · Scroll to zoom\n\n"
        f"Blue/orange: original left/right hand and wrist · White: verified {endpoint_label}"
        + (" · Cyan: gripper TCP" if wrist_matching else "")
        + "\nPath: green pass, purple pose/IK failure, gray unassigned; red is a baseline workspace failure.\n\n"
        + explanation + " Collisions and dynamic limits are unchecked.")
    slider = server.gui.add_slider("Frame", min=0, max=len(wrists) - 1, step=1, initial_value=0)
    play = server.gui.add_checkbox("Play", initial_value=False)
    camera_control = server.gui.add_checkbox("Camera path", initial_value=True)
    path_control = server.gui.add_checkbox("Wrist paths", initial_value=True)
    orientation_handles = []
    if pose_fitting:
        predicted_control = server.gui.add_checkbox("Show unverified robot poses", initial_value=False)
        axes_control = server.gui.add_checkbox("Orientation axes", initial_value=True)
        for name in ("left_target", "left_robot", "right_target", "right_robot", "camera_target", "camera_robot"):
            target = name.endswith("_target")
            handle = server.scene.add_frame(f"/orientations/{name}", axes_length=.10 if target else .075, axes_radius=.002)
            server.scene.add_label(f"/orientations/{name}/label", name.replace("_", " "),
                                   position=(0, 0, .12 if target else -.10))
            orientation_handles.append(handle)

        @predicted_control.on_update
        def toggle_predictions(event):
            update(int(slider.value))

        @axes_control.on_update
        def toggle_axes(event):
            update(int(slider.value))
    if meshes:
        mesh_control = server.gui.add_checkbox("MANO meshes", initial_value=True)
        opacity_control = server.gui.add_slider("MANO opacity", min=.1, max=1., step=.05, initial_value=.65)

        @mesh_control.on_update
        def toggle_meshes(event):
            update(int(slider.value))

        @opacity_control.on_update
        def change_opacity(event):
            for handle in mesh_handles:
                handle.opacity = event.target.value
    status = server.gui.add_markdown("")

    @camera_control.on_update
    def toggle_camera(event):
        camera_points.visible = event.target.value

    @path_control.on_update
    def toggle_paths(event):
        for path in paths:
            path.visible = event.target.value

    def update(frame):
        eid = int(arrays["episode_id"][frame])
        state, label = frame_state(frame, arrays, report)
        base_axes.visible = eid >= 0
        if eid >= 0:
            episode = report["episodes"][eid]
            transform = arrays["transform_aligned_from_base"][episode["candidate_id"]]
            robot.newcoords(Coordinates(pos=transform[:3, 3], rot=transform[:3, :3]))
            base_axes.position = transform[:3, 3]
            base_axes.wxyz = Rotation.from_matrix(transform[:3, :3]).as_quat(scalar_first=True)
            if pose_fitting:
                for name, angle in zip(report["settings"]["neck_joints"], arrays["neck_joint_angles_rad"][frame]):
                    robot.__dict__[name].joint_angle(float(angle))
            for hand in range(2):
                if arrays["ik_success"][frame, hand] or pose_fitting:
                    for name, angle in zip(settings["arm_joints"][hand], arrays["joint_angles_rad"][frame, hand]):
                        robot.__dict__[name].joint_angle(float(angle))
        for link in robot.link_list:
            # The URDF uses uppercase arm names and lowercase gripper names.
            name = link.name.upper()
            hand = 0 if name.startswith("LEFT_") else 1 if name.startswith("RIGHT_") else None
            handle = viewer._linkid_to_handle.get(str(id(link)))
            if handle is not None:
                handle.visible = eid >= 0 and (hand is None or bool(arrays["ik_success"][frame, hand])
                                               or (pose_fitting and predicted_control.value))
        for hand in range(2):
            if meshes:
                handle = mesh_handles[hand]
                handle.visible = mesh_control.value and eid >= 0 and bool(arrays["export_valid"][frame, hand])
                if handle.visible:
                    handle.vertices = meshes[hand][0][frame]
            targets[hand].visible = bool(arrays["export_valid"][frame, hand])
            if targets[hand].visible:
                targets[hand].position = wrists[frame, hand]
            endpoint_markers[hand].visible = eid >= 0 and bool(arrays["ik_success"][frame, hand])
            if endpoint_markers[hand].visible:
                endpoint_markers[hand].position = transform_points(endpoint_positions[frame, hand], transform)
            tcp_markers[hand].visible = wrist_matching and endpoint_markers[hand].visible
            if tcp_markers[hand].visible:
                tcp_markers[hand].position = transform_points(arrays["tcp_position_base_m"][frame, hand], transform)
        if pose_fitting:
            for i, handle in enumerate(orientation_handles):
                hand = i // 2
                observed = hand == 2 or bool(arrays["export_valid"][frame, hand])
                show_robot = hand == 2 or bool(arrays["ik_success"][frame, hand]) or predicted_control.value
                handle.visible = axes_control.value and eid >= 0 and (observed if i % 2 == 0 else show_robot)
                if not handle.visible:
                    continue
                if hand < 2:
                    position = wrists[frame, hand] if i % 2 == 0 else transform_points(endpoint_positions[frame, hand], transform)
                    rotation = (arrays["wrist_orientation_target_aligned"][frame, hand] if i % 2 == 0
                                else transform[:3, :3] @ arrays["tool_orientation_base"][frame, hand])
                else:
                    position = (camera[frame] if i % 2 == 0 else transform_points(arrays["camera_position_base_m"][frame], transform))
                    rotation = (arrays["camera_rotation_aligned_from_camera"][frame] if i % 2 == 0
                                else transform[:3, :3] @ arrays["camera_rotation_base_from_optical"][frame])
                handle.position = position
                handle.wxyz = Rotation.from_matrix(rotation).as_quat(scalar_first=True)
        seed_id, seed = next((i, s) for i, s in enumerate(report["seeds"]) if s["start"] <= frame < s["stop"])
        detail = f"Seed {seed_id}: [{seed['start']}, {seed['stop']})" + ("" if seed["retained"] else " (short, discarded)")
        if eid >= 0:
            region = episode_region(episode)
            detail += f" · Episode {eid}: [{region['start']}, {region['stop']})"
        if pose_fitting and eid >= 0:
            degrees = np.rad2deg(arrays["orientation_residual_rad"][frame])
            detail += (f"\n\nWrist L/R: {np.round(arrays['ik_residual_m'][frame] * 1000, 2).tolist()} mm · "
                       f"{np.round(degrees, 2).tolist()}° · Head: {np.rad2deg(arrays['camera_rotation_error_rad'][frame]):.2f}°")
            if predicted_control.value and not arrays["ik_success"][frame].all():
                detail += "\n\n**Unverified robot poses shown; missing observations remain unknown.**"
        if arrays["joint_jump"][frame].any():
            label += " · **Large joint change flagged**"
        status.content = (f"**Frame {frame} · {arrays['timestamp_s'][frame]:.3f} s**\n\n{label}\n\n{detail}\n\n"
                          f"Observed L/R: {arrays['export_valid'][frame].tolist()} · IK L/R: {arrays['ik_success'][frame].tolist()}\n\n"
                          f"Robot targets: {', '.join(target_frames)}")
        viewer.redraw()

    @slider.on_update
    def scrub(event):
        update(int(event.target.value))

    def playback():
        while viewer.is_active:
            frame = int(slider.value)
            delay = (arrays["timestamp_s"][frame + 1] - arrays["timestamp_s"][frame]
                     if frame < len(wrists) - 1 else np.median(np.diff(arrays["timestamp_s"])))
            time.sleep(float(delay))
            if play.value:
                slider.value = (int(slider.value) + 1) % len(wrists)

    update(0)
    viewer.set_camera(angles=[np.pi / 3, 0, 3 * np.pi / 4], distance=2.4, center=np.mean(wrists[arrays["export_valid"]], axis=0))
    viewer.show(open_browser=open_browser)
    threading.Thread(target=playback, daemon=True).start()
    return viewer
