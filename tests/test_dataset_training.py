"""Per-component masks must exclude invalid values before statistics and loss."""
import numpy as np
import pytest

from egocentric_pipeline.datasets.training import ee_validity, masked_mse
from egocentric_pipeline.datasets.robot_episode import joint_component_validity
from test_robot_episode import make_robot_regions
from egocentric_pipeline.run_metadata import read_json


def test_ee_dependency_mask():
    valid = np.ones((3, 18), bool)
    valid[0, 2] = False
    valid[1, 14] = False
    valid[2, 17] = False
    ee = ee_validity(valid)
    assert not ee[0, 0, :7].any() and ee[0, 0, 7] and ee[0, 1].all()
    assert ee[1].all()  # neck is not in the arm chain
    assert ee[2, 1, :7].all() and not ee[2, 1, 7]


def test_each_joint_motion_limit_invalidates_only_its_control(tmp_path):
    paths, _, _ = make_robot_regions(tmp_path)
    score = read_json(paths[0].parent / 'score.json')
    with np.load(paths[0].parent / 'benchmark_frame_metrics.npz') as saved:
        metrics = dict(saved)
    metrics['joint_positions_rad'][0, 0] = 4
    metrics['frame_max_speed_rad_s'][0, 1] = 6
    metrics['frame_acceleration_rad_s2'][0, 2] = 11
    valid = joint_component_validity(metrics, score, score['limits']['joint_names'])
    assert not valid[0, :3].any() and valid[0, 3:].all()


def test_masked_loss_sanitizes_nan_before_arithmetic_and_gradient():
    torch = pytest.importorskip('torch')
    prediction = torch.tensor([1., float('nan'), 3.], requires_grad=True)
    target = torch.tensor([2., float('nan'), 1000.])
    mask = torch.tensor([True, False, False])
    loss = masked_mse(prediction, target, mask)
    assert loss.item() == 1.
    loss.backward()
    torch.testing.assert_close(prediction.grad, torch.tensor([-2., 0., 0.]))
