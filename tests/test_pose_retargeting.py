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


def require_cuda():
    cp = pytest.importorskip("cupy")
    pytest.importorskip("nvmath")
    try:
        if cp.cuda.runtime.getDeviceCount() == 0:
            pytest.skip("CUDA tests require an NVIDIA GPU")
    except cp.cuda.runtime.CUDARuntimeError:
        pytest.skip("CUDA tests require NVIDIA driver/device access")


@pytest.fixture
def settings():
    return dict(json.loads((ROOT / "configs/joint_retargeting.json").read_text()), solver_backend="cpu")


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


@pytest.fixture
def palm_model(model, settings):
    from egocentric_pipeline.gripper_model import load_gripper_commands

    _, robot, rs = model
    settings.update(hand_target_mode="gripper_palm", gripper_opening_weight=20., missing_hand_velocity_weight=5.)
    return PoseModel(robot, rs, settings, load_gripper_commands(ROOT / "data/models/purdue-alex-assets")), robot, rs


def test_palm_fk_opening_and_mimics(palm_model):
    m, robot, _ = palm_model
    q = np.random.default_rng(17).uniform(m.lower, m.upper, (4, m.dof))
    p, r, *_ = m.forward(q)
    wrists = m.physical_wrists(q)
    for i, angles in enumerate(q):
        for name, angle in zip(m.joint_names, angles):
            robot.__dict__[name].joint_angle(float(angle))
        for other, first in m.coupled_joints.items():
            robot.__dict__[other].joint_angle(robot.__dict__[first].joint_angle())
        for h, side in enumerate(("left", "right")):
            palm = robot.__dict__[f"{side}_ezgripper_palm_link"]
            np.testing.assert_allclose(p[i,h], palm.worldpos(), atol=1e-7)
            np.testing.assert_allclose(r[i,h], palm.worldrot(), atol=1e-7)
            np.testing.assert_allclose(wrists[i,h], robot.__dict__[f"{side.upper()}_WRIST_X_LINK"].worldpos(), atol=1e-7)
            for stem in ("palm_l1", "l1_l2"):
                for finger in (1,2):
                    assert robot.__dict__[f"{side}_ezgripper_knuckle_{stem}_{finger}"].joint_angle() == pytest.approx(angles[16+h])


@pytest.mark.parametrize("fixed", [False, True])
def test_palm_objective_derivatives_and_opening(palm_model, settings, fixed):
    m, _, _ = palm_model
    q = np.tile(m.neutral, (4, 1)) + .01
    p,r,_,_,cameras=m.forward(q)
    valid=np.array([[True,True],[False,True],[False,False],[True,True]])
    p[~valid],r[~valid]=np.nan,np.nan
    actions=1-q[:,16:18]/m.closed_angle
    actions[~valid]=np.nan
    problem=PoseProblem(m,p,r,cameras,valid,np.array([0.,.03,.07,.10]),settings,
                        fixed_base=np.zeros(4) if fixed else None,smooth=fixed,
                        opening_targets=actions if fixed else None)
    x=q.ravel() if fixed else np.r_[np.zeros(4),q.ravel()]
    residual,jac=problem.evaluate(x)
    direction=np.random.default_rng(4).normal(size=len(x))
    eps=1e-6
    numerical=(problem.evaluate(x+eps*direction)[0]-problem.evaluate(x-eps*direction)[0])/(2*eps)
    np.testing.assert_allclose(jac@direction,numerical,atol=2e-5,rtol=1e-6)
    if fixed:
        np.testing.assert_allclose(residual[-valid.sum():],0,atol=1e-12)


def test_missing_hand_penalty_is_local_and_never_neck(palm_model, settings):
    m,_,_=palm_model
    q=np.tile(m.neutral,(4,1));q[1:]+=0.02
    p,r,_,_,c=m.forward(q)
    valid=np.array([[True,True],[False,True],[False,True],[True,True]])
    times=np.arange(4)*.1
    off=PoseProblem(m,p,r,c,valid,times,dict(settings,missing_hand_velocity_weight=0),fixed_base=np.zeros(4),smooth=True)
    on=PoseProblem(m,p,r,c,valid,times,settings,fixed_base=np.zeros(4),smooth=True)
    penalty=on.regularizer[off.regularizer.shape[0]:]
    assert penalty.shape[0]==16  # two missing destinations, seven arm joints plus opening
    cols=np.unique(penalty.nonzero()[1]%m.dof)
    np.testing.assert_array_equal(cols,[0,1,2,3,4,5,6,16])
    expected=5*np.diff(q,axis=0)[:2][:,[0,1,2,3,4,5,6,16]]/.1
    np.testing.assert_allclose(penalty@q.ravel(),expected.ravel(),atol=1e-12)
    first=PoseProblem(m,p,r,c,valid,times,settings)
    first_off=PoseProblem(m,p,r,c,valid,times,dict(settings,missing_hand_velocity_weight=0))
    np.testing.assert_array_equal(first.regularizer.toarray(),first_off.regularizer.toarray())


def test_palm_cpu_cuda_fixed_base_agreement(palm_model, settings):
    require_cuda()
    m, _, _ = palm_model
    q = np.tile(m.neutral, (4, 1))
    q[:, 16:18] += np.arange(4)[:, None] * .005
    p, r, _, _, cameras = m.forward(q)
    valid = np.ones((4, 2), bool)
    valid[1, 0] = False
    opening = 1 - q[:, 16:18] / m.closed_angle
    answers = []
    for backend in ("cpu", "cuda"):
        problem = PoseProblem(m, p, r, cameras, valid, np.arange(4) * .1,
                              dict(settings, solver_backend=backend), fixed_base=np.zeros(4),
                              smooth=True, opening_targets=opening)
        _, result, info = problem.solve(np.zeros(4), np.tile(m.neutral, (4, 1)), 50)
        answers.append((result, info["cost"]))
    np.testing.assert_allclose(answers[0][0], answers[1][0], atol=2e-5, rtol=2e-5)
    assert answers[0][1] == pytest.approx(answers[1][1], rel=1e-6, abs=1e-8)


def test_gripper_workflow_export_and_benchmark(tmp_path, aligned_input, palm_model, settings):
    from egocentric_pipeline.ik_benchmark import evaluate_run
    from egocentric_pipeline.joint_retargeting import joint_retarget_trajectory
    from egocentric_pipeline.run_metadata import write_json

    directory, source, _, rs = aligned_input
    m, _, _ = palm_model
    source.update(direct_detection=source["export_valid"].copy(),
                  root_translation_aligned_m=source["wrist_position_aligned_m"].copy(),
                  hand_pose_axis_angle=np.zeros((8, 2, 45)), mano_betas=np.zeros((8, 2, 10)))
    np.savez(directory / "trajectory_aligned.npz", **source)
    valid = source["export_valid"] & ~source["motion_infilled"]
    p, r, *_ = m.forward(np.tile(m.neutral, (8, 1)))
    transforms = np.broadcast_to(np.eye(4), (8, 2, 4, 4)).copy()
    transforms[..., :3, :3], transforms[..., :3, 3] = r, p
    transforms[~valid] = np.nan
    opening = np.full((8, 2), .5)
    opening[~valid] = np.nan
    mapping = tmp_path / "mapping"
    mapping.mkdir()
    np.savez(mapping / "gripper_mapping.npz", **source, mapping_valid=valid,
             transform_aligned_from_palm=transforms, gripper_action=opening)
    write_json(mapping / "mapping_report.json", {"schema_version": 1, "status": "completed",
        "hand_order": ["left", "right"], "robot_settings": rs, "settings": {"mapping_mode": "wrist_roll"}})
    settings.update(base_max_evaluations=10, trajectory_max_evaluations=10, fit_attempts=1)
    run = tmp_path / "benchmark/run"
    report = joint_retarget_trajectory(directory, run / "trajectory", settings, rs,
        ROOT / "data/models/purdue-alex-assets", mapping_directory=mapping, render_video=False)
    with np.load(run / "trajectory/trajectory_retargeted.npz") as data:
        assert data["joint_solution_rad"].shape == (8, 18)
        assert data["gripper_action"].shape == (8, 2)
        for name in source:
            np.testing.assert_array_equal(source[name], data[name])
        assert np.isnan(data["wrist_position_base_m"][~valid]).all()
    assert len(report["coupled_joint_leaders"]) == 2
    benchmark = json.loads((ROOT / "configs/ik_benchmark.json").read_text())
    benchmark.update(hand_position_window_s=.5, hand_orientation_window_s=.5)
    result = evaluate_run(run, mapping, benchmark, "test", "Small production workflow")
    assert result["components"]["position_tracking"]["evaluated"] == int(valid.sum())
    assert result["components"]["joint_feasibility"]["evaluated"] == 8
    assert result["missing_robot_frames"] == 0
    with np.load(run / "benchmark_frame_metrics.npz") as data:
        np.testing.assert_allclose(data["target_position_aligned_m"][valid], p[valid], atol=1e-10)
        assert data["joint_positions_rad"].shape == (8, 24)
    rescored = evaluate_run(run, mapping, benchmark, "test", "Small production workflow")
    assert result["components"] == rescored["components"]
    transforms[valid, :3, 3] += .001
    np.savez(mapping / "gripper_mapping.npz", **source, mapping_valid=valid,
             transform_aligned_from_palm=transforms, gripper_action=opening)
    with pytest.raises(ValueError, match="targets, timestamps or observations differ"):
        evaluate_run(run, mapping, benchmark, "test", "Changed targets must not share the scoreboard")


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


def test_cuda_bound_optimum_and_evaluation_budget():
    require_cuda()
    from scipy import sparse
    from scipy.optimize import least_squares
    from egocentric_pipeline.gpu_least_squares import least_squares_cuda

    matrix = sparse.csr_matrix([[2., .3, 0.], [.2, 3., .4], [0., .2, 1.]])
    target = np.array([3., -4., .2])
    initial, lower, upper = np.zeros(3), np.full(3, -.5), np.full(3, .5)
    evaluate = lambda x: (matrix @ x - target, matrix)
    cpu = least_squares(lambda x: evaluate(x)[0], initial, jac=lambda x: matrix,
                        bounds=(lower, upper), x_scale="jac", ftol=1e-10, xtol=1e-10, gtol=1e-10)
    gpu = least_squares_cuda(evaluate, initial, lower, upper, 80, 1e-10)
    np.testing.assert_allclose(gpu.x, cpu.x, atol=2e-7)
    assert gpu.cost == pytest.approx(cpu.cost, rel=1e-10)
    assert np.all(gpu.x >= lower) and np.all(gpu.x <= upper)
    assert gpu.success and gpu.gpu["linear_solves"] > 0
    assert gpu.gpu["max_linear_backward_error"] < 1e-10
    stopped = least_squares_cuda(evaluate, initial, lower, upper, 1, 1e-10)
    np.testing.assert_array_equal(stopped.x, initial)
    assert stopped.nfev == 1 and not stopped.success


@pytest.mark.parametrize("fixed", [False, True])
@pytest.mark.parametrize("prior_weight", [0., .3])
def test_cuda_pose_fit_matches_cpu_objective_and_bounds(model, settings, fixed, prior_weight):
    require_cuda()
    m, _, _ = model
    times = np.array([0., .03, .07, .10, .15])
    target_q = np.tile(m.neutral, (len(times), 1)) + .025
    p, r, _, _, cameras = m.forward(target_q)
    base = np.array([.3, -.2, .1, .4])
    rotation = base_transform(base)[:3, :3].T
    wrists, rotations, cameras = p @ rotation.T + base[:3], rotation @ r, rotation @ cameras
    valid = np.array([[True, True], [False, True], [False, False], [True, False], [True, True]])
    wrists[~valid], rotations[~valid] = np.nan, np.nan
    costs = []
    for backend in ("cpu", "cuda"):
        options = dict(settings, solver_backend=backend, base_initialization_weight=prior_weight)
        problem = PoseProblem(m, wrists, rotations, cameras, valid, times, options,
                              fixed_base=base if fixed else None, smooth=fixed)
        b, q, info = problem.solve(base, np.tile(m.neutral, (len(times), 1)), 150)
        residual, jacobian = problem.evaluate(q.ravel() if fixed else np.r_[b, q.ravel()])
        assert np.isfinite(residual).all() and np.isfinite(jacobian.data).all()
        assert np.all(q >= m.lower) and np.all(q <= m.upper)
        assert info["cost"] == pytest.approx(.5 * residual @ residual, rel=1e-12)
        assert info["solver_backend"] == backend
        costs.append(info["cost"])
    # Nonlinear local paths need not match joint-for-joint; this near-neutral
    # problem should reach the same objective basin at the same tolerances.
    assert costs[1] <= costs[0] * 1.01 + 1e-8


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


@pytest.mark.parametrize("backend", ["cpu", "cuda"])
@pytest.mark.parametrize("refinement", [False, True])
def test_joint_workflow_ignores_infilled_geometry_and_exports_missing_labels(tmp_path, aligned_input, model, settings, backend, refinement):
    from egocentric_pipeline.joint_retargeting import joint_retarget_trajectory
    from egocentric_pipeline.retargeting_comparison import compare_quality

    directory, source, offsets, rs = aligned_input
    if backend == "cuda":
        require_cuda()
    settings["solver_backend"] = backend
    settings.update(base_max_evaluations=30, trajectory_max_evaluations=30, fit_attempts=1)
    if refinement:
        settings.update(hand_position_window_s=.5, hand_orientation_window_s=.5,
                        hand_filter_polyorder=1, base_initialization_weight=.3, merge_adjacent_regions=True)
    eligible = source["export_valid"] & ~source["motion_infilled"]
    outputs = []
    for index in range(2):
        if index:
            if not refinement:
                # Omitted new keys reproduce explicit disabled settings exactly.
                for key in list(settings):
                    if key.startswith(('hand_position_window', 'hand_orientation_window', 'hand_filter_', 'base_prior_', 'base_initialization_')) or key == 'merge_adjacent_regions':
                        del settings[key]
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
                     "ik_residual_m", "orientation_residual_rad", "wrist_position_filtered_aligned_m",
                     "wrist_orientation_filtered_aligned", "filtered_ik_residual_m", "filtered_orientation_residual_rad"):
            assert np.isnan(arrays[name][~eligible]).all(), name
        assert np.isfinite(arrays["joint_solution_rad"]).all()
        assert report["episodes"][0]["region"]["observed_frames"] == 6
        assert report["episodes"][0]["region"]["longest_nonpassing_s"] >= 1 / 3 - 1e-10
        expected = eligible & (arrays['ik_residual_m'] <= settings['ik_tolerance_m']) & (arrays['orientation_residual_rad'] <= settings['orientation_tolerance_rad'])
        np.testing.assert_array_equal(arrays['ik_success'], expected)
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


def test_base_prior_derivatives_wraparound_and_fixed_stage_exclusion(model, settings):
    m, _, _ = model
    q = np.tile(m.neutral, (3, 1))
    p, r, _, _, cameras = m.forward(q)
    times, valid = np.arange(3) / 30, np.ones((3, 2), bool)
    reference = np.array([.3, -.2, .1, np.pi - .02])
    base = reference + np.array([.1, -.3, .2, -2*np.pi + .04])
    options = dict(settings, base_initialization_weight=.3,
                   base_prior_translation_scale_m=.5, base_prior_yaw_scale_rad=.2)
    for fixed in (False, True):
        kwargs = dict(fixed_base=base if fixed else None, base_reference=reference)
        original = PoseProblem(m, p, r, cameras, valid, times, settings, **kwargs)
        problem = PoseProblem(m, p, r, cameras, valid, times, options, **kwargs)
        x = q.ravel() if fixed else np.r_[base, q.ravel()]
        res, jac = problem.evaluate(x)
        old, old_jac = original.evaluate(x)
        if fixed:
            np.testing.assert_array_equal(res, old)
            np.testing.assert_array_equal(jac.toarray(), old_jac.toarray())
        else:
            np.testing.assert_array_equal(res[:-4], old)
            np.testing.assert_array_equal(jac[:-4].toarray(), old_jac.toarray())
            np.testing.assert_allclose(res[-4:], .3 * np.array([.1/.5, -.3/.5, .2/.5, .04/.2]))
            for j in range(4):
                step = np.eye(len(x))[j] * 1e-6
                numerical = (problem.evaluate(x + step)[0] - problem.evaluate(x - step)[0]) / 2e-6
                np.testing.assert_allclose(jac[:, j].toarray().ravel(), numerical, atol=2e-6)


def test_restart_ranking_uses_original_observations(model, settings, monkeypatch):
    m, _, _ = model
    times = np.arange(8) / 6
    target_q = np.tile(m.neutral, (8, 1))
    raw_q = target_q.copy()
    raw_q[:, 3] += .2
    raw_q[:, 10] += .2
    p, r, _, _, cameras = m.forward(target_q)
    raw_p, raw_r, *_ = m.forward(raw_q)
    calls = []
    def solve(problem, base, initial_q, budget):
        attempt = len(calls) // 2
        calls.append(problem.fixed_base is not None)
        q = target_q.copy() if attempt == 0 else raw_q.copy()
        if problem.fixed_base is None:
            q[1::2, 3] += .02  # before is rougher, so raw-pose ranking decides
        return base, q, {'cost': 0. if attempt == 0 else 100.}
    monkeypatch.setattr(PoseProblem, 'solve', solve)
    settings.update(base_frame_stride=1, fit_attempts=2)
    _, _, q, info = fit_region(m, p, r, cameras, np.ones((8, 2), bool), times, np.zeros(4), settings,
                               raw_wrists=raw_p, raw_orientations=raw_r)
    assert info['selected_attempt'] == 1
    assert info['attempts'][0]['pose']['passing_frames'] == 0
    assert info['pose']['passing_frames'] == 8
    np.testing.assert_array_equal(q, raw_q)


@pytest.mark.parametrize('key,value', [('hand_position_window_s', -1), ('hand_orientation_window_s', np.nan),
                                     ('hand_filter_polyorder', 1.5), ('merge_adjacent_regions', 1),
                                     ('base_initialization_weight', -1), ('base_prior_translation_scale_m', 0),
                                     ('base_prior_yaw_scale_rad', np.inf)])
def test_invalid_refinement_settings(settings, key, value):
    with pytest.raises(ValueError):
        validate_settings(dict(settings, **{key: value}))
