"""Essential segmentation, fixed-base geometry, missing-data and IK contracts."""

import json
from pathlib import Path

import numpy as np
import pytest

from egocentric_pipeline.base_placement import base_transform, evaluate_placement, optimize_base, transform_points
from egocentric_pipeline.manipulation_regions import camera_segments, expand_region, frame_edges, interval_metrics, select_disjoint_regions
from egocentric_pipeline.retargeting import load_alignment, validate_settings
from egocentric_pipeline.workspace import WorkspaceGrid


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def settings():
    return json.loads((ROOT / "configs/trajectory_retargeting.json").read_text())


def sphere_grid():
    origin, spacing, shape = np.array([-1., -1., -.5]), .04, (50, 50, 50)
    xyz = np.stack(np.meshgrid(*[origin[i] + (np.arange(n) + .5) * spacing for i, n in enumerate(shape)], indexing="ij"), axis=-1)
    distances = np.stack([np.linalg.norm(xyz - [0, y, .5], axis=-1) - .25 for y in (.35, -.35)])
    return WorkspaceGrid(origin, spacing, distances < 0, distances)


def test_sustained_crossing_uses_first_crossing_and_keeps_short_tail(settings):
    settings.update(camera_smoothing_sigma_s=0, camera_sustain_s=.3, minimum_episode_s=.5)
    times = np.arange(12) * .1
    camera = np.zeros((12, 3))
    camera[1, 0] = .5  # isolated noise never confirms a crossing
    camera[5:, 0] = .4
    _, segments = camera_segments(camera, times, settings)
    assert [(s["start"], s["stop"]) for s in segments] == [(0, 6), (6, 12)]
    assert all(s["retained"] for s in segments)
    camera[9:, 0] = .8
    _, segments = camera_segments(camera, times, settings)
    assert [(s["start"], s["stop"], s["retained"]) for s in segments] == [(0, 6, True), (6, 10, False), (10, 12, False)]
    np.testing.assert_allclose([s["duration_s"] for s in segments], [.6, .4, .2])


def test_segmentation_ignores_z_and_smoothing_preserves_input(settings):
    times = np.arange(61) / 30
    camera = np.zeros((61, 3))
    camera[:, 2] = np.arange(61)
    original = camera.copy()
    smooth, segments = camera_segments(camera, times, settings)
    assert len(segments) == 1 and segments[0]["stop"] == 61
    np.testing.assert_array_equal(camera, original)
    assert not np.array_equal(camera, smooth)
    with pytest.raises(ValueError, match="uniform"):
        camera_segments(camera, times ** 2, settings)
    with pytest.raises(ValueError, match="increasing"):
        frame_edges([0, 1, 1])


def test_strict_fraction_gap_edges_unknowns_and_irregular_time(settings):
    times = np.arange(40) * .05
    edges = frame_edges(times)
    observed = np.ones(40, bool)
    passed = observed.copy()
    passed[:2] = False
    assert not interval_metrics(0, 40, passed, observed, edges, settings)["accepted"]  # exactly 95%
    passed[1] = True
    assert interval_metrics(0, 40, passed, observed, edges, settings)["accepted"]
    observed[:5] = False
    passed[:5] = False
    result = interval_metrics(0, 40, passed, observed, edges, settings)
    assert result["passing_fraction"] == 1 and not result["accepted"]  # unknown gap 0.25s
    assert result["longest_nonpassing_s"] == pytest.approx(.25)
    assert interval_metrics(0, 40, passed, np.zeros(40, bool), edges, settings)["passing_fraction"] is None
    # Gap duration uses time support, not a hard-coded 30 FPS count.
    edges = frame_edges([0, .01, .3, .5])
    result = interval_metrics(0, 4, np.array([True, False, True, True]), np.ones(4, bool), edges, settings)
    assert result["longest_nonpassing_s"] == pytest.approx(.29)


def test_expansion_does_not_bridge_long_gap_and_overlap_rechecks(settings):
    edges = frame_edges(np.arange(100) * .1)
    observed, passed = np.ones(100, bool), np.ones(100, bool)
    passed[65:70] = False
    seed = {"start": 20, "stop": 35}
    result = expand_region(seed, passed, observed, edges, settings)
    assert result["start"] == 0 and result["stop"] == 67
    assert result["longest_nonpassing_s"] == pytest.approx(.2)
    assert expand_region({"start": 60, "stop": 75}, passed, observed, edges, settings) is None
    candidates = [
        {"candidate_id": 0, "seed": {"start": 0, "stop": 30}, "expanded": interval_metrics(0, 60, observed, observed, edges, settings)},
        {"candidate_id": 1, "seed": {"start": 55, "stop": 80}, "expanded": interval_metrics(50, 100, observed, observed, edges, settings)},
    ]
    selected = select_disjoint_regions(candidates, [{"frame_passed": observed}] * 2, observed, edges, settings)
    assert [(c["retained"]["start"], c["retained"]["stop"]) for c in selected] == [(0, 60), (60, 100)]
    assert all(c["retained"]["accepted"] for c in selected)


def test_transform_direction_composition_and_inverse():
    transform = base_transform([1, 2, 3, np.pi / 2])
    np.testing.assert_allclose(transform_points([[1, 3, 3]], transform), [[1, 0, 0]], atol=1e-15)
    points = np.array([[.1, .2, .3], [-1, 2, 5]])
    np.testing.assert_allclose(transform_points(transform_points(points, transform), np.linalg.inv(transform)), points, atol=1e-14)
    aligned = base_transform([0, 0, 0, .3])
    np.testing.assert_allclose(transform_points(points, transform @ aligned), transform_points(transform_points(points, aligned), transform))


def test_sdf_hand_identity_missing_and_out_of_domain():
    grid = sphere_grid()
    wrists = np.array([[[0., .35, .5], [0, -.35, .5]], [[0, .35, .5], [np.nan]*3], [[np.nan]*3]*2, [[10, 0, 0], [0, -.35, .5]]])
    valid = np.isfinite(wrists).all(axis=-1)
    result = evaluate_placement(wrists, valid, np.eye(4), grid, .03)
    np.testing.assert_array_equal(result["frame_passed"], [True, True, False, False])
    assert not result["query_valid"][3, 0]
    assert np.isnan(result["distance_m"][~result["query_valid"]]).all()
    swapped = evaluate_placement(wrists[:1, ::-1], valid[:1], np.eye(4), grid, .03)
    assert not swapped["hand_passed"].any()


def test_seeded_optimizer_finds_known_feasible_placement(settings):
    grid = sphere_grid()
    base = np.array([[[x, .35, .5], [x, -.35, .5]] for x in np.linspace(-.08, .08, 8)])
    desired = base_transform([.6, -.2, .9, .7])
    wrists = transform_points(base, np.linalg.inv(desired))
    valid = np.ones((8, 2), bool)
    settings.update(optimizer_iterations=35, optimizer_population=8)
    transform, info = optimize_base(wrists, valid, grid, settings)
    assert evaluate_placement(wrists, valid, transform, grid, .03)["frame_passed"].all()
    assert not info["global_optimum_claimed"]
    with pytest.raises(ValueError, match="without any valid"):
        optimize_base(wrists, np.zeros_like(valid), grid, settings)


@pytest.mark.parametrize("field,value", [("workspace_margin_m", .02), ("ik_tolerance_m", .01),
                                        ("minimum_feasible_fraction", .9), ("optimizer_iterations", 0),
                                        ("camera_sustain_s", np.nan)])
def test_reject_invalid_or_weakened_acceptance_settings(settings, field, value):
    settings[field] = value
    with pytest.raises(ValueError):
        validate_settings(settings)


def test_alignment_loader_detects_mismatched_source_time(tmp_path):
    n = 4
    times = np.arange(n) / 30
    arrays = dict(timestamp_s=times, source_timestamp_s=times + 10, frame_index=np.arange(n),
                  export_valid=np.ones((n, 2), bool), wrist_position_aligned_m=np.zeros((n, 2, 3)),
                  rotation_aligned_from_world=np.eye(3))
    np.savez(tmp_path / "trajectory_aligned.npz", **arrays)
    clip = {"prepared": {"frame_count": n}, "frames": {"mapping": [{"timestamp_s": float(t), "source_timestamp_s": float(t + 10)} for t in times]}}
    metadata = tmp_path / "clip.json"
    metadata.write_text(json.dumps(clip))
    report = {"status": "completed", "hand_order": ["left", "right"], "inputs": {"clip_metadata": {"path": str(metadata)}}}
    (tmp_path / "alignment_report.json").write_text(json.dumps(report))
    restored, _, _ = load_alignment(tmp_path)
    np.testing.assert_array_equal(restored["source_timestamp_s"], times + 10)
    clip["frames"]["mapping"][0]["source_timestamp_s"] = 9
    metadata.write_text(json.dumps(clip))
    with pytest.raises(ValueError, match="timestamps disagree"):
        load_alignment(tmp_path)


def test_real_robot_sequential_ik_missing_and_unreachable(settings):
    from egocentric_pipeline.positional_ik import solve_trajectory
    from egocentric_pipeline.robot_workspace import arm_parameters, load_robot, verify_asset_source
    from skrobot.kinematics.differentiable import forward_kinematics_ee_batched_numpy

    assets = ROOT / "data/models/purdue-alex-assets"
    if not assets.exists():
        pytest.skip("Requires pinned Purdue assets; see environment/README.md")
    robot_settings = json.loads((ROOT / "configs/robot_workspace.json").read_text())
    robot = load_robot(verify_asset_source(assets, robot_settings), robot_settings["base_frame"])
    wrists = np.empty((4, 2, 3))
    bounds = []
    for hand in range(2):
        _, _, p = arm_parameters(robot, robot_settings["tool_frames"][hand], robot_settings["arm_joints"][hand])
        q = np.zeros((4, 7))
        q[1:, 1] = .02
        wrists[:, hand], _ = forward_kinematics_ee_batched_numpy(q, p)
        bounds.append((p["joint_limits_lower"], p["joint_limits_upper"]))
    valid = np.ones((4, 2), bool)
    valid[2, 1], wrists[2, 1] = False, np.nan
    wrists[3] = 10
    settings.update(ik_attempts=2, ik_iterations=20)
    result = solve_trajectory(robot, wrists, valid, robot_settings, settings)
    assert result["ik_success"][:2].all()
    assert not result["ik_success"][2, 1] and not result["ik_success"][3].any()
    assert np.isnan(result["joint_angles_rad"][~result["ik_success"]]).all()
    assert np.nanmax(result["ik_residual_m"]) <= settings["ik_tolerance_m"]
    for hand, (lower, upper) in enumerate(bounds):
        q = result["joint_angles_rad"][result["ik_success"][:, hand], hand]
        assert np.all(q >= lower) and np.all(q <= upper)


def test_visual_state_exposes_ik_failure_even_when_workspace_also_fails():
    from egocentric_pipeline.retargeting_visualization import frame_state
    arrays = {"episode_id": np.array([0, 0, 0, 0, -1]),
              "export_valid": np.array([[True, True], [True, True], [True, False], [False, False], [True, True]]),
              "ik_success": np.array([[True, False], [True, True], [True, False], [False, False], [False, False]]),
              "candidate_frame_passed": np.array([[False, False, True, False, False]])}
    report = {"episodes": [{"candidate_id": 0}]}
    assert [frame_state(i, arrays, report)[0] for i in range(5)] == ["ik_failed", "infeasible", "feasible", "unknown", "unknown"]
    assert "workspace margin failed" in frame_state(0, arrays, report)[1]
