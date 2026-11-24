"""Essential contracts for the ground-truth hand benchmark."""

from copy import deepcopy

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from egocentric_pipeline.evaluation.hand_trajectory import (
    JOINT_ORDER, evaluate_trajectory, finger_pa_error, initial_yaw_translation,
    interval_pairs, relative_translation_error, validate_trajectory,
)


SETTINGS = {"initial_alignment_s": 1., "rpe_intervals_s": [.5, 2., 4.],
            "scale_interval_s": 1., "scale_min_gt_displacement_m": .01,
            "timestamp_tolerance_s": .0001}


def trajectory():
    n = 150
    times = np.arange(n) / 30
    camera = np.tile(np.eye(4), (n, 1, 1))
    camera[:, :3, :3] = Rotation.from_euler("z", times * .1).as_matrix()
    camera[:, :3, 3] = np.column_stack((times * .02, times * 0, times * 0 + 1))
    wrists = np.column_stack((times * .05, .04 * np.sin(times), times * 0 + .8))
    wrists = np.stack((wrists + [0, -.15, 0], wrists + [0, .15, 0]), axis=1)
    offsets = np.random.default_rng(42).normal(size=(21, 3)) * .02
    offsets[0] = 0
    joints = wrists[:, :, None] + offsets
    local = np.einsum("tji,thkj->thki", camera[:, :3, :3], joints - camera[:, None, None, :3, 3])
    return {"timestamp_s": times, "frame_index": np.arange(n), "joint_order": np.array(JOINT_ORDER),
            "camera_to_world": camera, "joints_world_m": joints, "joints_camera_m": local,
            "wrist_rotation_world": np.tile(np.eye(3), (n, 2, 1, 1)), "up_world": np.array([0., 0., 1.]),
            "hand_valid": np.ones((n, 2), bool), "camera_valid": np.ones(n, bool),
            "direct_valid": np.ones((n, 2), bool), "infilled": np.zeros((n, 2), bool)}


def update_local(data):
    camera = data["camera_to_world"]
    data["joints_camera_m"] = np.einsum("tji,thkj->thki", camera[:, :3, :3],
                                          data["joints_world_m"] - camera[:, None, None, :3, 3])


def test_identical_trajectories_and_exact_interval_counts():
    data = trajectory()
    report, curves = evaluate_trajectory(data, data, SETTINGS)
    assert report["alignment"]["fit_samples"] == 60
    for hand in report["hands"].values():
        for name in ("initial_wrist_error", "gt_camera_wrist_error", "finger_pa_mpjpe", "rpe_0.5s", "rpe_2s", "rpe_4s"):
            assert hand[name]["value"] == pytest.approx(0, abs=1e-10)
        assert [hand[f"rpe_{interval}s"]["samples"] for interval in ("0.5", "2", "4")] == [135, 90, 30]
        assert hand["scale_ratio"]["value"] == pytest.approx(1)
        assert hand["scale_ratio"]["samples"] == 120
        assert hand["completeness"]["value"] == 100
    assert curves["left_rpe_4s"].shape == (30, 3)


def test_gravity_yaw_translation_gauge_removed_but_scale_preserved():
    gt = trajectory()
    pred = deepcopy(gt)
    rotation = Rotation.from_euler("xyz", [31, -27, 113], degrees=True).as_matrix()
    shift = np.array([3, 2, -5])
    pred["up_world"] = rotation @ gt["up_world"]
    pred["joints_world_m"] = gt["joints_world_m"] @ rotation.T + shift
    pred["wrist_rotation_world"] = rotation @ gt["wrist_rotation_world"]
    pred["camera_to_world"][:, :3, :3] = rotation @ gt["camera_to_world"][:, :3, :3]
    pred["camera_to_world"][:, :3, 3] = gt["camera_to_world"][:, :3, 3] @ rotation.T + shift
    report, _ = evaluate_trajectory(pred, gt, SETTINGS)
    assert report["hands"]["left"]["initial_wrist_error"]["value"] == pytest.approx(0, abs=1e-9)
    # A metric-scale error must survive yaw/translation fitting.
    pred = deepcopy(gt)
    pred["joints_world_m"] *= 2
    update_local(pred)
    report, _ = evaluate_trajectory(pred, gt, SETTINGS)
    assert report["hands"]["left"]["initial_wrist_error"]["value"] > 50
    assert report["hands"]["left"]["scale_ratio"]["value"] == pytest.approx(2)


def test_gt_camera_diagnostic_removes_only_camera_drift():
    gt = trajectory()
    pred = deepcopy(gt)
    drift = gt["timestamp_s"][:, None] * np.array([.1, 0, 0])
    pred["camera_to_world"][:, :3, 3] += drift
    pred["joints_world_m"] += drift[:, None, None]
    report, _ = evaluate_trajectory(pred, gt, SETTINGS)
    for hand in report["hands"].values():
        assert hand["gt_camera_wrist_error"]["value"] == pytest.approx(0, abs=1e-10)
        assert hand["initial_wrist_error"]["value"] > 100
        assert hand["rpe_4s"]["value"] == pytest.approx(400)


def test_rpe_matches_full_se3_composition_including_wrist_rotation():
    rng = np.random.default_rng(22)
    p, g = np.tile(np.eye(4), (7, 1, 1)), np.tile(np.eye(4), (7, 1, 1))
    for transforms in (p, g):
        transforms[:, :3, :3] = Rotation.random(7, random_state=rng).as_matrix()
        transforms[:, :3, 3] = rng.normal(size=(7, 3))
    i, j = np.arange(5), np.arange(2, 7)
    expected = np.linalg.inv(np.linalg.inv(g[i]) @ g[j]) @ (np.linalg.inv(p[i]) @ p[j])
    actual = relative_translation_error(p[:, :3, 3], p[:, :3, :3], g[:, :3, 3], g[:, :3, :3], i, j)
    np.testing.assert_allclose(actual, np.linalg.norm(expected[:, :3, 3], axis=-1), atol=1e-12)


def test_missing_frame_breaks_intervals_without_zero_error_or_shifted_start():
    gt, pred = trajectory(), trajectory()
    pred["hand_valid"][75, 0] = pred["direct_valid"][75, 0] = False
    report, curves = evaluate_trajectory(pred, gt, SETTINGS)
    left = report["hands"]["left"]
    assert np.isnan(curves["predicted_wrist_aligned_m"][75, 0]).all()
    assert left["rpe_4s"]["samples"] == 0 and left["rpe_4s"]["value"] is None
    assert left["completeness"]["value"] == pytest.approx(149 / 150 * 100)
    pred["hand_valid"][:30] = pred["direct_valid"][:30] = False
    report, _ = evaluate_trajectory(pred, gt, SETTINGS)
    assert report["alignment"] is None
    assert report["hands"]["right"]["initial_wrist_error"]["value"] is None


def test_scale_stationary_intervals_are_unavailable_with_counts():
    gt = trajectory()
    gt["joints_world_m"][:] = gt["joints_world_m"][0]
    update_local(gt)
    report, _ = evaluate_trajectory(gt, gt, SETTINGS)
    scale = report["hands"]["left"]["scale_ratio"]
    assert scale["value"] is None and scale["low_motion_pairs"] == 120


def test_pa_fits_similarity_but_does_not_reflect_or_include_wrist_in_error():
    gt = np.random.default_rng(3).normal(size=(21, 3)) * .03
    transform = Rotation.from_euler("xyz", [12, 32, 71], degrees=True)
    pred = transform.apply(gt) * 1.3 + [3, 4, 5]
    assert finger_pa_error(pred, gt) == pytest.approx(0, abs=1e-12)
    pred = gt.copy()
    pred[:, 0] *= -1
    assert finger_pa_error(pred, gt) > .005
    assert np.isnan(finger_pa_error(np.zeros((21, 3)), gt))


def test_common_support_preserves_fit_and_full_gt_completeness_denominator():
    gt, pred = trajectory(), trajectory()
    pred["joints_world_m"][80:, 0, :, 0] += .2
    update_local(pred)
    own, _ = evaluate_trajectory(pred, gt, SETTINGS)
    mask = np.ones((150, 2), bool)
    mask[80:, 0] = False
    common, _ = evaluate_trajectory(pred, gt, SETTINGS, common_support={"world": mask, "local": mask})
    assert own["alignment"] == common["alignment"]
    assert own["hands"]["left"]["initial_wrist_error"]["value"] > 0
    assert common["hands"]["left"]["initial_wrist_error"]["value"] == pytest.approx(0, abs=1e-10)
    assert common["hands"]["left"]["completeness"]["value"] == 100


def test_artifact_validation_rejects_silent_transform_and_identity_errors():
    data = trajectory()
    data["joints_world_m"] *= 1000
    with pytest.raises(ValueError, match="World/camera"):
        validate_trajectory(data)
    data = trajectory()
    data["camera_to_world"][0, 0, 0] *= -1
    with pytest.raises(ValueError, match="proper rotations"):
        validate_trajectory(data)
    data = trajectory()
    data["joint_order"] = "wrong"
    with pytest.raises(ValueError, match="joint order"):
        validate_trajectory(data)


def test_source_gaps_and_timestamp_mismatch_are_not_interpolated():
    gt, pred = trajectory(), trajectory()
    pred["timestamp_s"] += .001
    with pytest.raises(ValueError, match="frame/timestamp"):
        evaluate_trajectory(pred, gt, SETTINGS)
    frames = gt["frame_index"].copy()
    frames[75:] += 1
    i, j = interval_pairs(gt["timestamp_s"], frames, np.ones(150, bool), 4, .0001)
    assert len(i) == len(j) == 0
    points = np.ones((150, 2, 3))
    assert initial_yaw_translation(points, points, gt["timestamp_s"], gt["hand_valid"], 1) is None


def test_report_cli_preserves_missing_trials_and_equal_clip_averages(tmp_path):
    import json
    from pathlib import Path
    import subprocess
    import sys

    settings = {**SETTINGS, "methods": ["baseline", "missing"], "clips": [
        {"sequence_id": "one"}, {"sequence_id": "two"}], "plot_sequence_id": "one", "source_root": "."}
    config = tmp_path / "settings.json"
    config.write_text(json.dumps(settings))
    for seq, shift in (("one", .01), ("two", .03)):
        gt, pred = trajectory(), trajectory()
        pred["joints_camera_m"] += shift
        camera = pred["camera_to_world"]
        pred["joints_world_m"] = np.einsum("tij,thkj->thki", camera[:, :3, :3], pred["joints_camera_m"]) + camera[:, None, None, :3, 3]
        reference = tmp_path / "reference" / seq
        reference.mkdir(parents=True)
        np.savez(reference / "reference.npz", **gt)
        method = tmp_path / "baseline" / seq
        method.mkdir(parents=True)
        np.savez(method / "prediction.npz", **pred)
        (method / "run.json").write_text(json.dumps({"status": "completed", "performance": {
            "wall_time_s": 10 if seq == "one" else 30, "end_to_end_fps": 15 if seq == "one" else 5,
            "peak_vram_gib": 8 if seq == "one" else 12}, "components": [{"name": "detection",
            "status": "completed", "wall_time_s": 2, "effective_fps": 75, "processed_frames": 150, "frame_unit": "RGB frames"}]}))
    root = Path(__file__).resolve().parents[1]
    subprocess.run([sys.executable, str(root / "scripts/benchmark_hands.py"), "--config", str(config),
                    "--output", str(tmp_path), "--stage", "evaluate"], check=True, capture_output=True, text=True)
    report = json.loads((tmp_path / "evaluation.json").read_text())
    assert len(report["trials"]) == 4
    summary = report["summary"]
    assert summary["baseline"]["method"]["gt_camera_wrist_error"]["mean"] == pytest.approx(np.sqrt(3) * 20)
    assert summary["baseline"]["common"]["gt_camera_wrist_error"]["count"] == 0
    assert summary["baseline"]["performance"]["end_to_end_fps"]["mean"] == 10
    assert summary["baseline"]["completed_run_throughput_fps"] == 7.5
    assert summary["baseline"]["worst_peak_vram_gib"] == 12
    assert summary["missing"]["status_counts"] == {"not_run": 2}
    assert summary["missing"]["method"]["completeness"]["mean"] is None
    assert (tmp_path / "wrist-trajectories.pdf").is_file()
    assert (tmp_path / "component-averages.csv").read_text().splitlines()[1] == "baseline,detection,75.0,0.0,2"
