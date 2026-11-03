"""Known geometry, estimator decisions and the supported failure path."""

import json
from pathlib import Path

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from egocentric_pipeline.gravity_alignment import (
    aggregate_up, gravity_basis, load_camera_trajectory, rotate_mano_parameters,
)
from egocentric_pipeline.gravity_estimation import read_video_frames, select_sharp_frames
from egocentric_pipeline.gravity_pipeline import align_run, validate_settings


@pytest.mark.parametrize("up", [[0, 0, 1], [0, 0, -1], [1, 1e-10, 0], [-1, 0, 1e-10], [.3, -.8, .5]])
def test_known_tilt_proper_rotation_and_reversible_geometry(up):
    up = np.asarray(up, dtype=float)
    up /= np.linalg.norm(up)
    matrix, reference = gravity_basis(up)
    np.testing.assert_allclose(matrix @ up, [0, 0, 1], atol=1e-12)
    np.testing.assert_allclose(matrix @ matrix.T, np.eye(3), atol=1e-12)
    np.testing.assert_allclose(np.linalg.det(matrix), 1, atol=1e-12)
    repeated, same_reference = gravity_basis(up)
    assert np.array_equal(matrix, repeated) and reference == same_reference
    points = np.array([[1, 2, 3], [-4, 2, 6], [0, .2, 1]])
    transformed = points @ matrix.T
    np.testing.assert_allclose(transformed @ matrix, points, atol=1e-12)
    np.testing.assert_allclose(np.linalg.norm(np.diff(points, axis=0), axis=1),
                               np.linalg.norm(np.diff(transformed, axis=0), axis=1), atol=1e-12)


def test_camera_to_world_before_median_with_outlier_and_sign_flip():
    rotation = Rotation.from_euler("xyz", [[i * .05, -.4, .2] for i in range(12)]).as_matrix()
    up = np.array([.2, -.3, .9]); up /= np.linalg.norm(up)
    world = np.tile(up, (12, 1))
    world[3] *= -1
    world[10] = [.9, .1, .1]
    camera = np.einsum("nji,nj->ni", rotation, world)
    result, evidence = aggregate_up(camera, rotation)
    np.testing.assert_allclose(result, up, atol=1e-12)
    assert evidence["hemisphere_flipped"][3]
    assert not evidence["mad_inlier"][10]
    assert evidence["inlier_count"] == 11
    assert evidence["dispersion_before_mad_deg"]["p95"] > 1
    assert evidence["dispersion_after_mad_deg"]["p95"] < 1e-5
    # Using world-to-camera here would tilt the result: this fixture catches it.
    wrong, _ = aggregate_up(camera, rotation.transpose(0, 2, 1))
    assert np.linalg.norm(wrong - up) > .1


def test_small_sample_zero_mad_and_explicit_failures():
    up = np.tile([0., 0., 1.], (3, 1))
    rotation = np.tile(np.eye(3), (3, 1, 1))
    result, evidence = aggregate_up(up, rotation)
    assert evidence["small_sample_median"] and evidence["inlier_count"] == 3
    assert not evidence["mad_applied"]
    np.testing.assert_array_equal(result, [0, 0, 1])
    with pytest.raises(ValueError, match="Insufficient"):
        aggregate_up(up[:2], rotation[:2])
    with pytest.raises(ValueError, match="Degenerate"):
        gravity_basis([0, 0, 0])
    with pytest.raises(ValueError, match="finite"):
        aggregate_up([[0, 0, np.nan]] * 3, rotation)
    with pytest.raises(ValueError, match="after MAD"):
        aggregate_up(np.tile(np.eye(3), (4, 1)), np.tile(np.eye(3), (12, 1, 1)))
    rotation[0, 0, 0] = -1
    with pytest.raises(ValueError, match="proper rotations"):
        aggregate_up(up, rotation)


def test_mano_root_offset_preserves_full_geometry_not_just_translation():
    matrix, _ = gravity_basis([.4, -.8, .2])
    translation = np.array([[.4, -.1, .8], [-.3, .2, .4]], np.float32)
    orientation = np.array([[.1, -.2, .7], [-.8, .3, .2]], np.float32)
    offsets = np.array([[.04, -.02, .03], [-.01, .05, .02]], np.float32)
    local = np.array([[0, 0, 0], [.02, .05, .01], [-.03, .01, .07]])
    p, r = rotate_mano_parameters(translation, orientation, offsets, matrix)
    original = np.einsum("nij,kj->nki", Rotation.from_rotvec(orientation).as_matrix(), local) + (translation + offsets)[:, None]
    transformed = np.einsum("nij,kj->nki", Rotation.from_rotvec(r).as_matrix(), local) + (p + offsets)[:, None]
    np.testing.assert_allclose(transformed, original @ matrix.T, atol=2e-7)
    assert np.max(np.abs(p - translation @ matrix.T)) > .01
    restored_p, restored_r = rotate_mano_parameters(p, r, offsets, matrix.T)
    np.testing.assert_allclose(restored_p, translation, atol=2e-7)
    np.testing.assert_allclose(Rotation.from_rotvec(restored_r).as_matrix(), Rotation.from_rotvec(orientation).as_matrix(), atol=2e-7)


def test_camera_dense_pose_convention_scale_and_intrinsics(tmp_path):
    path = tmp_path / "camera.npz"
    rotations = Rotation.from_euler("z", [0, .2, .4, .6])
    translations = np.arange(12).reshape(4, 3)
    trajectory = np.column_stack((translations, rotations.as_quat()))
    np.savez(path, traj=trajectory, scale=2., img_focal=100., img_center=[50, 30], tstamp=[0, 3])
    clip = {"prepared": {"frame_count": 4, "width": 100, "height": 60}, "hawor_camera": {"focal_length_px": 100.}}
    r, t = load_camera_trajectory(path, clip)
    np.testing.assert_allclose(r, rotations.as_matrix())
    np.testing.assert_array_equal(t, translations * 2)
    clip["prepared"]["frame_count"] = 2
    with pytest.raises(ValueError, match="per prepared frame"):
        load_camera_trajectory(path, clip)
    clip["prepared"]["frame_count"] = 4
    clip["hawor_camera"]["focal_length_px"] = 99
    with pytest.raises(ValueError, match="intrinsics"):
        load_camera_trajectory(path, clip)


def test_sharp_frame_count_ties_and_video_alignment(tmp_path):
    from test_clip_preparation import make_video
    np.testing.assert_array_equal(select_sharp_frames(np.ones(10), .3, 4), [0, 1, 2, 3])
    np.testing.assert_array_equal(select_sharp_frames([1, 2, 3], .3, 50), [0, 1, 2])
    video = make_video(tmp_path / 'rgb.mp4', count=6, rate=30)
    frames = list(read_video_frames(video, 6, [0, 3, 5]))
    assert [i for i, _ in frames] == [0, 3, 5]
    assert abs(frames[1][1].mean() - 50) < 3
    with pytest.raises(ValueError, match="truncated"):
        list(read_video_frames(video, 7))
    with pytest.raises(ValueError, match="extra"):
        list(read_video_frames(video, 5))


def test_failed_estimator_keeps_diagnostics_and_never_accepts_export(tmp_path, monkeypatch):
    pytest.importorskip("geocalib")
    pytest.importorskip("smplx")
    import egocentric_pipeline.gravity_pipeline as pipeline
    source = tmp_path / "input"; source.mkdir()
    model_root = source / "hawor"
    for p in [model_root / "_DATA/data_left/mano_left/MANO_LEFT.pkl", model_root / "_DATA/data/mano/MANO_RIGHT.pkl"]:
        p.parent.mkdir(parents=True); p.write_bytes(b"not used by failed estimator")
    manifest_path = source / "manifest.json"; manifest_path.write_text('{}')
    native = source / "native"; (native / "SLAM").mkdir(parents=True)
    np.savez(native / "SLAM/hawor_slam_w_scale_0_3.npz", traj=np.tile([0, 0, 0, 0, 0, 0, 1], (3, 1)), scale=1., img_focal=100., img_center=[50, 30])
    clip = {"prepared": {"frame_count": 3, "width": 100, "height": 60}, "hawor_camera": {"focal_length_px": 100.}}
    manifest = {"run_id": "test", "run_directory": str(source), "inference": {"native_directory": str(native)}}
    # Provide the video artifact but stop before model, geometry or publication.
    monkeypatch.setattr(pipeline, "load_run", lambda _: (manifest, {"prepared_video": manifest_path}, clip,
                                                        {"schema_version": "1.0"}, {"frame_index": np.arange(3)}))
    def fail(video, clip, checkpoint, settings, diagnostics, **kwargs):
        diagnostics["frames"] = [{"frame_index": 0, "accepted": False, "reason": "pitch_or_roll_filter"}]
        return []
    monkeypatch.setattr(pipeline, "predict_up", fail)
    settings = json.loads(Path('configs/gravity_alignment.json').read_text())
    output = tmp_path / "failed"
    with pytest.raises(ValueError, match="Insufficient"):
        align_run(manifest_path, output, tmp_path / "weights", model_root, settings)
    assert json.loads((output / 'alignment_report.json').read_text())["status"] == "failed"
    assert json.loads((output / 'gravity_diagnostics.json').read_text())["frames"][0]["reason"] == "pitch_or_roll_filter"
    assert not (output / 'trajectory_aligned.npz').exists()
    with pytest.raises(FileExistsError):
        align_run(manifest_path, output, tmp_path / "weights", model_root, settings)
    settings["min_inliers"] = 2
    with pytest.raises(ValueError, match="min_inliers"):
        validate_settings(settings)
