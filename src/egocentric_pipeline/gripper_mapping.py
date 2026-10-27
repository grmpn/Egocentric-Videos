"""Direct MANO landmark → free gripper pose/opening, independent of arm IK."""

from pathlib import Path
import sys

import numpy as np
from scipy.spatial.transform import Rotation

from .gripper_model import load_grippers
from .hand_geometry import load_mano_model, reconstruct_mano
from .retargeting import load_alignment
from .run_metadata import read_json, utc_now, write_json


LANDMARK_NAMES = ("wrist", "thumb_mcp", "index_mcp", "thumb_tip", "index_tip", "thumb_ip", "index_pip")


def validate_settings(settings):
    if settings.get("forward_axis", "wrist_to_thumb_mcp") not in (
            "wrist_to_thumb_mcp", "thumb_mcp_to_ip", "index_mcp_to_pip", "wrist_to_mcp_midpoint"):
        raise ValueError("forward_axis must be wrist_to_thumb_mcp, thumb_mcp_to_ip, index_mcp_to_pip or wrist_to_mcp_midpoint")
    if settings.get("orientation_priority", "closing") not in ("closing", "forward"):
        raise ValueError("orientation_priority must be closing or forward")
    offset = settings.get("wrist_thumb_offset_m", 0.)
    if not np.isfinite(offset) or offset < 0:
        raise ValueError("wrist_thumb_offset_m must be nonnegative and finite")
    if offset and settings.get("forward_axis") != "wrist_to_mcp_midpoint":
        raise ValueError("A wrist thumb offset requires forward_axis wrist_to_mcp_midpoint")
    closed, opened = settings["closed_distance_m"], settings["open_distance_m"]
    if not np.isfinite([closed, opened]).all() or not 0 <= closed < opened:
        raise ValueError("Require 0 <= closed_distance_m < open_distance_m")
    if not np.isfinite(settings["minimum_axis_length_m"]) or settings["minimum_axis_length_m"] <= 0:
        raise ValueError("minimum_axis_length_m must be positive and finite")
    if not 0 < settings["minimum_axis_sine"] < 1:
        raise ValueError("minimum_axis_sine must be between 0 and 1")
    for key in ("tcp_offset_grasp_m", "tcp_rotation_grasp_xyz_rad"):
        value = np.asarray(settings[key])
        if value.shape != (2, 3) or not np.isfinite(value).all():
            raise ValueError(f"{key} must be finite [2,3], left then right")


def reconstruct_grasp_geometry(arrays, model_paths, *, landmark_count=7):
    """Landmarks [T,2,7,3] and left/right (vertices [T,778,3], faces), metres.

    MANO native joints: wrist=0, index MCP/PIP=1/2, thumb CMC/MCP/IP=13/14/15.
    Tips use SMPL-X's MANO vertex IDs. Original articulation/shape and aligned
    root poses are evaluated unchanged. Missing/infilled samples remain NaN.
    Request five or six landmarks only when reconstructing earlier saved runs.
    """
    from smplx.vertex_ids import vertex_ids

    if landmark_count not in (5, 6, 7):
        raise ValueError("Expected five, six or seven saved MANO landmarks")
    observed = arrays["export_valid"] & ~arrays["motion_infilled"]
    landmarks = np.full((*observed.shape, landmark_count, 3), np.nan, np.float32)
    meshes = []
    for hand, path in enumerate(model_paths):
        model = load_mano_model(path, hand)
        vertices = np.full((len(observed), len(model.v_template), 3), np.nan, np.float32)
        indices = np.flatnonzero(observed[:, hand])
        if len(indices):
            joints, verts = reconstruct_mano(
                model, arrays["root_translation_aligned_m"][indices, hand],
                arrays["root_orientation_aligned_axis_angle"][indices, hand],
                arrays["hand_pose_axis_angle"][indices, hand], arrays["mano_betas"][indices, hand])
            if not np.allclose(joints[:, 0], arrays["wrist_position_aligned_m"][indices, hand], atol=1e-5, rtol=0):
                raise ValueError("Reconstructed wrist differs from alignment; check MANO assets/hand order")
            points = [joints[:, 0], joints[:, 14], joints[:, 1],
                      verts[:, vertex_ids["mano"]["thumb"]], verts[:, vertex_ids["mano"]["index"]]]
            if landmark_count >= 6:
                points.append(joints[:, 15])
            if landmark_count == 7:
                points.append(joints[:, 2])
            landmarks[indices, hand] = np.stack(points, axis=1)
            vertices[indices] = verts
        meshes.append((vertices, model.faces))
    return landmarks, meshes


def grasp_forward_segment(landmarks, settings):
    """Start/end positions [...,3] in aligned metres, shared by mapping/display.

    Shift the wrist toward the thumb along index-MCP→thumb-MCP. This is a
    construction point; the original MANO wrist and fingertip center stay fixed.
    """
    points = np.asarray(landmarks, dtype=float)
    wrist, thumb, index = (points[..., i, :] for i in range(3))
    axis = settings.get("forward_axis", "wrist_to_thumb_mcp")
    if axis == "wrist_to_mcp_midpoint":
        closing = index - thumb
        length = np.linalg.norm(closing, axis=-1, keepdims=True)
        thumbward = -closing / np.maximum(length, settings["minimum_axis_length_m"])
        return wrist + settings.get("wrist_thumb_offset_m", 0.) * thumbward, (thumb + index) / 2
    if axis == "index_mcp_to_pip":
        if points.shape[-2] != 7:
            raise ValueError("index_mcp_to_pip requires index PIP landmarks; regenerate the mapping")
        return index, points[..., 6, :]
    if axis == "thumb_mcp_to_ip":
        if points.shape[-2] < 6:
            raise ValueError("thumb_mcp_to_ip requires thumb IP landmarks; regenerate the mapping")
        return thumb, points[..., 5, :]
    return wrist, thumb


def map_grasp_landmarks(landmarks, observed, settings):
    """Map [T,2,7,3] aligned landmarks to [T,2,4,4] column-vector transforms.

    +X follows the configured forward segment; +Y follows thumb MCP→index MCP.
    The priority axis is preserved and the other projected perpendicular to it;
    +Z=X×Y. Older settings default to closing priority, zero wrist shift and
    wrist→thumb MCP. Local corrections are T_grasp_from_TCP. No interpolation,
    filtering, sign flips or IK. Missing/degenerate outputs are NaN.
    """
    validate_settings(settings)
    points = np.asarray(landmarks, dtype=float)
    observed = np.asarray(observed)
    if (observed.ndim != 2 or observed.shape[1] != 2 or observed.dtype != bool
            or points.shape not in tuple((*observed.shape, n, 3) for n in (5, 6, 7))):
        raise ValueError("Expected landmarks [T,2,5|6|7,3] and boolean observed [T,2]")
    _, thumb, index, thumb_tip, index_tip = np.moveaxis(points[..., :5, :], 2, 0)
    start, end = grasp_forward_segment(points, settings)
    forward = end - start
    closing = index - thumb
    lengths = np.linalg.norm(closing, axis=-1)
    forward_lengths = np.linalg.norm(forward, axis=-1)
    eps = settings["minimum_axis_length_m"]
    if settings.get("orientation_priority", "closing") == "forward":
        x = forward / np.maximum(forward_lengths[..., None], eps)
        orthogonal = closing - np.sum(closing * x, axis=-1)[..., None] * x
        y = orthogonal / np.maximum(np.linalg.norm(orthogonal, axis=-1, keepdims=True), eps)
        secondary_lengths = lengths
    else:
        y = closing / np.maximum(lengths[..., None], eps)
        orthogonal = forward - np.sum(forward * y, axis=-1)[..., None] * y
        x = orthogonal / np.maximum(np.linalg.norm(orthogonal, axis=-1, keepdims=True), eps)
        secondary_lengths = forward_lengths
    orthogonal_lengths = np.linalg.norm(orthogonal, axis=-1)
    sine = orthogonal_lengths / np.maximum(secondary_lengths, eps)
    valid = (observed & np.isfinite(points).all(axis=(-1, -2)) & (lengths > eps)
             & (forward_lengths > eps) & (orthogonal_lengths > eps) & (sine > settings["minimum_axis_sine"]))
    grasp = np.full((*observed.shape, 4, 4), np.nan)
    grasp[valid] = np.eye(4)
    rotation = np.stack((x, y, np.cross(x, y)), axis=-1)
    grasp[..., :3, :3][valid] = rotation[valid]
    grasp[..., :3, 3][valid] = ((thumb_tip + index_tip) / 2)[valid]
    correction = np.tile(np.eye(4), (2, 1, 1))
    correction[:, :3, 3] = settings["tcp_offset_grasp_m"]
    correction[:, :3, :3] = Rotation.from_euler("xyz", settings["tcp_rotation_grasp_xyz_rad"]).as_matrix()
    separation = np.linalg.norm(thumb_tip - index_tip, axis=-1)
    separation[~observed | ~np.isfinite(points[..., 3:5, :]).all(axis=(-1, -2))] = np.nan
    action = np.clip((separation - settings["closed_distance_m"]) /
                     (settings["open_distance_m"] - settings["closed_distance_m"]), 0., 1.)
    action[~valid] = np.nan
    return {"observation_valid": observed.copy(), "mapping_valid": valid,
            "transform_aligned_from_grasp": grasp, "transform_aligned_from_tcp": grasp @ correction,
            "fingertip_distance_m": separation, "gripper_action": action}


def mapping_summary(arrays):
    """Observed/invalid counts and opening saturation for review, per hand."""
    summary = {}
    for hand, side in enumerate(("left", "right")):
        valid = arrays["mapping_valid"][:, hand]
        d = arrays["fingertip_distance_m"][valid, hand]
        a = arrays["gripper_action"][valid, hand]
        summary[side] = {"observed": int(arrays["observation_valid"][:, hand].sum()),
                         "mapped": int(valid.sum()),
                         "degenerate": int((arrays["observation_valid"][:, hand] & ~valid).sum()),
                         "distance_min_m": float(d.min()) if len(d) else None,
                         "distance_max_m": float(d.max()) if len(d) else None,
                         "closed_saturated": int((a == 0).sum()), "open_saturated": int((a == 1).sum())}
    return summary


def save_mapping(directory, arrays, report, settings):
    """Save a new review result; never replace source data or earlier tuning."""
    mapped = map_grasp_landmarks(arrays["landmarks_aligned_m"], arrays["export_valid"] & ~arrays["motion_infilled"], settings)
    saved = {**arrays, **mapped}
    saved["transform_aligned_from_palm"] = (mapped["transform_aligned_from_tcp"] @
                                          np.linalg.inv(arrays["transform_palm_from_tcp"]))
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    with (directory / "gripper_mapping.npz").open("xb") as stream:
        np.savez_compressed(stream, **saved)
    result = {**report, "status": "completed", "saved_at": utc_now(), "settings": settings,
              "summary": mapping_summary(saved)}
    write_json(directory / "mapping_report.json", result)
    write_json(directory / "settings.json", settings)
    return result


def prepare_gripper_mapping(alignment_directory, output_directory, settings, robot_settings,
                            asset_root, start, stop, model_paths=None):
    """Prepare a selected source interval without loading an arm or solving IK."""
    import torch

    torch.set_num_threads(4)
    validate_settings(settings)
    source, alignment, clip = load_alignment(alignment_directory)
    if not 0 <= start < stop <= len(source["timestamp_s"]):
        raise ValueError("Require 0 <= frame-start < frame-stop <= source frame count")
    # Retain only the source fields needed to reconstruct/review this interval.
    fields = ("frame_index", "timestamp_s", "source_timestamp_s", "export_valid", "motion_infilled",
              "direct_detection", "root_translation_aligned_m", "root_orientation_aligned_axis_angle",
              "wrist_position_aligned_m", "hand_pose_axis_angle", "mano_betas")
    arrays = {name: source[name][start:stop].copy() for name in fields}
    model_paths = model_paths or [alignment["inputs"][f"mano_{side}"]["path"] for side in ("left", "right")]
    landmarks, _ = reconstruct_grasp_geometry(arrays, model_paths)
    grippers = load_grippers(asset_root, robot_settings)
    arrays.update(landmarks_aligned_m=landmarks,
                  transform_palm_from_tcp=np.array([g.transform_palm_from_tcp for g in grippers]))
    report = {"schema_version": 1, "method": "direct_gripper_mapping", "hand_order": ["left", "right"],
              "alignment_directory": str(Path(alignment_directory).resolve()),
              "prepared_video": alignment["inputs"]["prepared_video"]["path"],
              "video_size": [clip["prepared"]["width"], clip["prepared"]["height"]],
              "mano_models": [str(Path(p).resolve()) for p in model_paths],
              "asset_root": str(Path(asset_root).resolve()), "robot_settings": robot_settings,
              "frame_interval": [start, stop], "landmark_names": list(LANDMARK_NAMES),
              "landmarks": {"wrist_joint": 0, "thumb_mcp_joint": 14, "thumb_ip_joint": 15, "index_mcp_joint": 1, "index_pip_joint": 2,
                            "tips": "smplx.vertex_ids.vertex_ids['mano']"},
              "command": [sys.executable, *sys.argv],
              "units": {"length": "metres", "angle": "radians", "time": "seconds"},
              "observation_policy": "export_valid AND NOT motion_infilled",
              "pose_convention": "column vectors; T_destination_from_source; gravity-aligned frame",
              "action_convention": "continuous 0 closed / 1 open; uncalibrated distance scale",
              "limitations": "Nominal TCP; uncalibrated contact/metric scale. Direct mapping only, no IK, collision or dynamics checks."}
    result = save_mapping(output_directory, arrays, report, settings)
    for gripper in grippers:
        (Path(output_directory) / f"{gripper.side}_gripper.urdf").write_text(gripper.xml)
    return result


def load_mapping(directory):
    directory = Path(directory)
    report = read_json(directory / "mapping_report.json")
    if report["schema_version"] != 1 or report["status"] != "completed" or report["hand_order"] != ["left", "right"]:
        raise ValueError("Require a completed left/right direct gripper mapping run")
    with np.load(directory / "gripper_mapping.npz", allow_pickle=False) as saved:
        arrays = dict(saved)
    return arrays, report
