"""Exercise the production exporter with tiny, CPU-only native artifact files."""

from pathlib import Path
from types import SimpleNamespace

import joblib
import numpy as np
import pytest

from egocentric_pipeline.run_metadata import read_json, sha256_file, write_json
from egocentric_pipeline.world_export import WORLD_FIELDS, export_world


def detection(frame, hand, confidence=0.75):
    return {"frame": frame, "det": True,
            "det_box": np.array([[10, 20, 30, 40, confidence]], dtype=np.float32),
            "det_handedness": np.array([hand], dtype=np.float32)}


@pytest.fixture
def native_fixture(tmp_path):
    frame_count = 6
    native = tmp_path / "native"
    native.mkdir()
    tracks_directory = native / "tracks_0_6"
    tracks_directory.mkdir()
    arrays = [(np.arange(2 * frame_count * size, dtype=np.float32).reshape(2, frame_count, size) / 7)
              for _, _, size in WORLD_FIELDS]
    arrays[0][0, 0, 0] = np.float32(-0.0)
    for values in arrays:
        values[1, -1] = 0
    valid = np.ones((2, frame_count), dtype=bool)
    valid[1, -1] = False
    arrays.append(valid)
    joblib.dump(arrays, native / "world_space_res.pth")
    tracks = {2.0: [detection(0, 0, 0.5), detection(1, 0, 0.6), detection(2, 1, 0.7)],
              7.0: [detection(0, 1, 0.8), detection(2, 1, 0.9), detection(4, 1, 0.95)]}
    np.save(tracks_directory / "model_tracks.npy", np.array(tracks, dtype=object))
    chunks = {0: [np.arange(3)], 1: [np.array([0]), np.array([2]), np.array([4])]}
    joblib.dump(chunks, tracks_directory / "frame_chunks_all.npy")
    for hand, hand_chunks in chunks.items():
        for frames in hand_chunks:
            count = len(frames)
            camera = {"init_root_orient": np.tile(np.eye(3), (1, count, 1, 1)).tolist(),
                      "init_hand_pose": np.tile(np.eye(3), (1, count, 15, 1, 1)).tolist(),
                      "init_trans": np.zeros((1, count, 3)).tolist(),
                      "init_betas": np.zeros((1, count, 10)).tolist()}
            write_json(native / "cam_space" / str(hand) / f"{frames[0]}_{frames[-1]}.json", camera)
    (native / "SLAM").mkdir()
    np.savez(native / "SLAM/hawor_slam_w_scale_0_6.npz", traj=np.zeros((frame_count, 7)), scale=1)
    metadata_path = tmp_path / "clip_metadata.json"
    mapping = [{"frame_index": index, "timestamp_s": index / 30,
                "source_timestamp_s": 2 + index / 30} for index in range(frame_count)]
    write_json(metadata_path, {"prepared": {"frame_count": frame_count}, "frames": {"mapping": mapping}})
    prepared = SimpleNamespace(video_path=tmp_path / "rgb.mp4", metadata_path=metadata_path,
                               metadata=SimpleNamespace(prepared={"frame_count": frame_count}, frames={"mapping": mapping}))
    return native, prepared, tmp_path / "export", arrays


def test_values_axes_dtypes_and_provenance(native_fixture):
    native, prepared, output, original = native_fixture
    native_hash = sha256_file(native / "world_space_res.pth")
    result = export_world(native, prepared, output, upstream_stages_completed=True)
    with np.load(result["trajectory_world"], allow_pickle=False) as exported:
        for index, (field, _, size) in enumerate(WORLD_FIELDS):
            assert exported[field].shape == (6, 2, size)
            assert exported[field].dtype == np.float32
            assert exported[field].transpose(1, 0, 2).tobytes() == original[index].tobytes()
        assert exported["frame_index"].dtype == np.int64
        assert exported["timestamp_s"].dtype == np.float64
        np.testing.assert_array_equal(exported["timestamp_s"], np.arange(6) / 30)
        np.testing.assert_array_equal(exported["source_timestamp_s"], 2 + np.arange(6) / 30)
        np.testing.assert_array_equal(exported["hawor_valid"], original[-1].T)
        np.testing.assert_array_equal(exported["export_valid"], original[-1].T)
        np.testing.assert_array_equal(exported["direct_detection"][:, 0], [1, 1, 1, 0, 0, 0])
        np.testing.assert_array_equal(exported["direct_detection"][:, 1], [1, 0, 1, 0, 1, 0])
        np.testing.assert_array_equal(exported["motion_infilled"][:, 0], [0, 0, 0, 1, 1, 1])
        np.testing.assert_array_equal(exported["motion_infilled"][:, 1], [0, 1, 0, 1, 0, 0])
        assert exported["detector_confidence"][2, 0] == np.float32(0.7)
        assert exported["detector_confidence"][2, 1] == np.float32(0.9)
        assert np.isnan(exported["detector_confidence"][~exported["direct_detection"]]).all()
    assert sha256_file(native / "world_space_res.pth") == native_hash
    metadata = read_json(Path(result["trajectory_metadata"]))
    assert metadata["validation"]["raw_handedness_disagreements"] == [
        {"track_id": "2.0", "frame_index": 2, "raw_hand": "right", "native_hand": "left"}]
    assert metadata["validation"]["native_float32_values_bitwise_preserved"] is True
    assert metadata["validation"]["coordinate_transform_applied"] is False
    assert metadata["validation"]["bbox_interpolation_is_noop"] is True
    assert metadata["trajectory"]["sha256"] == sha256_file(Path(result["trajectory_world"]))


def test_nonfinite_native_values_are_preserved_but_invalid(native_fixture):
    native, prepared, output, arrays = native_fixture
    arrays[0][0, 4, 2] = np.nan
    joblib.dump(arrays, native / "world_space_res.pth")
    result = export_world(native, prepared, output, upstream_stages_completed=True)
    with np.load(result["trajectory_world"]) as exported:
        assert np.isnan(exported["root_translation_world_m"][4, 0, 2])
        assert exported["hawor_valid"][4, 0]
        assert exported["motion_infilled"][4, 0]
        assert not exported["export_valid"][4, 0]
    assert result["validation"]["nonfinite_frame_hand_count"] == 1


def test_completion_evidence_is_required_and_controls_export_valid(native_fixture):
    native, prepared, output, _ = native_fixture
    with pytest.raises(TypeError, match="upstream_stages_completed"):
        export_world(native, prepared, output)
    result = export_world(native, prepared, output, upstream_stages_completed=False)
    with np.load(result["trajectory_world"]) as exported:
        assert not exported["export_valid"].any()
        assert exported["hawor_valid"].sum() == 11


@pytest.mark.parametrize("change,match", [("count", "pred_trans"), ("dtype", "float32"), ("time", "30 FPS"),
                                          ("source_time", "Source timestamps")])
def test_invalid_array_or_timestamp_contract_is_rejected(native_fixture, change, match):
    native, prepared, output, arrays = native_fixture
    if change == "count":
        arrays[0] = arrays[0][:, :-1]
    elif change == "dtype":
        arrays[1] = arrays[1].astype(np.float64)
    elif change == "time":
        prepared.metadata.frames["mapping"][2]["timestamp_s"] += 0.005
    else:
        prepared.metadata.frames["mapping"][2]["source_timestamp_s"] = 0
    joblib.dump(arrays, native / "world_space_res.pth")
    with pytest.raises(ValueError, match=match):
        export_world(native, prepared, output, upstream_stages_completed=True)
    assert not (output / "trajectory_world.npz").exists()


def test_singleton_hand_detection_is_not_direct_estimation(native_fixture):
    native, prepared, output, _ = native_fixture
    track_path = native / "tracks_0_6/model_tracks.npy"
    tracks = np.load(track_path, allow_pickle=True).item()
    tracks[2.0] = [detection(0, 0)]
    np.save(track_path, np.array(tracks, dtype=object))
    chunks_path = native / "tracks_0_6/frame_chunks_all.npy"
    chunks = joblib.load(chunks_path)
    chunks[0] = []
    joblib.dump(chunks, chunks_path)
    result = export_world(native, prepared, output, upstream_stages_completed=True)
    with np.load(result["trajectory_world"]) as exported:
        assert exported["direct_detection"][0, 0]
        assert exported["motion_infilled"][0, 0]
        assert exported["detector_confidence"][0, 0] == 0.75
    assert result["validation"]["direct_estimation_count_by_hand"][0] == 0


def test_tied_track_handedness_is_assigned_right(native_fixture):
    native, prepared, output, _ = native_fixture
    track_path = native / "tracks_0_6/model_tracks.npy"
    tracks = np.load(track_path, allow_pickle=True).item()
    tracks[7.0] = [detection(0, 0, 0.8), detection(2, 1, 0.9)]
    np.save(track_path, np.array(tracks, dtype=object))
    chunks_path = native / "tracks_0_6/frame_chunks_all.npy"
    chunks = joblib.load(chunks_path)
    chunks[1] = [np.array([0]), np.array([2])]
    joblib.dump(chunks, chunks_path)
    result = export_world(native, prepared, output, upstream_stages_completed=True)
    with np.load(result["trajectory_world"]) as exported:
        assert exported["direct_detection"][0, 1]
        assert exported["detector_confidence"][0, 1] == np.float32(0.8)
        assert exported["motion_infilled"][4, 1]
    assert {"track_id": "7.0", "frame_index": 0, "raw_hand": "left", "native_hand": "right"} in result["validation"]["raw_handedness_disagreements"]


@pytest.mark.parametrize("change,match", [("duplicate", "Multiple detections"), ("non_direct", "direct detections"),
                                          ("chunks", "coverage"), ("camera_shape", "init_trans")])
def test_unverifiable_provenance_is_rejected(native_fixture, change, match):
    native, prepared, output, _ = native_fixture
    track_path = native / "tracks_0_6/model_tracks.npy"
    tracks = np.load(track_path, allow_pickle=True).item()
    if change == "duplicate":
        tracks[8] = [detection(0, 0)]
    elif change == "non_direct":
        tracks[2.0][0]["det"] = False
    elif change == "chunks":
        joblib.dump({0: [], 1: [np.array([0]), np.array([2]), np.array([4])]}, native / "tracks_0_6/frame_chunks_all.npy")
    else:
        path = native / "cam_space/0/0_2.json"
        camera = read_json(path)
        camera["init_trans"] = [[[0, 0, 0]]]
        write_json(path, camera, overwrite=True)
    np.save(track_path, np.array(tracks, dtype=object))
    with pytest.raises(ValueError, match=match):
        export_world(native, prepared, output, upstream_stages_completed=True)


def test_existing_export_is_not_overwritten(native_fixture):
    native, prepared, output, _ = native_fixture
    result = export_world(native, prepared, output, upstream_stages_completed=True)
    original_hash = sha256_file(Path(result["trajectory_world"]))
    with pytest.raises(FileExistsError):
        export_world(native, prepared, output, upstream_stages_completed=True)
    assert sha256_file(Path(result["trajectory_world"])) == original_hash
