"""Validity-aware hand trajectory accuracy in metres and seconds.

The common artifact uses [time, left/right, joint, xyz], with 21 joints ordered
wrist, thumb, index, middle, ring, pinky (four joints per finger). Rotations map
MANO wrist axes into world axes; camera transforms map OpenCV camera to world.
hand_valid describes camera-relative output; world validity also needs a camera.
up_world is estimated from RGB for predictions and the dataset convention for GT.
"""

import warnings

import numpy as np
from scipy.spatial.transform import Rotation

from egocentric_pipeline.geometry.gravity_alignment import gravity_basis


JOINT_ORDER = "mano21_thumb_first_v1"
HANDS = ("left", "right")


def validate_trajectory(data):
    """Reject inconsistent time, identity, units/geometry and validity contracts."""
    times = np.asarray(data["timestamp_s"])
    n = len(times)
    shapes = {"timestamp_s": (n,), "frame_index": (n,), "joints_camera_m": (n, 2, 21, 3),
              "joints_world_m": (n, 2, 21, 3), "wrist_rotation_world": (n, 2, 3, 3),
              "camera_to_world": (n, 4, 4), "hand_valid": (n, 2), "camera_valid": (n,),
              "direct_valid": (n, 2), "infilled": (n, 2), "up_world": (3,)}
    if n < 2 or not np.isfinite(times).all() or np.any(np.diff(times) <= 0):
        raise ValueError("Need at least two strictly increasing finite timestamps")
    for name, shape in shapes.items():
        if np.shape(data[name]) != shape:
            raise ValueError(f"{name} must have shape {shape}")
    if str(data["joint_order"]) != JOINT_ORDER:
        raise ValueError("Convert the native joint order before evaluation")
    frames = np.asarray(data["frame_index"])
    if frames.dtype.kind not in "iu" or np.any(np.diff(frames) <= 0):
        raise ValueError("frame_index must contain increasing source frame integers")
    for name in ("hand_valid", "camera_valid", "direct_valid", "infilled"):
        if np.asarray(data[name]).dtype != bool:
            raise ValueError(f"{name} must be boolean")
    hand, camera = data["hand_valid"], data["camera_valid"]
    if np.any(data["direct_valid"] & data["infilled"]):
        raise ValueError("Direct estimation and infilling must be disjoint")
    if np.any((data["direct_valid"] | data["infilled"]) & ~hand):
        raise ValueError("Provenance cannot claim a missing hand result")
    world = hand & camera[:, None]
    for field, valid in (("joints_camera_m", hand), ("joints_world_m", world),
                         ("wrist_rotation_world", world), ("camera_to_world", camera)):
        if not np.isfinite(data[field][valid]).all():
            raise ValueError(f"{field} contains nonfinite valid samples")
    for rotations in (data["camera_to_world"][camera, :3, :3], data["wrist_rotation_world"][world]):
        if (not np.allclose(rotations @ rotations.swapaxes(-1, -2), np.eye(3), atol=2e-4, rtol=0)
                or not np.allclose(np.linalg.det(rotations), 1, atol=2e-4, rtol=0)):
            raise ValueError("Camera and wrist orientations must be proper rotations")
    if not np.allclose(data["camera_to_world"][camera, 3], [0, 0, 0, 1], atol=1e-6, rtol=0):
        raise ValueError("Invalid camera homogeneous transform")
    poses = data["camera_to_world"]
    composed = np.einsum("tij,thkj->thki", poses[:, :3, :3], data["joints_camera_m"]) + poses[:, None, None, :3, 3]
    if not np.allclose(composed[world], data["joints_world_m"][world], atol=2e-5, rtol=1e-6):
        raise ValueError("World/camera joints disagree; check transform direction, units and timestamps")
    gravity_basis(data["up_world"])


def load_trajectory(path):
    with np.load(path, allow_pickle=False) as archive:
        data = dict(archive)
    validate_trajectory(data)
    return data


def level_world(data):
    """One constant proper rotation; preserve gravity errors and metric scale."""
    basis, _ = gravity_basis(data["up_world"])
    poses = data["camera_to_world"].copy()
    poses[:, :3, :3] = basis @ poses[:, :3, :3]
    poses[:, :3, 3] = poses[:, :3, 3] @ basis.T
    return {**data, "joints_world_m": data["joints_world_m"] @ basis.T,
            "wrist_rotation_world": basis @ data["wrist_rotation_world"],
            "camera_to_world": poses, "up_world": np.array([0., 0., 1.])}


def initial_yaw_translation(predicted, reference, times, valid, window_s):
    """Fit one yaw/translation from the fixed initial window, pooling both wrists.

    No search for a later convenient start, no scale, no pitch/roll correction.
    Stationary separated wrists still identify yaw; coincident horizontal points
    or zero horizontal cross-correlation do not.
    """
    support = valid & ((times - times[0]) < window_s)[:, None]
    a, b = predicted[support], reference[support]
    if len(a) < 2:
        return None
    ma, mb = a.mean(axis=0), b.mean(axis=0)
    aa, bb = a - ma, b - mb
    cosine = np.sum(aa[:, :2] * bb[:, :2])
    sine = np.sum(aa[:, 0] * bb[:, 1] - aa[:, 1] * bb[:, 0])
    spread = np.linalg.norm(aa[:, :2]) * np.linalg.norm(bb[:, :2])
    if spread < 1e-12 or np.hypot(cosine, sine) < 1e-8 * spread:
        return None
    yaw = np.arctan2(sine, cosine)
    rotation = Rotation.from_euler("z", yaw).as_matrix()
    translation = mb - rotation @ ma
    return {"rotation": rotation, "translation": translation, "yaw_rad": float(yaw),
            "fit_samples": int(support.sum()), "window_s": float(window_s)}


def interval_pairs(times, frame_index, valid, interval_s, tolerance_s):
    """All forward pairs at the requested duration, without crossing missing data."""
    times = np.asarray(times)
    if interval_s <= 0 or tolerance_s < 0 or tolerance_s >= interval_s / 2:
        raise ValueError("Invalid interval or timestamp tolerance")
    target = times + interval_s
    upper = np.searchsorted(times, target)
    upper = np.minimum(upper, len(times) - 1)
    lower = np.maximum(upper - 1, 0)
    j = np.where(abs(times[lower] - target) < abs(times[upper] - target), lower, upper)
    i = np.arange(len(times))
    missing = np.concatenate(([0], np.cumsum(~valid)))
    frame_gaps = np.concatenate(([0], np.cumsum(np.diff(frame_index) != 1)))
    keep = ((j > i) & (abs(times[j] - target) <= tolerance_s)
            & (missing[j + 1] == missing[i]) & (frame_gaps[j] == frame_gaps[i]))
    return i[keep], j[keep]


def relative_translation_error(pred_position, pred_rotation, gt_position, gt_rotation, i, j):
    """Norm of trans((G_i^-1 G_j)^-1 (P_i^-1 P_j)), in metres.

    The outer GT relative rotation preserves the norm, so only the translations
    expressed in each starting wrist frame are needed. This includes orientation
    errors and is not a comparison of path lengths or displacement magnitudes.
    """
    pd = np.einsum("nji,nj->ni", pred_rotation[i], pred_position[j] - pred_position[i])
    gd = np.einsum("nji,nj->ni", gt_rotation[i], gt_position[j] - gt_position[i])
    return np.linalg.norm(pd - gd, axis=1)


def finger_pa_error(predicted, reference):
    """Proper similarity fitted to 21 joints; return mean distance on fingers only.

    SciPy's existing Kabsch solver enforces det(R)=+1. Reject degenerate geometry;
    allowing a reflection would hide a left/right conversion error.
    """
    a = predicted - predicted.mean(axis=0)
    b = reference - reference.mean(axis=0)
    if min(np.linalg.matrix_rank(a, tol=1e-10), np.linalg.matrix_rank(b, tol=1e-10)) < 2:
        return np.nan
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        try:
            rotation, _ = Rotation.align_vectors(b, a)
        except UserWarning:
            return np.nan
    rotated = rotation.apply(a)
    scale = np.sum(rotated * b) / np.sum(a * a)
    if scale <= 0:
        return np.nan
    return float(np.linalg.norm(scale * rotated[1:] - b[1:], axis=-1).mean())


def metric(values, *, reduction="mean", unit="mm"):
    values = np.asarray(values)
    values = values[np.isfinite(values)]
    value = None
    if len(values):
        value = float(np.sqrt(np.mean(values ** 2)) if reduction == "rmse"
                      else np.median(values) if reduction == "median" else np.mean(values))
    return {"value": value, "samples": len(values), "unit": unit, "reduction": reduction}


def metric_support(predicted, reference):
    hand = predicted["hand_valid"] & reference["hand_valid"]
    camera = predicted["camera_valid"] & reference["camera_valid"]
    return {"world": hand & camera[:, None],
            "local": hand & reference["camera_valid"][:, None]}


def evaluate_trajectory(predicted, reference, settings, *, common_support=None):
    """Return per-hand summaries and frame/pair curves; never fill missing samples.

    common_support optionally restricts scoring to the intersection across methods.
    Initial alignment always uses the method's own initial support so comparing
    support does not change the fitted trajectory. Completeness always uses GT.
    """
    for data in (predicted, reference):
        validate_trajectory(data)
    if (not np.array_equal(predicted["frame_index"], reference["frame_index"])
            or not np.allclose(predicted["timestamp_s"], reference["timestamp_s"], atol=1e-8, rtol=0)):
        raise ValueError("Prediction and reference must share the exact frame/timestamp mapping")
    pred, gt = level_world(predicted), level_world(reference)
    times, frames = gt["timestamp_s"], gt["frame_index"]
    support = metric_support(pred, gt)
    pw, gw = pred["joints_world_m"][:, :, 0], gt["joints_world_m"][:, :, 0]
    alignment = initial_yaw_translation(pw, gw, times, support["world"], settings["initial_alignment_s"])
    aligned = np.full_like(pw, np.nan) if alignment is None else pw @ alignment["rotation"].T + alignment["translation"]
    if common_support is not None:
        support = {key: value & common_support[key] for key, value in support.items()}
    oracle = np.einsum("tij,thj->thi", gt["camera_to_world"][:, :3, :3], pred["joints_camera_m"][:, :, 0])
    oracle += gt["camera_to_world"][:, None, :3, 3]
    curves = {"timestamp_s": times,
              "predicted_wrist_aligned_m": np.where(support["world"][..., None], aligned, np.nan),
              "gt_wrist_m": np.where((gt["hand_valid"] & gt["camera_valid"][:, None])[..., None], gw, np.nan),
              "initial_error_mm": np.where(support["world"], np.linalg.norm(aligned - gw, axis=-1) * 1000, np.nan),
              "gt_camera_error_mm": np.where(support["local"], np.linalg.norm(oracle - gw, axis=-1) * 1000, np.nan)}
    hands = {}
    for h, name in enumerate(HANDS):
        valid = support["world"][:, h]
        rows = {"initial_wrist_error": metric(curves["initial_error_mm"][:, h]),
                "gt_camera_wrist_error": metric(curves["gt_camera_error_mm"][:, h])}
        for interval in settings["rpe_intervals_s"]:
            i, j = interval_pairs(times, frames, valid, interval, settings["timestamp_tolerance_s"])
            errors = relative_translation_error(pw[:, h], pred["wrist_rotation_world"][:, h],
                                                gw[:, h], gt["wrist_rotation_world"][:, h], i, j) * 1000
            key = f"rpe_{interval:g}s"
            rows[key] = metric(errors, reduction="rmse")
            curves[f"{name}_{key}"] = np.column_stack((i, j, errors))
        i, j = interval_pairs(times, frames, valid, settings["scale_interval_s"], settings["timestamp_tolerance_s"])
        numerator = np.linalg.norm(pw[j, h] - pw[i, h], axis=-1)
        denominator = np.linalg.norm(gw[j, h] - gw[i, h], axis=-1)
        moving = denominator >= settings["scale_min_gt_displacement_m"]
        ratios = numerator[moving] / denominator[moving]
        rows["scale_ratio"] = {**metric(ratios, reduction="median", unit="ratio"),
                                "low_motion_pairs": int((~moving).sum()), "valid_pairs": len(i)}
        curves[f"{name}_scale_ratio"] = np.column_stack((i[moving], j[moving], ratios))
        pa = np.full(len(times), np.nan)
        for t in np.flatnonzero(support["local"][:, h]):
            pa[t] = finger_pa_error(pred["joints_camera_m"][t, h], gt["joints_camera_m"][t, h]) * 1000
        curves[f"{name}_finger_pa_mm"] = pa
        rows["finger_pa_mpjpe"] = metric(pa)
        gt_valid = gt["hand_valid"][:, h] & gt["camera_valid"]
        world_valid = pred["hand_valid"][:, h] & pred["camera_valid"]
        for key, available in (("completeness", world_valid), ("direct_completeness", world_valid & pred["direct_valid"][:, h]),
                               ("infilled_completeness", world_valid & pred["infilled"][:, h])):
            rows[key] = metric(available[gt_valid] * 100., unit="percent")
        rows["camera_completeness"] = metric(pred["camera_valid"][gt["camera_valid"]] * 100., unit="percent")
        hands[name] = rows
    alignment_report = None if alignment is None else {key: value.tolist() if isinstance(value, np.ndarray) else value for key, value in alignment.items()}
    return {"hands": hands, "alignment": alignment_report,
            "support": "common" if common_support is not None else "method"}, curves
