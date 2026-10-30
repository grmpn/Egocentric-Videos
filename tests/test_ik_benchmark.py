"""Score denominators, physical time, and the real pinned robot collision model."""

import json
from pathlib import Path

import numpy as np
import pytest

from egocentric_pipeline.ik_benchmark import joint_motion, score_components, update_report, validate_settings
from egocentric_pipeline.robot_constraints import RobotConstraints
from egocentric_pipeline.run_metadata import write_json


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def settings():
    return json.loads((ROOT / "configs/ik_benchmark.json").read_text())


@pytest.mark.parametrize("key,value", [("position_tolerance_m", np.nan), ("orientation_tolerance_degrees", 181),
                                       ("acceleration_limit_rad_s2", 0), ("joint_position_tolerance_rad", -1),
                                       ("region_limit", 0), ("region_limit", True), ("region_limit", 1.5)])
def test_invalid_benchmark_definition_rejected(settings, key, value):
    with pytest.raises(ValueError):
        validate_settings(dict(settings, **{key: value}))


def test_scores_use_observed_hand_samples_and_all_evaluated_frames(settings):
    observed = np.array([[True, True], [False, True], [False, False], [True, True]])
    evaluated = np.array([True, True, True, False])
    pe = np.array([[.01, .01001], [np.nan, np.nan], [np.nan, np.nan], [0, 0]])
    oe = np.deg2rad([[4, 4.001], [np.nan, 1], [np.nan, np.nan], [0, 0]])
    result, total = score_components(pe, oe, observed, evaluated,
        np.array([True, False, True, True]), np.array([True, True, False, True]), settings)
    assert result["position_tracking"]["evaluated"] == 3
    assert result["position_tracking"]["passed"] == 1
    assert result["orientation_tracking"]["passed"] == 2
    assert result["joint_feasibility"]["evaluated"] == 3
    assert total == pytest.approx(25 * 7 / 3)
    _, empty = score_components(pe, oe, observed * False, evaluated,
        np.ones(4, bool), np.ones(4, bool), settings)
    assert empty is None


def test_source_time_derivatives_endpoints_and_missing_predictions():
    t = np.array([0., .1, .3, .4])
    q = np.column_stack([2 * t ** 2, -3 * t])
    v, a, speed, frame_a = joint_motion(q, t)
    np.testing.assert_allclose(v[:, 0], 2 * (t[1:] + t[:-1]))
    np.testing.assert_allclose(a, [[4, 0]] * 2, atol=1e-12)
    np.testing.assert_allclose(frame_a, [[4, 0]] * 4, atol=1e-12)
    np.testing.assert_allclose(speed[:, 1], 3)
    np.testing.assert_allclose(speed[:, 0], [0.2, .8, 1.4, 1.4])
    q[1] = np.nan
    assert np.isnan(joint_motion(q, t)[3]).all()
    with pytest.raises(ValueError, match="three"):
        joint_motion(q[:2], t[:2])
    with pytest.raises(ValueError, match="increasing"):
        joint_motion(q, t[::-1])


def test_actual_robot_collisions_bounds_and_coupled_mimics(settings):
    assets = ROOT / "data/models/purdue-alex-assets"
    if not assets.exists():
        pytest.skip("Pinned robot assets are local inputs")
    constraints = RobotConstraints(assets, json.loads((ROOT / "configs/robot_workspace.json").read_text()), settings)
    assert constraints.collision_pairs() == []
    first = "right_ezgripper_knuckle_palm_l1_1"
    second = "right_ezgripper_knuckle_l1_l2_1"
    q = constraints.set_pose([first, second], [1.4706902157656252, 1.8831541673261123])
    assert ("right_ezgripper_finger_l2_1", "right_ezgripper_finger_l2_2") in constraints.collision_pairs()
    q = constraints.set_pose([first], [.6], {second: first})
    for name in constraints.names:
        if name.startswith("right_ezgripper"):
            assert q[constraints.names.index(name)] == pytest.approx(.6)
    assert constraints.collision_pairs() == []
    # The FK library must not clip a bad trajectory into an apparently valid one.
    q = constraints.set_pose(["LEFT_ELBOW_Y"], [-3.])
    j = constraints.names.index("LEFT_ELBOW_Y")
    assert q[j] == -3. and q[j] < constraints.lower[j]


def test_report_preserves_prior_experiments_and_discloses_failure(tmp_path, settings):
    write_json(tmp_path / "benchmark_settings.json", settings)
    for slug in ("a", "b"):
        write_json(tmp_path / slug / "experiment.json", {"name": slug, "description": f"Configuration {slug}",
                                                       "status": "failed" if slug == "b" else "running"})
    update_report(tmp_path)
    text = (tmp_path / "REPORT.md").read_text()
    assert "smoothed hand-derived" in text and "10 rad/s² benchmark proxy" in text
    assert "first 1 retained manipulation region" in text
    assert "a (running)" in text and "b (failed)" in text
    assert "Configuration a" in text and "Configuration b" in text
    update_report(tmp_path)
    assert (tmp_path / "REPORT.md").read_text() == text
