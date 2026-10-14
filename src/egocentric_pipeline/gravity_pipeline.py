"""Completed HaWoR run → independent Z-up trajectory and review artifacts."""

import importlib.metadata
from pathlib import Path
import sys
import time

import numpy as np

from .gravity_alignment import aggregate_up, gravity_basis, load_camera_trajectory
from .gravity_estimation import predict_up
from .hand_geometry import align_hand_geometry
from .run_metadata import sha256_file, utc_now, write_json
from .world_export import HAND_ORDER, load_run


def validate_settings(settings):
    expected = {"sharp_fraction", "min_sharp_frames", "max_roll_degrees", "min_inliers",
                "mad_scale", "mad_floor", "mad_thresholds", "parallel_threshold", "torch_threads"}
    if set(settings) != expected:
        raise ValueError(f"Gravity settings must contain exactly {sorted(expected)}")
    for name in ("min_sharp_frames", "min_inliers", "torch_threads"):
        if type(settings[name]) is not int or settings[name] < (3 if name == "min_inliers" else 1):
            raise ValueError(f"Invalid gravity setting: {name}")
    thresholds = settings["mad_thresholds"]
    if len(thresholds) != 3 or not np.isfinite([*thresholds, settings["mad_scale"], settings["mad_floor"]]).all():
        raise ValueError("Expected three finite MAD thresholds and finite scale/floor")
    if min(*thresholds, settings["mad_scale"], settings["mad_floor"]) <= 0:
        raise ValueError("MAD thresholds/scale/floor must be positive")
    if not (0 < settings["sharp_fraction"] <= 1 and 0 < settings["max_roll_degrees"] < 90
            and 0 < settings["parallel_threshold"] < 1):
        raise ValueError("Invalid sharp fraction, roll limit, or axis fallback threshold")


def align_run(manifest_path, output_directory, checkpoint, hawor_root, settings, *, device="cuda"):
    """Write a new run directory. Failures retain diagnostics and no success claim.

    Output NPZ preserves every world field exactly and adds shared-frame derived
    poses. JSON owns units, frame conventions, settings, evidence and status.
    A completed report means numerical validation, with manual review still pending.
    """
    validate_settings(settings)
    manifest_path, output = Path(manifest_path).resolve(), Path(output_directory).resolve()
    manifest, artifacts, clip, world_meta, world = load_run(manifest_path)
    native = Path(manifest["inference"]["native_directory"])
    if native.is_relative_to(manifest["run_directory"]):
        native = manifest_path.parent / native.relative_to(manifest["run_directory"])
    camera_path = native / "SLAM" / f"hawor_slam_w_scale_0_{len(world['frame_index'])}.npz"
    camera_rotation, camera_position = load_camera_trajectory(camera_path, clip)
    hawor_root = Path(hawor_root).resolve()
    models = [hawor_root / "_DATA/data_left/mano_left/MANO_LEFT.pkl", hawor_root / "_DATA/data/mano/MANO_RIGHT.pkl"]
    inputs = {**artifacts, "native_camera": camera_path, "source_manifest": manifest_path,
              "mano_left": models[0], "mano_right": models[1]}
    hashes = {name: sha256_file(path) for name, path in inputs.items()}
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    report = {"schema_version": "1.0", "status": "running", "started_at": utc_now(),
              "source_run_id": manifest["run_id"], "command": [sys.executable, *sys.argv],
              "inputs": {name: {"path": str(path), "sha256": hashes[name]} for name, path in inputs.items()},
              "settings": settings, "hand_order": HAND_ORDER, "manual_review": "pending",
              "packages": {name: importlib.metadata.version(name) for name in
                           ("numpy", "scipy", "torch", "torchvision", "geocalib", "smplx", "chumpy", "kornia")},
              "units": {"position": "HaWoR claimed metres (scale unverified)", "axis_angle": "radians", "time": "seconds"},
              "frames": {"world": "native clip-local HaWoR world; unchanged",
                         "aligned": "shared Z-up frame; same origin/scale; arbitrary deterministic yaw",
                         "camera": "OpenCV: X right, Y down, Z forward; camera-to-world/aligned poses",
                         "mano_translation": "parameter; physical wrist = translation + mano_root_offset_m",
                         "rotation_convention": "column vectors; R_destination_from_source",
                         "invalid_geometry": "derived hand poses/wrists/offsets NaN where export_valid is false"},
              "limitations": ["No measured gravity reference, scale correction, heading or floor estimate",
                              "No robot feasibility or iPhone pilot acceptance"],
              "camera_assumptions": clip["hawor_camera"], "source_world_metadata": world_meta["schema_version"]}
    diagnostics = {"max_roll_degrees": settings["max_roll_degrees"]}
    report_path = output / "alignment_report.json"
    write_json(report_path, report)
    try:
        candidates = predict_up(artifacts["prepared_video"], clip, checkpoint, settings, diagnostics, device=device)
        indices = [row["frame_index"] for row in candidates]
        up, aggregation = aggregate_up(np.asarray([row["up_camera"] for row in candidates]).reshape(-1, 3),
                                       camera_rotation[indices], min_inliers=settings["min_inliers"],
                                       mad_scale=settings["mad_scale"], mad_floor=settings["mad_floor"],
                                       mad_thresholds=settings["mad_thresholds"])
        diagnostics["aggregation"] = aggregation
        for i, row in enumerate(candidates):
            row.update(mad_inlier=aggregation["mad_inlier"][i], hemisphere_flipped=aggregation["hemisphere_flipped"][i],
                       up_world=aggregation["up_world_per_frame"][i], angle_to_consensus_deg=aggregation["angle_to_consensus_deg"][i])
        rotation, reference = gravity_basis(up, settings["parallel_threshold"])
        np.testing.assert_allclose(rotation @ rotation.T, np.eye(3), atol=1e-6, rtol=0)
        np.testing.assert_allclose(np.linalg.det(rotation), 1, atol=1e-6, rtol=0)
        np.testing.assert_allclose(rotation @ up, [0, 0, 1], atol=1e-6, rtol=0)
        derived, hand_checks = align_hand_geometry(world, rotation, models)
        aligned = {**world, **derived, "rotation_aligned_from_world": rotation,
                   "rotation_world_from_aligned": rotation.T, "up_world": up,
                   "camera_rotation_world_from_camera": camera_rotation,
                   "camera_position_world_m": camera_position,
                   "camera_rotation_aligned_from_camera": rotation @ camera_rotation,
                   "camera_position_aligned_m": camera_position @ rotation.T}
        # Relative hand/camera geometry must survive the same frame change.
        world_relative = np.einsum("tji,thj->thi", camera_rotation,
                                   derived["wrist_position_world_m"] - camera_position[:, None])
        aligned_relative = np.einsum("tji,thj->thi", aligned["camera_rotation_aligned_from_camera"],
                                     derived["wrist_position_aligned_m"] - aligned["camera_position_aligned_m"][:, None])
        tolerance = max(check.get("tolerance_m", 0) for check in hand_checks.values())
        np.testing.assert_allclose(aligned_relative, world_relative, atol=tolerance, rtol=0)
        np.testing.assert_allclose(aligned["camera_position_aligned_m"] @ rotation, camera_position, atol=1e-9, rtol=0)
        path = output / "trajectory_aligned.npz"
        np.savez_compressed(path, **aligned)
        with np.load(path, allow_pickle=False) as reloaded:
            if set(reloaded.files) != set(aligned):
                raise ValueError("Aligned export fields changed on reload")
            for name, expected in aligned.items():
                if reloaded[name].dtype != expected.dtype or reloaded[name].tobytes() != expected.tobytes():
                    raise ValueError(f"Aligned export reload changed values: {name}")
        from .gravity_visualization import save_gravity_review
        save_gravity_review(output, aligned, clip, artifacts["prepared_video"], diagnostics)
        for name, path in inputs.items():
            if sha256_file(path) != hashes[name]:
                raise ValueError(f"Source changed during gravity alignment: {name}")
        report.update(status="completed", transform={"rotation_aligned_from_world": rotation.tolist(),
                      "rotation_world_from_aligned": rotation.T.tolist(), "translation": [0., 0., 0.],
                      "up_world": up.tolist(), "axis_reference": reference, "down_aligned": [0., 0., -1.]},
                      validation={"hands": hand_checks, "rotation_checks": "passed (absolute tolerance 1e-6)",
                                  "hand_camera_relative_error_m": float(np.nanmax(np.abs(aligned_relative - world_relative))),
                                  "source_files_unchanged": True, "source_fields_preserved_exactly": list(world),
                                  "export_reload": "all fields, dtypes and bytes match"},
                      artifacts={name: str(output / name) for name in
                                 ("trajectory_aligned.npz", "gravity_diagnostics.json", "trajectory_comparison.png",
                                  "vertical_review.png", "gravity_diagnostics.png")})
    except (Exception, KeyboardInterrupt) as error:
        report.update(status="failed", failure={"type": type(error).__name__, "message": str(error)})
        raise
    finally:
        report.update(finished_at=utc_now(), wall_time_s=time.monotonic() - started)
        write_json(output / "gravity_diagnostics.json", diagnostics)
        write_json(report_path, report, overwrite=True)
    return report
