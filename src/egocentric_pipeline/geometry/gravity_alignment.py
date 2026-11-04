"""Gravity directions and rigid geometry in a clip-local Z-up frame.

Column-vector convention: R_destination_from_source @ point_source.
Positions are metres, rotations are radians, and gravity estimates denote UP.
"""

import numpy as np
from scipy.spatial.transform import Rotation


def unit_vectors(vectors):
    vectors = np.asarray(vectors, dtype=np.float64)
    if vectors.shape[-1:] != (3,) or not np.isfinite(vectors).all():
        raise ValueError("Directions must be finite 3-vectors")
    norms = np.linalg.norm(vectors, axis=-1, keepdims=True)
    if (norms < 1e-8).any():
        raise ValueError("Degenerate direction; cannot establish gravity")
    return vectors / norms


def gravity_basis(up_world, parallel_threshold=0.9):
    """Return one proper world-to-aligned rotation and the chosen reference axis.

    +Z is up; X is perpendicular to a fixed world reference, without fitting the
    old X direction. The reference fallback is selected once for the whole clip.
    """
    z = unit_vectors(up_world)
    if z.shape != (3,) or not 0 < parallel_threshold < 1:
        raise ValueError("Expected one up vector and a parallel threshold in (0,1)")
    reference = 1 if abs(z[0]) > parallel_threshold else 0
    x = unit_vectors(np.cross(np.eye(3)[reference], z))
    y = np.cross(z, x)
    return np.stack((x, y, z)), "world_y" if reference else "world_x"


def aggregate_up(up_camera, camera_to_world, *, min_inliers=3,
                 mad_scale=1.4826, mad_floor=1e-8, mad_thresholds=(4., 3.5, 3.)):
    """HuRo-style hemisphere alignment and component-wise MAD/median reduction.

    Inputs: [N,3] camera UP estimates and matching [N,3,3] camera-to-world
    rotations. Returns a normalized world UP and inspectable per-input decisions.
    Unlike HuRo's all-rejected fallback, inadequate support raises explicitly.
    """
    up_camera = unit_vectors(up_camera)
    rotations = np.asarray(camera_to_world, dtype=np.float64)
    if up_camera.ndim != 2 or rotations.shape != (len(up_camera), 3, 3):
        raise ValueError("Expected matched [N,3] directions and [N,3,3] rotations")
    if (not isinstance(min_inliers, int) or min_inliers < 3 or mad_scale <= 0 or mad_floor <= 0
            or len(mad_thresholds) != 3 or not np.isfinite([mad_scale, mad_floor, *mad_thresholds]).all()
            or min(mad_thresholds) <= 0):
        raise ValueError("Invalid MAD settings or min_inliers (must be at least three)")
    if len(up_camera) < min_inliers:
        raise ValueError(f"Insufficient gravity support: {len(up_camera)} < {min_inliers}")
    if (not np.isfinite(rotations).all()
            or not np.allclose(rotations @ rotations.transpose(0, 2, 1), np.eye(3), atol=1e-6, rtol=0)
            or not np.allclose(np.linalg.det(rotations), 1, atol=1e-6, rtol=0)):
        raise ValueError("Camera-to-world rotations must be proper rotations")
    world = unit_vectors(np.einsum("nij,nj->ni", rotations, up_camera))
    flipped = world @ world[0] <= 0
    unified = np.where(flipped[:, None], -world, world)
    median = np.median(unified, axis=0)
    mad = np.median(np.abs(unified - median), axis=0)
    sigma = np.maximum(mad_scale * mad, mad_floor)
    threshold = mad_thresholds[0 if len(world) <= 6 else 1 if len(world) <= 9 else 2]
    keep = np.ones(len(world), dtype=bool)
    if len(world) >= 5:
        keep = (np.abs(unified - median) / sigma <= threshold).all(axis=1)
    if keep.sum() < min_inliers:
        raise ValueError(f"Insufficient gravity support after MAD: {keep.sum()} < {min_inliers}; no fallback")
    up = unit_vectors(np.median(unified[keep], axis=0))
    angles = np.degrees(np.arccos(np.clip(unified @ up, -1, 1)))
    raw_angles = np.degrees(np.arccos(np.clip(world @ up, -1, 1)))
    return up, {
        "up_world_per_frame": world.tolist(), "hemisphere_flipped": flipped.tolist(),
        "mad_inlier": keep.tolist(), "mad": mad.tolist(), "sigma": sigma.tolist(),
        "mad_threshold": threshold, "mad_applied": len(world) >= 5,
        "small_sample_median": len(world) < 5, "fallback_to_rejected_samples": False,
        "inlier_count": int(keep.sum()), "reference_sample": 0,
        "angle_to_consensus_deg": angles.tolist(), "raw_angle_to_consensus_deg": raw_angles.tolist(),
        "dispersion_before_mad_deg": {"median": float(np.median(angles)), "p95": float(np.percentile(angles, 95))},
        "dispersion_after_mad_deg": {"median": float(np.median(angles[keep])), "p95": float(np.percentile(angles[keep], 95))},
    }


def rotate_mano_parameters(translation, orientation, root_offset, rotation):
    """Rotate MANO poses about the world origin, retaining the model root offset.

    Inputs [N,3]: MANO translation, global axis-angle, and rest root J(beta).
    Wrist = translation + J(beta). Naively rotating translation alone is wrong.
    Call on finite, valid poses only; local articulation and beta are unchanged.
    """
    translation, orientation, root_offset = [np.asarray(x, dtype=np.float64)
                                             for x in (translation, orientation, root_offset)]
    if (translation.ndim != 2 or translation.shape[1] != 3
            or translation.shape != orientation.shape or translation.shape != root_offset.shape
            or not all(np.isfinite(x).all() for x in (translation, orientation, root_offset))):
        raise ValueError("Expected finite, matched [N,3] MANO parameters and offsets")
    position = (translation + root_offset) @ rotation.T - root_offset
    orientation = (Rotation.from_matrix(rotation) * Rotation.from_rotvec(orientation)).as_rotvec()
    return position.astype(np.float32), orientation.astype(np.float32)


def load_camera_trajectory(path, clip):
    """Read native HaWoR scaled camera-to-world poses for EVERY prepared frame.

    Native traj is [T,7] (xyz translation, xyzw quaternion); tstamp only indexes
    SLAM keyframes and must not be used as the dense frame correspondence.
    """
    with np.load(path, allow_pickle=False) as data:
        trajectory = data["traj"].astype(np.float64)
        scale = float(data["scale"])
        focal = float(data["img_focal"])
        center = data["img_center"]
    count = clip["prepared"]["frame_count"]
    if trajectory.shape != (count, 7) or not np.isfinite(trajectory).all():
        raise ValueError("Camera trajectory must have one finite pose per prepared frame")
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError("Native camera scale must be positive and finite")
    if (focal != clip["hawor_camera"]["focal_length_px"]
            or not np.array_equal(center, [clip["prepared"]["width"] / 2, clip["prepared"]["height"] / 2])):
        raise ValueError("Native camera intrinsics disagree with prepared RGB")
    if not np.allclose(np.linalg.norm(trajectory[:, 3:], axis=1), 1, atol=1e-4, rtol=0):
        raise ValueError("Native camera quaternion is not unit length")
    return Rotation.from_quat(trajectory[:, 3:]).as_matrix(), trajectory[:, :3] * scale
