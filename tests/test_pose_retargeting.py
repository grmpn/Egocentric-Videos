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
            np.testing.assert_allclose(p[i, h], links[rs["target_frames"][h]].worldpos()
                                       + links[rs["tool_frames"][h]].worldrot() @ m.wrist_offset, atol=1e-6)
            assert np.linalg.norm(p[i, h] - links[rs["target_frames"][h]].worldpos()) == pytest.approx(.05)
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
    # Missing wrist geometry contributes no pose residual, including wholly
    # missing frames; only camera rotation and regularization constrain them.
    perturbed = wrists.copy()
    perturbed[~valid] = 1e6
    other = PoseProblem(m, perturbed, rotations, cameras, valid, times, settings,
                        fixed_base=base if fixed else None, smooth=fixed)
    np.testing.assert_array_equal(other.evaluate(x)[0], residual)
    # Alter nominal camera translation without changing rotations/Jacobians.
    # Neither stage may acquire a camera-position objective through FK.
    original_forward = m.forward
    def translated_head(*args, **kwargs):
        result = list(original_forward(*args, **kwargs))
        result[3] = result[3] + np.array([2., -1., 3.])
        return tuple(result)
    m.forward = translated_head
    other.cached_x = None
    changed, changed_jac = other.evaluate(x)
    np.testing.assert_array_equal(changed, residual)
    np.testing.assert_array_equal(changed_jac.toarray(), jac.toarray())


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


@pytest.mark.parametrize("method", ["joint_base", "workspace"])
def test_viewer_treats_excluded_hands_as_missing(method):
    from egocentric_pipeline.retargeting_visualization import frame_state

    arrays = {"episode_id": np.zeros(3, int), "export_valid": np.ones((3, 2), bool),
              "retarget_valid": np.array([[False, True], [False, False], [True, False]]),
              "ik_success": np.array([[False, True], [False, False], [False, False]]),
              "candidate_frame_passed": np.array([[True, False, False]])}
    report = {"method": method, "episodes": [{"candidate_id": 0}]}
    assert [frame_state(i, arrays, report)[0] for i in range(3)] == ["feasible", "unknown", "ik_failed"]


@pytest.fixture
def aligned_input(tmp_path, model):
    """Small real FK input through the production alignment/retargeting boundary."""
    from egocentric_pipeline.hand_geometry import mano_palm_frames

    m, _, rs = model
    paths = [ROOT / "external/HaWoR" / p for p in (
        "_DATA/data_left/mano_left/MANO_LEFT.pkl", "_DATA/data/mano/MANO_RIGHT.pkl")]
    if not all(p.exists() for p in paths):
        pytest.skip("Requires licensed MANO assets")
    offsets = mano_palm_frames(paths)
    times = np.arange(8) / 6
    p, r, _, hp, hr = m.forward(np.tile(m.neutral, (8, 1)))
    source = dict(timestamp_s=times, source_timestamp_s=times + 10, frame_index=np.arange(8),
                  export_valid=np.ones((8, 2), bool), motion_infilled=np.zeros((8, 2), bool),
                  wrist_position_aligned_m=p, rotation_aligned_from_world=np.eye(3),
                  root_orientation_aligned_axis_angle=Rotation.from_matrix(
                      (r @ offsets.transpose(0, 2, 1)).reshape(-1, 3, 3)).as_rotvec().reshape(8, 2, 3),
                  camera_position_aligned_m=hp, camera_rotation_aligned_from_camera=hr)
    source["motion_infilled"][1, 0] = True
    source["motion_infilled"][2:4] = True
    source["motion_infilled"][4, 1] = True
    directory = tmp_path / "alignment"
    directory.mkdir()
    metadata = directory / "clip.json"
    metadata.write_text(json.dumps({"prepared": {"frame_count": 8}, "frames": {"mapping": [
        {"timestamp_s": float(t), "source_timestamp_s": float(t + 10)} for t in times]}}))
    inputs = {"clip_metadata": {"path": str(metadata)}, "prepared_video": {"path": "unused.mp4"},
              **{f"mano_{hand}": {"path": str(path)} for hand, path in zip(("left", "right"), paths)}}
    (directory / "alignment_report.json").write_text(json.dumps(
        {"status": "completed", "hand_order": ["left", "right"], "source_run_id": "synthetic", "inputs": inputs}))
    np.savez(directory / "trajectory_aligned.npz", **source)
    return directory, source, offsets, rs


def test_joint_workflow_ignores_infilled_geometry_and_exports_missing_labels(tmp_path, aligned_input, model, settings):
    from egocentric_pipeline.joint_retargeting import joint_retarget_trajectory
    from egocentric_pipeline.retargeting_comparison import compare_quality

    directory, source, offsets, rs = aligned_input
    settings.update(base_max_evaluations=30, trajectory_max_evaluations=30, fit_attempts=1)
    eligible = source["export_valid"] & ~source["motion_infilled"]
    outputs = []
    for index in range(2):
        if index:
            # Excluded NaN/absurd geometry must not influence either fitting stage.
            source["wrist_position_aligned_m"][~eligible] = np.nan
            source["root_orientation_aligned_axis_angle"][~eligible] = 1e6
            np.savez(directory / "trajectory_aligned.npz", **source)
        output = tmp_path / f"run-{index}"
        report = joint_retarget_trajectory(directory, output, settings, rs,
                                          ROOT / "data/models/purdue-alex-assets", render_video=False)
        with np.load(output / "trajectory_retargeted.npz") as f:
            arrays = dict(f)
        for name, values in source.items():
            assert arrays[name].dtype == values.dtype and arrays[name].tobytes() == values.tobytes()
        np.testing.assert_array_equal(arrays["retarget_valid"], eligible)
        np.testing.assert_array_equal(arrays["joint_prediction"], ~eligible)
        assert not arrays["ik_success"][~eligible].any()
        for name in ("wrist_position_base_m", "wrist_orientation_target_aligned", "wrist_orientation_target_base",
                     "ik_residual_m", "orientation_residual_rad"):
            assert np.isnan(arrays[name][~eligible]).all(), name
        assert np.isfinite(arrays["joint_solution_rad"]).all()
        assert report["episodes"][0]["region"]["observed_frames"] == 6
        assert report["episodes"][0]["region"]["longest_nonpassing_s"] >= 1 / 3 - 1e-10
        quality = compare_quality(output, model[0], offsets, settings)
        assert quality["observed_hand_frames"] == int(eligible.sum())
        assert quality["observed_frames"] == 6
        outputs.append(arrays)
    for name in ("joint_solution_rad", "transform_base_from_aligned", "ik_success", "ik_residual_m",
                 "orientation_residual_rad", "candidate_frame_passed"):
        np.testing.assert_array_equal(outputs[0][name], outputs[1][name])


def test_entirely_infilled_region_has_no_fit(tmp_path, aligned_input, settings):
    from egocentric_pipeline.joint_retargeting import joint_retarget_trajectory

    directory, source, _, rs = aligned_input
    source["motion_infilled"][:] = True
    np.savez(directory / "trajectory_aligned.npz", **source)
    output = tmp_path / "no-observations"
    report = joint_retarget_trajectory(directory, output, settings, rs,
                                      ROOT / "data/models/purdue-alex-assets", render_video=False)
    assert report["status"] == "completed" and not report["demo_accepted"]
    assert not report["episodes"] and report["seeds"][0]["reason"] == "no_observed_wrists"
    with np.load(output / "trajectory_retargeted.npz") as arrays:
        assert not arrays["retarget_valid"].any() and not arrays["ik_success"].any()
        assert np.isnan(arrays["joint_solution_rad"]).all()


@pytest.mark.parametrize("missing_hand", [0, 1])
def test_entirely_infilled_hand_still_allows_opposite_hand_fit_and_viewer(tmp_path, aligned_input, settings, model, missing_hand):
    from egocentric_pipeline.joint_retargeting import joint_retarget_trajectory
    from egocentric_pipeline.retargeting_comparison import compare_quality
    from egocentric_pipeline.retargeting_visualization import view_retargeting

    directory, source, offsets, rs = aligned_input
    source["motion_infilled"][:, missing_hand] = True
    np.savez(directory / "trajectory_aligned.npz", **source)
    settings.update(base_max_evaluations=5, trajectory_max_evaluations=5, fit_attempts=1)
    output = tmp_path / "one-hand"
    report = joint_retarget_trajectory(directory, output, settings, rs,
                                      ROOT / "data/models/purdue-alex-assets", render_video=False)
    assert report["episodes"][0]["observed_hand_frames"][missing_hand] == 0
    quality = compare_quality(output, model[0], offsets, settings)
    assert quality["observed_hand_frames"] == int((source["export_valid"] & ~source["motion_infilled"]).sum())
    # Exercise actual scene creation: Viser requires [N,3] path colors even
    # when one entire hand has no observations and its path is empty.
    viewer = view_retargeting(output, show_mano=False)
    viewer.close()


def test_workspace_workflow_ignores_infilled_geometry(tmp_path, aligned_input):
    from egocentric_pipeline.retargeting import retarget_trajectory
    from egocentric_pipeline.workspace import WorkspaceGrid

    directory, source, _, rs = aligned_input
    settings = json.loads((ROOT / "configs/trajectory_retargeting.json").read_text())
    settings.update(optimizer_iterations=2, optimizer_population=2, ik_attempts=1, ik_iterations=5)
    rs = dict(rs, voxel_size_m=.1)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    # A synthetic field suffices to exercise placement and IK masking; it does
    # not assert physical reachability or replace the sampled production grid.
    distances = np.full((2, 20, 20, 20), -.1)
    WorkspaceGrid(np.array([-1., -1., 0.]), .1, distances < 0, distances).save(workspace / "workspace_grid.npz")
    (workspace / "workspace_report.json").write_text(json.dumps({
        "status": "completed", "hand_order": ["left", "right"], "settings": rs,
        "arms": [{"tool_frame": tool, "target_frame": target}
                 for tool, target in zip(rs["tool_frames"], rs["target_frames"])]}))
    eligible = source["export_valid"] & ~source["motion_infilled"]
    outputs = []
    for index in range(2):
        if index:
            source["wrist_position_aligned_m"][~eligible] = np.nan
            np.savez(directory / "trajectory_aligned.npz", **source)
        output = tmp_path / f"workspace-run-{index}"
        report = retarget_trajectory(directory, workspace, output, settings,
                                    ROOT / "data/models/purdue-alex-assets", regions_only=True, render_video=False)
        with np.load(output / "trajectory_retargeted.npz") as f:
            arrays = dict(f)
        np.testing.assert_array_equal(arrays["retarget_valid"], eligible)
        assert not arrays["ik_success"][~eligible].any()
        assert not arrays["candidate_query_valid"][:, ~eligible].any()
        assert not arrays["candidate_hand_passed"][:, ~eligible].any()
        assert not arrays["ik_attempts"][~eligible].any()
        for name in ("wrist_position_base_m", "joint_angles_rad", "ik_residual_m"):
            assert np.isnan(arrays[name][~eligible]).all()
        assert report["episodes"][0]["combined"]["observed_frames"] == 6
        outputs.append(arrays)
    for name in ("transform_base_from_aligned", "candidate_frame_passed", "joint_angles_rad", "ik_success"):
        np.testing.assert_array_equal(outputs[0][name], outputs[1][name])


@pytest.mark.parametrize("stride", [1, 2])
def test_known_pose_region_fit_with_missing_observation(model, settings, stride):
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
    settings.update(base_max_evaluations=60, trajectory_max_evaluations=60, fit_attempts=1,
                    base_frame_stride=stride)
    b, before, after, info = fit_region(m, wrists, rotations, rot @ cameras, valid, times, base, settings)
    assert np.isfinite(after).all()
    assert np.all(after >= m.lower) and np.all(after <= m.upper)
    p, r, *_ = m.forward(after)
    rb = base_transform(b)[:3, :3].T
    assert np.max(np.linalg.norm((p @ rb.T + b[:3] - wrists)[valid], axis=-1)) <= .005
    assert np.max(rotation_error((rb @ r)[valid], rotations[valid])) <= np.deg2rad(10)
    assert info["base_sample_indices"] == list(range(0, 8, stride))
    assert before.shape == after.shape == (8, 16)
    if stride == 2:
        np.testing.assert_array_equal(before[-1], before[-2])
        np.testing.assert_allclose(before[1], (before[0] + before[2]) / 2)
    else:
        assert info["after_smoothing"]["acceleration_rms_rad_s2"] < info["before_smoothing"]["acceleration_rms_rad_s2"]
    # Interpolated alternate-frame poses can be smoother than observations.
    # Refinement must report, rather than conceal, that acceleration increase.
    _, acceleration = temporal_operators(times)
    for key, angles in [("before_smoothing", before), ("after_smoothing", after)]:
        assert info[key]["acceleration_rms_rad_s2"] == pytest.approx(
            np.sqrt(np.mean((acceleration @ angles.ravel())**2)))


@pytest.mark.parametrize("key,value", [("ik_tolerance_m", .01), ("orientation_tolerance_rad", .2),
                                      ("maximum_gap_s", .3), ("minimum_feasible_fraction", .9),
                                      ("fit_attempts", 0), ("position_scale_m", 0),
                                      ("hand_position_weight", 0), ("hand_orientation_weight", np.nan),
                                      ("base_frame_stride", 0), ("base_frame_stride", 1.5),
                                      ("wrist_offset_tool_m", [0, 0]), ("wrist_offset_tool_m", [np.nan, 0, 0])])
def test_reject_weakened_acceptance_and_invalid_solver_settings(settings, key, value):
    settings[key] = value
    with pytest.raises(ValueError):
        validate_settings(settings)


@pytest.mark.parametrize("fixed", [False, True])
def test_hand_weights_scale_only_matching_residuals(model, settings, fixed):
    m, _, _ = model
    q = np.tile(m.neutral, (3, 1)) + .01
    p, r, _, _, cameras = m.forward(q)
    wrists = p + .03
    orientations = Rotation.from_euler("z", .2).as_matrix() @ r
    valid = np.ones((3, 2), bool)
    times = np.array([0., .03, .08])
    base = np.zeros(4)
    x = q.ravel() if fixed else np.r_[base, q.ravel()]
    kwargs = dict(fixed_base=base if fixed else None, smooth=fixed)
    original = PoseProblem(m, wrists, orientations, cameras, valid, times, settings, **kwargs)
    reduced = PoseProblem(m, wrists, orientations, cameras, valid, times,
                          dict(settings, hand_position_weight=.2, hand_orientation_weight=.5), **kwargs)
    residual, jac = original.evaluate(x)
    weaker, weaker_jac = reduced.evaluate(x)
    factors = np.ones(len(residual))
    for start in (0, 36):
        factors[start:start + 9] = .2
        factors[start + 9:start + 36] = .5
    np.testing.assert_allclose(weaker, residual * factors, atol=1e-12)
    np.testing.assert_allclose(weaker_jac.toarray(), jac.toarray() * factors[:, None], atol=1e-12)
