"""Scientific review figures for the hand benchmark, with metres and shared axes."""

from pathlib import Path

import numpy as np


def reference_overlays(clips, output_root, *, prediction_method=None):
    """Project released GT joints into first/middle/last RGB frames of every clip."""
    import cv2
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from egocentric_pipeline.evaluation.hand_trajectory import load_trajectory

    output_root = Path(output_root)
    fig, axes = plt.subplots(len(clips), 3, figsize=(16, 3.2 * len(clips)), squeeze=False)
    for row, clip in enumerate(clips):
        seq = clip["clip"]["sequence_id"]
        data = load_trajectory(output_root / "reference" / seq / "reference.npz")
        prediction = None if prediction_method is None else load_trajectory(
            output_root / prediction_method / seq / "prediction.npz")
        capture = cv2.VideoCapture(clip["video"])
        try:
            for column, frame in enumerate((0, len(data["timestamp_s"]) // 2, len(data["timestamp_s"]) - 1)):
                capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
                ok, rgb = capture.read()
                if not ok:
                    raise ValueError(f"Cannot decode {seq} frame {frame}")
                ax = axes[row, column]
                ax.imshow(cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB))
                for source, colors, style in ((data, ("cyan", "magenta"), "-"),
                                               (prediction, ("yellow", "orange"), "--")):
                    if source is None:
                        continue
                    for hand, color in enumerate(colors):
                        if not source["hand_valid"][frame, hand]:
                            continue
                        xyz = source["joints_camera_m"][frame, hand]
                        projected = xyz @ np.asarray(clip["intrinsics"]).T
                        xy = projected[:, :2] / projected[:, 2, None]
                        xy[xyz[:, 2] <= 0] = np.nan
                        for finger in range(5):
                            chain = [0, *range(1 + 4 * finger, 5 + 4 * finger)]
                            ax.plot(*xy[chain].T, color=color, linestyle=style, linewidth=1.2, marker=".", markersize=3)
                ax.set_xlim(0, rgb.shape[1])
                ax.set_ylim(rgb.shape[0], 0)
                ax.set_title(f"{seq} · frame {frame} · {data['timestamp_s'][frame]:.2f} s")
                ax.axis("off")
        finally:
            capture.release()
    title = "TACO reference projection · left cyan / right magenta · released fitted MANO poses"
    if prediction_method:
        title += f"\n{prediction_method} prediction · left yellow / right orange · dashed"
    fig.suptitle(title)
    fig.tight_layout()
    destination = output_root / ("reference-overlays.png" if prediction_method is None else f"{prediction_method}-overlays.png")
    fig.savefig(destination, dpi=140)
    plt.close(fig)
    return destination


def wrist_trajectories(sequence_id, ground_truth, curves, destination):
    """Plot both wrists on equal metre axes; NaNs preserve missing-frame gaps."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(14, 6))
    points = [ground_truth.reshape(-1, 3)]
    points.extend(item["predicted_wrist_aligned_m"].reshape(-1, 3) for item in curves.values())
    points = np.concatenate(points)
    points = points[np.isfinite(points).all(axis=1)]
    lower, upper = points.min(axis=0), points.max(axis=0)
    center = (lower + upper) / 2
    radius = max(float((upper - lower).max()) / 2, 0.01) * 1.05
    for hand, side in enumerate(("Left", "Right")):
        ax = fig.add_subplot(1, 2, hand + 1, projection="3d")
        ax.plot(*ground_truth[:, hand].T, color="black", linewidth=2, label="GT")
        for method, item in curves.items():
            ax.plot(*item["predicted_wrist_aligned_m"][:, hand].T, label=method, linewidth=1.2)
        ax.set(xlabel="X (m)", ylabel="Y (m)", zlabel="Z / up (m)", title=f"{side} wrist")
        ax.set_xlim(center[0] - radius, center[0] + radius)
        ax.set_ylim(center[1] - radius, center[1] + radius)
        ax.set_zlim(center[2] - radius, center[2] + radius)
        ax.set_box_aspect((1, 1, 1))
        ax.legend(fontsize=8)
    fig.suptitle(f"{sequence_id} · gravity + first-second yaw/translation alignment · no scale fit")
    fig.tight_layout()
    destination = Path(destination)
    fig.savefig(destination.with_suffix(".png"), dpi=180)
    fig.savefig(destination.with_suffix(".pdf"))
    plt.close(fig)
