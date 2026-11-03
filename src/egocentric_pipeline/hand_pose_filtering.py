"""Offline Savitzky–Golay targets in aligned-frame metres and rotations.

Source observations are never edited. Each eligible hand span is independent,
including at region boundaries. No resampling or missing-data interpolation.
"""

import numpy as np
from scipy.signal import savgol_coeffs, savgol_filter
from scipy.spatial.transform import Rotation

from .manipulation_regions import frame_edges


def validate_filter_settings(settings):
    for key in ("hand_position_window_s", "hand_orientation_window_s"):
        value = settings.get(key, 0.)
        if not np.isfinite(value) or value < 0:
            raise ValueError(f"{key} must be nonnegative finite; zero disables filtering")
    order = settings.get("hand_filter_polyorder", 2)
    if type(order) is not int or order < 0:
        raise ValueError("hand_filter_polyorder must be a nonnegative integer")


def smooth_hand_targets(positions, orientations, valid, timestamps, regions, settings):
    """Return independent [T,2,3] / [T,2,3,3] targets and span diagnostics.

    Windows round to the nearest odd sample count (ties round upward). XYZ uses
    mode='interp'. For rotation i, fit log(R_i.T @ R_j) over the same local
    window and evaluate at i, then return R_i @ exp(filtered log). This avoids
    quaternion-sign and global +/-pi discontinuities. Relative rotations at the
    log cut locus (pi) are ambiguous: leave that sample unchanged and report it.
    """
    validate_filter_settings(settings)
    frame_edges(timestamps)
    p, r = np.array(positions, copy=True), np.array(orientations, copy=True)
    valid = np.asarray(valid)
    if (p.shape != (len(timestamps), 2, 3) or r.shape != (len(timestamps), 2, 3, 3)
            or valid.shape != (len(timestamps), 2) or valid.dtype != bool):
        raise ValueError("Expected positions [T,2,3], rotations [T,2,3,3], boolean eligibility [T,2]")
    if not np.isfinite(p[valid]).all() or not np.isfinite(r[valid]).all():
        raise ValueError("Eligible hand targets must be finite")
    if (not np.allclose(r[valid].transpose(0, 2, 1) @ r[valid], np.eye(3), atol=1e-6)
            or not np.allclose(np.linalg.det(r[valid]), 1., atol=1e-6)):
        raise ValueError("Eligible hand orientations must be proper rotations")
    windows = [settings.get(k, 0.) for k in ("hand_position_window_s", "hand_orientation_window_s")]
    dt = np.diff(timestamps)
    if any(windows) and not np.allclose(dt, np.median(dt), atol=1e-7, rtol=1e-5):
        raise ValueError("Hand smoothing requires uniform timestamps; set hand_position_window_s and hand_orientation_window_s to 0 for irregular input")
    counts = [2 * int(np.floor(w / (2 * np.median(dt)) + 1e-10)) + 1 if w else 0 for w in windows]
    order = settings.get("hand_filter_polyorder", 2)
    if any(count and count <= order for count in counts):
        raise ValueError("Hand smoothing window must contain more samples than hand_filter_polyorder; increase the window or disable it")
    diagnostics = {"window_samples": dict(zip(("position", "orientation"), counts)),
                   "polyorder": order, "endpoint_mode": "polynomial interpolation within first/last full window",
                   "spans": [], "ambiguous_rotation_samples": []}
    for region in regions:
        for hand in range(2):
            start, stop = region["start"], region["stop"]
            changes = np.diff(np.r_[False, valid[start:stop, hand], False].astype(int))
            for a, b in zip(np.flatnonzero(changes == 1) + start, np.flatnonzero(changes == -1) + start):
                span = {"hand": hand, "start": int(a), "stop": int(b)}
                for name, count in zip(("position", "orientation"), counts):
                    span[name] = "disabled" if not count else "too_short" if b - a < count else "filtered"
                diagnostics["spans"].append(span)
                if span["position"] == "filtered":
                    p[a:b, hand] = savgol_filter(positions[a:b, hand], counts[0], order, axis=0, mode="interp")
                if span["orientation"] != "filtered":
                    continue
                count = counts[1]
                coefficients = {i: savgol_coeffs(count, order, pos=i, use="dot") for i in range(count)}
                for i in range(a, b):
                    lo = min(max(i - count // 2, a), b - count)
                    reference = orientations[i, hand]
                    local = Rotation.from_matrix(reference.T @ orientations[lo:lo + count, hand]).as_rotvec()
                    if np.any(np.linalg.norm(local, axis=1) >= np.pi - 1e-6):
                        diagnostics["ambiguous_rotation_samples"].append({"frame": int(i), "hand": hand})
                        continue
                    r[i, hand] = reference @ Rotation.from_rotvec(coefficients[i - lo] @ local).as_matrix()
    return p, r, diagnostics
