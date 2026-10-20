"""FK, sparse derivatives, orientation frames and region-level pose contracts."""

import json
from pathlib import Path

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from egocentric_pipeline.base_placement import base_transform
from egocentric_pipeline.joint_retargeting import validate_settings
from egocentric_pipeline.pose_retargeting import (
    PoseModel, PoseProblem, fit_region, initialize_base, rotation_error, temporal_operators)
from egocentric_pipeline.robot_workspace import load_robot

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def settings():
    return json.loads((ROOT / "configs/joint_retargeting.json").read_text())


@pytest.fixture
def model(settings):
    robot_settings = json.loads((ROOT / "configs/robot_workspace.json").read_text())
    urdf = ROOT / "data/models/purdue-alex-assets" / robot_settings["urdf"]
    if not urdf.exists():
        pytest.skip("Requires pinned Purdue Alex assets; see environment/README.md")
    robot = load_robot(urdf, robot_settings["base_frame"])
    return PoseModel(robot, robot_settings, settings), robot, robot_settings


def test_library_fk_matches_ordinary_model_and_optical_axes(model):
    m, robot, rs = model
    q = np.random.default_rng(5).uniform(m.lower, m.upper, (5, 16))
    p, r, tcp, hp, hr = m.forward(q)
    links = {link.name: link for link in robot.link_list}
    for i, angles in enumerate(q):
        for name, angle in zip(m.joint_names, angles):
            robot.__dict__[name].joint_angle(float(angle))
        for h in range(2):
            np.testing.assert_allclose(p[i, h], links[rs["target_frames"][h]].worldpos(), atol=1e-6)
            np.testing.assert_allclose(tcp[i, h], links[rs["tool_frames"][h]].worldpos(), atol=1e-6)
            assert rotation_error(r[i, h], links[rs["tool_frames"][h]].worldrot()) < 1e-6
        head = links["HEAD_ZED_X_MINI_LINK"]
        np.testing.assert_allclose(hp[i], head.worldpos(), atol=1e-6)
        # Optical forward/right/down match body forward/right/down, not identity.
        np.testing.assert_allclose(hr[i, :, 2], head.worldrot()[:, 0], atol=1e-6)
        np.testing.assert_allclose(hr[i, :, 0], -head.worldrot()[:, 1], atol=1e-6)
        np.testing.assert_allclose(hr[i, :, 1], -head.worldrot()[:, 2], atol=1e-6)


def test_camera_initialization_wraparound_offset_and_degenerate_heading(model):
    m, _, _ = model
    yaw = np.deg2rad([179, -179])
    cameras = Rotation.from_euler("z", yaw).as_matrix() @ m.optical
    positions = np.array([[1., 2., 3.], [1.2, 2., 3.]])
    base = initialize_base(positions, cameras, m, .01)
    assert abs(abs(base[3]) - np.pi) < 1e-10
    offset = m.forward(m.neutral[None])[3][0]
    np.testing.assert_allclose(base[:3] + Rotation.from_euler("z", base[3]).apply(offset), [1.1, 2., 3.])
    with pytest.raises(ValueError, match="horizontal"):
        initialize_base(positions, np.tile(np.eye(3), (2, 1, 1)), m, .01)
    with pytest.raises(ValueError, match="cancel"):
        initialize_base(positions, Rotation.from_euler("z", [0, np.pi]).as_matrix() @ m.optical, m, .01)


@pytest.mark.parametrize("heading_deg", [25., 179., -179.])
def test_camera_initialization_medians_resist_heading_and_position_outliers(model, heading_deg):
    m, _, _ = model
    yaw = np.deg2rad([heading_deg, heading_deg, heading_deg + 80])
    cameras = Rotation.from_euler("z", yaw).as_matrix() @ m.optical
    positions = np.array([[1., 2., 3.], [1., 2., 3.], [90., -50., 80.]])
    base = initialize_base(positions, cameras, m, .01)
    rotation = Rotation.from_euler("z", base[3]).as_matrix()
    np.testing.assert_allclose(rotation, Rotation.from_euler("z", yaw[0]).as_matrix(), atol=1e-12)
    offset = m.forward(m.neutral[None])[3][0]
    np.testing.assert_allclose(base[:3] + rotation @ offset, [1., 2., 3.], atol=1e-12)
    # The same observations in a different temporal order give the same median.
    np.testing.assert_allclose(initialize_base(positions[::-1], cameras[::-1], m, .01), base)


@pytest.mark.parametrize("fixed", [False, True])
def test_sparse_objective_derivatives_missing_hands_and_irregular_times(model, settings, fixed):
    m, _, _ = model
    times = np.array([0., .03, .07, .10])
    q = np.tile(m.neutral, (4, 1)) + .01
    p, r, _, _, cameras = m.forward(q)
    base = np.array([.3, -.2, .1, .4])
    rot = base_transform(base)[:3, :3].T
    wrists, rotations, cameras = p @ rot.T + base[:3], rot @ r, rot @ cameras
    valid = np.array([[True, True], [False, True], [False, False], [True, True]])
    wrists[~valid], rotations[~valid] = np.nan, np.nan
    problem = PoseProblem(m, wrists, rotations, cameras, valid, times, settings,
                          fixed_base=base if fixed else None, smooth=fixed)
    x = q.ravel() if fixed else np.r_[base, q.ravel()]
    residual, jac = problem.evaluate(x)
    assert np.isfinite(residual).all() and np.isfinite(jac.data).all()
    for seed in range(3):
        direction = np.random.default_rng(seed).normal(size=len(x))
        direction /= np.linalg.norm(direction)
        eps = 1e-5
        numerical = (problem.evaluate(x + eps * direction)[0] - problem.evaluate(x - eps * direction)[0]) / (2 * eps)
        np.testing.assert_allclose(jac @ direction, numerical, atol=2e-6, rtol=1e-6)
    # No camera translations are accepted by the objective at all. Missing
    # wrist geometry contributes no pose residual, including wholly missing frames.
    perturbed = wrists.copy()
    perturbed[~valid] = 1e6
    other = PoseProblem(m, perturbed, rotations, cameras, valid, times, settings,
                        fixed_base=base if fixed else None, smooth=fixed)
    np.testing.assert_array_equal(other.evaluate(x)[0], residual)


def test_source_timed_derivatives_and_rotations_near_pi():
    times = np.array([0., .1, .4, .6])
    velocity, acceleration = temporal_operators(times, 1)
    np.testing.assert_allclose(velocity @ (times**2), times[1:] + times[:-1])
    np.testing.assert_allclose(acceleration @ (times**2), 2.)
    assert rotation_error(Rotation.from_euler("z", np.pi).as_matrix(), np.eye(3)) == pytest.approx(np.pi)
    with pytest.raises(ValueError, match="increasing"):
        temporal_operators([0, 0, 1])


def test_neutral_mano_palm_frames_preserve_hand_identity():
    from egocentric_pipeline.hand_geometry import mano_palm_frames, load_mano_model, reconstruct_mano
    paths = [ROOT / "external/HaWoR" / p for p in (
        "_DATA/data_left/mano_left/MANO_LEFT.pkl", "_DATA/data/mano/MANO_RIGHT.pkl")]
    if not all(p.exists() for p in paths):
        pytest.skip("Requires licensed MANO assets")
    frames = mano_palm_frames(paths)
    np.testing.assert_allclose(frames.transpose(0, 2, 1) @ frames, np.tile(np.eye(3), (2, 1, 1)), atol=1e-12)
    np.testing.assert_allclose(np.linalg.det(frames), 1.)
    assert frames[0, 0, 0] > .9 and frames[1, 0, 0] < -.9
    for h, path in enumerate(paths):
        model = load_mano_model(path, h)
        zero = np.zeros((1, 3), np.float32)
        joints, _ = reconstruct_mano(model, zero, zero, np.zeros((1, 45), np.float32), np.zeros((1, 10), np.float32))
        # A neutral middle knuckle lies on palm +X; index is on the +Y side.
        local = (joints[0] - joints[0, 0]) @ frames[h]
        np.testing.assert_allclose(local[4, 1:], 0, atol=1e-8)
        assert local[4, 0] > 0 and local[1, 1] > local[7, 1]


def test_pose_viewer_distinguishes_failure_missing_and_unassigned():
    from egocentric_pipeline.retargeting_visualization import frame_state
    arrays = {"episode_id": np.array([0, 0, 0, -1]),
              "export_valid": np.array([[True, True], [False, True], [False, False], [True, True]]),
              "ik_success": np.array([[False, True], [False, True], [False, False], [False, False]])}
    report = {"method": "joint_base", "episodes": [{"candidate_id": 0}]}
    assert [frame_state(i, arrays, report)[0] for i in range(4)] == ["ik_failed", "feasible", "unknown", "unknown"]


def test_known_pose_region_fit_with_missing_observation(model, settings):
    m, _, _ = model
    times = np.arange(8) / 6
    q = np.tile(m.neutral, (8, 1))
    q[:, 3] -= .025 * np.sin(np.arange(8))
    p, r, _, _, cameras = m.forward(q)
    base = np.array([.2, .1, -.4, .3])
    rot = base_transform(base)[:3, :3].T
    wrists, rotations = p @ rot.T + base[:3], rot @ r
    valid = np.ones((8, 2), bool)
    valid[2, 0] = False
    wrists[~valid], rotations[~valid] = np.nan, np.nan
    settings.update(base_max_evaluations=60, trajectory_max_evaluations=60, fit_attempts=1)
    b, before, after, info = fit_region(m, wrists, rotations, rot @ cameras, valid, times, base, settings)
    assert np.isfinite(after).all()
    assert np.all(after >= m.lower) and np.all(after <= m.upper)
    p, r, *_ = m.forward(after)
    rb = base_transform(b)[:3, :3].T
    assert np.max(np.linalg.norm((p @ rb.T + b[:3] - wrists)[valid], axis=-1)) <= .005
    assert np.max(rotation_error((rb @ r)[valid], rotations[valid])) <= np.deg2rad(10)
    assert info["after_smoothing"]["acceleration_rms_rad_s2"] < info["before_smoothing"]["acceleration_rms_rad_s2"]


@pytest.mark.parametrize("key,value", [("ik_tolerance_m", .01), ("orientation_tolerance_rad", .2),
                                      ("maximum_gap_s", .3), ("minimum_feasible_fraction", .9),
                                      ("fit_attempts", 0), ("position_scale_m", 0)])
def test_reject_weakened_acceptance_and_invalid_solver_settings(settings, key, value):
    settings[key] = value
    with pytest.raises(ValueError):
        validate_settings(settings)
