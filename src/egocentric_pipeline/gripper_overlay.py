"""Project saved detached grippers onto the original prepared RGB frames."""

from fractions import Fraction
import json
import os
from pathlib import Path
import subprocess
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .gripper_mapping import load_mapping
from .gripper_model import load_grippers
from .retargeting import load_alignment
from .run_metadata import write_json


def camera_pose_opengl(rotation_aligned_from_camera, position_aligned_m):
    """Aligned-from-OpenGL camera pose; input camera is CV (+X right,+Y down,+Z forward)."""
    pose = np.eye(4)
    pose[:3, :3] = rotation_aligned_from_camera @ np.diag([1., -1., -1.])
    pose[:3, 3] = position_aligned_m
    return pose


def render_gripper_overlay(mapping_directory, output, *, opacity=.7):
    """Render every saved source frame with ordinary FK, metres and native intrinsics.

    Grippers depth-test against each other, then alpha-composite over RGB. There
    is no reconstructed scene depth or physical hand/object occlusion model.
    Invalid mappings are hidden, never interpolated. Output timestamps start at
    zero; source frame indices/times remain in the banner and saved mapping.
    """
    # EGL is provided by the installed pyrender/scikit-robot rendering stack.
    os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
    import pyrender

    output = Path(output)
    if output.suffix.lower() != ".mp4" or not 0 < opacity <= 1:
        raise ValueError("Require an .mp4 output and 0 < opacity <= 1")
    report_path = output.with_suffix(".json")
    if output.exists() or report_path.exists():
        raise FileExistsError("Overlay output already exists; choose a new path")
    arrays, report = load_mapping(mapping_directory)
    source, _, clip = load_alignment(report["alignment_directory"])
    indices = arrays["frame_index"]
    if not np.array_equal(indices, np.arange(indices[0], indices[-1]+1)):
        raise ValueError("Overlay requires contiguous original frame indices")
    for name in ("frame_index", "timestamp_s", "source_timestamp_s"):
        if not np.array_equal(arrays[name], source[name][indices]):
            raise ValueError(f"Mapping/source {name} mismatch")
    width, height = report["video_size"]
    fps = Fraction(clip["prepared"]["fps"])
    if not np.allclose(np.diff(arrays["timestamp_s"]), 1/float(fps), atol=1e-8, rtol=0):
        raise ValueError("Overlay requires constant-rate prepared timestamps")
    focal = clip["hawor_camera"]["focal_length_px"]
    rotations = source["camera_rotation_aligned_from_camera"][indices]
    positions = source["camera_position_aligned_m"][indices]
    if not np.isfinite(rotations).all() or not np.isfinite(positions).all():
        raise ValueError("Camera poses contain nonfinite values")
    grippers = load_grippers(report["asset_root"], report["robot_settings"])
    scene = pyrender.Scene(bg_color=[0, 0, 0, 0], ambient_light=[.65, .65, .65])
    camera = scene.add(pyrender.IntrinsicsCamera(focal, focal, width/2, height/2, znear=.001, zfar=100.))
    light = scene.add(pyrender.DirectionalLight(color=np.ones(3), intensity=2.))
    colors = ((.12, .55, 1.), (1., .46, .10))
    nodes = []
    for hand, gripper in enumerate(grippers):
        material = pyrender.MetallicRoughnessMaterial(baseColorFactor=[*colors[hand], 1.], metallicFactor=0., roughnessFactor=.65)
        links = []
        for link in gripper.model.link_list:
            mesh = link.concatenated_visual_mesh
            if mesh is not None and len(mesh.faces):
                node = scene.add(pyrender.Mesh.from_trimesh(mesh, material=material, smooth=False))
                links.append((link, node))
        nodes.append(links)
    renderer = pyrender.OffscreenRenderer(width, height)
    output.parent.mkdir(parents=True, exist_ok=True)
    first, last = map(int, (indices[0], indices[-1]))
    decoder = subprocess.Popen(["ffmpeg", "-v", "error", "-nostdin", "-i", report["prepared_video"],
        "-vf", f"select=between(n\\,{first}\\,{last})", "-vsync", "0", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE)
    encoder = subprocess.Popen(["ffmpeg", "-v", "error", "-nostdin", "-n", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{width}x{height}", "-r", str(fps), "-i", "-", "-an", "-c:v", "libx264", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)], stdin=subprocess.PIPE)
    labels = {"wrist_roll": "Config 2 | Wrist anchor, fingertip forward", "roll_blend": "Config 3 | Rotation blend",
              "thumb_point_blend": "Config 4 | Interpolated thumb plane"}
    label = labels.get(report["settings"]["mapping_mode"], report["settings"]["mapping_mode"])
    font = ImageFont.load_default(size=18)
    start = time.monotonic()
    visible_frames = 0
    try:
        for i, frame in enumerate(indices):
            raw = decoder.stdout.read(width*height*3)
            if len(raw) != width*height*3:
                raise ValueError(f"Source RGB decode failed at frame {frame}")
            rgb = np.frombuffer(raw, np.uint8).reshape(height, width, 3).copy()
            pose = camera_pose_opengl(rotations[i], positions[i])
            scene.set_pose(camera, pose); scene.set_pose(light, pose)
            states = []
            for hand, gripper in enumerate(grippers):
                valid = bool(arrays["mapping_valid"][i, hand])
                if valid:
                    gripper.set_opening(arrays["gripper_action"][i, hand])
                    gripper.place_tcp(arrays["transform_aligned_from_tcp"][i, hand])
                for link, node in nodes[hand]:
                    node.mesh.is_visible = valid
                    if valid:
                        scene.set_pose(node, link.worldcoords().T())
                state = "mapped" if valid else "missing/infilled" if not arrays["observation_valid"][i, hand] else "invalid geometry/opening"
                states.append(f"{('Left', 'Right')[hand]}: {state}")
            if arrays["mapping_valid"][i].any():
                color, depth = renderer.render(scene)
                mask = depth > 0
                visible_frames += int(mask.any())
                rgb[mask] = np.clip((1-opacity)*rgb[mask] + opacity*color[mask], 0, 255).astype(np.uint8)
            image = Image.fromarray(rgb)
            draw = ImageDraw.Draw(image)
            draw.rectangle((0, 0, width, 56), fill=(20, 24, 32))
            draw.text((10, 5), f"{label} | Frame {frame} | {arrays['timestamp_s'][i]:.2f}s", font=font, fill="white")
            for hand, state in enumerate(states):
                draw.text((10 + hand*width//2, 31), state, font=font, fill=tuple(int(c*255) for c in colors[hand]))
            encoder.stdin.write(np.asarray(image).tobytes())
            if (i+1) % 100 == 0 or i+1 == len(indices):
                print(f"Rendered {i+1}/{len(indices)} frames ({time.monotonic()-start:.1f}s)", flush=True)
        if decoder.stdout.read(1) or decoder.wait() != 0:
            raise ValueError("Source frame count or decoder failure")
        encoder.stdin.close()
        if encoder.wait() != 0:
            raise RuntimeError("Overlay encoding failed; inspect render log")
    finally:
        renderer.delete()
        decoder.stdout.close()
        if not encoder.stdin.closed:
            encoder.stdin.close()
        for process in (decoder, encoder):
            if process.poll() is None:
                process.terminate(); process.wait()
    probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_frames",
        "-show_entries", "stream=width,height,r_frame_rate:frame=best_effort_timestamp_time", "-of", "json", str(output)]))
    stream = probe["streams"][0]
    timestamps = np.array([float(f["best_effort_timestamp_time"]) for f in probe["frames"]])
    if (len(timestamps) != len(indices) or (stream["width"], stream["height"]) != (width, height)
            or Fraction(stream["r_frame_rate"]) != fps
            or not np.allclose(timestamps, arrays["timestamp_s"] - arrays["timestamp_s"][0], rtol=0, atol=1e-6)):
        raise ValueError("Encoded overlay failed frame/dimension/timestamp validation")
    subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(output), "-f", "null", "-"], check=True)
    result = {"status": "completed", "mapping_directory": str(Path(mapping_directory).resolve()),
              "output": str(output.resolve()), "frames": len(indices), "frame_interval": [first, last+1],
              "width": width, "height": height, "fps": str(fps), "duration_s": len(indices)/float(fps),
              "elapsed_s": time.monotonic()-start, "frames_with_visible_mesh_pixels": visible_frames,
              "mapped_samples_per_hand": arrays["mapping_valid"].sum(axis=0).tolist(),
              "validation": "Frame count, dimensions, timestamps and full decode passed",
              "projection": "Aligned camera poses; original pinhole intrinsics; CV-to-OpenGL axis conversion",
              "renderer": f"pyrender {pyrender.__version__}", "opacity": opacity,
              "limitations": "No real-scene depth occlusion; uncalibrated reconstruction/physical contact; missing/infilled mappings hidden"}
    write_json(report_path, result)
    return result
