"""Essential comparison contracts: frame conventions, metric geometry and support."""

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from egocentric_pipeline.evaluation.trajectory_comparison import (
    align_trajectory, depth_to_droid_grid, initial_basis, pairwise_disagreement,
)


def fixture_trajectory():
    poses = np.tile(np.eye(4), (4, 1, 1))
    poses[:, :3, 3] = [[0, 0, 0], [1, 0, 0], [2, 1, 0], [3, 2, 0]]
    poses[:, :3, :3] = Rotation.from_euler("y", [0, 10, 20, 30], degrees=True).as_matrix()
    joints = np.zeros((4, 2, 2, 3))
    joints[:, :, 0] = [0.1, 0.2, 0.8]
    joints[:, :, 1] = [0.1, 0.2, 0.9]
    return poses, joints, np.ones((4, 2), bool)


def test_gauge_and_scale_changes_cancel_without_changing_hand_size():
    poses, joints, observed = fixture_trajectory()
    gauge = Rotation.from_euler("xyz", [35, -17, 80], degrees=True).as_matrix()
    moved = poses.copy()
    moved[:, :3, :3] = gauge @ poses[:, :3, :3]
    moved[:, :3, 3] = poses[:, :3, 3] @ gauge.T / 7 + [12, -9, 5]
    a = align_trajectory(poses, 1, [0, -1, 0], joints, observed)
    b = align_trajectory(moved, 7, [0, -1, 0], joints, observed)
    np.testing.assert_allclose(a["camera_pose"], b["camera_pose"], atol=1e-12)
    np.testing.assert_allclose(a["joints_m"], b["joints_m"], atol=1e-12)
    np.testing.assert_allclose(np.linalg.norm(b["joints_m"][:, :, 1] - b["joints_m"][:, :, 0], axis=-1), .1)
    np.testing.assert_allclose(a["camera_pose"][0, :3, 3], 0)


def test_camera_translation_affects_both_hands_and_later_drift_is_preserved():
    poses, joints, observed = fixture_trajectory()
    a = align_trajectory(poses, 1, [0, -1, 0], joints, observed)
    poses[-1, 0, 3] += 2
    b = align_trajectory(poses, 1, [0, -1, 0], joints, observed)
    delta = b["camera_pose"][-1, :3, 3] - a["camera_pose"][-1, :3, 3]
    assert np.linalg.norm(delta) == pytest.approx(2)
    np.testing.assert_allclose(b["joints_m"][-1] - a["joints_m"][-1], np.broadcast_to(delta, (2, 2, 3)))


def test_common_support_sum_mean_rmse_and_missing_gaps():
    poses, joints, observed = fixture_trajectory()
    items = {}
    for name, factor in [("a", 1), ("b", 2), ("c", 3)]:
        item = align_trajectory(poses, factor, [0, -1, 0], joints, observed)
        items[name] = item
    items["c"]["hand_valid"][2, 0] = False
    items["c"]["joints_m"][2, 0] = np.nan
    rows, curves = pairwise_disagreement(items, np.arange(4) / 30)
    assert len(rows) == 9
    row = next(r for r in rows if r["channel"] == "left_wrist" and r["method_a"] == "a" and r["method_b"] == "b")
    distances = np.array([0, 1, np.sqrt(13)])
    assert row["samples"] == 3
    assert row["coverage"] == .75
    assert row["sum_m"] == pytest.approx(distances.sum())
    assert row["mean_m"] == pytest.approx(distances.mean())
    assert row["rmse_m"] == pytest.approx(np.sqrt(np.mean(distances ** 2)))
    assert np.isnan(curves["left_wrist__a__b"][2])


def test_missing_camera_hides_hands_and_reference_must_exist():
    poses, joints, observed = fixture_trajectory()
    poses[2] = np.nan
    item = align_trajectory(poses, 1, [0, -1, 0], joints, observed)
    assert not item["hand_valid"][2].any()
    assert np.isnan(item["joints_m"][2]).all()
    poses[0] = np.nan
    with pytest.raises(ValueError, match="Initial camera"):
        align_trajectory(poses, 1, [0, -1, 0], joints, observed)


@pytest.mark.parametrize("bad", [-1, 0, np.nan])
def test_reject_invalid_metric_scale(bad):
    poses, joints, observed = fixture_trajectory()
    with pytest.raises(ValueError, match="scale"):
        align_trajectory(poses, bad, [0, -1, 0], joints, observed)


def test_reject_reflected_camera_frame_and_mismatched_timeline():
    poses, joints, observed = fixture_trajectory()
    good = align_trajectory(poses, 1, [0, -1, 0], joints, observed)
    poses[1, :, 0] *= -1
    with pytest.raises(ValueError, match="proper rigid"):
        align_trajectory(poses, 1, [0, -1, 0], joints, observed)
    with pytest.raises(ValueError, match="timeline"):
        pairwise_disagreement({"a": good, "b": good}, np.arange(3))
    with pytest.raises(ValueError, match="increasing"):
        pairwise_disagreement({"a": good, "b": good}, [0, 1, 1, 2])


def test_gravity_heading_is_right_handed_including_vertical_fallback():
    for up in ([0, -1, 0], [0, 0, 1]):
        basis, fallback = initial_basis(up)
        np.testing.assert_allclose(basis @ up, [0, 0, 1])
        np.testing.assert_allclose(basis @ basis.T, np.eye(3))
        assert np.linalg.det(basis) == pytest.approx(1)
        assert fallback == (up[2] == 1)


def test_depth_mapping_crops_instead_of_stretching_droid_border():
    # At the intermediate DROID resize dimensions, remapping is exactly a crop.
    h, w = 540, 960
    ratio = np.sqrt(384 * 512 / (h * w))
    rh, rw = int(h * ratio), int(w * ratio)
    depth = np.arange(rh * rw, dtype=np.float32).reshape(rh, rw)
    np.testing.assert_array_equal(depth_to_droid_grid(depth, (h, w)), depth[:rh - rh % 8, :rw - rw % 8])


def test_cli_preserves_configured_venv_interpreter_on_resume(tmp_path):
    import json
    from pathlib import Path
    import subprocess
    import sys

    # Virtual environments use symlinks to a base Python. Following that symlink
    # would lose the environment's packages when the stage subprocess is launched.
    executable = tmp_path / "venv/bin/python"
    executable.parent.mkdir(parents=True)
    executable.symlink_to(sys.executable)
    settings = {"mapping_python": str(executable)}
    config = tmp_path / "config.json"
    config.write_text(json.dumps(settings))
    output = tmp_path / "run"
    output.mkdir()
    (output / "settings.json").write_text(json.dumps(settings))
    (output / "input.json").write_text("{}")
    root = Path(__file__).resolve().parents[1]
    subprocess.run([sys.executable, str(root / "scripts/compare_trajectories.py"),
                    "--config", str(config), "--output", str(output), "--stage", "prepare"], check=True)


def test_production_shared_scale_recovers_known_units(tmp_path, monkeypatch):
    pytest.importorskip("torchmin", reason="Native scale fit runs in the HaWoR environment")
    import json
    from pathlib import Path
    from egocentric_pipeline.tracking.comparison_inference import scale
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    settings = json.loads((root / "configs/experiments/trajectory_comparison.json").read_text())
    settings["hawor_root"] = str(root / settings["hawor_root"])
    (tmp_path / "input/rgb/tracks_0_2").mkdir(parents=True)
    (tmp_path / "input.json").write_text(json.dumps({"height": 540, "width": 960, "frame_count": 2}))
    mask = np.zeros((2, 540, 960), bool)
    mask[:, 50:100, 100:200] = True
    np.save(tmp_path / "input/rgb/tracks_0_2/model_masks.npy", mask)
    target = np.full((2, 540, 960), .6, np.float32)
    grid = np.stack([depth_to_droid_grid(p, (540, 960)) for p in target])
    np.savez(tmp_path / "metric_depth.npz", frame_index=[0, 1], depth_m=target)
    np.savez(tmp_path / "hawor_raw.npz", keyframe_index=[0, 1], depth=grid / 3)
    np.savez(tmp_path / "lingbot_raw.npz", keyframe_index=[0, 1], depth=np.full((2, 294, 518), .6 / 5, np.float32))
    np.savez(tmp_path / "amb3r_raw.npz", keyframe_index=[0, 1], depth=np.full((2, 392, 518), .6 / 2, np.float32),
             depth_m=np.full((2, 392, 518), .6, np.float32))
    scale(settings, tmp_path, {})
    result = json.loads((tmp_path / "scales.json").read_text())
    for name, expected in [("hawor", 3), ("lingbot", 5), ("amb3r", 2)]:
        assert result[name]["scale"] == pytest.approx(expected, rel=1e-5)
    assert result["hawor"]["per_frame"][0]["pixels"] == result["lingbot"]["per_frame"][0]["pixels"]
