"""Comparable 100-point IK scoring from saved source-timed robot trajectories."""

import importlib.metadata
from pathlib import Path

import numpy as np

from .gripper_mapping import load_mapping_for_alignment
from .hand_pose_filtering import smooth_hand_targets, validate_filter_settings
from .pose_retargeting import rotation_error
from .robot_constraints import RobotConstraints
from .run_metadata import read_json, utc_now, write_json


def validate_settings(settings):
    validate_filter_settings(settings)
    for key in ("position_tolerance_m", "orientation_tolerance_degrees", "acceleration_limit_rad_s2"):
        if not np.isfinite(settings[key]) or settings[key] <= 0:
            raise ValueError(f"{key} must be positive finite")
    if settings["orientation_tolerance_degrees"] > 180:
        raise ValueError("Orientation tolerance must not exceed 180 degrees")
    tolerance = settings["joint_position_tolerance_rad"]
    if not np.isfinite(tolerance) or tolerance < 0:
        raise ValueError("joint_position_tolerance_rad must be nonnegative finite")


def joint_motion(angles, timestamps):
    """Interval velocity and centred acceleration; finite differences, no filtering.

    Frame speed bounds check both incident intervals. Interior acceleration is
    the change in interval velocity divided by midpoint separation. Endpoints
    use the nearest acceleration estimate; no differentiation across regions.
    Fewer than three frames cannot establish acceleration feasibility.
    """
    dt = np.diff(timestamps)
    if len(dt) < 2 or not np.isfinite(dt).all() or np.any(dt <= 0):
        raise ValueError("Benchmark regions need at least three strictly increasing timestamps")
    velocity = np.diff(angles, axis=0) / dt[:, None]
    acceleration = np.diff(velocity, axis=0) / ((dt[:-1] + dt[1:]) / 2)[:, None]
    speed = np.maximum(np.abs(np.vstack([velocity[:1], velocity])),
                       np.abs(np.vstack([velocity, velocity[-1:]])))
    accel = np.vstack([acceleration[:1], acceleration, acceleration[-1:]])
    return velocity, acceleration, speed, accel


def score_components(position_error, orientation_error, observed, evaluated,
                     joint_feasible, collision_free, settings):
    """Missing predictions fail; empty denominators yield unavailable scores."""
    observed = observed & evaluated[:, None]
    masks = {
        "position_tracking": (observed, np.isfinite(position_error) & (position_error <= settings["position_tolerance_m"])),
        "orientation_tracking": (observed, np.isfinite(orientation_error) &
                                  (orientation_error <= np.deg2rad(settings["orientation_tolerance_degrees"]))),
        "joint_feasibility": (evaluated, joint_feasible),
        "self_collision_avoidance": (evaluated, collision_free),
    }
    result = {}
    for name, (mask, passed) in masks.items():
        count, total = int((mask & passed).sum()), int(mask.sum())
        result[name] = {"passed": count, "evaluated": total,
                        "percent": 100 * count / total if total else None,
                        "score": 25 * count / total if total else None}
    points = [r["score"] for r in result.values()]
    return result, sum(points) if all(p is not None for p in points) else None


def distribution(values):
    """Diagnostics use finite values only; always disclose excluded failures."""
    values = np.asarray(values)
    finite = values[np.isfinite(values)]
    return {"samples": int(values.size), "nonfinite": int(values.size - finite.size),
            "rms": float(np.sqrt(np.mean(finite ** 2))) if finite.size else None,
            "median": float(np.median(finite)) if finite.size else None,
            "p95": float(np.percentile(np.abs(finite), 95)) if finite.size else None}


def evaluate_run(run_directory, mapping_directory, settings, name, description):
    """Score a run's trajectory with ordinary FK and preserve frame-level evidence."""
    validate_settings(settings)
    run = Path(run_directory)
    report = read_json(run / "trajectory/retargeting_report.json")
    if report["status"] != "completed":
        raise ValueError("Only completed trajectories can be scored")
    with np.load(run / "trajectory/trajectory_retargeted.npz", allow_pickle=False) as data:
        arrays = dict(data)
    mapping, mapped_report = load_mapping_for_alignment(mapping_directory, arrays)
    if mapped_report["robot_settings"] != report["robot_settings"]:
        raise ValueError("Scoring and mapping require the same pinned robot")
    n = len(arrays["timestamp_s"])
    observed = arrays["export_valid"] & ~arrays["motion_infilled"] & mapping["mapping_valid"]
    raw = mapping["transform_aligned_from_palm"]
    positions, rotations, filtering = smooth_hand_targets(raw[..., :3, 3], raw[..., :3, :3], observed,
        arrays["timestamp_s"], report["regions"], settings)
    evaluated = np.zeros(n, bool)
    for region in report["regions"]:
        evaluated[region["start"]:region["stop"]] = True
    contract = {"settings": settings, "source_run_id": report["source_run_id"], "frame_count": n,
                "mapping_settings": mapped_report["settings"], "robot_settings": report["robot_settings"],
                "regions": [[r["start"], r["stop"]] for r in report["regions"]],
                "observation_policy": "export_valid AND NOT motion_infilled AND mapping_valid",
                "comparison_target": "filtered mapped palm pose in aligned frame"}
    contract_path = run.parent / "benchmark.json"
    if contract_path.exists() and read_json(contract_path) != contract:
        raise ValueError("Benchmark definition/source/regions differ; use a separate benchmark directory or consistently rescore every run")
    # Equal names/settings alone do not establish equal observations. Compare
    # actual scoring arrays before ranking a new run against preserved results.
    common_arrays = dict(evaluated=evaluated, observed=observed, timestamp_s=arrays["timestamp_s"],
                         source_timestamp_s=arrays["source_timestamp_s"], target_position_aligned_m=positions,
                         target_rotation_aligned=rotations, raw_target_transform_aligned_from_palm=raw,
                         target_opening_action=mapping["gripper_action"])
    for previous in sorted(run.parent.glob("*/score.json")):
        with np.load(previous.parent / "benchmark_frame_metrics.npz", allow_pickle=False) as saved:
            if any(not np.array_equal(saved[key], value, equal_nan=True) for key, value in common_arrays.items()):
                raise ValueError("Benchmark targets, timestamps or observations differ from saved experiments; use a separate directory")
    constraints = RobotConstraints(report["asset_root"], report["robot_settings"], settings)
    full_q = np.full((n, len(constraints.names)), np.nan)
    position_error = np.full((n, 2), np.nan)
    orientation_error = np.full((n, 2), np.nan)
    raw_position_error, raw_orientation_error = position_error.copy(), orientation_error.copy()
    opening_error = position_error.copy()
    predicted_position = np.full((n, 2, 3), np.nan)
    predicted_rotation = np.full((n, 2, 3, 3), np.nan)
    collision_free = np.zeros(n, bool)
    collisions = {}
    for frame in np.flatnonzero(evaluated):
        q = arrays["joint_solution_rad"][frame]
        eid = int(arrays["episode_id"][frame])
        if eid < 0 or not np.isfinite(q).all():
            continue
        full_q[frame] = constraints.set_pose(report["joint_names"], q, report.get("coupled_joint_leaders"))
        pairs = constraints.collision_pairs()
        collision_free[frame] = not pairs
        if pairs:
            collisions[str(frame)] = pairs
        cid = report["episodes"][eid]["candidate_id"]
        transform = arrays["transform_aligned_from_base"][cid]
        for h, side in enumerate(("left", "right")):
            palm = constraints.links[f"{side}_ezgripper_palm_link"].worldcoords().T()
            predicted = transform @ palm
            predicted_position[frame, h], predicted_rotation[frame, h] = predicted[:3, 3], predicted[:3, :3]
            if observed[frame, h]:
                position_error[frame, h] = np.linalg.norm(predicted[:3, 3] - positions[frame, h])
                orientation_error[frame, h] = rotation_error(predicted[:3, :3], rotations[frame, h])
                raw_position_error[frame, h] = np.linalg.norm(predicted[:3, 3] - raw[frame, h, :3, 3])
                raw_orientation_error[frame, h] = rotation_error(predicted[:3, :3], raw[frame, h, :3, :3])
                leader = constraints.robot.__dict__[f"{side}_ezgripper_knuckle_palm_l1_1"].joint_angle()
                opening_error[frame, h] = leader  # converted once below using the asset helper
    from .gripper_model import load_gripper_commands
    closed = load_gripper_commands(report["asset_root"]).EZGRIPPER_CLOSED_ANGLE_RAD
    opening_error = np.abs(1 - opening_error / closed - mapping["gripper_action"])
    frame_speed, frame_acceleration = np.full_like(full_q, np.nan), np.full_like(full_q, np.nan)
    velocities, accelerations = [], []
    for region in report["regions"]:
        sl = slice(region["start"], region["stop"])
        v, a, speed, accel = joint_motion(full_q[sl], arrays["timestamp_s"][sl])
        frame_speed[sl], frame_acceleration[sl] = speed, accel
        velocities.append(v)
        accelerations.append(a)
    tolerance = settings["joint_position_tolerance_rad"]
    position_ok = np.isfinite(full_q).all(axis=1) & ((full_q >= constraints.lower - tolerance) & (full_q <= constraints.upper + tolerance)).all(axis=1)
    velocity_ok = np.isfinite(frame_speed).all(axis=1) & (frame_speed <= constraints.velocity).all(axis=1)
    acceleration_ok = np.isfinite(frame_acceleration).all(axis=1) & (np.abs(frame_acceleration) <= constraints.acceleration).all(axis=1)
    feasible = position_ok & velocity_ok & acceleration_ok
    components, total = score_components(position_error, orientation_error, observed, evaluated, feasible, collision_free, settings)
    mask = observed & evaluated[:, None]
    v = np.concatenate(velocities) if velocities else np.empty((0, len(constraints.names)))
    a = np.concatenate(accelerations) if accelerations else np.empty_like(v)
    metrics = {"joint_velocity_rad_s": distribution(v), "joint_acceleration_rad_s2": distribution(a),
               "position_error_m": distribution(position_error[mask]),
               "orientation_error_degrees": distribution(np.rad2deg(orientation_error[mask])),
               "raw_position_error_m": distribution(raw_position_error[mask]),
               "raw_orientation_error_degrees": distribution(np.rad2deg(raw_orientation_error[mask])),
               "opening_action_error": distribution(opening_error[mask]),
               "per_joint": {joint: {"velocity_rad_s": distribution(v[:, j]), "acceleration_rad_s2": distribution(a[:, j])}
                             for j, joint in enumerate(constraints.names)}}
    result = {"schema_version": 1, "name": name, "description": description, "scored_at": utc_now(),
              "status": "completed", "score": total, "components": components, "metrics": metrics,
              "solve_s": report["timing"]["solve_s"], "timing": report["timing"],
              "definition": contract, "limits": constraints.metadata(), "target_filtering": filtering,
              "excluded_frames": int((~evaluated).sum()),
              "mapping_invalid_observations": int((arrays["export_valid"] & ~arrays["motion_infilled"] & ~mapping["mapping_valid"]).sum()),
              "joint_position_passing_frames": int((position_ok & evaluated).sum()),
              "joint_velocity_passing_frames": int((velocity_ok & evaluated).sum()),
              "joint_acceleration_passing_frames": int((acceleration_ok & evaluated).sum()),
              "collision_frames": collisions,
              "missing_robot_frames": int((evaluated & ~np.isfinite(full_q).all(axis=1)).sum()),
              "packages": {p: importlib.metadata.version(p) for p in ("scikit-robot", "trimesh", "python-fcl", "numpy")}}
    np.savez_compressed(run / "benchmark_frame_metrics.npz", evaluated=evaluated, observed=observed,
        joint_positions_rad=full_q, frame_max_speed_rad_s=frame_speed, frame_acceleration_rad_s2=frame_acceleration,
        position_error_m=position_error, orientation_error_rad=orientation_error,
        raw_position_error_m=raw_position_error, raw_orientation_error_rad=raw_orientation_error,
        joint_feasible=feasible, collision_free=collision_free, opening_action_error=opening_error,
        target_position_aligned_m=positions, target_rotation_aligned=rotations,
        predicted_position_aligned_m=predicted_position, predicted_rotation_aligned=predicted_rotation,
        raw_target_transform_aligned_from_palm=raw, target_opening_action=mapping["gripper_action"],
        timestamp_s=arrays["timestamp_s"], source_timestamp_s=arrays["source_timestamp_s"])
    if not contract_path.exists():
        write_json(contract_path, contract)
    write_json(run / "score.json", result, overwrite=True)
    return result


def update_report(directory):
    """Regenerate the scoreboard from every preserved registered experiment."""
    root = Path(directory).resolve()
    entries = []
    for path in sorted(root.glob("*/experiment.json")):
        experiment = read_json(path)
        score_path = path.parent / "score.json"
        score = read_json(score_path) if score_path.exists() else None
        entries.append((path.parent.name, experiment, score))
    definition = read_json(root / "benchmark.json") if (root / "benchmark.json").exists() else None
    settings = definition["settings"] if definition else read_json(root / "benchmark_settings.json")
    lines = ["# IK benchmark", "", "**Targets: smoothed hand-derived gripper palm position and orientation.**",
             f"XYZ/SO(3) Savitzky–Golay windows {settings['hand_position_window_s']}/{settings['hand_orientation_window_s']} seconds, order {settings['hand_filter_polyorder']}; independent eligible spans within each region.",
             f"**Acceleration: {settings['acceleration_limit_rad_s2']:g} rad/s² benchmark proxy, not a verified Alex hardware limit.**",
             "Position/velocity bounds come from the pinned Purdue Alex model. See each run's complete limits and exclusions.",
             "", "## Current benchmark configuration", "",
             f"Each component is 25 × passing fraction: position ≤{settings['position_tolerance_m']*100:g} cm, orientation ≤{settings['orientation_tolerance_degrees']:g}°, all joint limits, no self-collision.",
             "Tracking denominators are observed hand targets; feasibility/collision denominators are all selected frames.",
             "Missing predictions fail. Missing/infilled observations are excluded only from tracking. No fifth opening score.",
             "All 24 physical revolute joints (including neck and gripper mimics) enter joint diagnostics and feasibility.",
             f"Joint-position comparisons allow {settings['joint_position_tolerance_rad']:g} rad numerical tolerance.",
             "Velocity uses source-time intervals; acceleration uses interval midpoints with nearest-value endpoints.",
             "Frame speed checks both incident intervals. No derivatives cross region boundaries.",
             "Collision checks use the actual URDF collision meshes at saved frames, with structural and documented asset exclusions.",
             "This does not test inter-frame collisions, scene contact, torque or dynamics. Scores do not replace prior demo gates.",
             "Error/motion summaries use finite samples and report exclusions in score.json; score denominators retain failures.", ""]
    if settings.get("joint_acceleration_limits_rad_s2"):
        lines += [f"Per-joint acceleration overrides (rad/s²): `{settings['joint_acceleration_limits_rad_s2']}`.", ""]
    if definition:
        lines += [f"Source: `{definition['source_run_id']}`; {definition['frame_count']} source frames; regions `{definition['regions']}`.",
                  "Full definition: [benchmark.json](benchmark.json). Changes require consistent rescoring or a separate benchmark directory.", ""]
    lines += ["## Scoreboard", "", "| Configuration | Total /100 | Position /25 | Orientation /25 | Joint feasibility /25 | Collision-free /25 | Solve (s) |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]

    def fmt(value):
        return "N/A" if value is None else f"{value:.3f}"

    ranked = sorted(entries, key=lambda e: -(e[2]["score"] if e[2] and e[2]["score"] is not None else -1))
    for slug, experiment, score in ranked:
        if score:
            points = [score["score"], *[r["score"] for r in score["components"].values()], score["solve_s"]]
            lines.append(f"| [{score['name']}]({slug}/score.json) | " + " | ".join(map(fmt, points)) + " |")
        else:
            lines.append(f"| {experiment['name']} ({experiment['status']}) | — | — | — | — | — | — |")
    lines += ["", "## Diagnostics", "", "| Configuration | Velocity RMS / P95 (rad/s) | Acceleration RMS / P95 (rad/s²) | Position median / P95 (mm) | Orientation median / P95 (°) |",
              "| --- | ---: | ---: | ---: | ---: |"]
    for slug, experiment, score in ranked:
        if not score:
            continue
        m = score["metrics"]
        values = []
        for key, central, scale in (("joint_velocity_rad_s", "rms", 1), ("joint_acceleration_rad_s2", "rms", 1),
                                    ("position_error_m", "median", 1000), ("orientation_error_degrees", "median", 1)):
            values.append(" / ".join(fmt(m[key][k] * scale if m[key][k] is not None else None) for k in (central, "p95")))
        lines.append(f"| {score['name']} | " + " | ".join(values) + " |")
    lines += ["", "## Configuration explanations and preserved runs", ""]
    for slug, experiment, score in entries:
        lines += [f"### {experiment['name']}", "", experiment["description"], "",
                  f"[Settings]({slug}/config.json) · [Experiment]({slug}/experiment.json) · [Log]({slug}/run.log)"]
        if score:
            lines += [f"[Trajectory report]({slug}/trajectory/retargeting_report.json) · [Trajectory arrays]({slug}/trajectory/trajectory_retargeted.npz) · [Frame metrics]({slug}/benchmark_frame_metrics.npz)",
                      f"Excluded source frames: {score['excluded_frames']}; invalid mapped observations: {score['mapping_invalid_observations']}; missing robot frames: {score['missing_robot_frames']}.",
                      f"Raw-target errors and opening error, per-joint motion, exact score numerators/denominators, limits and collision pairs: [score.json]({slug}/score.json).",
                      f"Viewer: `PYTHONPATH=src .venv-workspace/bin/python scripts/view_retargeting.py {root / slug / 'trajectory'}`"]
        lines.append("")
    (root / "REPORT.md").write_text("\n".join(lines) + "\n")
