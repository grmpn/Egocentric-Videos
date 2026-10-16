"""Reconstruct existing MANO poses and verify a rigid change of world frame.

Uses the same SMPL-X MANOLayer and left shapedirs correction as pinned HaWoR.
Licensed model assets remain local inputs; no model data is embedded in code.
"""

import numpy as np
from scipy.spatial.transform import Rotation

from .gravity_alignment import rotate_mano_parameters
from .world_export import HAND_ORDER


def load_mano_model(path, hand):
    """Load a licensed MANO asset with HaWoR's left-hand shape correction."""
    import smplx

    model = smplx.MANOLayer(str(path), is_rhand=hand == 1)
    if hand == 0:
        model.shapedirs[:, 0, :] *= -1
    return model


def reconstruct_mano(model, translation, orientation, hand_pose, betas):
    """Evaluate saved MANO parameters: metres, axis-angle radians, batch first.

    Translation is the MANO parameter, not the physical wrist. Returns CPU
    joints [N,16,3] and vertices [N,778,3] in the parameters' coordinate frame.
    """
    import torch

    pose = torch.from_numpy(Rotation.from_rotvec(hand_pose.reshape(-1, 3))
                            .as_matrix().astype(np.float32)).reshape(-1, 15, 3, 3)
    root = torch.from_numpy(Rotation.from_rotvec(orientation)
                            .as_matrix().astype(np.float32))[:, None]
    with torch.no_grad():
        result = model(betas=torch.from_numpy(betas.copy()), hand_pose=pose,
                       global_orient=root, transl=torch.from_numpy(translation.copy()),
                       pose2rot=False)
    return result.joints.numpy(), result.vertices.numpy()


def align_hand_geometry(world, rotation, model_paths):
    """Return corrected MANO poses, physical wrists, rest roots and error evidence.

    Derived poses/wrists/offsets are [T,2,3] float32, left then right; invalid
    geometry stays NaN. All source arrays and local articulation/beta stay intact.
    Geometry evaluation runs on CPU; full original/aligned vertices are temporary.
    """
    import smplx
    import torch

    valid = world["export_valid"]
    if not valid.any():
        raise ValueError("No export-valid hands to align")
    arrays = {name: np.full((*valid.shape, 3), np.nan, dtype=np.float32) for name in (
        "root_translation_aligned_m", "root_orientation_aligned_axis_angle",
        "wrist_position_world_m", "wrist_position_aligned_m", "mano_root_offset_m")}
    evidence = {}
    for hand, name in enumerate(HAND_ORDER):
        indices = np.flatnonzero(valid[:, hand])
        if not len(indices):
            evidence[name] = {"valid_frames": 0, "geometry_check": "absent_hand"}
            continue
        model = load_mano_model(model_paths[hand], hand)
        translation = world["root_translation_world_m"][indices, hand]
        orientation = world["root_orientation_world_axis_angle"][indices, hand]
        pose = world["hand_pose_axis_angle"][indices, hand]
        betas = torch.from_numpy(world["mano_betas"][indices, hand].copy())

        def reconstruct(position, orient):
            return reconstruct_mano(model, position, orient, pose, betas.numpy())

        joints, vertices = reconstruct(translation, orientation)
        # J(beta) is independent of global rotation and articulation. Obtain it
        # directly from SMPL-X's existing shape blend and joint regressor.
        with torch.no_grad():
            shaped = model.v_template + smplx.lbs.blend_shapes(betas, model.shapedirs)
            offset = smplx.lbs.vertices2joints(model.J_regressor, shaped)[:, 0].numpy()
        aligned_t, aligned_r = rotate_mano_parameters(translation, orientation, offset, rotation)
        aligned_joints, aligned_vertices = reconstruct(aligned_t, aligned_r)
        tolerance = float(32 * np.finfo(np.float32).eps * max(1., np.max(np.abs(vertices))))
        vertex_error = float(np.max(np.abs(aligned_vertices - vertices @ rotation.T)))
        joint_error = float(np.max(np.abs(aligned_joints - joints @ rotation.T)))
        inverse_error = float(np.max(np.abs((aligned_t + offset) @ rotation - offset - translation)))
        if max(vertex_error, joint_error, inverse_error) > tolerance:
            raise ValueError(f"{name} rigid MANO geometry verification failed; inspect root offset/conventions")
        np.testing.assert_allclose(joints[:, 0], translation + offset, atol=tolerance, rtol=0)
        arrays["root_translation_aligned_m"][indices, hand] = aligned_t
        arrays["root_orientation_aligned_axis_angle"][indices, hand] = aligned_r
        arrays["wrist_position_world_m"][indices, hand] = joints[:, 0]
        arrays["wrist_position_aligned_m"][indices, hand] = aligned_joints[:, 0]
        arrays["mano_root_offset_m"][indices, hand] = offset
        original_rotations = Rotation.from_rotvec(orientation).as_matrix()
        restored = rotation.T @ Rotation.from_rotvec(aligned_r).as_matrix()
        np.testing.assert_allclose(restored, original_rotations, atol=1e-6, rtol=0)
        evidence[name] = {"valid_frames": len(indices), "vertices_per_hand": vertices.shape[1],
                          "joints_per_hand": joints.shape[1], "tolerance_m": tolerance,
                          "max_vertex_error_m": vertex_error, "max_joint_error_m": joint_error,
                          "max_translation_roundtrip_error_m": inverse_error,
                          "max_rotation_roundtrip_error": float(np.max(np.abs(restored - original_rotations)))}
    return arrays, evidence
