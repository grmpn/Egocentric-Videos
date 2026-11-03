"""Direct geometry contracts, real gripper FK, and the preparation entry point."""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest
from scipy.spatial.transform import Rotation, Slerp

from egocentric_pipeline.gripper_mapping import grasp_forward_segment, load_mapping, map_grasp_landmarks, save_mapping
from egocentric_pipeline.run_metadata import read_json


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def settings():
    # Preserve the revision-5 mapping contract for historical output reloads.
    return {"forward_axis": "wrist_to_mcp_midpoint", "orientation_priority": "forward",
            "wrist_thumb_offset_m": .025, "closed_distance_m": .010637088979430357,
            "open_distance_m": .3586942059948014, "minimum_axis_length_m": 1e-6,
            "minimum_axis_sine": .001, "tcp_offset_grasp_m": [[0.,0.,0.], [0.,0.,0.]],
            "tcp_rotation_grasp_xyz_rad": [[0.,0.,0.], [0.,0.,0.]]}


@pytest.fixture
def grippers():
    from egocentric_pipeline.gripper_model import load_grippers

    assets = ROOT / "data/models/purdue-alex-assets"
    if not assets.exists():
        pytest.skip("Pinned robot assets are local inputs")
    return load_grippers(assets, read_json(ROOT / "configs/robot_workspace.json"))


def test_exact_tip_mapping_fk_twist_and_equivariance(grippers):
    settings = {**read_json(ROOT / "configs/gripper_mapping.json"), "mapping_mode": "fingertip_correspondence"}
    # Includes observed extrema and the user's two reference frames.
    points = landmarks([.003720637467527735, .02107880248989149, .12549593759450284, .15052035605268244, .2799])
    observed = np.ones(points.shape[:2], bool)
    result = map_grasp_landmarks(points, observed, settings, grippers)
    assert result["mapping_valid"].all()
    assert result["tip_error_m"].max() < 1e-10
    for hand, g in enumerate(grippers):
        marker = settings["distal_tip_local_m"]
        mesh = g.links[f"{g.side}_ezgripper_finger_l2_1"].concatenated_visual_mesh
        # Marker is the center of the most distal mesh edge, not the fixed TCP.
        edge = mesh.vertices[np.isclose(mesh.vertices[:,0], mesh.vertices[:,0].max(), atol=1e-9, rtol=0)]
        np.testing.assert_allclose(marker, np.unique(edge, axis=0).mean(axis=0), atol=1e-12)
        for frame in range(len(points)):
            g.set_opening(result["gripper_action"][frame, hand])
            g.place_tcp(result["transform_aligned_from_tcp"][frame, hand])
            np.testing.assert_allclose(g.tip_positions(marker), points[frame,hand,3:5], atol=1e-10)
            assert all(j.min_angle <= j.joint_angle() <= j.max_angle for j in g.joints.values())
        rotation = result["transform_aligned_from_grasp"][:,hand,:3,:3]
        np.testing.assert_allclose(np.linalg.det(rotation), 1., atol=1e-14)
        y = points[:,hand,4] - points[:,hand,3]
        y /= np.linalg.norm(y, axis=-1, keepdims=True)
        forward = points[:,hand,1] - points[:,hand,0]
        x = forward - np.sum(forward*y, axis=-1, keepdims=True)*y
        x /= np.linalg.norm(x, axis=-1, keepdims=True)
        np.testing.assert_allclose(rotation[:,:,0], x, atol=1e-14)
        np.testing.assert_allclose(rotation[:,:,1], y, atol=1e-14)
    transform = np.eye(4)
    transform[:3,:3] = Rotation.from_euler('xyz', [.4, -.6, 2.]).as_matrix()
    transform[:3,3] = [.5, -.9, .2]
    moved = map_grasp_landmarks(points @ transform[:3,:3].T + transform[:3,3], observed, settings, grippers)
    for key in ("transform_aligned_from_grasp", "transform_aligned_from_tcp"):
        np.testing.assert_allclose(moved[key], transform @ result[key], atol=1e-10)
    np.testing.assert_allclose(moved["gripper_action"], result["gripper_action"], atol=1e-10)


def test_tip_mapping_rejects_unreachable_degenerate_and_missing(grippers):
    settings = {**read_json(ROOT / "configs/gripper_mapping.json"), "mapping_mode": "fingertip_correspondence"}
    points = landmarks([.05]*5)
    observed = np.ones((5,2), bool)
    observed[0,0] = False
    points[1,0,4] = points[1,0,3]  # Coincident tips cannot determine an axis.
    points[2,0,1] = points[2,0,0] + [0., 1., 0.]  # Twist vector parallel to tips.
    points[3,0,4] = points[3,0,3] + [0., 1., 0.]  # Beyond maximum jaw span.
    points[4,0,1] = np.nan
    result = map_grasp_landmarks(points, observed, settings, grippers)
    assert not result["mapping_valid"][:,0].any()
    assert result["mapping_valid"][:,1].all()
    assert not result["opening_reachable"][3,0]
    for key in ("transform_aligned_from_tcp", "gripper_action", "gripper_tips_aligned_m"):
        assert np.isnan(result[key][:,0]).all()
    with pytest.raises(ValueError, match="requires left/right"):
        map_grasp_landmarks(points, observed, settings)


def landmarks(distances):
    """Analytic MCP midpoint geometry: +X forward; opposite closing signs."""
    points = np.zeros((len(distances), 2, 7, 3))
    for i, distance in enumerate(distances):
        for hand, sign in enumerate((-1, 1)):
            # Finger-segment directions differ from wrist→MCP midpoint.
            points[i, hand] = [[0, 0, 0], [.06, -.02 * sign, 0], [.06, .02 * sign, 0],
                               [.15, -distance / 2 * sign, 0], [.15, distance / 2 * sign, 0],
                               [.10, -.01 * sign, .02], [.10, .01 * sign, -.03]]
    return points


@pytest.mark.parametrize("mode", ["mcp_plane", "thumb_ip_plane"])
def test_mcp_plane_axes_fk_center_and_unchanged_opening(grippers, mode):
    settings = {**read_json(ROOT / "configs/gripper_mapping.json"), "mapping_mode": mode}
    points = landmarks([.02107880248989149, .12549593759450284])
    # Tilt the fingertip line away from the MCP jaw line: individual tips must
    # differ, while their midpoint and distance remain exact.
    points[..., 3, 0] += .012
    points[..., 4, 0] -= .012
    observed = np.ones((2, 2), bool)
    mapped = map_grasp_landmarks(points, observed, settings, grippers)
    previous = map_grasp_landmarks(points, observed, {**settings, "mapping_mode": "fingertip_correspondence"}, grippers)
    assert mapped["mapping_valid"].all()
    np.testing.assert_allclose(mapped["gripper_action"], previous["gripper_action"], atol=1e-12)
    for hand, sign in enumerate((-1, 1)):
        x, y = np.array([.8, 0., -.6]), np.array([0., sign, 0.])
        if mode == "thumb_ip_plane":
            # Analytic directions for index MCP→thumb IP and projected index PIP.
            y = np.array([4., -3.*sign, 2.]) / np.sqrt(29)
            x = np.array([64., 10.*sign, -113.]) / np.sqrt(16965)
        rotation = np.stack([x, y, np.cross(x, y)], axis=-1)
        for frame in range(2):
            np.testing.assert_allclose(mapped["transform_aligned_from_grasp"][frame,hand,:3,:3], rotation, atol=1e-14)
            g = grippers[hand]
            g.set_opening(mapped["gripper_action"][frame,hand])
            g.place_tcp(mapped["transform_aligned_from_tcp"][frame,hand])
            tips = g.tip_positions(settings["distal_tip_local_m"])
            np.testing.assert_allclose(tips.mean(axis=0), points[frame,hand,3:5].mean(axis=0), atol=1e-12)
            np.testing.assert_allclose(tips[1]-tips[0], y * mapped["fingertip_distance_m"][frame,hand], atol=1e-12)
            assert np.linalg.det(g.model.root_link.worldrot()) == pytest.approx(1.)
    assert mapped["tip_error_m"].min() > .001
    transform = np.eye(4)
    transform[:3,:3] = Rotation.from_euler('xyz', [.4, -.6, 2.]).as_matrix()
    transform[:3,3] = [.5, -.9, .2]
    moved = map_grasp_landmarks(points @ transform[:3,:3].T + transform[:3,3], observed, settings, grippers)
    for key in ("transform_aligned_from_grasp", "transform_aligned_from_tcp"):
        np.testing.assert_allclose(moved[key], transform @ mapped[key], atol=1e-10)


@pytest.mark.parametrize("mode", ["mcp_plane", "thumb_ip_plane"])
def test_mcp_plane_degenerate_and_missing_observations(grippers, mode):
    settings = {**read_json(ROOT / "configs/gripper_mapping.json"), "mapping_mode": mode}
    points = landmarks([.05]*5)
    observed = np.ones((5,2), bool)
    observed[0,0] = False
    points[1,0,2] = points[1,0,1]  # Coincident MCPs.
    points[2,0,6] = points[2,0,2]  # Coincident index MCP/PIP.
    points[3,0,6] = points[3,0,2] + (points[3,0,2]-points[3,0,1])  # Collinear plane.
    if mode == "thumb_ip_plane":
        points[1,0,5] = points[1,0,2]
        points[3,0,6] = points[3,0,2] + (points[3,0,5]-points[3,0,2])
    points[4,0,4] = points[4,0,3] + [0., 1., 0.]  # Unreachable opening.
    result = map_grasp_landmarks(points, observed, settings, grippers)
    assert not result["mapping_valid"][:,0].any()
    assert result["mapping_valid"][:,1].all()
    assert np.isnan(result["transform_aligned_from_tcp"][:,0]).all()
    with pytest.raises(ValueError, match="requires index PIP"):
        map_grasp_landmarks(points[:,:,:6], observed, settings, grippers)


@pytest.mark.parametrize("forward_axis", ["wrist_to_mcp_midpoint", "wrist_to_tip_midpoint"])
@pytest.mark.parametrize("backward", [None, 0.025])
def test_wrist_anchor_roll_reference_and_rigid_equivariance(grippers, forward_axis, backward):
    settings = {**read_json(ROOT / "configs/gripper_wrist_roll.json"), "forward_axis": forward_axis}
    settings.pop("wrist_backward_offset_m")
    if backward is not None:
        settings["wrist_backward_offset_m"] = backward
    angles = np.array([0., np.pi/2, -np.pi/2])
    points = landmarks([.05]*3)
    open_points = points[..., :5 if forward_axis == "wrist_to_tip_midpoint" else 3, :].copy()
    observed = np.ones((3,2), bool)
    swing = Rotation.from_euler("y", .35).as_matrix()
    for i, angle in enumerate(angles):
        points[i] = points[i] @ (swing @ Rotation.from_euler("x", angle).as_matrix()).T
    mapped = map_grasp_landmarks(points, observed, settings, grippers, open_hand_landmarks=open_points)
    assert mapped["mapping_valid"].all()
    np.testing.assert_allclose(mapped["gripper_roll_rad"], np.repeat(angles[:,None], 2, axis=1), atol=1e-14)
    for hand, sign in enumerate((-1, 1)):
        zero_rotation = swing @ np.diag([1., sign, sign])
        np.testing.assert_allclose(mapped["zero_roll_rotation_aligned"][:,hand], np.tile(zero_rotation, (3,1,1)), atol=1e-14)
        for i, angle in enumerate(angles):
            g = grippers[hand]
            g.set_opening(mapped["gripper_action"][i,hand])
            g.place_tcp(mapped["transform_aligned_from_tcp"][i,hand])
            np.testing.assert_allclose(g.model.root_link.worldpos(), points[i,hand,0] - (backward or 0.) * swing[:,0], atol=1e-12)
            expected = swing @ Rotation.from_euler("x", angle).as_matrix() @ np.diag([1., sign, sign])
            np.testing.assert_allclose(g.model.root_link.worldrot(), expected, atol=1e-12)
            assert np.linalg.det(g.model.root_link.worldrot()) == pytest.approx(1.)
            tips = g.tip_positions(settings["distal_tip_local_m"])
            assert np.linalg.norm(tips[1]-tips[0]) == pytest.approx(.05, abs=1e-12)
    transform = np.eye(4)
    transform[:3,:3] = Rotation.from_euler("xyz", [.4,-.6,2.]).as_matrix()
    transform[:3,3] = [.5,-.9,.2]
    moved = map_grasp_landmarks(points @ transform[:3,:3].T + transform[:3,3], observed, settings, grippers,
                               open_hand_landmarks=open_points @ transform[:3,:3].T + transform[:3,3])
    np.testing.assert_allclose(moved["transform_aligned_from_tcp"], transform @ mapped["transform_aligned_from_tcp"], atol=1e-12)
    np.testing.assert_allclose(moved["gripper_roll_rad"], mapped["gripper_roll_rad"], atol=1e-12)
    np.testing.assert_allclose(moved["gripper_action"], mapped["gripper_action"], atol=1e-12)


@pytest.mark.parametrize("forward_axis", ["wrist_to_mcp_midpoint", "wrist_to_tip_midpoint"])
def test_wrist_roll_missing_degenerate_and_unreachable(grippers, forward_axis):
    settings = {**read_json(ROOT / "configs/gripper_wrist_roll.json"), "forward_axis": forward_axis}
    points = landmarks([.05]*7)
    open_points = points[..., :5 if forward_axis == "wrist_to_tip_midpoint" else 3, :].copy()
    observed = np.ones((7,2), bool)
    observed[0,0] = False
    forward_pair = slice(3,5) if forward_axis == "wrist_to_tip_midpoint" else slice(1,3)
    points[1,0,0] = points[1,0,forward_pair].mean(axis=0)  # No forward direction.
    points[2,0,1:3] = [[.04,0,0],[.08,0,0]]  # Jaw parallel to forward.
    points[3,0,4] = points[3,0,3] + [0.,1.,0.]  # Unreachable opening.
    open_points[4,0] = np.nan
    open_points[5,0,forward_pair] *= -1  # No unique shortest rotation for opposite X.
    open_points[6,0,1:3] = [[.04,0,0],[.08,0,0]]  # Degenerate reference jaw.
    result = map_grasp_landmarks(points, observed, settings, grippers, open_hand_landmarks=open_points)
    assert not result["mapping_valid"][:,0].any()
    assert result["mapping_valid"][:,1].all()
    for key in ("gripper_roll_rad", "zero_roll_rotation_aligned", "transform_aligned_from_tcp", "gripper_action"):
        assert np.isnan(result[key][:,0]).all()
    with pytest.raises(ValueError, match="requires open hand landmarks"):
        map_grasp_landmarks(points, observed, settings, grippers)


def test_tip_forward_differs_from_mcp_forward_and_matches_offset_wrist(grippers):
    settings = read_json(ROOT / "configs/gripper_wrist_roll.json")
    points = landmarks([.05])
    points[...,3:5,:] += [0., .04, .03]
    result = map_grasp_landmarks(points, np.ones((1,2),bool), settings, grippers,
                                 open_hand_landmarks=points[...,:5,:])
    assert result["mapping_valid"].all()
    expected = np.array([.15,.04,.03]); expected /= np.linalg.norm(expected)
    for hand,g in enumerate(grippers):
        g.place_tcp(result["transform_aligned_from_tcp"][0,hand])
        np.testing.assert_allclose(g.model.root_link.worldrot()[:,0], expected, atol=1e-12)
        np.testing.assert_allclose(g.model.root_link.worldpos(), points[0,hand,0] - .025 * expected, atol=1e-12)
    np.testing.assert_allclose(result["gripper_roll_rad"], 0., atol=1e-12)


def test_roll_blend_endpoints_weights_fk_and_equivariance(grippers):
    settings = read_json(ROOT / "configs/gripper_roll_blend.json")
    angles = [0.,30.,37.5,45.,90.,-37.5]
    points = landmarks([.05]*len(angles)); opened = points[...,:5,:].copy()
    observed = np.ones(points.shape[:2],bool)
    for i,angle in enumerate(angles):
        points[i] = points[i] @ Rotation.from_euler('x',angle,degrees=True).as_matrix().T
    result = map_grasp_landmarks(points,observed,settings,grippers,open_hand_landmarks=opened)
    original = map_grasp_landmarks(points,observed,{**settings,'mapping_mode':'mcp_plane'},grippers)
    config1 = map_grasp_landmarks(points,observed,{**settings,'mapping_mode':'thumb_ip_plane'},grippers)
    expected_weights = [0.,0.,.5,1.,1.,.5]
    np.testing.assert_allclose(result['blend_original_weight'],np.repeat(np.array(expected_weights)[:,None],2,axis=1),atol=1e-14)
    np.testing.assert_allclose(result['gripper_action'],original['gripper_action'],atol=1e-12)
    for i,weight in enumerate(expected_weights):
        for h,g in enumerate(grippers):
            r0 = config1['transform_aligned_from_grasp'][i,h,:3,:3] @ np.diag([1.,-1.,-1.])
            r1 = original['transform_aligned_from_grasp'][i,h,:3,:3]
            expected = Slerp([0,1],Rotation.from_matrix([r0,r1]))([weight]).as_matrix()[0]
            np.testing.assert_allclose(result['transform_aligned_from_grasp'][i,h,:3,:3],expected,atol=1e-12)
            g.set_opening(result['gripper_action'][i,h]);g.place_tcp(result['transform_aligned_from_tcp'][i,h])
            np.testing.assert_allclose(g.tip_positions(settings['distal_tip_local_m']).mean(axis=0),points[i,h,3:5].mean(axis=0),atol=1e-12)
            assert np.linalg.det(g.model.root_link.worldrot()) == pytest.approx(1.)
    transform = np.eye(4);transform[:3,:3]=Rotation.from_euler('xyz',[.4,-.3,.8]).as_matrix();transform[:3,3]=[.7,-.2,.3]
    moved = map_grasp_landmarks(points @ transform[:3,:3].T + transform[:3,3],observed,settings,grippers,
        open_hand_landmarks=opened @ transform[:3,:3].T + transform[:3,3])
    np.testing.assert_allclose(moved['transform_aligned_from_tcp'],transform @ result['transform_aligned_from_tcp'],atol=1e-12)
    np.testing.assert_allclose(moved['blend_original_weight'],result['blend_original_weight'],atol=1e-12)


def test_roll_blend_invalid_inputs_and_thresholds(grippers):
    settings = read_json(ROOT / "configs/gripper_roll_blend.json")
    points=landmarks([.05]*5);opened=points[...,:5,:].copy();observed=np.ones((5,2),bool)
    observed[0,0]=False
    points[1,0,5]=points[1,0,2]  # Config 1 plane undefined.
    points[2,0,6]=points[2,0,2]  # Both plane forwards undefined.
    opened[3,0]=np.nan
    points[4,0,4]=points[4,0,3]+[0.,1.,0.]
    result=map_grasp_landmarks(points,observed,settings,grippers,open_hand_landmarks=opened)
    assert not result['mapping_valid'][:,0].any() and result['mapping_valid'][:,1].all()
    for key in ('blend_original_weight','blend_endpoint_angle_rad','gripper_roll_rad','transform_aligned_from_tcp'):
        assert np.isnan(result[key][:,0]).all()
    for low,high in [(-1,45),(45,45),(60,30),(0,181),(0,float('nan'))]:
        with pytest.raises(ValueError,match='blend_open_roll_degrees'):
            map_grasp_landmarks(points,observed,{**settings,'blend_open_roll_degrees':low,'blend_pinch_roll_degrees':high},grippers,open_hand_landmarks=opened)


def test_thumb_point_blend_geometry_fk_and_equivariance(grippers):
    settings = read_json(ROOT / "configs/gripper_thumb_point_blend.json")
    angles = [0., 30., 37.5, 45., 90., -37.5]
    points = landmarks([.05]*len(angles))
    opened = points[..., :5, :].copy()
    observed = np.ones(points.shape[:2], bool)
    for i, angle in enumerate(angles):
        points[i] = points[i] @ Rotation.from_euler('x', angle, degrees=True).as_matrix().T
    result = map_grasp_landmarks(points, observed, settings, grippers, open_hand_landmarks=opened)
    weights = np.repeat(np.array([0., 0., .5, 1., 1., .5])[:, None], 2, axis=1)
    expected_thumb = (1-weights[..., None])*points[..., 5, :] + weights[..., None]*points[..., 1, :]
    np.testing.assert_allclose(result['thumb_mcp_weight'], weights, atol=1e-14)
    np.testing.assert_allclose(result['interpolated_thumb_aligned_m'], expected_thumb, atol=1e-14)
    jaw = expected_thumb - points[..., 2, :]
    jaw /= np.linalg.norm(jaw, axis=-1, keepdims=True)
    forward = points[..., 6, :] - points[..., 2, :]
    forward -= np.sum(forward*jaw, axis=-1, keepdims=True)*jaw
    forward /= np.linalg.norm(forward, axis=-1, keepdims=True)
    expected_rotation = np.stack((forward, jaw, np.cross(forward, jaw)), axis=-1)
    np.testing.assert_allclose(result['transform_aligned_from_grasp'][..., :3, :3], expected_rotation, atol=1e-12)
    for hand, g in enumerate(grippers):
        for i in range(len(angles)):
            g.set_opening(result['gripper_action'][i, hand])
            g.place_tcp(result['transform_aligned_from_tcp'][i, hand])
            tips = g.tip_positions(settings['distal_tip_local_m'])
            np.testing.assert_allclose(tips.mean(axis=0), points[i, hand, 3:5].mean(axis=0), atol=1e-12)
            assert np.linalg.norm(tips[1]-tips[0]) == pytest.approx(.05, abs=1e-12)
    for mode, rows, flip in [('thumb_ip_plane', [0, 1], np.eye(3)),
                              ('mcp_plane', [3, 4], np.diag([1., -1., -1.]))]:
        endpoint = map_grasp_landmarks(points, observed, {**settings, 'mapping_mode': mode}, grippers)
        np.testing.assert_allclose(result['transform_aligned_from_grasp'][rows, :, :3, :3],
                                   endpoint['transform_aligned_from_grasp'][rows, :, :3, :3] @ flip, atol=1e-12)
    transform = np.eye(4)
    transform[:3, :3] = Rotation.from_euler('xyz', [.4, -.3, .8]).as_matrix()
    transform[:3, 3] = [.7, -.2, .3]
    moved = map_grasp_landmarks(points @ transform[:3, :3].T + transform[:3, 3], observed, settings, grippers,
        open_hand_landmarks=opened @ transform[:3, :3].T + transform[:3, 3])
    np.testing.assert_allclose(moved['transform_aligned_from_tcp'], transform @ result['transform_aligned_from_tcp'], atol=1e-12)
    np.testing.assert_allclose(moved['thumb_mcp_weight'], result['thumb_mcp_weight'], atol=1e-12)


def test_thumb_point_blend_invalid_geometry(grippers):
    settings = read_json(ROOT / "configs/gripper_thumb_point_blend.json")
    points = landmarks([.05]*4)
    opened = points[..., :5, :].copy()
    observed = np.ones((4, 2), bool)
    observed[0, 0] = False
    points[1, 0, 5] = points[1, 0, 2]  # At zero roll the chosen thumb point equals index MCP.
    points[2, 0, 6] = points[2, 0, 2]  # Undefined plane forward.
    opened[3, 0] = np.nan
    result = map_grasp_landmarks(points, observed, settings, grippers, open_hand_landmarks=opened)
    assert not result['mapping_valid'][:, 0].any() and result['mapping_valid'][:, 1].all()
    for key in ('thumb_mcp_weight', 'interpolated_thumb_aligned_m', 'transform_aligned_from_tcp'):
        assert np.isnan(result[key][:, 0]).all()
    with pytest.raises(ValueError, match='blend_open_roll_degrees'):
        map_grasp_landmarks(points, observed, {**settings, 'blend_open_roll_degrees': 45.}, grippers, open_hand_landmarks=opened)


def test_overlay_camera_transform_preserves_cv_projection():
    from egocentric_pipeline.gripper_overlay import camera_pose_opengl

    rotation = Rotation.from_euler('xyz', [.4, -.3, .8]).as_matrix()
    position = np.array([.7, -.2, .3])
    cv_points = np.array([[.1, .2, 1.], [-.2, -.1, 2.], [0, 0, 3.]])
    aligned = cv_points @ rotation.T + position
    pose = camera_pose_opengl(rotation, position)
    gl_points = (aligned-pose[:3, 3]) @ pose[:3, :3]
    np.testing.assert_allclose(gl_points, cv_points * [1, -1, -1], atol=1e-12)
    cv_pixels = 500*cv_points[:, :2]/cv_points[:, 2:] + [480, 270]
    gl_pixels = 500*gl_points[:, :2]*[1, -1]/(-gl_points[:, 2:]) + [480, 270]
    np.testing.assert_allclose(gl_pixels, cv_pixels, atol=1e-12)


def test_analytic_axes_center_and_continuous_opening(settings):
    settings = {**settings, "closed_distance_m": 0., "open_distance_m": .10}
    points = landmarks([0., .02, .05, .10, .20])
    original = points.copy()
    mapped = map_grasp_landmarks(points, np.ones((5, 2), bool), settings)
    assert mapped["mapping_valid"].all()
    for hand, sign in enumerate((-1, 1)):
        expected = np.array([[12/13, -5/13, 0], [5*sign/13, 12*sign/13, 0], [0, 0, sign]])
        np.testing.assert_allclose(mapped["transform_aligned_from_grasp"][:, hand, :3, :3],
                                   np.tile(expected, (5, 1, 1)), atol=1e-15)
    np.testing.assert_allclose(mapped["transform_aligned_from_tcp"][..., :3, 3], np.tile([.15, 0, 0], (5, 2, 1)))
    np.testing.assert_allclose(mapped["gripper_action"], np.repeat([[0], [.2], [.5], [1], [1]], 2, axis=1))
    np.testing.assert_array_equal(points, original)


def test_original_five_landmark_mapping_remains_reproducible(settings):
    legacy = {k: v for k, v in settings.items() if k not in ("orientation_priority", "wrist_thumb_offset_m")}
    legacy.pop("forward_axis")
    points = landmarks([.03])[..., :5, :].copy()
    points[..., 0, 2] = 0.
    mapped = map_grasp_landmarks(points, np.ones((1, 2), bool), legacy)
    for hand, sign in enumerate((-1, 1)):
        np.testing.assert_allclose(mapped["transform_aligned_from_grasp"][0, hand, :3, :3],
                                   np.diag([1, sign, sign]), atol=1e-15)
    with pytest.raises(ValueError, match="requires index PIP"):
        map_grasp_landmarks(points, np.ones((1, 2), bool), {**legacy, "forward_axis": "index_mcp_to_pip"})


def test_six_landmark_thumb_mapping_remains_reproducible(settings):
    points = landmarks([.03])[..., :6, :]
    legacy = {k: v for k, v in settings.items() if k not in ("orientation_priority", "wrist_thumb_offset_m")}
    legacy["forward_axis"] = "thumb_mcp_to_ip"
    mapped = map_grasp_landmarks(points, np.ones((1, 2), bool), legacy)
    x = np.array([2., 0., 1.]) / np.sqrt(5.)
    for hand, sign in enumerate((-1, 1)):
        y = np.array([0., sign, 0.])
        np.testing.assert_allclose(mapped["transform_aligned_from_grasp"][0, hand, :3, :3],
                                   np.stack([x, y, np.cross(x, y)], axis=-1), atol=1e-15)
    with pytest.raises(ValueError, match="requires index PIP"):
        map_grasp_landmarks(points, np.ones((1, 2), bool), {**legacy, "forward_axis": "index_mcp_to_pip"})


def test_index_segment_mapping_remains_reproducible(settings):
    points = landmarks([.03])
    legacy = {k: v for k, v in settings.items() if k not in ("orientation_priority", "wrist_thumb_offset_m")}
    mapped = map_grasp_landmarks(points, np.ones((1, 2), bool), {**legacy, "forward_axis": "index_mcp_to_pip"})
    x = np.array([.8, 0., -.6])
    for hand, sign in enumerate((-1, 1)):
        y = np.array([0., sign, 0.])
        np.testing.assert_allclose(mapped["transform_aligned_from_grasp"][0, hand, :3, :3],
                                   np.stack([x, y, np.cross(x, y)], axis=-1), atol=1e-15)


def test_thumbward_shift_and_axis_priority(settings):
    points = landmarks([.05])
    original = points.copy()
    start, end = grasp_forward_segment(points, settings)
    np.testing.assert_allclose(start[0], [[0, .025, 0], [0, -.025, 0]], atol=1e-15)
    np.testing.assert_allclose(end[0], [[.06, 0, 0], [.06, 0, 0]], atol=1e-15)
    np.testing.assert_array_equal(points, original)
    observed = np.ones((1, 2), bool)
    current = map_grasp_landmarks(points, observed, settings)
    direction = end - start
    np.testing.assert_allclose(current["transform_aligned_from_grasp"][..., :3, 0],
                               direction / np.linalg.norm(direction, axis=-1, keepdims=True), atol=1e-15)
    # Keeping closing exact cancels lateral shifts; preserve that historical rule.
    unshifted = map_grasp_landmarks(points, observed, {**settings, "wrist_thumb_offset_m": 0., "orientation_priority": "closing"})
    closing_first = map_grasp_landmarks(points, observed, {**settings, "orientation_priority": "closing"})
    np.testing.assert_allclose(closing_first["transform_aligned_from_grasp"], unshifted["transform_aligned_from_grasp"], atol=1e-15)
    assert not np.allclose(current["transform_aligned_from_grasp"], unshifted["transform_aligned_from_grasp"])


def test_opening_matches_user_selected_iphone_examples(settings):
    # Measured right-hand tip distances at source frames 92 and 119.
    points = landmarks([0.02107880248989149, 0.12549593759450284])
    result = map_grasp_landmarks(points, np.ones((2, 2), bool), settings)
    np.testing.assert_allclose(result["gripper_action"], [[.03, .03], [.33, .33]], atol=1e-12)
    # Distances below/above the fitted range still obey the action contract.
    points = landmarks([0., settings["open_distance_m"] + .01])
    result = map_grasp_landmarks(points, np.ones((2, 2), bool), settings)
    np.testing.assert_array_equal(result["gripper_action"], [[0., 0.], [1., 1.]])


def test_frame_equivariance_and_local_offsets(settings):
    points = landmarks([.03, .07])
    settings["tcp_offset_grasp_m"] = [[.01, .02, .03], [-.03, .04, .02]]
    settings["tcp_rotation_grasp_xyz_rad"] = [[.1, -.2, .3], [-.5, .6, -.1]]
    valid = np.ones((2, 2), bool)
    mapped = map_grasp_landmarks(points, valid, settings)
    transform = np.eye(4)
    transform[:3, :3] = Rotation.from_euler("xyz", [.7, -.4, 2.8]).as_matrix()
    transform[:3, 3] = [-.8, 1.2, .3]
    moved = map_grasp_landmarks(points @ transform[:3, :3].T + transform[:3, 3], valid, settings)
    for key in ("transform_aligned_from_grasp", "transform_aligned_from_tcp"):
        np.testing.assert_allclose(moved[key], transform @ mapped[key], atol=2e-14)
    np.testing.assert_allclose(moved["gripper_action"], mapped["gripper_action"], atol=1e-14)
    for hand in range(2):
        relative = np.linalg.inv(mapped["transform_aligned_from_grasp"][0, hand]) @ mapped["transform_aligned_from_tcp"][0, hand]
        np.testing.assert_allclose(relative[:3, 3], settings["tcp_offset_grasp_m"][hand], atol=1e-14)
        np.testing.assert_allclose(relative[:3, :3], Rotation.from_euler("xyz", settings["tcp_rotation_grasp_xyz_rad"][hand]).as_matrix(), atol=1e-14)


def test_invalid_geometry_and_missing_hand_isolation(settings):
    points = landmarks([.05] * 6)
    observed = np.ones((6, 2), bool)
    observed[0, 0] = False
    points[1, 0, 2] = points[1, 0, 1]  # Zero closing direction.
    closing = points[2, 0, 2] - points[2, 0, 1]
    points[2, 0, 0] = (points[2, 0, 1] + points[2, 0, 2]) / 2 + settings["wrist_thumb_offset_m"] * closing / np.linalg.norm(closing)
    points[3, 0, :3] = [[0, 0, 0], [.1, 0, 0], [.2, 0, 0]]
    points[4, 0, :3] = [[0, 0, 0], [.1, 0, 0], [.2, 1e-8, 0]]
    points[5, 0, 4] = np.nan
    mapped = map_grasp_landmarks(points, observed, settings)
    assert not mapped["mapping_valid"][:, 0].any()
    assert mapped["mapping_valid"][:, 1].all()
    for key in ("transform_aligned_from_grasp", "transform_aligned_from_tcp", "gripper_action"):
        assert np.isnan(mapped[key][:, 0]).all()
        assert np.isfinite(mapped[key][:, 1]).all()
    assert np.isnan(mapped["fingertip_distance_m"][0, 0])


@pytest.mark.parametrize("change", [
    {"open_distance_m": 0.}, {"closed_distance_m": -.1}, {"open_distance_m": float("nan")},
    {"minimum_axis_sine": 0.}, {"minimum_axis_length_m": -1.},
    {"tcp_offset_grasp_m": [[0, 0, 0]]}, {"tcp_rotation_grasp_xyz_rad": [[0, 0, 0], [0, 0, float("inf")]]},
    {"forward_axis": "unknown"},
    {"orientation_priority": "unknown"}, {"wrist_thumb_offset_m": -.01},
    {"wrist_thumb_offset_m": float("nan")}, {"forward_axis": "thumb_mcp_to_ip"},
])
def test_reject_invalid_configuration(settings, change):
    with pytest.raises(ValueError):
        map_grasp_landmarks(landmarks([.05]), np.ones((1, 2), bool), {**settings, **change})


def test_detached_gripper_matches_full_model_and_free_tcp_pose():
    from egocentric_pipeline.gripper_model import load_grippers
    from egocentric_pipeline.robot_workspace import load_robot, verify_asset_source

    assets = ROOT / "data/models/purdue-alex-assets"
    if not assets.is_dir():
        pytest.skip("Pinned Purdue assets are local inputs")
    robot_settings = read_json(ROOT / "configs/robot_workspace.json")
    full = load_robot(verify_asset_source(assets, robot_settings), robot_settings["base_frame"])
    full_links = {link.name: link for link in full.link_list}
    full_joints = {joint.name: joint for joint in full.joint_list}
    for gripper in load_grippers(assets, robot_settings):
        assert len(gripper.links) == 6 and len(gripper.joints) == 4
        root = full_links[f"{gripper.side}_ezgripper_palm_link"]
        for action in (0., .25, .5, .75, 1.):
            targets = gripper.set_opening(action)
            gripper.place_tcp(gripper.transform_palm_from_tcp)
            for name, angle in gripper.opening_command(action, gripper.side).items():
                full_joints[name].joint_angle(angle)
            transform = np.linalg.inv(root.worldcoords().T())
            for name, link in gripper.links.items():
                np.testing.assert_allclose(link.worldcoords().T(), transform @ full_links[name].worldcoords().T(), atol=1e-12)
                mesh = link.concatenated_visual_mesh
                if mesh is not None:
                    np.testing.assert_array_equal(mesh.vertices, full_links[name].concatenated_visual_mesh.vertices)
                    np.testing.assert_array_equal(mesh.faces, full_links[name].concatenated_visual_mesh.faces)
            assert all(angle == pytest.approx(1.3 * (1-action)) for angle in targets.values())
            assert all(j.min_angle <= j.joint_angle() <= j.max_angle for j in gripper.joints.values())
        target = np.eye(4)
        target[:3, :3] = Rotation.from_euler("xyz", [.9, -.6, 2.]).as_matrix()
        target[:3, 3] = [.6, -.3, .9]
        for action in (0., .5, 1.):
            gripper.set_opening(action)
            palm = gripper.place_tcp(target)
            np.testing.assert_allclose(gripper.tcp.worldcoords().T(), target, atol=1e-12)
            np.testing.assert_allclose(gripper.model.root_link.worldcoords().T(), palm, atol=1e-12)
        for action in (-.1, 1.1, np.nan):
            with pytest.raises(ValueError):
                gripper.set_opening(action)
        with pytest.raises(ValueError, match="rigid transform"):
            gripper.place_tcp(np.zeros((4, 4)))


@pytest.mark.parametrize("mode", ["landmark_frame", "fingertip_correspondence", "mcp_plane", "thumb_ip_plane", "wrist_roll", "wrist_roll_tips", "roll_blend", "thumb_point_blend"])
def test_cli_selected_frames_mano_landmarks_rgb_and_snapshot(tmp_path, settings, mode, grippers):
    from egocentric_pipeline.hand_geometry import load_mano_model, reconstruct_mano
    from egocentric_pipeline.gripper_visualization import review_rgb
    from smplx.vertex_ids import vertex_ids
    import torch

    torch.set_num_threads(2)
    models = [ROOT / "external/HaWoR/_DATA/data_left/mano_left/MANO_LEFT.pkl",
              ROOT / "external/HaWoR/_DATA/data/mano/MANO_RIGHT.pkl"]
    if not all(p.exists() for p in models) or not (ROOT / "data/models/purdue-alex-assets").exists():
        pytest.skip("Licensed MANO and pinned robot assets are local inputs")
    n = 6
    source = {"frame_index": np.arange(n), "timestamp_s": np.arange(n)/30,
              "source_timestamp_s": 5 + np.arange(n)/30,
              "export_valid": np.ones((n, 2), bool), "motion_infilled": np.zeros((n, 2), bool),
              "direct_detection": np.ones((n, 2), bool), "rotation_aligned_from_world": np.eye(3),
              "root_translation_aligned_m": np.zeros((n, 2, 3), np.float32),
              "root_orientation_aligned_axis_angle": np.zeros((n, 2, 3), np.float32),
              "hand_pose_axis_angle": np.zeros((n, 2, 45), np.float32), "mano_betas": np.zeros((n, 2, 10), np.float32),
              "wrist_position_aligned_m": np.zeros((n, 2, 3), np.float32)}
    source["root_translation_aligned_m"][:, 1, 0] = .5
    expected = []
    for hand, path in enumerate(models):
        model = load_mano_model(path, hand)
        joints, vertices = reconstruct_mano(model, source["root_translation_aligned_m"][:, hand],
            source["root_orientation_aligned_axis_angle"][:, hand], source["hand_pose_axis_angle"][:, hand], source["mano_betas"][:, hand])
        source["wrist_position_aligned_m"][:, hand] = joints[:, 0]
        expected.append((joints, vertices))
    source["motion_infilled"][1, 0] = True
    source["direct_detection"][1, 0] = False
    source["export_valid"][4, 1] = False
    source["direct_detection"][4, 1] = False
    source["wrist_position_aligned_m"][4, 1] = np.nan
    alignment = tmp_path / "alignment"
    alignment.mkdir()
    np.savez(alignment / "trajectory_aligned.npz", **source)
    video = tmp_path / "rgb.mp4"
    rgb = np.broadcast_to((np.arange(n)*30).astype(np.uint8)[:,None,None,None], (n,48,64,3)).copy()
    subprocess.run(["ffmpeg","-v","error","-f","rawvideo","-pix_fmt","rgb24","-s","64x48","-r","30","-i","-",
                    "-an","-c:v","libx264","-crf","0","-pix_fmt","yuv444p",str(video)], input=rgb.tobytes(), check=True)
    clip_path = tmp_path / "clip.json"
    clip_path.write_text(json.dumps({"prepared":{"frame_count":n,"width":64,"height":48},
        "frames":{"mapping":[{"timestamp_s":float(t),"source_timestamp_s":float(st)} for t,st in zip(source["timestamp_s"],source["source_timestamp_s"])]}}))
    (alignment / "alignment_report.json").write_text(json.dumps({"status":"completed","hand_order":["left","right"],
        "inputs":{"clip_metadata":{"path":str(clip_path)},"prepared_video":{"path":str(video)},
                  "mano_left":{"path":str(models[0])},"mano_right":{"path":str(models[1])}}}))
    output = tmp_path / "mapping"
    if mode != "landmark_frame":
        settings = {**read_json(ROOT / "configs/gripper_mapping.json"), "mapping_mode": mode}
    if mode in ("wrist_roll_tips", "roll_blend", "thumb_point_blend"):
        settings = read_json(ROOT / ("configs/gripper_wrist_roll.json" if mode == "wrist_roll_tips" else f"configs/gripper_{mode}.json"))
    config = tmp_path / "mapping-config.json"
    config.write_text(json.dumps(settings))
    command = [sys.executable,str(ROOT / "scripts/map_gripper.py"),"--alignment-directory",str(alignment),
               "--output-directory",str(output),"--frame-start","1","--frame-stop","5","--config",str(config)]
    subprocess.run(command, check=True, env={**os.environ,"PYTHONPATH":str(ROOT / "src")}, capture_output=True, text=True)
    arrays, report = load_mapping(output)
    np.testing.assert_array_equal(arrays["frame_index"], [1,2,3,4])
    for name in source:
        if name in arrays:
            np.testing.assert_array_equal(arrays[name], source[name][1:5])
    assert not arrays["mapping_valid"][0,0] and not arrays["mapping_valid"][3,1]
    if mode in ("wrist_roll", "wrist_roll_tips", "roll_blend", "thumb_point_blend"):
        # Source uses identity articulation, exactly the ideal-open reference.
        np.testing.assert_allclose(arrays["gripper_roll_rad"][arrays["mapping_valid"]], 0., atol=1e-12)
        if mode in ("wrist_roll", "wrist_roll_tips"):
            target = arrays["wrist_position_aligned_m"] - settings.get("wrist_backward_offset_m", 0.) * arrays["transform_aligned_from_palm"][..., :3, 0]
            np.testing.assert_allclose(arrays["transform_aligned_from_palm"][arrays["mapping_valid"], :3, 3],
                                       target[arrays["mapping_valid"]], atol=1e-7)
    assert np.isnan(arrays["landmarks_aligned_m"][0,0]).all()
    for hand in range(2):
        joints, vertices = expected[hand]
        points = arrays["landmarks_aligned_m"][1,hand]
        # Float32 MANO evaluation can round differently with different batch sizes.
        np.testing.assert_allclose(points[:3], joints[2,[0,14,1]], atol=1e-7, rtol=0)
        np.testing.assert_allclose(points[3:5], vertices[2,[vertex_ids["mano"]["thumb"],vertex_ids["mano"]["index"]]], atol=1e-7, rtol=0)
        np.testing.assert_allclose(points[5], joints[2,15], atol=1e-7, rtol=0)
        np.testing.assert_allclose(points[6], joints[2,2], atol=1e-7, rtol=0)
    decoded = review_rgb(report, arrays["frame_index"])
    np.testing.assert_allclose(decoded.mean(axis=(1,2,3)), [30,60,90,120], atol=2)
    tuned = copy.deepcopy(settings)
    if mode == "landmark_frame":
        tuned["open_distance_m"] = .2
    snapshot = tmp_path / "tuned"
    save_mapping(snapshot, arrays, report, tuned)
    saved, saved_report = load_mapping(snapshot)
    assert saved_report["settings"] == tuned
    np.testing.assert_allclose(saved["gripper_action"], map_grasp_landmarks(arrays["landmarks_aligned_m"], arrays["mapping_valid"], tuned, grippers,
        open_hand_landmarks=arrays.get("open_hand_landmarks_aligned_m"))["gripper_action"], equal_nan=True)
    if mode in ("wrist_roll", "wrist_roll_tips", "roll_blend", "thumb_point_blend"):
        for key in ("gripper_roll_rad", "zero_roll_rotation_aligned", "open_hand_landmarks_aligned_m"):
            np.testing.assert_allclose(saved[key], arrays[key], equal_nan=True)
    with pytest.raises(FileExistsError):
        save_mapping(snapshot, arrays, report, tuned)
