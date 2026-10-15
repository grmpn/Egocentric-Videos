"""Essential FK/frame, voxel and interpolation contracts, plus the real CLI."""

import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from egocentric_pipeline.workspace import WorkspaceGrid, build_grid


def test_voxel_indices_negative_coordinates_boundaries_and_round_trip():
    grid = build_grid([np.array([[-.033, .047, .081]]), np.array([[.027, -.031, -.022]])])
    points = np.array([[-.033, .047, .081], [.027, -.031, -.022]])
    indices, valid = grid.indices(points)
    assert valid.all()
    np.testing.assert_array_equal(grid.indices(grid.centers(indices))[0], indices)
    assert np.max(np.abs(grid.centers(indices) - points)) <= .01 + 1e-12
    hits, _ = grid.contains(points)
    np.testing.assert_array_equal(hits, [[True, False], [False, True]])
    upper = grid.origin_m + grid.shape * grid.spacing_m
    _, valid = grid.indices([grid.origin_m, upper, grid.origin_m - 1e-6, [np.nan, 0, 0], [np.inf, 0, 0]])
    np.testing.assert_array_equal(valid, [True, False, False, False, False])
    cell = grid.centers(indices[:1])[0]
    boundary = cell + [grid.spacing_m / 2, 0, 0]
    # Use a small distance on either side, avoiding representation-dependent exact decimal ties.
    before, _ = grid.indices([boundary - [1e-10, 0, 0]])
    after, _ = grid.indices([boundary + [1e-10, 0, 0]])
    np.testing.assert_array_equal(after - before, [[1, 0, 0]])


def test_edt_sign_metric_distances_padding_and_no_hole_filling(tmp_path):
    grid = build_grid([[[0, 0, 0], [.04, 0, 0]], [[0, .06, 0]]], .02, 2)
    index = grid.indices([[0, 0, 0]])[0][0]
    x, y, z = index
    assert grid.distance_m[0, x, y, z] == pytest.approx(-.02)
    assert grid.distance_m[0, x + 1, y, z] == pytest.approx(.02)
    assert grid.distance_m[0, x + 1, y + 1, z + 1] == pytest.approx(np.sqrt(3) * .02)
    assert not grid.occupancy[:, [0, -1], :, :].any()
    assert not grid.occupancy[:, :, [0, -1], :].any()
    assert not grid.occupancy[:, :, :, [0, -1]].any()
    assert grid.occupancy.sum() == 3
    path = tmp_path / "grid.npz"
    grid.save(path)
    restored = WorkspaceGrid.load(path)
    for key in ("origin_m", "spacing_m", "occupancy", "distance_m"):
        np.testing.assert_array_equal(getattr(grid, key), getattr(restored, key))
    with pytest.raises(FileExistsError):
        grid.save(path)


@pytest.mark.parametrize("dtype_name,tolerance", [("float32", 2e-6), ("float64", 1e-12)])
def test_trilinear_axis_order_centers_intermediate_values_gradient_and_domain(dtype_name, tolerance):
    torch = pytest.importorskip("torch")
    origin, spacing = np.array([-.2, -.3, -.4]), .02
    shape = (5, 7, 9)
    x, y, z = np.meshgrid(*[origin[a] + (np.arange(n) + .5) * spacing for a, n in enumerate(shape)], indexing="ij")
    field = np.stack([x + 2 * y + 3 * z, 4 * x - y + z])
    grid = WorkspaceGrid(origin, spacing, np.zeros((2, *shape), bool), field)
    dtype = getattr(torch, dtype_name)
    points = torch.tensor([[-.16, -.24, -.32], [-.15, -.25, -.35]], dtype=dtype, requires_grad=True)
    values, valid = grid.query(points)
    assert valid.all()
    expected = torch.stack([points[:, 0] + 2 * points[:, 1] + 3 * points[:, 2],
                            4 * points[:, 0] - points[:, 1] + points[:, 2]], dim=1)
    torch.testing.assert_close(values, expected, atol=tolerance, rtol=0)
    values[:, 0].sum().backward()
    torch.testing.assert_close(points.grad, torch.tensor([[1, 2, 3], [1, 2, 3]], dtype=dtype), atol=tolerance * 10, rtol=0)
    centers = torch.tensor(grid.centers(np.array([[0, 0, 0], [4, 6, 8]])), dtype=dtype)
    center_values, center_valid = grid.query(centers)
    assert center_valid.all()
    np.testing.assert_allclose(center_values.numpy(), field[:, [0, 4], [0, 6], [0, 8]].T, atol=tolerance, rtol=0)
    bad_points = torch.tensor(np.array([origin, [np.nan, 0, 0], [np.inf, 0, 0], [10, 10, 10]]), dtype=dtype)
    values, valid = grid.query(bad_points)
    assert not valid.any() and torch.isnan(values).all()
    # Lower corner belongs to a cell, but lies outside the center interpolation domain.
    assert grid.indices([origin])[1][0]


@pytest.mark.parametrize("clouds,spacing,padding", [([[], []], .02, 2), ([[[np.nan, 0, 0]], [[0, 0, 0]]], .02, 2),
                                                   ([[[0, 0, 0]], [[0, 0, 0]]], 0, 2),
                                                   ([[[0, 0, 0]], [[0, 0, 0]]], .02, 0)])
def test_reject_bad_grid_inputs(clouds, spacing, padding):
    with pytest.raises(ValueError):
        build_grid(clouds, spacing, padding)


def test_fk_known_rotated_base_fixed_tool_offset_and_seeded_prefix(tmp_path):
    pytest.importorskip("skrobot")
    from egocentric_pipeline.robot_workspace import arm_parameters, load_robot, sample_arm, verify_fk
    urdf = tmp_path / "arm.urdf"
    urdf.write_text('''<robot name="analytic"><link name="base"/><link name="shoulder"/><link name="arm"/><link name="tool"/>
      <joint name="mount" type="fixed"><parent link="base"/><child link="shoulder"/>
        <origin xyz="0.2 -0.3 0.4" rpy="0 0 1.5707963267948966"/></joint>
      <joint name="hinge" type="revolute"><parent link="shoulder"/><child link="arm"/><axis xyz="0 0 1"/>
        <limit lower="-3" upper="3" effort="1" velocity="1"/></joint>
      <joint name="offset" type="fixed"><parent link="arm"/><child link="tool"/><origin xyz="0.5 0 0"/></joint></robot>''')
    robot = load_robot(urdf, "base")
    chain, tool, parameters = arm_parameters(robot, "tool", ["hinge"])
    q, points = sample_arm(robot, parameters, 100, 21, 13)
    expected = np.column_stack((.2 - .5 * np.sin(q[:, 0]), -.3 + .5 * np.cos(q[:, 0]), np.full(100, .4)))
    np.testing.assert_allclose(points, expected, atol=1e-12)
    short_q, short_points = sample_arm(robot, parameters, 10, 21, 7)
    np.testing.assert_array_equal(short_q, q[:10])
    np.testing.assert_allclose(short_points, points[:10], atol=1e-15)
    check = verify_fk(robot, chain, tool, parameters, q[:5], 1e-8)
    assert check["max_position_error_m"] < 1e-8
    with pytest.raises(ValueError, match="chain"):
        arm_parameters(robot, "tool", ["wrong"])
    with pytest.raises(ValueError, match="Missing tool"):
        arm_parameters(robot, "missing", ["hinge"])


def test_cli_build_and_reload_actual_purdue_assets(tmp_path):
    pytest.importorskip("skrobot")
    pytest.importorskip("torch")
    root = Path(__file__).resolve().parents[1]
    assets = root / "data/models/purdue-alex-assets"
    if not assets.exists():
        pytest.skip("Requires the pinned Purdue Alex assets; see environment/README.md")
    settings = json.loads((root / "configs/robot_workspace.json").read_text())
    settings.update(samples_per_arm=64, held_out_samples_per_arm=16, fk_check_samples_per_arm=4)
    config = tmp_path / "settings.json"
    config.write_text(json.dumps(settings))
    output = tmp_path / "workspace"
    command = [sys.executable, str(root / "scripts/build_robot_workspace.py"), "--config", str(config), "--output-directory", str(output)]
    environment = dict(os.environ, PYTHONPATH=str(root / "src"))
    result = subprocess.run(command, env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((output / "workspace_report.json").read_text())
    assert report["status"] == "completed" and report["grid"]["reload_exact"]
    grid = WorkspaceGrid.load(output / "workspace_grid.npz")
    for hand, name in enumerate(("left", "right")):
        with np.load(output / f"samples_{name}.npz", allow_pickle=False) as data:
            points, q = data["positions_base_m"], data["joint_angles_rad"]
            assert points.shape == (64, 3) and q.shape == (64, 7)
            assert np.all(q >= report["arms"][hand]["lower_rad"])
            assert np.all(q <= report["arms"][hand]["upper_rad"])
            hits, valid = grid.contains(points)
            assert valid.all() and hits[:, hand].all()
    second = subprocess.run(command, env=environment, capture_output=True, text=True)
    assert second.returncode != 0 and 'FileExistsError' in second.stderr
