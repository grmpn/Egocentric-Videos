"""Static, shareable camera/wrist comparison figures; paths retain missing gaps."""

import numpy as np


def plot_shared_hands(output, hands, focal_px):
    """Inspect the shared metric hand geometry on six source RGB frames."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image

    paths = sorted((output / "input/rgb/extracted_images").glob("*.jpg"))
    indices = np.linspace(0, len(paths) - 1, 6, dtype=int)
    fig, axes = plt.subplots(2, 3, figsize=(16, 7))
    for ax, index in zip(axes.flat, indices):
        rgb = np.asarray(Image.open(paths[index]))
        height, width = rgb.shape[:2]
        ax.imshow(rgb)
        labels = []
        for hand, (name, color) in enumerate((("Left", "#00FFFF"), ("Right", "#FF55FF"))):
            valid = hands["valid"][index, hand]
            labels.append(f"{name}: {'observed' if valid else 'missing'}")
            if not valid:
                continue
            joints = hands["joints_camera_m"][index, hand]
            vertices = hands["vertices_camera_m"][index, hand]
            for points, size, alpha in ((vertices, .5, .25), (joints, 7, 1)):
                front = points[:, 2] > 0
                uv = focal_px * points[front, :2] / points[front, 2:] + [width / 2, height / 2]
                ax.scatter(*uv.T, s=size, color=color, alpha=alpha)
            if np.all(joints[:, 2] > 0):
                uv = focal_px * joints[:, :2] / joints[:, 2:] + [width / 2, height / 2]
                for start in (1, 4, 7, 10, 13):
                    chain = [0, start, start + 1, start + 2]
                    ax.plot(*uv[chain].T, color=color, lw=.8)
        ax.set(xlim=(0, width), ylim=(height, 0), title=f"Frame {index} · {' / '.join(labels)}")
        ax.axis("off")
    fig.suptitle("Shared camera-space hands • cyan left / magenta right • missing estimates omitted")
    fig.tight_layout()
    fig.savefig(output / "hand_overlays.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_comparison(output, trajectories, times, curves, runtime):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {"hawor": "#0072B2", "lingbot": "#D55E00", "amb3r": "#009E73"}
    channels = ["Camera", "Left wrist", "Right wrist"]
    def path(item, channel):
        return item["camera_pose"][:, :3, 3] if channel == 0 else item["joints_m"][:, channel - 1, 0]
    fig = plt.figure(figsize=(16, 10))
    for channel in range(3):
        xyz = fig.add_subplot(2, 3, channel + 1, projection="3d")
        xy = fig.add_subplot(2, 3, channel + 4)
        all_points = []
        for name, item in trajectories.items():
            p = path(item, channel)
            xyz.plot(*p.T, color=colors[name], label=name, lw=1)
            xy.plot(p[:, 0], p[:, 1], color=colors[name], label=name, lw=1)
            all_points.append(p[np.isfinite(p).all(axis=1)])
        points = np.concatenate(all_points)
        if len(points):
            lo, hi = points.min(axis=0), points.max(axis=0)
            center = (lo + hi) / 2
            radius = max(float((hi - lo).max()) / 2, .05) * 1.05
            for i, setter in enumerate((xyz.set_xlim, xyz.set_ylim, xyz.set_zlim)):
                setter(center[i] - radius, center[i] + radius)
            xyz.set_box_aspect((1, 1, 1))
        xyz.set(title=channels[channel], xlabel="X (m)", ylabel="Y (m)", zlabel="Z (m)")
        xy.set(xlabel="X (m)", ylabel="Y (m)", aspect="equal")
        xyz.legend(fontsize=8); xy.grid(alpha=.25)
    fig.suptitle("Same initial camera pose • Z up • pairwise comparison, no ground truth")
    # 3D axis labels can extend beyond their reported tight bounding boxes.
    fig.tight_layout(rect=(.025, .025, .94, .95))
    fig.savefig(output / "trajectories.png", dpi=180); plt.close(fig)
    fig, axes = plt.subplots(3, 3, figsize=(15, 10), sharex=True)
    for channel in range(3):
        for axis in range(3):
            for name, item in trajectories.items():
                axes[channel, axis].plot(times, path(item, channel)[:, axis], label=name, color=colors[name], lw=1)
            axes[channel, axis].set(ylabel=f"{channels[channel]} {'XYZ'[axis]} (m)", xlabel="Time (s)")
            axes[channel, axis].grid(alpha=.25)
    axes[0, 0].legend(); fig.tight_layout(); fig.savefig(output / "coordinates.png", dpi=180, bbox_inches="tight"); plt.close(fig)
    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    for row, channel in enumerate(("camera", "left_wrist", "right_wrist")):
        for key, distance in curves.items():
            kind, a, b = key.split("__")
            if kind == channel:
                axes[row].plot(times, distance, label=f"{a} vs {b}", lw=1)
        axes[row].set(ylabel=f"{channel}\ndisagreement (m)")
        axes[row].grid(alpha=.25); axes[row].legend()
    axes[-1].set_xlabel("Time (s)")
    fig.tight_layout(); fig.savefig(output / "disagreement.png", dpi=180, bbox_inches="tight"); plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 5))
    bottom = np.zeros(len(runtime))
    for key, label in [("shared_hands_gravity_s", "Shared hands + gravity"), ("metric3d_s", "Shared metric depth"),
                       ("backend_stage_s", "Backend stage"), ("scale_fit_s", "Scale fit"),
                       ("alignment_export_s", "Alignment + export")]:
        values = [r[key] for r in runtime]
        ax.bar([r["method"] for r in runtime], values, bottom=bottom, label=label)
        bottom += values
    ax.set(ylabel="Seconds", title="Single-run assembled processing times")
    ax.legend(); fig.tight_layout(); fig.savefig(output / "runtime.png", dpi=180, bbox_inches="tight"); plt.close(fig)
