"""Static, shareable camera/wrist comparison figures; paths retain missing gaps."""

import numpy as np


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
    fig.tight_layout(); fig.savefig(output / "trajectories.png", dpi=180); plt.close(fig)
    fig, axes = plt.subplots(3, 3, figsize=(15, 10), sharex=True)
    for channel in range(3):
        for axis in range(3):
            for name, item in trajectories.items():
                axes[channel, axis].plot(times, path(item, channel)[:, axis], label=name, color=colors[name], lw=1)
            axes[channel, axis].set(ylabel=f"{channels[channel]} {'XYZ'[axis]} (m)", xlabel="Time (s)")
            axes[channel, axis].grid(alpha=.25)
    axes[0, 0].legend(); fig.tight_layout(); fig.savefig(output / "coordinates.png", dpi=180); plt.close(fig)
    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    for row, channel in enumerate(("camera", "left_wrist", "right_wrist")):
        for key, distance in curves.items():
            kind, a, b = key.split("__")
            if kind == channel:
                axes[row].plot(times, distance, label=f"{a} vs {b}", lw=1)
        axes[row].set(ylabel=f"{channel}\ndisagreement (m)")
        axes[row].grid(alpha=.25); axes[row].legend()
    axes[-1].set_xlabel("Time (s)")
    fig.tight_layout(); fig.savefig(output / "disagreement.png", dpi=180); plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 5))
    bottom = np.zeros(len(runtime))
    for key, label in [("shared_hands_gravity_s", "Shared hands + gravity"), ("metric3d_s", "Shared metric depth"),
                       ("backend_stage_s", "Backend stage"), ("scale_fit_s", "Scale fit")]:
        values = [r[key] for r in runtime]
        ax.bar([r["method"] for r in runtime], values, bottom=bottom, label=label)
        bottom += values
    ax.set(ylabel="Seconds", title="Single-run assembled processing times")
    ax.legend(); fig.tight_layout(); fig.savefig(output / "runtime.png", dpi=180); plt.close(fig)
