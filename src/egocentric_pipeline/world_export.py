"""Copy the pinned HaWoR world result into the frame-major pipeline contract.

Native files are trusted, locally generated joblib/NumPy pickle artifacts. This
module never loads artifacts downloaded from an untrusted source. Importing it
does not import Torch; joblib needs Torch only when loading real native tensors.
"""

from pathlib import Path
from typing import TYPE_CHECKING

import joblib
import numpy as np

from .run_metadata import read_json, sha256_file, utc_now, write_json

if TYPE_CHECKING:
    from .video_preparation import PreparedClip


WORLD_FIELDS = (
    ("root_translation_world_m", "pred_trans", 3),
    ("root_orientation_world_axis_angle", "pred_rot", 3),
    ("hand_pose_axis_angle", "pred_hand_pose", 45),
    ("mano_betas", "pred_betas", 10),
)
HAND_ORDER = ["left", "right"]


def _frame_index(value, frame_count):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"Native frame index must be an integer, got {value!r}")
    if not 0 <= value < frame_count:
        raise ValueError(f"Native frame index {value} is outside [0, {frame_count})")
    return int(value)


def _provenance(native_directory, frame_count):
    """Follow native majority assignment; establish estimation from saved chunks."""
    track_directory = native_directory / f"tracks_0_{frame_count}"
    tracks_path = track_directory / "model_tracks.npy"
    chunks_path = track_directory / "frame_chunks_all.npy"
    tracks = np.load(tracks_path, allow_pickle=True).item()
    chunks = joblib.load(chunks_path)
    if not isinstance(tracks, dict) or not isinstance(chunks, dict):
        raise ValueError("Native tracks and frame chunks must be dictionaries")
    direct = np.zeros((frame_count, 2), dtype=bool)
    confidence = np.full((frame_count, 2), np.nan, dtype=np.float32)
    disagreements = []
    for track_id, track in tracks.items():
        if not track:
            raise ValueError(f"Native track {track_id} is empty")
        rows = []
        for record in track:
            if not isinstance(record.get("det"), (bool, np.bool_)) or not record["det"]:
                raise ValueError("Pinned demo tracks must contain direct detections only")
            frame = _frame_index(record["frame"], frame_count)
            box = np.asarray(record["det_box"])
            handedness = np.asarray(record["det_handedness"])
            if box.shape != (1, 5) or not np.isfinite(box).all():
                raise ValueError("Native det_box must be finite [1,5] coordinates plus confidence")
            if not 0 < box[0, 4] <= 1:
                raise ValueError("Native direct detector confidence must be in (0,1]")
            if handedness.shape != (1,) or handedness[0] not in (0, 1):
                raise ValueError("Native detector handedness must be [0] or [1]")
            rows.append((frame, int(handedness[0]), np.float32(box[0, 4])))
        # This is the exact track-to-hand rule in pinned hawor_video.py.
        native_hand = int(sum(row[1] for row in rows) / len(rows) >= 0.5)
        for frame, raw_hand, score in rows:
            if direct[frame, native_hand]:
                raise ValueError(
                    f"Multiple detections map to native {HAND_ORDER[native_hand]} at frame {frame}; "
                    "inspect the saved tracks before assigning confidence"
                )
            direct[frame, native_hand] = True
            confidence[frame, native_hand] = score
            if raw_hand != native_hand:
                disagreements.append({"track_id": str(track_id), "frame_index": frame,
                                      "raw_hand": HAND_ORDER[raw_hand],
                                      "native_hand": HAND_ORDER[native_hand]})

    estimated = np.zeros_like(direct)
    artifacts = [tracks_path, chunks_path]
    if any(hand not in (0, 1) for hand in chunks):
        raise ValueError("Native frame chunks contain an unknown hand index")
    for hand in range(2):
        for chunk in chunks.get(hand, []):
            frames = np.asarray([_frame_index(frame, frame_count) for frame in chunk], dtype=np.int64)
            if not len(frames) or (np.diff(frames) != 1).any():
                raise ValueError("Native estimation chunks must be nonempty contiguous frame sequences")
            if estimated[frames, hand].any():
                raise ValueError("Native estimation chunks overlap")
            camera_path = native_directory / "cam_space" / str(hand) / f"{frames[0]}_{frames[-1]}.json"
            camera = read_json(camera_path)
            expected = {"init_root_orient": (1, len(frames), 3, 3),
                        "init_hand_pose": (1, len(frames), 15, 3, 3),
                        "init_trans": (1, len(frames), 3), "init_betas": (1, len(frames), 10)}
            for field, shape in expected.items():
                if field not in camera or np.shape(camera[field]) != shape:
                    raise ValueError(f"{camera_path}: {field} must have shape {shape}")
            estimated[frames, hand] = True
            artifacts.append(camera_path)
        expected_estimation = direct[:, hand] if direct[:, hand].sum() >= 2 else np.zeros(frame_count, dtype=bool)
        if not np.array_equal(estimated[:, hand], expected_estimation):
            raise ValueError("Saved chunks disagree with the pinned demo's direct-estimation coverage")
    return direct, confidence, estimated, disagreements, artifacts


def export_world(native_directory: Path, prepared: "PreparedClip", output_directory: Path,
                 *, upstream_stages_completed: bool) -> dict:
    """Export unchanged float32 values, with explicit upstream completion evidence.

    ``upstream_stages_completed`` must come from the runner's successful detector,
    hand estimation, scaled SLAM, and infiller execution. Artifact presence alone
    is insufficient. False evidence preserves native output but makes every
    ``export_valid`` entry false. Hands remain [left, right]; time is seconds and
    world translations retain HaWoR's claimed metres and clip-local SLAM gauge.
    """
    if not isinstance(upstream_stages_completed, bool):
        raise TypeError("upstream_stages_completed must be an explicit boolean")
    native_directory = Path(native_directory).resolve()
    output_directory = Path(output_directory).resolve()
    trajectory_path = output_directory / "trajectory_world.npz"
    metadata_path = output_directory / "trajectory_metadata.json"
    if trajectory_path.exists() or metadata_path.exists():
        raise FileExistsError("World export already exists; allocate a new run directory")
    frame_count = prepared.metadata.prepared["frame_count"]
    if isinstance(frame_count, bool) or not isinstance(frame_count, int) or frame_count <= 0:
        raise ValueError("Prepared frame_count must be a positive integer")
    mapping = prepared.metadata.frames["mapping"]
    if len(mapping) != frame_count:
        raise ValueError("Prepared frame mapping length differs from frame_count")
    indices = np.asarray([_frame_index(row["frame_index"], frame_count) for row in mapping], dtype=np.int64)
    timestamps = np.asarray([row["timestamp_s"] for row in mapping], dtype=np.float64)
    source_timestamps = np.asarray([row["source_timestamp_s"] for row in mapping], dtype=np.float64)
    if not np.array_equal(indices, np.arange(frame_count)):
        raise ValueError("Prepared frame indices must be contiguous from zero")
    if not np.isfinite(timestamps).all() or not np.allclose(timestamps, indices / 30, rtol=0, atol=1e-9):
        raise ValueError("Prepared timestamps must match the 30 FPS grid")
    if not np.isfinite(source_timestamps).all() or (source_timestamps < 0).any() or (np.diff(source_timestamps) < 0).any():
        raise ValueError("Source timestamps must be finite, nonnegative, and nondecreasing")

    world_path = native_directory / "world_space_res.pth"
    native = joblib.load(world_path)
    if not isinstance(native, (list, tuple)) or len(native) != 5:
        raise ValueError("Pinned world_space_res.pth must contain its five positional arrays")
    arrays = {"frame_index": indices, "timestamp_s": timestamps, "source_timestamp_s": source_timestamps}
    native_arrays = []
    finite = np.ones((frame_count, 2), dtype=bool)
    field_mapping = {}
    for position, (export_name, native_name, size) in enumerate(WORLD_FIELDS):
        values = np.asarray(native[position])
        if values.shape != (2, frame_count, size) or values.dtype != np.float32:
            raise ValueError(f"{native_name} must be float32 [2,{frame_count},{size}], got {values.dtype} {values.shape}")
        copied = values.transpose(1, 0, 2).copy()
        # The only numeric operation is axis reordering: no transform, scale,
        # offset, smoothing, alignment, or dtype conversion is allowed here.
        assert copied.transpose(1, 0, 2).tobytes() == values.tobytes(), "World coordinates changed"
        arrays[export_name] = copied
        native_arrays.append(values)
        finite &= np.isfinite(copied).all(axis=2)
        field_mapping[export_name] = {"native_field": native_name, "native_list_index": position,
                                      "operation": "transpose(1,0,2); copy; no dtype conversion"}
    native_valid = np.asarray(native[4])
    if native_valid.shape != (2, frame_count) or native_valid.dtype != np.bool_:
        raise ValueError(f"pred_valid must be bool [2,{frame_count}]")
    direct, confidence, estimated, disagreements, provenance_artifacts = _provenance(native_directory, frame_count)
    valid = native_valid.T.copy()
    arrays.update({"direct_detection": direct, "motion_infilled": valid & ~estimated,
                   "hawor_valid": valid, "export_valid": valid & finite & upstream_stages_completed,
                   "detector_confidence": confidence})
    field_mapping.update({
        "frame_index": {"source": "prepared metadata frames.mapping[].frame_index", "operation": "int64 copy"},
        "timestamp_s": {"source": "prepared metadata frames.mapping[].timestamp_s", "operation": "float64 copy"},
        "source_timestamp_s": {"source": "prepared metadata frames.mapping[].source_timestamp_s", "operation": "float64 copy"},
        "direct_detection": {"source": "model_tracks.npy frame/det/det_handedness", "operation": "native track majority assignment"},
        "detector_confidence": {"source": "model_tracks.npy det_box[0,4]", "operation": "native track assignment; NaN without detection"},
        "hawor_valid": {"native_field": "pred_valid", "native_list_index": 4, "operation": "transpose(1,0); bool copy"},
        "motion_infilled": {"source": "pred_valid, frame_chunks_all.npy, camera chunk JSON", "operation": "hawor_valid AND NOT direct_estimation"},
        "export_valid": {"source": "pred_valid, exported numeric fields, runner completion evidence", "operation": "hawor_valid AND finite AND stages_completed"},
    })

    native_artifacts = [world_path, *provenance_artifacts,
                        native_directory / "SLAM" / f"hawor_slam_w_scale_0_{frame_count}.npz"]
    artifact_evidence = [{"path": str(path), "sha256": sha256_file(path)} for path in native_artifacts]
    validation = {"frame_count": frame_count, "hand_order": HAND_ORDER,
                  "native_float32_values_bitwise_preserved": True, "dtype_conversion_applied": False,
                  "coordinate_transform_applied": False, "upstream_stages_completed": upstream_stages_completed,
                  "nonfinite_frame_hand_count": int((~finite).sum()),
                  "raw_handedness_disagreements": disagreements,
                  "raw_handedness_disagreement_count": len(disagreements),
                  "bbox_interpolation_is_noop": True,
                  "direct_estimation_count_by_hand": estimated.sum(axis=0).tolist(),
                  "direct_detection_count_by_hand": direct.sum(axis=0).tolist(),
                  "motion_infilled_count_by_hand": arrays["motion_infilled"].sum(axis=0).tolist(),
                  "hawor_valid_count_by_hand": valid.sum(axis=0).tolist(),
                  "export_valid_count_by_hand": arrays["export_valid"].sum(axis=0).tolist()}
    metadata = {"schema_version": "1.0", "created_at": utc_now(),
                "coordinate_frame": "unchanged HaWoR metric world frame",
                "world_frame_limitation": "Origin and orientation are clip-local SLAM gauge choices; not comparable across clips.",
                "units": {"translation": "metres claimed by HaWoR; no metric accuracy claim",
                          "rotation": "axis-angle radians", "mano_betas": "dimensionless MANO shape coefficients"},
                "translation_definition": "Native pred_trans MANO root translation parameter, not an independently derived wrist joint.",
                "hand_order": HAND_ORDER, "native_field_mapping": field_mapping,
                "arrays": {key: {"shape": list(value.shape), "dtype": str(value.dtype)} for key, value in arrays.items()},
                "provenance": {
                    "direct_detection": "Saved detector output assigned by native track majority handedness, ties right.",
                    "detector_confidence": "Saved det_box[0,4] after native hand assignment; NaN without a direct detection.",
                    "direct_estimation": "Saved frame chunks cross-checked against camera JSON shapes and grouped detections; entire singleton hands are skipped.",
                    "motion_infilled": "hawor_valid AND NOT direct_estimation; may coexist with an unused direct detection.",
                    "hawor_valid": "Unmodified final native pred_valid, including validity set by infilling.",
                    "export_valid": "hawor_valid AND all exported geometry finite AND required upstream stages completed.",
                    "missing_values": "Invalid native values are preserved, never interpolated or silently replaced by the exporter."},
                "native_artifacts": artifact_evidence,
                "prepared_metadata": {"path": str(prepared.metadata_path), "sha256": sha256_file(prepared.metadata_path)},
                "validation": validation}
    output_directory.mkdir(parents=True, exist_ok=True)
    with trajectory_path.open("xb") as stream:
        np.savez_compressed(stream, **arrays)
    with np.load(trajectory_path, allow_pickle=False) as stored:
        for (export_name, _, _), original in zip(WORLD_FIELDS, native_arrays):
            assert stored[export_name].transpose(1, 0, 2).tobytes() == original.tobytes(), "Serialized world coordinates changed"
    metadata["trajectory"] = {"path": str(trajectory_path), "sha256": sha256_file(trajectory_path)}
    write_json(metadata_path, metadata)
    return {"trajectory_world": str(trajectory_path), "trajectory_metadata": str(metadata_path), "validation": validation}
