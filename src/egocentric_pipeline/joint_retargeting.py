"""Aligned observations to bounded wrist/head pose trajectories and shared viewer."""

import importlib.metadata
from pathlib import Path
import sys
import time

import numpy as np
from scipy.spatial.transform import Rotation

from .base_placement import base_transform, transform_points
from .hand_geometry import mano_palm_frames
from .hand_pose_filtering import smooth_hand_targets, validate_filter_settings
from .manipulation_regions import camera_segments, frame_edges, interval_metrics, retained_regions
from .pose_retargeting import PoseModel, fit_region, initialize_base, rotation_error
from .retargeting import load_alignment, save_retargeting
from .robot_workspace import load_robot, verify_asset_source
from .run_metadata import utc_now, write_json


def validate_settings(settings):
    validate_filter_settings(settings)
    if type(settings.get("merge_adjacent_regions", False)) is not bool:
        raise ValueError("merge_adjacent_regions must be boolean")
    for key in ("base_prior_translation_scale_m", "base_prior_yaw_scale_rad"):
        if not np.isfinite(settings.get(key, 1.)) or settings.get(key, 1.) <= 0:
            raise ValueError(f"{key} must be positive finite")
    weight = settings.get("base_initialization_weight", 0.)
    if not np.isfinite(weight) or weight < 0:
        raise ValueError("base_initialization_weight must be nonnegative finite")
    if settings.get("solver_backend", "cpu") not in ("cpu", "cuda"):
        raise ValueError("solver_backend must be 'cpu' or 'cuda'")
    for key in ("camera_displacement_m", "camera_sustain_s", "minimum_episode_s", "ik_tolerance_m",
                "orientation_tolerance_rad", "joint_jump_report_rad", "heading_min_norm",
                "base_translation_radius_m", "position_scale_m", "orientation_scale_rad",
                "camera_rotation_scale_rad", "hand_position_weight", "hand_orientation_weight",
                "neutral_weight", "solver_tolerance"):
        if key not in settings or not np.isfinite(settings[key]) or settings[key] <= 0:
            raise ValueError(f"{key} must be positive finite")
    for key in ("camera_smoothing_sigma_s", "maximum_gap_s", "velocity_weight", "acceleration_weight"):
        if not np.isfinite(settings[key]) or settings[key] < 0:
            raise ValueError(f"{key} must be nonnegative finite")
    for key in ("base_max_evaluations", "trajectory_max_evaluations", "torch_threads", "fit_attempts",
                "base_frame_stride"):
        if type(settings[key]) is not int or settings[key] < 1:
            raise ValueError(f"{key} must be a positive integer")
    if (settings["ik_tolerance_m"] > .005 or settings["orientation_tolerance_rad"] > np.deg2rad(10)
            or not .95 <= settings["minimum_feasible_fraction"] < 1
            or settings["maximum_gap_s"] > .2 or settings["minimum_episode_s"] < 1):
        raise ValueError("Acceptance requires <=5 mm / 10 degrees, >95%, <=0.2 s gaps, >=1 s")
    if len(settings["neck_joints"]) != 2:
        raise ValueError("Specify two neck joints in base-to-camera order")
    if type(settings["seed"]) is not int or settings["seed"] < 0:
        raise ValueError("seed must be a nonnegative integer")
    offset = np.asarray(settings["wrist_offset_tool_m"])
    if offset.shape != (3,) or not np.isfinite(offset).all():
        raise ValueError("wrist_offset_tool_m must contain three finite tool-frame metres")


def joint_retarget_trajectory(alignment_directory, output_directory, settings, robot_settings,
                              asset_root, *, render_video=True):
    """Process retained camera seeds only; save failed regions for honest review."""
    import torch

    validate_settings(settings)
    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    report = {"schema_version": 6, "method": "joint_base", "status": "running", "started_at": utc_now(),
              "command": [sys.executable, *sys.argv], "settings": settings, "robot_settings": robot_settings,
              "alignment_directory": str(Path(alignment_directory).resolve()),
              "asset_root": str(Path(asset_root).resolve()), "hand_order": ["left", "right"],
              "target_frames": robot_settings["target_frames"], "orientation_frames": robot_settings["tool_frames"],
              "manual_review": "pending", "regions_only": True,
              "observation_policy": "export_valid AND NOT motion_infilled; infilled hands are missing data",
              "units": {"position": "metres", "joint_angles": "radians", "time": "seconds"},
              "transform_convention": "column vectors; T_destination_from_source; Z-up yaw-only base rotation",
              "limitations": "Kinematic fit only; collision, dynamics, scale, gravity and floor height unverified.",
              "camera_position_use": "segmentation, median initialization, optional shared-base prior and diagnostic errors; no per-frame tracking",
              "acceptance_targets": "original eligible observations, including restart pose-ranking",
              "camera_position_objective": False,
              "position_mapping": "human wrist matches robot wrist origin + tool rotation @ wrist_offset_tool_m; physical wrist and TCP saved separately",
              "base_initialization": "yaw from component-wise median of normalized horizontal optical forward vectors; XYZ from median camera position minus rotated neutral camera offset",
              "orientation_mapping": "Neutral MANO wrist-to-middle MCP X; pinky-to-index MCP Y orthogonalized; Z=X cross Y. Match EZGripper palm/TCP axes.",
              "camera_convention": "URDF mount +X forward,+Y left,+Z up to optical +Z forward,+X right,+Y down; nominal mount centre, not calibrated lens centre",
              "invalid_geometry": "Original missing geometry remains NaN. joint_solution_rad contains regularized predictions within seeds; ik_success is observed pose acceptance, not solver convergence."}
    write_json(output / "retargeting_report.json", report)
    try:
        torch.set_num_threads(settings["torch_threads"])
        arrays, alignment, clip = load_alignment(alignment_directory)
        robot = load_robot(verify_asset_source(asset_root, robot_settings), robot_settings["base_frame"])
        model = PoseModel(robot, robot_settings, settings)
        paths = [alignment["inputs"][f"mano_{hand}"]["path"] for hand in ("left", "right")]
        offsets = mano_palm_frames(paths)
        n, times = len(arrays["timestamp_s"]), arrays["timestamp_s"]
        valid = arrays["export_valid"] & ~arrays["motion_infilled"]
        wrists_aligned = arrays["wrist_position_aligned_m"].copy()
        wrists_aligned[~valid] = np.nan
        orientations = np.full((n, 2, 3, 3), np.nan)
        for hand in range(2):
            orientations[valid[:, hand], hand] = Rotation.from_rotvec(
                arrays["root_orientation_aligned_axis_angle"][valid[:, hand], hand]).as_matrix() @ offsets[hand]
        cameras = arrays["camera_rotation_aligned_from_camera"]
        if (not np.isfinite(cameras).all()
                or not np.allclose(cameras @ cameras.transpose(0, 2, 1), np.eye(3), atol=1e-6)
                or not np.allclose(np.linalg.det(cameras), 1., atol=1e-6)):
            raise ValueError("Camera rotations must be finite proper optical-to-aligned rotations")
        smooth, seeds = camera_segments(arrays["camera_position_aligned_m"], times, settings)
        regions = retained_regions(seeds, times, settings.get("merge_adjacent_regions", False))
        filtered_positions, filtered_rotations, filtering = smooth_hand_targets(
            wrists_aligned, orientations, valid, times, regions, settings)
        edges = frame_edges(times)
        derived = {
            "retarget_valid": valid,
            "camera_position_smoothed_m": smooth,
            "rotation_mano_from_palm": offsets,
            "wrist_orientation_target_aligned": orientations,
            "wrist_position_filtered_aligned_m": filtered_positions,
            "wrist_orientation_filtered_aligned": filtered_rotations,
            "episode_id": np.full(n, -1, np.int32),
            "joint_solution_rad": np.full((n, 16), np.nan),
            "joint_solution_before_smoothing_rad": np.full((n, 16), np.nan),
            "joint_angles_rad": np.full((n, 2, 7), np.nan),
            "neck_joint_angles_rad": np.full((n, 2), np.nan),
            "joint_prediction": np.zeros((n, 2), bool),
            "wrist_position_base_m": np.full((n, 2, 3), np.nan),
            "wrist_orientation_target_base": np.full((n, 2, 3, 3), np.nan),
            "target_position_base_m": np.full((n, 2, 3), np.nan),
            "robot_wrist_position_base_m": np.full((n, 2, 3), np.nan),
            "tcp_position_base_m": np.full((n, 2, 3), np.nan),
            "tool_orientation_base": np.full((n, 2, 3, 3), np.nan),
            "camera_position_base_m": np.full((n, 3), np.nan),
            "camera_position_error_m": np.full(n, np.nan),
            "camera_rotation_base_from_optical": np.full((n, 3, 3), np.nan),
            "camera_rotation_error_rad": np.full(n, np.nan),
            "ik_residual_m": np.full((n, 2), np.nan),
            "orientation_residual_rad": np.full((n, 2), np.nan),
            "filtered_ik_residual_m": np.full((n, 2), np.nan),
            "filtered_orientation_residual_rad": np.full((n, 2), np.nan),
            "ik_success": np.zeros((n, 2), bool),
            "joint_step_rad": np.full((n, 2), np.nan),
            "joint_jump": np.zeros((n, 2), bool),
        }
        report.update(source_run_id=alignment["source_run_id"], prepared_video=alignment["inputs"]["prepared_video"]["path"],
                      joint_names=model.joint_names, joint_lower_rad=model.lower.tolist(), joint_upper_rad=model.upper.tolist(),
                      locked_joint_positions_rad={j.name: 0. for j in robot.joint_list if j.name not in model.joint_names},
                      packages={p: importlib.metadata.version(p) for p in ("scikit-robot", "numpy", "scipy", "torch", "viser", "smplx")},
                      seeds=seeds, regions=regions, hand_target_filtering=filtering,
                      timing={"loading_s": time.perf_counter() - started})
        report["solver_backend"] = settings.get("solver_backend", "cpu")
        if report["solver_backend"] == "cuda":
            report["packages"].update({p: importlib.metadata.version(p) for p in
                                       ("cupy-cuda12x", "nvmath-python", "nvidia-cudss-cu12")})
        candidates, episodes, transforms, frame_passed = [], [], [], []
        solve_started = time.perf_counter()
        for seed in regions:
            seed_index = seed["seed_indices"][0]
            sl = slice(seed["start"], seed["stop"])
            v = valid[sl]
            if not v.any():
                seed["reason"] = "no_observed_wrists"
                for index in seed["seed_indices"]:
                    seeds[index]["reason"] = "no_observed_wrists"
                continue
            initial = initialize_base(arrays["camera_position_aligned_m"][sl], cameras[sl], model,
                                      settings["heading_min_norm"])
            pose, before, q, info = fit_region(model, filtered_positions[sl],
                                               filtered_rotations[sl], cameras[sl], v, times[sl], initial, settings,
                                               seed_index=seed_index, raw_wrists=wrists_aligned[sl],
                                               raw_orientations=orientations[sl])
            transform = base_transform(pose)
            wrists = transform_points(wrists_aligned[sl], transform)
            target_rotations = transform[:3, :3] @ orientations[sl]
            p, r, tcp, hp, hr = model.forward(q)
            errors = np.linalg.norm(p - wrists, axis=-1)
            angles = np.full(v.shape, np.nan)
            angles[v] = rotation_error(r[v], target_rotations[v])
            success = v & (errors <= settings["ik_tolerance_m"]) & (angles <= settings["orientation_tolerance_rad"])
            passed = v.any(axis=1) & (success | ~v).all(axis=1)
            region = interval_metrics(0, len(v), passed, v.any(axis=1), edges[seed["start"]:seed["stop"] + 1], settings)
            region.update(start=seed["start"], stop=seed["stop"])
            smoothed = info["after_smoothing"]["acceleration_rms_rad_s2"] < info["before_smoothing"]["acceleration_rms_rad_s2"]
            cid, eid = len(candidates), len(episodes)
            candidates.append({"candidate_id": cid, "seed_index": seed_index, "seed": seed,
                               "initial_base_xyz_yaw": initial.tolist(), "base_xyz_yaw": pose.tolist(),
                               "optimization": info, "selection": "heuristic_region"})
            episodes.append({"episode_id": eid, "candidate_id": cid, "region": region, "pose": region,
                             "demonstrated": bool(region["accepted"] and smoothed),
                             "smoothing_improved": bool(smoothed),
                             "observed_hand_frames": v.sum(axis=0).tolist(),
                             "ik_successful_hand_frames": success.sum(axis=0).tolist(),
                             "max_fk_residual_m": float(errors[v].max()),
                             "max_orientation_residual_rad": float(angles[v].max())})
            mask = np.zeros(n, bool)
            mask[sl] = passed
            frame_passed.append(mask)
            transforms.append(transform)
            derived["episode_id"][sl] = eid
            derived["joint_solution_rad"][sl] = q
            derived["joint_solution_before_smoothing_rad"][sl] = before
            derived["joint_angles_rad"][sl] = q[:, :14].reshape(-1, 2, 7)
            derived["neck_joint_angles_rad"][sl] = q[:, 14:]
            derived["joint_prediction"][sl] = ~v
            derived["wrist_position_base_m"][sl] = wrists
            derived["wrist_orientation_target_base"][sl] = target_rotations
            derived["target_position_base_m"][sl] = p
            derived["robot_wrist_position_base_m"][sl] = p - r @ model.wrist_offset
            derived["tcp_position_base_m"][sl] = tcp
            derived["tool_orientation_base"][sl] = r
            derived["camera_position_base_m"][sl] = hp
            derived["camera_position_error_m"][sl] = np.linalg.norm(
                hp - transform_points(arrays["camera_position_aligned_m"][sl], transform), axis=-1)
            derived["camera_rotation_base_from_optical"][sl] = hr
            derived["camera_rotation_error_rad"][sl] = rotation_error(hr, transform[:3, :3] @ cameras[sl])
            derived["ik_residual_m"][sl], derived["orientation_residual_rad"][sl] = errors, angles
            derived["filtered_ik_residual_m"][sl] = np.linalg.norm(
                p - transform_points(filtered_positions[sl], transform), axis=-1)
            filtered_angles = np.full(v.shape, np.nan)
            filtered_angles[v] = rotation_error(r[v], (transform[:3, :3] @ filtered_rotations[sl])[v])
            derived["filtered_orientation_residual_rad"][sl] = filtered_angles
            derived["ik_success"][sl] = success
            steps = np.max(np.abs(np.diff(q[:, :14].reshape(-1, 2, 7), axis=0)), axis=-1)
            derived["joint_step_rad"][seed["start"] + 1:seed["stop"]] = steps
            print(f"Region [{seed['start']},{seed['stop']}): pose {region['passing_fraction']:.2%}, "
                  f"acceleration RMS {info['before_smoothing']['acceleration_rms_rad_s2']:.2f} → "
                  f"{info['after_smoothing']['acceleration_rms_rad_s2']:.2f}", flush=True)
        report["timing"]["solve_s"] = time.perf_counter() - solve_started
        world_to_aligned = np.eye(4)
        world_to_aligned[:3, :3] = arrays["rotation_aligned_from_world"]
        transforms = np.asarray(transforms).reshape(-1, 4, 4)
        derived.update(transform_base_from_aligned=transforms, transform_base_from_world=transforms @ world_to_aligned,
                       transform_aligned_from_base=np.linalg.inv(transforms),
                       candidate_frame_passed=np.asarray(frame_passed, dtype=bool).reshape(-1, n))
        derived["joint_jump"] = derived["joint_step_rad"] > settings["joint_jump_report_rad"]
        report.update(candidates=candidates, episodes=episodes, demo_accepted=any(e["demonstrated"] for e in episodes),
                      source_fields_preserved=list(arrays), frame_count=n)
        save_retargeting(output, dict(arrays, **derived), report, clip, render_video=render_video)
        report.update(status="completed", finished_at=utc_now(), wall_time_s=time.perf_counter() - started)
        write_json(output / "retargeting_report.json", report, overwrite=True)
        return report
    except (Exception, KeyboardInterrupt) as error:
        report.update(status="failed", error=f"{type(error).__name__}: {error}", finished_at=utc_now())
        write_json(output / "retargeting_report.json", report, overwrite=True)
        raise
