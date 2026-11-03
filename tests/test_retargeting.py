"""Essential segmentation, fixed-base geometry, missing-data and IK contracts."""

import json
from pathlib import Path

import numpy as np
import pytest

from egocentric_pipeline.retargeting.base_placement import base_transform, evaluate_placement, optimize_base, transform_points
from egocentric_pipeline.retargeting.manipulation_regions import camera_segments, frame_edges, interval_metrics
from egocentric_pipeline.retargeting.trajectory import load_alignment
from egocentric_pipeline.retargeting.workspace import WorkspaceGrid


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def settings():
    settings = json.loads((ROOT / "configs/defaults/retargeting.json").read_text())
    settings.update(workspace_margin_m=.03, optimizer_iterations=100, optimizer_population=16)
    return settings


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


def test_sdf_camera_initialization_bounds_and_prior(settings):
    grid = sphere_grid()
    points = np.array([[[0., .35, .5], [0., -.35, .5]]] * 4)
    settings.update(optimizer_iterations=20, optimizer_population=8,
                    base_translation_radius_m=.05, base_initialization_weight=2.,
                    camera_rotation_scale_rad=1.)
    initial = np.zeros(4)
    _, info = optimize_base(points, np.ones((4, 2), bool), grid, settings,
        initial_base=initial, camera_rotations=np.tile(np.eye(3), (4, 1, 1)),
        neutral_camera_rotation=np.eye(3))
    bounds = np.asarray(info["bounds_xyz_yaw"])
    np.testing.assert_allclose(bounds[:3], [[-.05, .05]] * 3)
    np.testing.assert_allclose(bounds[3], [-np.pi, np.pi])
    pose = np.asarray(info["base_xyz_yaw"])
    assert np.all(pose >= bounds[:, 0]) and np.all(pose <= bounds[:, 1])
    assert abs(pose[3]) < .1


def test_alignment_loader_detects_mismatched_source_time(tmp_path):
    n = 4
    times = np.arange(n) / 30
    arrays = dict(timestamp_s=times, source_timestamp_s=times + 10, frame_index=np.arange(n),
                  export_valid=np.ones((n, 2), bool), motion_infilled=np.zeros((n, 2), bool), wrist_position_aligned_m=np.zeros((n, 2, 3)),
                  rotation_aligned_from_world=np.eye(3))
    np.savez(tmp_path / "trajectory_aligned.npz", **arrays)
    clip = {"prepared": {"frame_count": n}, "frames": {"mapping": [{"timestamp_s": float(t), "source_timestamp_s": float(t + 10)} for t in times]}}
    metadata = tmp_path / "clip.json"
    metadata.write_text(json.dumps(clip))
    report = {"status": "completed", "hand_order": ["left", "right"], "inputs": {"clip_metadata": {"path": str(metadata)}}}
    (tmp_path / "alignment_report.json").write_text(json.dumps(report))
    for provenance in (None, np.zeros(n, bool), np.zeros((n, 2), float)):
        malformed = dict(arrays)
        if provenance is None:
            malformed.pop("motion_infilled")
        else:
            malformed["motion_infilled"] = provenance
        np.savez(tmp_path / "trajectory_aligned.npz", **malformed)
        with pytest.raises(ValueError, match="motion_infilled"):
            load_alignment(tmp_path)
    np.savez(tmp_path / "trajectory_aligned.npz", **arrays)
    restored, _, _ = load_alignment(tmp_path)
    np.testing.assert_array_equal(restored["source_timestamp_s"], times + 10)
    clip["frames"]["mapping"][0]["source_timestamp_s"] = 9
    metadata.write_text(json.dumps(clip))
    with pytest.raises(ValueError, match="timestamps disagree"):
        load_alignment(tmp_path)


def test_visual_state_exposes_ik_failure_even_when_workspace_also_fails():
    from egocentric_pipeline.visualization.retargeting_visualization import frame_state
    arrays = {"episode_id": np.array([0, 0, 0, 0, -1]),
              "export_valid": np.array([[True, True], [True, True], [True, False], [False, False], [True, True]]),
              "ik_success": np.array([[True, False], [True, True], [True, False], [False, False], [False, False]]),
              "candidate_frame_passed": np.array([[False, False, True, False, False]])}
    report = {"episodes": [{"candidate_id": 0}]}
    assert [frame_state(i, arrays, report)[0] for i in range(5)] == ["ik_failed", "infeasible", "feasible", "unknown", "unknown"]
    assert "workspace margin failed" in frame_state(0, arrays, report)[1]


@pytest.mark.parametrize("exclude_infill", [False, True])
def test_original_mano_meshes_follow_episode_base_and_missing_hand_validity(exclude_infill):
    pytest.importorskip("smplx")
    from scipy.spatial.transform import Rotation
    from egocentric_pipeline.geometry.hand_geometry import align_hand_geometry, load_mano_model, reconstruct_mano
    from egocentric_pipeline.visualization.retargeting_visualization import base_hand_meshes

    models = [ROOT / "external/HaWoR" / path for path in (
        "_DATA/data_left/mano_left/MANO_LEFT.pkl", "_DATA/data/mano/MANO_RIGHT.pkl")]
    if not all(p.is_file() for p in models):
        pytest.skip("Requires licensed MANO assets; see environment/README.md")
    rng = np.random.default_rng(7)
    arrays = {name: rng.normal(0, .15, (5, 2, width)).astype(np.float32) for name, width in (
        ("root_translation_world_m", 3), ("root_orientation_world_axis_angle", 3),
        ("hand_pose_axis_angle", 45), ("mano_betas", 10))}
    arrays["export_valid"] = np.ones((5, 2), bool)
    arrays["export_valid"][1, 1] = False
    original = {k: v.copy() for k, v in arrays.items()}
    rotation = Rotation.from_rotvec([.4, -.6, .2]).as_matrix()
    aligned, _ = align_hand_geometry(arrays, rotation, models)
    arrays.update(aligned)
    world_to_aligned = np.eye(4)
    world_to_aligned[:3, :3] = rotation
    base_transforms = [base_transform([.2, -.1, .4, .7]), base_transform([-.5, .3, -.2, -.6])]
    arrays["transform_base_from_world"] = np.array([t @ world_to_aligned for t in base_transforms])
    arrays["episode_id"] = np.array([0, 0, 1, 1, -1])
    arrays["ik_success"] = np.zeros((5, 2), bool)  # original meshes survive IK failure
    arrays["wrist_position_base_m"] = np.full((5, 2, 3), np.nan)
    report = {"episodes": [{"episode_id": 0, "candidate_id": 1}, {"episode_id": 1, "candidate_id": 0}]}
    for e in report["episodes"]:
        frames = arrays["episode_id"] == e["episode_id"]
        arrays["wrist_position_base_m"][frames] = transform_points(
            aligned["wrist_position_aligned_m"][frames], base_transforms[e["candidate_id"]])
    if exclude_infill:
        arrays["motion_infilled"] = np.zeros((5, 2), bool)
        arrays["motion_infilled"][2, 0] = True
        arrays["retarget_valid"] = arrays["export_valid"] & ~arrays["motion_infilled"]
        arrays["wrist_position_base_m"][~arrays["retarget_valid"]] = np.nan
    meshes = base_hand_meshes(arrays, report, models)
    for hand, (vertices, faces) in enumerate(meshes):
        valid = arrays.get("retarget_valid", arrays["export_valid"])[:, hand] & (arrays["episode_id"] >= 0)
        assert vertices.shape == (5, 778, 3) and faces.shape[1] == 3
        assert faces.min() == 0 and faces.max() < 778
        assert np.isnan(vertices[~valid]).all() and np.isfinite(vertices[valid]).all()
        # Independent route: reconstruct Part 1's rotated parameters, then apply
        # aligned-to-base. This catches wrong composition or an extra rotation.
        model = load_mano_model(models[hand], hand)
        _, aligned_vertices = reconstruct_mano(model,
            aligned["root_translation_aligned_m"][valid, hand],
            aligned["root_orientation_aligned_axis_angle"][valid, hand],
            arrays["hand_pose_axis_angle"][valid, hand], arrays["mano_betas"][valid, hand])
        for i, frame in enumerate(np.flatnonzero(valid)):
            cid = report["episodes"][arrays["episode_id"][frame]]["candidate_id"]
            np.testing.assert_allclose(vertices[frame], transform_points(aligned_vertices[i], base_transforms[cid]), atol=1e-6, rtol=0)
    for name, value in original.items():
        np.testing.assert_array_equal(arrays[name], value)
    arrays["wrist_position_base_m"][0, 0, 0] += .02
    with pytest.raises(ValueError, match="wrists disagree"):
        base_hand_meshes(arrays, report, models)
