"""Inspect physical wrists, camera path and image-space vertical consistency."""

import cv2
import numpy as np

from .gravity_estimation import read_video_frames
from .visualization import HAND_COLORS


def save_gravity_review(output, arrays, clip, video, diagnostics):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    valid = arrays["export_valid"]
    rotation = arrays["rotation_aligned_from_world"]
    clouds = [np.concatenate((arrays[f"wrist_position_{frame}_m"][valid],
                              arrays[f"camera_position_{frame}_m"], np.zeros((1, 3))))
              for frame in ("world", "aligned")]
    radius = max(max(np.ptp(points, axis=0)) for points in clouds) * .6
    radius = max(radius, .1)
    figure = plt.figure(figsize=(14, 7))
    # Explicit margins avoid Matplotlib's 3D label clipping under constrained layout.
    figure.subplots_adjust(left=.02, right=.92, bottom=.12, top=.83, wspace=.15)
    for panel, frame in enumerate(("world", "aligned")):
        ax = figure.add_subplot(1, 2, panel + 1, projection="3d")
        for hand, name in enumerate(("Left", "Right")):
            points = arrays[f"wrist_position_{frame}_m"][:, hand]
            ax.plot(*points.T, color=HAND_COLORS[hand], label=f"{name} wrist")
            infilled = arrays["motion_infilled"][:, hand] & valid[:, hand]
            ax.scatter(*points[infilled].T, marker="x", s=18, color=HAND_COLORS[hand])
        camera = arrays[f"camera_position_{frame}_m"]
        ax.plot(*camera.T, color="slategray", label="Camera")
        ax.scatter(*camera[[0, -1]].T, c=["black", "gray"], s=20)
        basis = rotation if frame == "world" else np.eye(3)
        for axis, color in enumerate(("tab:red", "tab:green", "tab:blue")):
            direction = basis[axis] * radius * .55
            ax.quiver(0, 0, 0, *direction, color=color)
            ax.text(*direction, f"A.{'XYZ'[axis]}", color=color)
        down = -basis[2] * radius * .45
        ax.quiver(0, 0, 0, *down, color="goldenrod")
        ax.text(*down, "gravity ↓", color="darkgoldenrod")
        center = (clouds[panel].min(axis=0) + clouds[panel].max(axis=0)) / 2
        ax.set(xlim=(center[0] - radius, center[0] + radius), ylim=(center[1] - radius, center[1] + radius),
               zlim=(center[2] - radius, center[2] + radius),
               xlabel=f"{frame} X (m)", ylabel=f"{frame} Y (m)", zlabel=f"{frame} Z (m)",
               title="Original world; aligned axes shown" if panel == 0 else "Gravity-aligned; Z up")
        ax.set_box_aspect((1, 1, 1))
        ax.legend(loc="upper left")
    missing = (~valid).sum(axis=0).tolist()
    figure.suptitle(f"One rigid rotation; same origin, scale and timing\n"
                   f"Crosses: infill; line breaks: invalid (L/R {missing}); HaWoR scale unverified")
    figure.savefig(output / "trajectory_comparison.png", dpi=160)
    plt.close(figure)

    rows = diagnostics["frames"]
    selected = np.array([row["frame_index"] for row in rows])
    times = arrays["timestamp_s"][selected]
    figure, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True, layout="constrained")
    for field, ax in zip(("roll_degrees", "pitch_degrees", "angle_to_consensus_deg"), axes):
        values = np.array([row.get(field, np.nan) for row in rows])
        colors = ["tab:blue" if row.get("mad_inlier") else "tab:red" for row in rows]
        ax.scatter(times, values, c=colors, s=14)
        ax.set_ylabel(field.replace("_", " "))
        ax.grid(alpha=.25)
    axes[0].axhline(diagnostics["max_roll_degrees"], linestyle="--", color="gray")
    axes[0].axhline(-diagnostics["max_roll_degrees"], linestyle="--", color="gray")
    axes[-1].set_xlabel("Prepared clip time (s)")
    figure.suptitle("GeoCalib selected frames: blue = final inlier; red = filtered\n"
                   "Angular residual is consistency with the estimate, not ground-truth error")
    figure.savefig(output / "gravity_diagnostics.png", dpi=150)
    plt.close(figure)

    # Show the whole timeline as well as estimator support, which may be clustered.
    inliers = [row for row in rows if row.get("mad_inlier")]
    indices = [0, len(valid) // 2, len(valid) - 1] + [inliers[i]["frame_index"] for i in (0, len(inliers) // 2, len(inliers) - 1)]
    predictions = {row["frame_index"]: row for row in rows}
    frames = dict(read_video_frames(video, len(valid), indices))
    focal = clip["hawor_camera"]["focal_length_px"]
    height, width = clip["prepared"]["height"], clip["prepared"]["width"]
    intrinsic = np.array([[focal, 0, width / 2], [0, focal, height / 2], [0, 0, 1.]])
    figure, axes = plt.subplots(2, 3, figsize=(16, 9), layout="constrained")
    for ax, index in zip(axes.flat, indices):
        row = predictions.get(index, {})
        ax.imshow(cv2.cvtColor(frames[index], cv2.COLOR_BGR2RGB))
        consensus = arrays["camera_rotation_world_from_camera"][index].T @ arrays["up_world"]
        vectors = [(consensus, "yellow")]
        if "up_camera" in row:
            vectors.insert(0, (np.asarray(row["up_camera"]), "cyan"))
        for up, color in vectors:
            for x in (.25 * width, .5 * width, .75 * width):
                for y in (.3 * height, .65 * height):
                    normalized_pixel = np.array([(x - width / 2) / focal, (y - height / 2) / focal])
                    direction = up[:2] - normalized_pixel * up[2]
                    length = np.linalg.norm(direction)
                    if length > 1e-8:
                        delta = direction / length * height * .12
                        ax.annotate("", xy=(x + delta[0], y + delta[1]), xytext=(x, y),
                                    arrowprops={"arrowstyle": "->", "color": color, "lw": 1.4})
            # Horizon: up_cam.T @ inverse(K) @ pixel = 0; often outside this view.
            line = np.linalg.solve(intrinsic.T, up)
            if abs(line[1]) > 1e-8:
                xs = np.array([0, width])
                ys = -(line[0] * xs + line[2]) / line[1]
                ax.plot(xs, ys, color=color, linestyle="--", linewidth=1)
        detail = (f"roll {row['roll_degrees']:.1f}° · pitch {row['pitch_degrees']:.1f}°"
                  if "roll_degrees" in row else "World consensus; frame not sampled by estimator")
        ax.set(xlim=(0, width), ylim=(height, 0), title=f"Frame {index} · {arrays['timestamp_s'][index]:.3f}s\n{detail}")
        ax.axis("off")
    diagnostics["review_frame_indices"] = indices
    figure.suptitle("Projected UP / horizon: cyan = frame estimate; yellow = world consensus\n"
                   "Top: clip beginning/middle/end; bottom: early/middle/late inliers. No measured gravity reference.")
    figure.savefig(output / "vertical_review.png", dpi=160)
    plt.close(figure)
