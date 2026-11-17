"""Full-video robot features from completed, independently evaluated trajectories.

Frames retain their source indices. Regions are half-open and may have different
fixed bases. No derivative or interpolation crosses a gap or region boundary.
"""

from pathlib import Path

import numpy as np

from egocentric_pipeline.run_metadata import read_json


ALIGNED_FIELDS = (
    "root_translation_aligned_m", "root_orientation_aligned_axis_angle",
    "wrist_position_world_m", "wrist_position_aligned_m", "mano_root_offset_m",
)
CAMERA_FIELDS = (
    "camera_position_world_m", "camera_rotation_world_from_camera",
    "camera_position_aligned_m", "camera_rotation_aligned_from_camera",
)


def load_robot_episode(directories, world, clip, source_run_id, evaluation_directories=None):
    """Combine disjoint solved regions on one unchanged full-video timeline.

    Each trajectory directory requires its sibling score.json and
    benchmark_frame_metrics.npz, produced by the ordinary URDF evaluator. The
    multi-directory form reuses disjoint historical region solves. Incompatible
    robots, targets, timelines, settings or overlapping regions are errors.

    The 18-component action contains left arm (7 rad), right arm (7 rad), neck
    (2 rad), then left/right gripper opening (0 closed, 1 open). Invalid action
    components retain predictions with false masks; gaps have NaN until export.
    """
    if not directories:
        raise ValueError("Supply at least one completed robot trajectory directory")
    count = len(world["frame_index"])
    region_ids = np.full((count, 1), -1, np.int32)
    q = np.full((count, 18), np.nan)
    action = np.full((count, 18), np.nan)
    action_valid = np.zeros((count, 18), bool)
    solved = np.zeros((count, 1), bool)
    observed = np.zeros((count, 2), bool)
    ik_success = np.zeros((count, 2), bool)
    feasible = np.zeros((count, 1), bool)
    collision_free = np.zeros((count, 1), bool)
    position_error = np.full((count, 2), np.nan)
    orientation_error = np.full((count, 2), np.nan)
    metadata = {"regions": [], "sources": [], "interval_convention": "half-open [start, stop)",
                "action_units": ["radians"] * 16 + ["normalized opening"] * 2,
                "validity": "Per-component observed tracking, joint limits and discrete self-collision checks; "
                            "invalid components are masked. Solver predictions are diagnostic, not executable commands.",
                "limitations": "No hardware, dynamics, scene collision or continuous collision certification."}
    geometry, common = None, None
    times = world["timestamp_s"]
    if count < 2 or not np.allclose(times, np.arange(count) / 30, atol=1e-9, rtol=0):
        raise ValueError("Robot dataset requires the complete synchronized 30 FPS timeline")
    # Source presentation times need not be uniform after 30 FPS preparation.
    source_edges = np.r_[world["source_timestamp_s"], clip["selection"]["resolved_interval_s"][1]]
    frame_map = clip["frames"]["mapping"]
    evaluations = evaluation_directories or [Path(d).parent for d in directories]
    if len(evaluations) != len(directories):
        raise ValueError("Provide one evaluation directory per trajectory")
    ee = np.full((count, 2, 8), np.nan)
    for directory, evaluation in zip(map(Path, directories), map(Path, evaluations)):
        report = read_json(directory / "retargeting_report.json")
        score = read_json(evaluation / "score.json")
        with np.load(directory / "trajectory_retargeted.npz", allow_pickle=False) as saved:
            arrays = dict(saved)
        with np.load(evaluation / "benchmark_frame_metrics.npz", allow_pickle=False) as saved:
            metrics = dict(saved)
        if not {'tcp_pose_base', 'gripper_opening', 'frame_max_speed_rad_s', 'frame_acceleration_rad_s2'} <= metrics.keys():
            raise ValueError('Evaluation lacks TCP FK/action feasibility; rerun pipeline/evaluate_trajectory.py into a new output directory')
        if (report["status"] != "completed" or report.get("schema_version") != 7
                or report["hand_order"] != ["left", "right"] or report["source_run_id"] != source_run_id
                or score["status"] != "completed" or score["definition"]["source_run_id"] != source_run_id):
            raise ValueError("Require completed, evaluated gripper trajectories for this HaWoR run")
        for key, value in world.items():
            if key not in arrays or arrays[key].dtype != value.dtype or not np.array_equal(arrays[key], value, equal_nan=True):
                raise ValueError(f"Robot trajectory differs from the original world data: {key}")
        for key in ("timestamp_s", "source_timestamp_s"):
            if not np.array_equal(metrics[key], world[key]):
                raise ValueError(f"Robot evaluation timeline differs: {key}")
        eligible = world["export_valid"] & ~world["motion_infilled"]
        if metrics["observed"].shape != (count, 2) or np.any(metrics["observed"] & ~eligible):
            raise ValueError("Robot observations cannot include missing or motion-infilled hands")
        names = report["joint_names"]
        expected = sum(report["robot_settings"]["arm_joints"], []) + report["settings"]["neck_joints"]
        if len(names) != 18 or names[:16] != expected or len(set(names)) != 18:
            raise ValueError("Robot joint order must be left arm, right arm, neck, then two gripper leaders")
        definition = score["definition"]
        if (definition["frame_count"] != count or definition["robot_settings"] != report["robot_settings"]
                or definition["mapping_settings"] != report["gripper_mapping_settings"]
                or not np.array_equal(metrics["observed"], arrays["retarget_valid"])):
            raise ValueError("Robot evaluation differs from the solve's robot, mapping or observations")
        joint_indices = [score["limits"]["joint_names"].index(name) for name in names]
        if not np.allclose(metrics["joint_positions_rad"][:, joint_indices], arrays["joint_solution_rad"],
                           atol=1e-12, rtol=0, equal_nan=True):
            raise ValueError("Robot evaluation belongs to different joint predictions; evaluate this solve again")
        contract = {key: report[key] for key in ("joint_names", "robot_settings", "settings", "gripper_mapping_settings")}
        contract["evaluation_settings"] = score["definition"]["settings"]
        # Region selections are evidence, not a difference in the motion/robot contract.
        contract["evaluation_settings"] = {k: v for k, v in contract["evaluation_settings"].items()
                                           if k not in ("selection", "region_limit")}
        current_geometry = {key: arrays[key] for key in (*ALIGNED_FIELDS, *CAMERA_FIELDS, "rotation_aligned_from_world")}
        if common is None:
            common, geometry = contract, current_geometry
        elif common != contract or any(not np.array_equal(geometry[k], v, equal_nan=True) for k, v in current_geometry.items()):
            raise ValueError("Region solves have incompatible robot, settings or aligned geometry")
        if arrays["joint_solution_rad"].shape != (count, 18) or arrays["gripper_action"].shape != (count, 2):
            raise ValueError("Robot solutions must retain all source frames and both grippers")
        settings = score["definition"]["settings"]
        tracking = (metrics["observed"] & (metrics["position_error_m"] <= settings["position_tolerance_m"])
                    & (metrics["orientation_error_rad"] <= np.deg2rad(settings["orientation_tolerance_degrees"])))
        component_valid = joint_component_validity(metrics, score, names)
        episodes = {(e["region"]["start"], e["region"]["stop"]): e for e in report["episodes"]}
        source = {"directory": str(directory.resolve()), "benchmark_selection": report.get("benchmark_selection")}
        metadata["sources"].append(source)
        for region in report["regions"]:
            start, stop = region["start"], region["stop"]
            if not (type(start) is int and type(stop) is int and 0 <= start < stop <= count):
                raise ValueError("Region boundaries must be half-open frame indices inside the full video")
            sl = slice(start, stop)
            if (region_ids[sl] >= 0).any():
                raise ValueError("Robot region solves overlap; provide disjoint regions")
            if not metrics["evaluated"][sl].all():
                raise ValueError("Evaluation does not cover the entire robot region")
            region_id = len(metadata["regions"])
            region_ids[sl] = region_id
            q[sl] = arrays["joint_solution_rad"][sl]
            solved[sl, 0] = np.isfinite(q[sl]).all(axis=1) & (arrays["episode_id"][sl] >= 0)
            observed[sl], ik_success[sl] = metrics["observed"][sl], arrays["ik_success"][sl]
            feasible[sl, 0], collision_free[sl, 0] = metrics["joint_feasible"][sl], metrics["collision_free"][sl]
            position_error[sl], orientation_error[sl] = metrics["position_error_m"][sl], metrics["orientation_error_rad"][sl]
            hand_valid = tracking[sl] & ik_success[sl] & solved[sl] & collision_free[sl]
            opening = metrics['gripper_opening'][sl]
            if not np.allclose(opening, arrays['gripper_action'][sl], atol=1e-8, rtol=0, equal_nan=True):
                raise ValueError('Gripper actions disagree with evaluated joint solutions')
            gripper_valid = hand_valid & np.isfinite(opening) & (opening >= 0) & (opening <= 1)
            valid = np.concatenate([np.repeat(hand_valid[:, :1], 7, axis=1),
                                    np.repeat(hand_valid[:, 1:], 7, axis=1),
                                    np.repeat(hand_valid.any(axis=1, keepdims=True), 2, axis=1), gripper_valid], axis=1)
            valid &= component_valid[sl]
            tcp = metrics.get("tcp_pose_base")
            if tcp is None or tcp.shape != (count, 2, 7):
                raise ValueError("Evaluation lacks TCP FK; rerun pipeline/evaluate_trajectory.py into a new output directory")
            finite_tcp = np.isfinite(tcp[sl]).all(axis=-1)
            if np.any(finite_tcp & ~np.isclose(np.linalg.norm(tcp[sl, :, 3:], axis=-1), 1., atol=1e-6)):
                raise ValueError('Evaluated TCP quaternions must be normalized xyzw')
            if np.any(hand_valid & ~finite_tcp):
                raise ValueError('Valid joint solutions require finite evaluated TCP poses')
            ee[sl] = np.concatenate([tcp[sl], opening[..., None]], axis=-1)
            action_valid[sl] = valid
            # Finite predictions remain available but never become unmasked targets.
            action[sl] = np.c_[q[sl, :16], opening]
            episode = episodes.get((start, stop))
            transform = None
            if episode is not None:
                transform = arrays["transform_base_from_aligned"][episode["candidate_id"]]
                if (transform.shape != (4, 4) or not np.isfinite(transform).all()
                        or not np.allclose(transform[3], [0, 0, 0, 1], atol=1e-9, rtol=0)
                        or not np.allclose(transform[:3, :3] @ transform[:3, :3].T, np.eye(3), atol=1e-8, rtol=0)
                        or not np.isclose(np.linalg.det(transform[:3, :3]), 1, atol=1e-8)):
                    raise ValueError("Region base transform must be rigid T_base_from_aligned")
                world_to_aligned = np.eye(4)
                world_to_aligned[:3, :3] = geometry["rotation_aligned_from_world"]
                if not np.allclose(transform @ world_to_aligned,
                                   arrays["transform_base_from_world"][episode["candidate_id"]], atol=1e-8, rtol=0):
                    raise ValueError("World-to-base transform composition disagrees with gravity alignment")
            elif solved[sl].any():
                raise ValueError("Solved frames require a corresponding fixed-base region")
            metadata["regions"].append({"region_id": region_id, "episode_frame_interval": [start, stop],
                "episode_time_interval_s": [start / 30, stop / 30],
                "source_frame_interval": [frame_map[start]["source_frame_index"], frame_map[stop - 1]["source_frame_index"] + 1],
                "source_time_interval_s": [float(source_edges[start]), float(source_edges[stop])],
                "transform_base_from_aligned": None if transform is None else transform.tolist(),
                "outcome": "unsolved" if episode is None else "evaluated",
                "solved_frames": int(solved[sl].sum()), "joint_feasible_frames": int(feasible[sl].sum()),
                "collision_free_frames": int(collision_free[sl].sum()),
                "constraint_valid_frames": int((solved[sl, 0] & collision_free[sl, 0]
                                                 & component_valid[sl].all(axis=1)).sum()),
                "valid_action_components": action_valid[sl].sum(axis=0).tolist(),
                "pose_acceptance": episode, "source_index": len(metadata["sources"]) - 1})
    metadata.update(contract=common, rotation_aligned_from_world=geometry["rotation_aligned_from_world"].tolist(),
                    action_names=common["joint_names"][:16] + ["left_gripper_opening", "right_gripper_opening"])
    features = {"action": action.astype(np.float32), "action.ee": ee.astype(np.float32), "observation.robot.action_valid": action_valid,
                "observation.robot.joint_solution_rad": q, "observation.robot.region_id": region_ids,
                "observation.robot.solved": solved, "observation.robot.observed_hand": observed,
                "observation.robot.ik_success": ik_success, "observation.robot.joint_feasible": feasible,
                "observation.robot.collision_free": collision_free,
                "observation.robot.position_error_m": position_error,
                "observation.robot.orientation_error_rad": orientation_error}
    features.update({f"observation.hands.{k}": geometry[k].reshape(count, -1) for k in ALIGNED_FIELDS})
    features.update({f"observation.{k}": geometry[k].reshape(count, -1) for k in CAMERA_FIELDS})
    return features, metadata


def joint_component_validity(metrics, score, action_joint_names):
    """Position/velocity/acceleration checks per independent control, including mimics.

    Temporal derivatives are the evaluator's ordered within-region differences.
    Locked joints with hard violations invalidate the complete configuration.
    """
    limits = score['limits']
    names = limits['joint_names']
    q = metrics['joint_positions_rad']
    speed = metrics['frame_max_speed_rad_s']
    acceleration = metrics['frame_acceleration_rad_s2']
    tolerance = score['definition']['settings'].get('joint_position_tolerance_rad', 0.)
    valid = (np.isfinite(q) & np.isfinite(speed) & np.isfinite(acceleration)
             & (q >= np.array(limits['position_lower_rad']) - tolerance)
             & (q <= np.array(limits['position_upper_rad']) + tolerance)
             & (speed <= np.array(limits['velocity_limit_rad_s']))
             & (np.abs(acceleration) <= np.array(limits['acceleration_limit_rad_s2'])))
    result = valid[:, [names.index(name) for name in action_joint_names]].copy()
    controlled = set(action_joint_names)
    for hand, side in enumerate(('left', 'right')):
        fingers = [j for j, name in enumerate(names) if name.startswith(side + '_ezgripper_')]
        if fingers:
            result[:, 16 + hand] &= valid[:, fingers].all(axis=1)
            controlled.update(names[j] for j in fingers)
    locked = [j for j, name in enumerate(names) if name not in controlled]
    if locked:
        result &= valid[:, locked].all(axis=1, keepdims=True)
    return result
