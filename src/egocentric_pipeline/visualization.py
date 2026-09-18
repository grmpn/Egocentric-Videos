"""Render native world geometry onto RGB, and plot unchanged world translations.

Heavy upstream imports run in a separate process with HaWoR as its working
directory, keeping licensed assets and GPU libraries outside CPU-safe imports.
"""

import argparse
from fractions import Fraction
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import TYPE_CHECKING

import numpy as np

from .run_metadata import sha256_file

if TYPE_CHECKING:
    from .video_preparation import PreparedClip


HAND_COLORS = ((0.10, 0.75, 0.65), (0.90, 0.35, 0.65))


def visualize(native_directory: Path, prepared: "PreparedClip", trajectory_path: Path,
              output_directory: Path, hawor_root: Path) -> dict:
    """Create an exact-frame-count 30 FPS RGB overlay and world-coordinate plot."""
    output_directory = Path(output_directory).resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    log_path = output_directory / "visualization.log"
    for name in ("overlay.mp4", "trajectory_preview.png", log_path.name):
        if (output_directory / name).exists():
            raise FileExistsError(f"Visualization artifact already exists: {output_directory / name}")
    command = [sys.executable, "-m", "egocentric_pipeline.visualization",
               "--native-directory", str(Path(native_directory).resolve()),
               "--clip-metadata", str(prepared.metadata_path.resolve()),
               "--trajectory", str(Path(trajectory_path).resolve()),
               "--output-directory", str(output_directory)]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join((str(Path(__file__).resolve().parents[1]), str(Path(hawor_root).resolve())))
    environment["MPLBACKEND"] = "Agg"
    if Path("/usr/lib/wsl/lib").is_dir():
        environment["LD_LIBRARY_PATH"] = "/usr/lib/wsl/lib:" + environment.get("LD_LIBRARY_PATH", "")
    with tempfile.TemporaryDirectory(prefix="hawor-render-cache-") as cache:
        environment["MPLCONFIGDIR"] = cache
        with log_path.open("x", encoding="utf-8") as log:
            log.write("Command: " + json.dumps(command) + "\n")
            log.flush()
            result = subprocess.run(command, cwd=hawor_root, env=environment, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"HaWoR overlay rendering failed with exit {result.returncode}; inspect {log_path}")
    result = json.loads(log_path.read_text(encoding="utf-8").splitlines()[-1])
    result["render_log"] = str(log_path)
    return result


def _render(native_directory, prepared, trajectory_path, output_directory):
    import cv2
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    import torch
    from pytorch3d.renderer import Materials
    from hawor.utils.process import run_mano, run_mano_left
    from lib.eval_utils.custom_utils import load_slam_cam
    from lib.vis.renderer import Renderer, create_meshes

    if not torch.cuda.is_available():
        raise RuntimeError("The HaWoR overlay needs the validated CUDA environment")
    native_world_path = native_directory / "world_space_res.pth"
    native_hash = sha256_file(native_world_path)
    trajectory_hash = sha256_file(trajectory_path)
    with np.load(trajectory_path, allow_pickle=False) as data:
        arrays = {name: data[name] for name in data.files}
    frame_count = prepared.metadata.prepared["frame_count"]
    width = prepared.metadata.prepared["width"]
    height = prepared.metadata.prepared["height"]
    focal = prepared.metadata.hawor_camera["focal_length_px"]
    if arrays["export_valid"].shape != (frame_count, 2):
        raise ValueError("Exported validity shape does not match prepared frames")
    camera_path = native_directory / "SLAM" / f"hawor_slam_w_scale_0_{frame_count}.npz"
    with np.load(camera_path, allow_pickle=False) as native_camera:
        if (float(native_camera["img_focal"]) != focal
                or not np.array_equal(native_camera["img_center"], [width / 2, height / 2])):
            raise ValueError("Native camera intrinsics disagree with the prepared focal length or image centre")
    R_w2c, t_w2c, _, _ = load_slam_cam(camera_path)
    if R_w2c.shape != (frame_count, 3, 3) or t_w2c.shape != (frame_count, 3):
        raise ValueError("Native camera count differs from prepared frame count")
    if not torch.isfinite(R_w2c).all() or not torch.isfinite(t_w2c).all():
        raise ValueError("Native camera poses contain nonfinite values")
    renderer = Renderer(width, height, focal, "cuda", bin_size=128, max_faces_per_bin=20000)
    vertices_by_hand = []
    faces_by_hand = []
    with torch.no_grad():
        for hand, mano in enumerate((run_mano_left, run_mano)):
            valid_frames = np.flatnonzero(arrays["export_valid"][:, hand])
            if not len(valid_frames):
                vertices_by_hand.append({})
                faces_by_hand.append(None)
                continue
            parameters = [torch.from_numpy(arrays[field][valid_frames, hand][None].copy())
                          for field in ("root_translation_world_m", "root_orientation_world_axis_angle",
                                        "hand_pose_axis_angle", "mano_betas")]
            output = mano(parameters[0], parameters[1], parameters[2],
                          is_right=torch.full((1, len(valid_frames), 1), float(hand)), betas=parameters[3])
            vertices_by_hand.append({int(frame): output["vertices"][0, index] for index, frame in enumerate(valid_frames)})
            faces_by_hand.append(output["faces"][0, 0].long().cuda())

    overlay_path = output_directory / "overlay.mp4"
    preview_path = output_directory / "trajectory_preview.png"
    if overlay_path.exists() or preview_path.exists():
        raise FileExistsError("Visualization outputs already exist; use a new run directory")
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-n", "-f", "rawvideo",
               "-pix_fmt", "rgb24", "-video_size", f"{width}x{height}", "-framerate", "30", "-i", "pipe:0",
               "-an", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(overlay_path)]
    capture = cv2.VideoCapture(str(prepared.video_path))
    if not capture.isOpened():
        raise ValueError(f"Cannot decode prepared RGB video: {prepared.video_path}")
    writer = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        with torch.no_grad():
            for frame_index in range(frame_count):
                success, bgr = capture.read()
                if not success or bgr.shape[:2] != (height, width):
                    raise ValueError(f"Prepared RGB decoding or geometry failed at frame {frame_index}")
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                active_hands = [hand for hand in range(2) if frame_index in vertices_by_hand[hand]]
                if active_hands:
                    vertices = [vertices_by_hand[hand][frame_index] for hand in active_hands]
                    faces = [faces_by_hand[hand] for hand in active_hands]
                    colors = [torch.tensor(HAND_COLORS[hand], device="cuda").expand(len(vertex), 3)
                              for hand, vertex in zip(active_hands, vertices)]
                    # Native CV camera projection already matches native world
                    # vertices. No world-axis flip or trajectory transform occurs.
                    mesh = create_meshes(vertices, faces, colors)
                    camera, lights = renderer.create_camera_from_cv(R_w2c[frame_index:frame_index+1].cuda(),
                                                                    t_w2c[frame_index:frame_index+1].cuda())
                    rendered = renderer.renderer(mesh, cameras=camera, lights=lights,
                                                 materials=Materials(device="cuda", shininess=0))[0].cpu().numpy()
                    mask = rendered[..., 3] > 0
                    rgb[mask] = np.clip(0.45 * rgb[mask] + 0.55 * rendered[..., :3][mask] * 255, 0, 255).astype(np.uint8)
                banner_height = max(34, int(height * 0.07))
                rgb[:banner_height] = (rgb[:banner_height].astype(np.float32) * 0.35).astype(np.uint8)
                scale = max(0.4, min(width / 1280, 1.0))
                for hand, name in enumerate(("Left", "Right")):
                    if not arrays["export_valid"][frame_index, hand]:
                        state = "invalid (not drawn)"
                    elif arrays["motion_infilled"][frame_index, hand]:
                        state = "motion infill"
                    else:
                        state = "direct estimation"
                    text = f"{name}: {state}"
                    color = tuple(int(channel * 255) for channel in HAND_COLORS[hand])
                    cv2.putText(rgb, text, (10 + hand * width // 2, int(banner_height * 0.45)),
                                cv2.FONT_HERSHEY_SIMPLEX, scale, color, 2, cv2.LINE_AA)
                cv2.putText(rgb, f"Frame {frame_index}/{frame_count-1}   t={frame_index/30:.3f}s   native world projection",
                            (10, int(banner_height * 0.87)), cv2.FONT_HERSHEY_SIMPLEX, scale * 0.7,
                            (240, 240, 240), 1, cv2.LINE_AA)
                writer.stdin.write(rgb.tobytes())
                if (frame_index + 1) % 30 == 0 or frame_index + 1 == frame_count:
                    print(f"Rendered {frame_index + 1}/{frame_count} overlay frames", flush=True)
        if capture.read()[0]:
            raise ValueError("Prepared RGB video has more frames than the exported trajectory")
        writer.stdin.close()
        stderr = writer.stderr.read().decode("utf-8", errors="replace")
        if writer.wait() != 0:
            raise RuntimeError(f"Overlay encoding failed: {stderr}")
    finally:
        capture.release()
        if writer.poll() is None:
            writer.terminate()
            writer.wait()
        if not writer.stdin.closed:
            writer.stdin.close()
        writer.stderr.close()

    figure = plt.figure(figsize=(8, 6))
    axes = figure.add_subplot(111, projection="3d")
    for hand, name in enumerate(("Left", "Right")):
        points = arrays["root_translation_world_m"][:, hand].copy()
        # NaNs hide invalid samples from this plot; no derived trajectory is saved.
        points[~arrays["export_valid"][:, hand]] = np.nan
        axes.plot(points[:, 0], points[:, 1], points[:, 2], color=HAND_COLORS[hand], label=name)
        infilled = arrays["motion_infilled"][:, hand] & arrays["export_valid"][:, hand]
        axes.scatter(*points[infilled].T, color=HAND_COLORS[hand], marker="x", s=12)
    axes.set(xlabel="HaWoR world X (m)", ylabel="HaWoR world Y (m)", zlabel="HaWoR world Z (m)",
             title="Unchanged MANO root translations\nClip-local SLAM world axes; crosses mark motion infill")
    for axis in (axes.xaxis, axes.yaxis, axes.zaxis):
        axis.set_major_locator(MaxNLocator(nbins=4))
        axis.labelpad = 12
    finite_points = arrays["root_translation_world_m"][arrays["export_valid"]]
    if len(finite_points):
        axes.set_box_aspect(np.maximum(np.ptp(finite_points, axis=0), 1e-6))
    axes.legend()
    figure.tight_layout()
    figure.savefig(preview_path, dpi=140)
    plt.close(figure)

    probe_command = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_frames",
                     "-show_entries", "stream=width,height,r_frame_rate,nb_read_frames:frame=best_effort_timestamp_time",
                     "-of", "json", str(overlay_path)]
    probe = json.loads(subprocess.run(probe_command, check=True, capture_output=True, text=True).stdout)
    stream = probe["streams"][0]
    timestamps = np.array([float(frame["best_effort_timestamp_time"]) for frame in probe["frames"]])
    if (int(stream["nb_read_frames"]) != frame_count or stream["width"] != width or stream["height"] != height
            or Fraction(stream["r_frame_rate"]) != 30 or len(timestamps) != frame_count
            or not np.allclose(timestamps, np.arange(frame_count) / 30, rtol=0, atol=1e-6)):
        raise ValueError("Rendered overlay failed frame-count, dimensions, or 30 FPS timestamp validation")
    subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(overlay_path), "-map", "0:v:0", "-f", "null", "-"], check=True)
    if sha256_file(native_world_path) != native_hash or sha256_file(trajectory_path) != trajectory_hash:
        raise AssertionError("Visualization changed stored trajectory data")
    return {"overlay": str(overlay_path), "trajectory_preview": str(preview_path),
            "validation": {"frame_count": frame_count, "width": width, "height": height, "fps": 30,
                           "decodable": True, "timestamps_match_prepared": True,
                           "native_camera_intrinsics_match_prepared": True,
                           "native_world_sha256_unchanged": native_hash,
                           "trajectory_sha256_unchanged": trajectory_hash,
                           "renderer": "HaWoR Renderer/create_camera_from_cv/create_meshes",
                           "display_transform": "Native camera projection only; stored world arrays unchanged.",
                           "overlay_sha256": sha256_file(overlay_path), "preview_sha256": sha256_file(preview_path),
                           "ffmpeg_command": command, "ffprobe_command": probe_command}}


def main():
    from .video_preparation import load_prepared_clip
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-directory", type=Path, required=True)
    parser.add_argument("--clip-metadata", type=Path, required=True)
    parser.add_argument("--trajectory", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    prepared = load_prepared_clip(args.clip_metadata)
    result = _render(args.native_directory, prepared, args.trajectory, args.output_directory)
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
