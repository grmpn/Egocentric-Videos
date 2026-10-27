"""Direct geometry contracts, real gripper FK, and the preparation entry point."""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from egocentric_pipeline.gripper_mapping import load_mapping, map_grasp_landmarks, save_mapping
from egocentric_pipeline.run_metadata import read_json


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def settings():
    return read_json(ROOT / "configs/gripper_mapping.json")


def landmarks(distances):
    """Analytic thumb geometry: +X forward; opposite left/right closing signs."""
    points = np.zeros((len(distances), 2, 6, 3))
    for i, distance in enumerate(distances):
        for hand, sign in enumerate((-1, 1)):
            # Wrist direction differs from thumb MCP→IP, so axes cannot pass by
            # accidentally using the original forward definition.
            points[i, hand] = [[0, 0, -.04], [.06, -.02 * sign, 0], [.06, .02 * sign, 0],
                               [.15, -distance / 2 * sign, 0], [.15, distance / 2 * sign, 0],
                               [.10, -.01 * sign, 0]]
    return points


def test_analytic_axes_center_and_continuous_opening(settings):
    settings = {**settings, "closed_distance_m": 0., "open_distance_m": .10}
    points = landmarks([0., .02, .05, .10, .20])
    original = points.copy()
    mapped = map_grasp_landmarks(points, np.ones((5, 2), bool), settings)
    assert mapped["mapping_valid"].all()
    for hand, sign in enumerate((-1, 1)):
        np.testing.assert_allclose(mapped["transform_aligned_from_grasp"][:, hand, :3, :3],
                                   np.tile(np.diag([1, sign, sign]), (5, 1, 1)), atol=1e-15)
    np.testing.assert_allclose(mapped["transform_aligned_from_tcp"][..., :3, 3], np.tile([.15, 0, 0], (5, 2, 1)))
    np.testing.assert_allclose(mapped["gripper_action"], np.repeat([[0], [.2], [.5], [1], [1]], 2, axis=1))
    np.testing.assert_array_equal(points, original)


def test_original_five_landmark_mapping_remains_reproducible(settings):
    legacy = dict(settings)
    legacy.pop("forward_axis")
    points = landmarks([.03])[..., :5, :].copy()
    points[..., 0, 2] = 0.
    mapped = map_grasp_landmarks(points, np.ones((1, 2), bool), legacy)
    for hand, sign in enumerate((-1, 1)):
        np.testing.assert_allclose(mapped["transform_aligned_from_grasp"][0, hand, :3, :3],
                                   np.diag([1, sign, sign]), atol=1e-15)
    with pytest.raises(ValueError, match="requires thumb IP"):
        map_grasp_landmarks(points, np.ones((1, 2), bool), settings)


def test_opening_matches_user_selected_iphone_examples(settings):
    # Measured right-hand tip distances at source frames 92 and 119.
    points = landmarks([0.02107880248989149, 0.12549593759450284])
    result = map_grasp_landmarks(points, np.ones((2, 2), bool), settings)
    np.testing.assert_allclose(result["gripper_action"], [[.03, .03], [.33, .33]], atol=1e-12)
    # Distances below/above the fitted range still obey the action contract.
    points = landmarks([0., settings["open_distance_m"] + .01])
    result = map_grasp_landmarks(points, np.ones((2, 2), bool), settings)
    np.testing.assert_array_equal(result["gripper_action"], [[0., 0.], [1., 1.]])


def test_frame_equivariance_and_local_offsets(settings):
    points = landmarks([.03, .07])
    settings["tcp_offset_grasp_m"] = [[.01, .02, .03], [-.03, .04, .02]]
    settings["tcp_rotation_grasp_xyz_rad"] = [[.1, -.2, .3], [-.5, .6, -.1]]
    valid = np.ones((2, 2), bool)
    mapped = map_grasp_landmarks(points, valid, settings)
    transform = np.eye(4)
    transform[:3, :3] = Rotation.from_euler("xyz", [.7, -.4, 2.8]).as_matrix()
    transform[:3, 3] = [-.8, 1.2, .3]
    moved = map_grasp_landmarks(points @ transform[:3, :3].T + transform[:3, 3], valid, settings)
    for key in ("transform_aligned_from_grasp", "transform_aligned_from_tcp"):
        np.testing.assert_allclose(moved[key], transform @ mapped[key], atol=2e-14)
    np.testing.assert_allclose(moved["gripper_action"], mapped["gripper_action"], atol=1e-14)
    for hand in range(2):
        relative = np.linalg.inv(mapped["transform_aligned_from_grasp"][0, hand]) @ mapped["transform_aligned_from_tcp"][0, hand]
        np.testing.assert_allclose(relative[:3, 3], settings["tcp_offset_grasp_m"][hand], atol=1e-14)
        np.testing.assert_allclose(relative[:3, :3], Rotation.from_euler("xyz", settings["tcp_rotation_grasp_xyz_rad"][hand]).as_matrix(), atol=1e-14)


def test_invalid_geometry_and_missing_hand_isolation(settings):
    points = landmarks([.05] * 6)
    observed = np.ones((6, 2), bool)
    observed[0, 0] = False
    points[1, 0, 2] = points[1, 0, 1]  # Zero closing direction.
    points[2, 0, 5] = points[2, 0, 1]  # Zero forward direction.
    points[3, 0, [1, 2, 5]] = [[0, 0, 0], [.1, 0, 0], [.2, 0, 0]]
    points[4, 0, [1, 2, 5]] = [[0, 0, 0], [.1, 0, 0], [.2, 1e-8, 0]]
    points[5, 0, 4] = np.nan
    mapped = map_grasp_landmarks(points, observed, settings)
    assert not mapped["mapping_valid"][:, 0].any()
    assert mapped["mapping_valid"][:, 1].all()
    for key in ("transform_aligned_from_grasp", "transform_aligned_from_tcp", "gripper_action"):
        assert np.isnan(mapped[key][:, 0]).all()
        assert np.isfinite(mapped[key][:, 1]).all()
    assert np.isnan(mapped["fingertip_distance_m"][0, 0])


@pytest.mark.parametrize("change", [
    {"open_distance_m": 0.}, {"closed_distance_m": -.1}, {"open_distance_m": float("nan")},
    {"minimum_axis_sine": 0.}, {"minimum_axis_length_m": -1.},
    {"tcp_offset_grasp_m": [[0, 0, 0]]}, {"tcp_rotation_grasp_xyz_rad": [[0, 0, 0], [0, 0, float("inf")]]},
    {"forward_axis": "unknown"},
])
def test_reject_invalid_configuration(settings, change):
    with pytest.raises(ValueError):
        map_grasp_landmarks(landmarks([.05]), np.ones((1, 2), bool), {**settings, **change})


def test_detached_gripper_matches_full_model_and_free_tcp_pose():
    from egocentric_pipeline.gripper_model import load_grippers
    from egocentric_pipeline.robot_workspace import load_robot, verify_asset_source

    assets = ROOT / "data/models/purdue-alex-assets"
    if not assets.is_dir():
        pytest.skip("Pinned Purdue assets are local inputs")
    robot_settings = read_json(ROOT / "configs/robot_workspace.json")
    full = load_robot(verify_asset_source(assets, robot_settings), robot_settings["base_frame"])
    full_links = {link.name: link for link in full.link_list}
    full_joints = {joint.name: joint for joint in full.joint_list}
    for gripper in load_grippers(assets, robot_settings):
        assert len(gripper.links) == 6 and len(gripper.joints) == 4
        root = full_links[f"{gripper.side}_ezgripper_palm_link"]
        for action in (0., .25, .5, .75, 1.):
            targets = gripper.set_opening(action)
            gripper.place_tcp(gripper.transform_palm_from_tcp)
            for name, angle in gripper.opening_command(action, gripper.side).items():
                full_joints[name].joint_angle(angle)
            transform = np.linalg.inv(root.worldcoords().T())
            for name, link in gripper.links.items():
                np.testing.assert_allclose(link.worldcoords().T(), transform @ full_links[name].worldcoords().T(), atol=1e-12)
                mesh = link.concatenated_visual_mesh
                if mesh is not None:
                    np.testing.assert_array_equal(mesh.vertices, full_links[name].concatenated_visual_mesh.vertices)
                    np.testing.assert_array_equal(mesh.faces, full_links[name].concatenated_visual_mesh.faces)
            assert all(angle == pytest.approx(1.3 * (1-action)) for angle in targets.values())
            assert all(j.min_angle <= j.joint_angle() <= j.max_angle for j in gripper.joints.values())
        target = np.eye(4)
        target[:3, :3] = Rotation.from_euler("xyz", [.9, -.6, 2.]).as_matrix()
        target[:3, 3] = [.6, -.3, .9]
        for action in (0., .5, 1.):
            gripper.set_opening(action)
            palm = gripper.place_tcp(target)
            np.testing.assert_allclose(gripper.tcp.worldcoords().T(), target, atol=1e-12)
            np.testing.assert_allclose(gripper.model.root_link.worldcoords().T(), palm, atol=1e-12)
        for action in (-.1, 1.1, np.nan):
            with pytest.raises(ValueError):
                gripper.set_opening(action)
        with pytest.raises(ValueError, match="rigid transform"):
            gripper.place_tcp(np.zeros((4, 4)))


def test_cli_selected_frames_mano_landmarks_rgb_and_snapshot(tmp_path, settings):
    from egocentric_pipeline.hand_geometry import load_mano_model, reconstruct_mano
    from egocentric_pipeline.gripper_visualization import review_rgb
    from smplx.vertex_ids import vertex_ids
    import torch

    torch.set_num_threads(2)
    models = [ROOT / "external/HaWoR/_DATA/data_left/mano_left/MANO_LEFT.pkl",
              ROOT / "external/HaWoR/_DATA/data/mano/MANO_RIGHT.pkl"]
    if not all(p.exists() for p in models) or not (ROOT / "data/models/purdue-alex-assets").exists():
        pytest.skip("Licensed MANO and pinned robot assets are local inputs")
    n = 6
    source = {"frame_index": np.arange(n), "timestamp_s": np.arange(n)/30,
              "source_timestamp_s": 5 + np.arange(n)/30,
              "export_valid": np.ones((n, 2), bool), "motion_infilled": np.zeros((n, 2), bool),
              "direct_detection": np.ones((n, 2), bool), "rotation_aligned_from_world": np.eye(3),
              "root_translation_aligned_m": np.zeros((n, 2, 3), np.float32),
              "root_orientation_aligned_axis_angle": np.zeros((n, 2, 3), np.float32),
              "hand_pose_axis_angle": np.zeros((n, 2, 45), np.float32), "mano_betas": np.zeros((n, 2, 10), np.float32),
              "wrist_position_aligned_m": np.zeros((n, 2, 3), np.float32)}
    source["root_translation_aligned_m"][:, 1, 0] = .5
    expected = []
    for hand, path in enumerate(models):
        model = load_mano_model(path, hand)
        joints, vertices = reconstruct_mano(model, source["root_translation_aligned_m"][:, hand],
            source["root_orientation_aligned_axis_angle"][:, hand], source["hand_pose_axis_angle"][:, hand], source["mano_betas"][:, hand])
        source["wrist_position_aligned_m"][:, hand] = joints[:, 0]
        expected.append((joints, vertices))
    source["motion_infilled"][1, 0] = True
    source["direct_detection"][1, 0] = False
    source["export_valid"][4, 1] = False
    source["direct_detection"][4, 1] = False
    source["wrist_position_aligned_m"][4, 1] = np.nan
    alignment = tmp_path / "alignment"
    alignment.mkdir()
    np.savez(alignment / "trajectory_aligned.npz", **source)
    video = tmp_path / "rgb.mp4"
    rgb = np.broadcast_to((np.arange(n)*30).astype(np.uint8)[:,None,None,None], (n,48,64,3)).copy()
    subprocess.run(["ffmpeg","-v","error","-f","rawvideo","-pix_fmt","rgb24","-s","64x48","-r","30","-i","-",
                    "-an","-c:v","libx264","-crf","0","-pix_fmt","yuv444p",str(video)], input=rgb.tobytes(), check=True)
    clip_path = tmp_path / "clip.json"
    clip_path.write_text(json.dumps({"prepared":{"frame_count":n,"width":64,"height":48},
        "frames":{"mapping":[{"timestamp_s":float(t),"source_timestamp_s":float(st)} for t,st in zip(source["timestamp_s"],source["source_timestamp_s"])]}}))
    (alignment / "alignment_report.json").write_text(json.dumps({"status":"completed","hand_order":["left","right"],
        "inputs":{"clip_metadata":{"path":str(clip_path)},"prepared_video":{"path":str(video)},
                  "mano_left":{"path":str(models[0])},"mano_right":{"path":str(models[1])}}}))
    output = tmp_path / "mapping"
    command = [sys.executable,str(ROOT / "scripts/map_gripper.py"),"--alignment-directory",str(alignment),
               "--output-directory",str(output),"--frame-start","1","--frame-stop","5"]
    subprocess.run(command, check=True, env={**os.environ,"PYTHONPATH":str(ROOT / "src")}, capture_output=True, text=True)
    arrays, report = load_mapping(output)
    np.testing.assert_array_equal(arrays["frame_index"], [1,2,3,4])
    for name in source:
        if name in arrays:
            np.testing.assert_array_equal(arrays[name], source[name][1:5])
    assert not arrays["mapping_valid"][0,0] and not arrays["mapping_valid"][3,1]
    assert np.isnan(arrays["landmarks_aligned_m"][0,0]).all()
    for hand in range(2):
        joints, vertices = expected[hand]
        points = arrays["landmarks_aligned_m"][1,hand]
        # Float32 MANO evaluation can round differently with different batch sizes.
        np.testing.assert_allclose(points[:3], joints[2,[0,14,1]], atol=1e-7, rtol=0)
        np.testing.assert_allclose(points[3:5], vertices[2,[vertex_ids["mano"]["thumb"],vertex_ids["mano"]["index"]]], atol=1e-7, rtol=0)
        np.testing.assert_allclose(points[5], joints[2,15], atol=1e-7, rtol=0)
    decoded = review_rgb(report, arrays["frame_index"])
    np.testing.assert_allclose(decoded.mean(axis=(1,2,3)), [30,60,90,120], atol=2)
    tuned = copy.deepcopy(settings)
    tuned["open_distance_m"] = .2
    snapshot = tmp_path / "tuned"
    save_mapping(snapshot, arrays, report, tuned)
    saved, saved_report = load_mapping(snapshot)
    assert saved_report["settings"]["open_distance_m"] == .2
    np.testing.assert_allclose(saved["gripper_action"], map_grasp_landmarks(arrays["landmarks_aligned_m"], arrays["mapping_valid"], tuned)["gripper_action"], equal_nan=True)
    with pytest.raises(FileExistsError):
        save_mapping(snapshot, arrays, report, tuned)
