"""Reversible, per-hand episode anchors; world arrays are never modified."""

import numpy as np
from scipy.spatial.transform import Rotation


def canonicalize(translation, orientation, valid):
    """Map [T,2,3] MANO root poses to each hand's first export-valid pose.

    Inputs are world metres, axis-angle radians, and bool [T,2], in left/right
    order. Each fixed anchor maps canonical coordinates into the clip-local
    world: p_world = R_anchor @ p_canonical + t_anchor. This preserves motion
    over time. It does not mirror left hands or change MANO articulation/shape.
    An entirely absent hand has no anchor. Invalid outputs remain NaN.
    """
    translation, orientation, valid = map(np.asarray, (translation, orientation, valid))
    if (translation.ndim != 3 or translation.shape[1:] != (2, 3)
            or orientation.shape != translation.shape or valid.shape != translation.shape[:2]
            or valid.dtype != np.bool_):
        raise ValueError("Expected translations/rotations [T,2,3] and bool validity [T,2]")
    if not np.isfinite(translation[valid]).all() or not np.isfinite(orientation[valid]).all():
        raise ValueError("Export-valid poses must be finite")
    position = np.full(translation.shape, np.nan, dtype=np.float32)
    rotation = np.full(orientation.shape, np.nan, dtype=np.float32)
    anchors = []
    for hand in range(2):
        indices = np.flatnonzero(valid[:, hand])
        if not len(indices):
            anchors.append(None)
            continue
        first = int(indices[0])
        origin = translation[first, hand].astype(np.float64)
        basis = Rotation.from_rotvec(orientation[first, hand].astype(np.float64))
        position[indices, hand] = basis.inv().apply(translation[indices, hand] - origin)
        rotation[indices, hand] = (basis.inv() * Rotation.from_rotvec(orientation[indices, hand])).as_rotvec()
        anchors.append({"frame_index": first, "translation_world_m": origin.tolist(),
                        "rotation_world_from_canonical": basis.as_matrix().tolist()})
    return position, rotation, anchors


def save_canonical_preview(path, timestamp_s, position, infilled):
    """Plot both independent hand frames in metres, with gaps and infill visible."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True, constrained_layout=True)
    for hand, name in enumerate(("Left", "Right")):
        for coordinate, color in enumerate(("tab:red", "tab:green", "tab:blue")):
            values = position[:, hand, coordinate]
            axes[hand].plot(timestamp_s, values, color=color, label="xyz"[coordinate])
            mask = infilled[:, hand] & np.isfinite(values)
            axes[hand].scatter(timestamp_s[mask], values[mask], marker="x", color=color, s=12)
        axes[hand].set_ylabel(f"{name} root (m)")
        axes[hand].legend(loc="upper right", ncol=3)
        axes[hand].grid(alpha=.2)
    axes[-1].set_xlabel("Prepared clip time (s)")
    figure.suptitle("Canonical root translation — independent first-valid hand anchors\n"
                    "Crosses: motion infill; breaks: invalid; HaWoR scale is unverified")
    figure.savefig(path, dpi=140)
    plt.close(figure)
