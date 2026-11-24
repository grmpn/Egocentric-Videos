"""Complete native inference → common benchmark artifact, with no GT pose inputs."""

from contextlib import contextmanager
from pathlib import Path
import time

import numpy as np

from egocentric_pipeline.run_metadata import ResourceMonitor, read_json, utc_now, write_json


@contextmanager
def component(report, name, frames, *, processed_frames=None, frame_unit="RGB frames", timing_note="wall clock including stage loading"):
    row = {"name": name, "status": "running", "processed_frames": processed_frames,
           "frame_unit": frame_unit, "timing_note": timing_note}
    report["components"].append(row)
    started = time.monotonic()
    try:
        yield row
        row["status"] = "completed"
    except BaseException:
        row["status"] = "failed"
        raise
    finally:
        row["wall_time_s"] = time.monotonic() - started
        row["effective_fps"] = frames / row["wall_time_s"] if row["status"] == "completed" else None


def hawor_prediction(prepared, output, root, report, monitor):
    """Run unchanged HaWoR, preserving its final native infilling and both hands."""
    from scipy.spatial.transform import Rotation

    from egocentric_pipeline.geometry.gravity_alignment import load_camera_trajectory
    from egocentric_pipeline.geometry.hand_geometry import load_mano_model, reconstruct_mano
    from egocentric_pipeline.tracking.hawor_runner import run_hawor
    from egocentric_pipeline.tracking.world_export import export_world

    count = prepared.metadata.prepared["frame_count"]
    inference = run_hawor(prepared, output / "native", root / "external/HaWoR",
                         resource_monitor=monitor, python_executable=root / ".conda/envs/hawor/bin/python")
    report["native_inference"] = inference
    for stage in inference["stages"]:
        seconds = stage["wall_time_s"]
        report["components"].append({**stage, "processed_frames": count if stage["name"] in
            ("detection_tracking", "slam_metric_scale") else None, "frame_unit": "RGB frames",
            "effective_fps": count / seconds if seconds and stage["status"] == "completed" else None,
            "timing_note": inference["timing_method"]})
    if inference["status"] != "completed":
        raise RuntimeError(f"Native HaWoR failed; inspect {inference['log']}")
    with component(report, "native_export_and_geometry", count, processed_frames=2 * count, frame_unit="hand frames") as stage:
        native = Path(inference["native_directory"])
        export_world(native, prepared, output, upstream_stages_completed=True)
        with np.load(output / "trajectory_world.npz", allow_pickle=False) as archive:
            world = dict(archive)
        valid = world["export_valid"]
        joints = np.full((count, 2, 21, 3), np.nan)
        rotations = np.full((count, 2, 3, 3), np.nan)
        for hand, path in enumerate(("_DATA/data_left/mano_left/MANO_LEFT.pkl", "_DATA/data/mano/MANO_RIGHT.pkl")):
            indices = np.flatnonzero(valid[:, hand])
            if not len(indices):
                continue
            model = load_mano_model(root / "external/HaWoR" / path, hand)
            j, v = reconstruct_mano(model, world["root_translation_world_m"][indices, hand],
                world["root_orientation_world_axis_angle"][indices, hand],
                world["hand_pose_axis_angle"][indices, hand], world["mano_betas"][indices, hand])
            tips = [745, 317, 445 if hand == 0 else 444, 556, 673]
            mano21 = np.concatenate((j[:, :16], v[:, tips]), axis=1)
            order = [0, 13, 14, 15, 16, 1, 2, 3, 17, 4, 5, 6, 18, 10, 11, 12, 19, 7, 8, 9, 20]
            joints[indices, hand] = mano21[:, order]
            rotations[indices, hand] = Rotation.from_rotvec(world["root_orientation_world_axis_angle"][indices, hand]).as_matrix()
        camera_rotation, camera_position = load_camera_trajectory(
            native / "SLAM" / f"hawor_slam_w_scale_0_{count}.npz", prepared.metadata.to_dict())
        camera = np.tile(np.eye(4), (count, 1, 1))
        camera[:, :3, :3], camera[:, :3, 3] = camera_rotation, camera_position
        local = np.einsum("tji,thkj->thki", camera_rotation, joints - camera_position[:, None, None])
        stage["processed_frames"] = int(valid.sum())
        for row in report["components"]:
            if row["name"] == "hand_estimation":
                row.update(processed_frames=int((valid & ~world["motion_infilled"]).sum()), frame_unit="hand frames")
            elif row["name"] == "infilling":
                row.update(processed_frames=int(world["motion_infilled"].sum()), frame_unit="infilled hand frames")
        return {"joints_world_m": joints, "joints_camera_m": local, "camera_to_world": camera,
                "wrist_rotation_world": rotations, "camera_valid": np.ones(count, bool),
                "hand_valid": valid, "direct_valid": valid & ~world["motion_infilled"],
                "infilled": valid & world["motion_infilled"]}


def run_method(method, sequence_id, output_root, settings, root, *, started=None):
    """One fresh process per trial; include native, gravity and export in elapsed time.

    The only dataset information consumed is the prepared RGB/frame mapping and
    supplied camera intrinsics. Reference hand/camera poses are never loaded.
    """
    from egocentric_pipeline.evaluation.hand_trajectory import JOINT_ORDER, validate_trajectory
    from egocentric_pipeline.geometry.gravity_alignment import aggregate_up
    from egocentric_pipeline.geometry.gravity_estimation import predict_up
    from egocentric_pipeline.video.video_preparation import load_prepared_clip

    if method != "hawor":
        raise ValueError(f"Native runner is not implemented yet: {method}")
    if sequence_id not in {clip["sequence_id"] for clip in settings["clips"]}:
        raise ValueError("Sequence is not part of the frozen benchmark")
    output_root, root = Path(output_root).resolve(), Path(root).resolve()
    output = output_root / method / sequence_id
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic() if started is None else started
    report = {"method": method, "sequence_id": sequence_id, "status": "running", "started_at": utc_now(),
              "components": [], "frame_count": settings["frame_count"],
              "randomness": "Unchanged HaWoR demo does not expose or set an inference seed; config seed is used for dataset selection.",
              "timing_scope": "Fresh CLI process through exported prediction, including RGB decoding, model loading, native subprocess, RGB gravity, geometry conversion and monitoring. Downloads, reference preparation, scoring and rendering excluded."}
    write_json(output / "run.json", report)
    monitor = ResourceMonitor(settings["resource_sample_interval_s"])
    monitor.start()
    try:
        with component(report, "input_validation", settings["frame_count"], processed_frames=settings["frame_count"]):
            prepared = load_prepared_clip(output_root / "prepared" / sequence_id / "clip_metadata.json")
            if prepared.metadata.prepared["frame_count"] != settings["frame_count"]:
                raise ValueError("Prepared clip has an unexpected frame count")
        data = hawor_prediction(prepared, output, root, report, monitor)
        gravity_settings = read_json(root / "configs/defaults/gravity_alignment.json")
        diagnostics = {}
        with component(report, "rgb_gravity", settings["frame_count"], frame_unit="GeoCalib frames") as stage:
            try:
                candidates = predict_up(prepared.video_path, prepared.metadata.to_dict(),
                    root / "data/models/geocalib/geocalib-pinhole-v1.0.tar", gravity_settings, diagnostics)
                indices = [row["frame_index"] for row in candidates if data["camera_valid"][row["frame_index"]]]
                ups = [row["up_camera"] for row in candidates if data["camera_valid"][row["frame_index"]]]
                data["up_world"], aggregation = aggregate_up(np.asarray(ups).reshape(-1, 3),
                    data["camera_to_world"][indices, :3, :3], min_inliers=gravity_settings["min_inliers"],
                    mad_scale=gravity_settings["mad_scale"], mad_floor=gravity_settings["mad_floor"],
                    mad_thresholds=gravity_settings["mad_thresholds"])
                diagnostics["aggregation"] = aggregation
                stage["processed_frames"] = len(diagnostics["selected_frame_indices"])
            finally:
                write_json(output / "gravity.json", {"settings": gravity_settings, **diagnostics})
        with component(report, "prediction_export", settings["frame_count"], processed_frames=settings["frame_count"]):
            mapping = prepared.metadata.frames["mapping"]
            data.update(timestamp_s=np.array([row["timestamp_s"] for row in mapping]),
                        frame_index=np.array([row["source_frame_index"] for row in mapping]), joint_order=np.array(JOINT_ORDER))
            validate_trajectory(data)
            np.savez_compressed(output / "prediction.npz", **data)
        report["status"] = "completed"
    except BaseException as error:
        report.update(status="interrupted" if isinstance(error, KeyboardInterrupt) else "failed",
                      failure={"type": type(error).__name__, "message": str(error)})
        raise
    finally:
        resources = monitor.stop()
        elapsed = time.monotonic() - started
        peak = resources["peak_device_gpu_memory_bytes"]
        samples = resources["samples"]
        baseline = samples[0]["device_gpu_memory_used_bytes"] if samples else None
        report.update(finished_at=utc_now(), resources=resources, performance={
            "wall_time_s": elapsed, "end_to_end_fps": settings["frame_count"] / elapsed if report["status"] == "completed" else None,
            "peak_vram_gib": None if peak is None else peak / 1024**3, "idle_device_memory_bytes": baseline})
        write_json(output / "run.json", report, overwrite=True)
    return report
