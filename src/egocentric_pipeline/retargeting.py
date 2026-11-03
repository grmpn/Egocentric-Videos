"""Reusable aligned-trajectory → fixed-base regions and positional IK workflow."""

import importlib.metadata
from pathlib import Path
import sys
import time

import numpy as np

from .base_placement import evaluate_placement, optimize_base
from .manipulation_regions import camera_segments, expand_region, frame_edges, interval_metrics, select_disjoint_regions
from .positional_ik import solve_trajectory
from .robot_workspace import arm_parameters, load_robot, position_target, verify_asset_source
from .run_metadata import read_json, utc_now, write_json
from .workspace import WorkspaceGrid


def validate_settings(settings):
    for key in ("camera_displacement_m", "camera_sustain_s", "minimum_episode_s", "workspace_margin_m",
                "ik_tolerance_m", "joint_jump_report_rad"):
        if not np.isfinite(settings[key]) or settings[key] <= 0:
            raise ValueError(f"{key} must be positive finite")
    for key in ("camera_smoothing_sigma_s", "maximum_gap_s"):
        if not np.isfinite(settings[key]) or settings[key] < 0:
            raise ValueError(f"{key} must be nonnegative finite seconds")
    for key in ("optimizer_iterations", "optimizer_population", "ik_attempts", "ik_iterations", "torch_threads"):
        if type(settings[key]) is not int or settings[key] < 1:
            raise ValueError(f"{key} must be a positive integer")
    if type(settings["seed"]) is not int or settings["seed"] < 0:
        raise ValueError("seed must be a nonnegative integer")
    if not .95 <= settings["minimum_feasible_fraction"] < 1:
        raise ValueError("minimum_feasible_fraction must be in [0.95, 1); acceptance is strictly greater")
    if settings["workspace_margin_m"] < .03 or settings["ik_tolerance_m"] > .005:
        raise ValueError("Approved acceptance requires at least 3 cm margin and at most 5 mm IK error")


def load_alignment(directory):
    """Consume the completed Part 1 contract and verify its prepared RGB timeline."""
    directory = Path(directory).resolve()
    report = read_json(directory / "alignment_report.json")
    if report["status"] != "completed" or report["hand_order"] != ["left", "right"]:
        raise ValueError("Require a completed left/right Part 1 alignment; inspect its report")
    with np.load(directory / "trajectory_aligned.npz", allow_pickle=False) as data:
        arrays = {key: data[key] for key in data.files}
    times, valid = arrays["timestamp_s"], arrays["export_valid"]
    frame_edges(times)
    n = len(times)
    if valid.shape != (n, 2) or valid.dtype != bool:
        raise ValueError("export_valid must be boolean [T,2] in left/right order")
    infilled = arrays.get("motion_infilled")
    if infilled is None or infilled.shape != (n, 2) or infilled.dtype != bool:
        raise ValueError("motion_infilled must be boolean [T,2]; regenerate alignment with hand provenance")
    wrists = arrays["wrist_position_aligned_m"]
    if wrists.shape != (n, 2, 3) or not np.isfinite(wrists[valid & ~infilled]).all() or not np.isnan(wrists[~valid]).all():
        raise ValueError("Physical wrists must be finite for non-infilled observations and NaN where export-invalid")
    rotation = arrays["rotation_aligned_from_world"]
    if (rotation.shape != (3, 3) or not np.allclose(rotation @ rotation.T, np.eye(3), atol=1e-8)
            or not np.isclose(np.linalg.det(rotation), 1, atol=1e-8)):
        raise ValueError("Aligned-from-world rotation must be proper and orthonormal")
    clip = read_json(report["inputs"]["clip_metadata"]["path"])
    mapping = clip["frames"]["mapping"]
    if (clip["prepared"]["frame_count"] != n or not np.array_equal(arrays["frame_index"], np.arange(n))
            or not np.array_equal(times, [f["timestamp_s"] for f in mapping])
            or not np.array_equal(arrays["source_timestamp_s"], [f["source_timestamp_s"] for f in mapping])):
        raise ValueError("Aligned trajectories and prepared RGB/source timestamps disagree")
    return arrays, report, clip


def save_retargeting(output, arrays, report, clip, *, render_video=True):
    """Shared lossless export and optional source-synchronized review artifacts."""
    from .retargeting_visualization import annotate_video

    started = time.perf_counter()
    with (Path(output) / "trajectory_retargeted.npz").open("xb") as stream:
        np.savez_compressed(stream, **arrays)
    with np.load(Path(output) / "trajectory_retargeted.npz", allow_pickle=False) as restored:
        if any(restored[key].dtype != value.dtype or restored[key].tobytes() != value.tobytes()
               for key, value in arrays.items()):
            raise ValueError("Retargeted export failed exact reload verification")
    report["export_reload_exact"] = True
    report.setdefault("timing", {})["export_s"] = time.perf_counter() - started
    started = time.perf_counter()
    if render_video:
        annotate_video(output, arrays, report, clip)
    report["timing"]["visualization_s"] = time.perf_counter() - started
    report["video_rendered"] = render_video


def retarget_trajectory(alignment_directory, workspace_directory, output_directory, settings, asset_root=None,
                       *, regions_only=False, render_video=True):
    """Save all candidate evidence plus disjoint retained regions and IK witnesses."""
    import torch

    validate_settings(settings)
    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    report = {"schema_version": 3, "method": "workspace", "regions_only": regions_only,
              "status": "running", "started_at": utc_now(),
              "command": [sys.executable, *sys.argv], "settings": settings,
              "alignment_directory": str(Path(alignment_directory).resolve()),
              "workspace_directory": str(Path(workspace_directory).resolve()),
              "hand_order": ["left", "right"], "manual_review": "pending",
              "observation_policy": "export_valid AND NOT motion_infilled; infilled hands are missing data",
              "units": {"position": "metres (input scale unverified)", "joint_angles": "radians", "time": "seconds"},
              "transform_convention": "column vectors; T_destination_from_source; Z-up yaw-only base rotation",
              "invalid_geometry": "NaN for missing wrists and missing/failed IK; gaps are not interpolated",
              "interval_convention": "half-open frame indices; last-frame duration is median dt",
              "limitations": "Position-only heuristic/IK; gravity and metric scale unverified. No collision, orientation, dynamic-limit or physical-floor certification."}
    write_json(output / "retargeting_report.json", report)
    try:
        torch.set_num_threads(settings["torch_threads"])
        arrays, alignment_report, clip = load_alignment(alignment_directory)
        workspace_report = read_json(Path(workspace_directory) / "workspace_report.json")
        if workspace_report["status"] != "completed" or workspace_report["hand_order"] != report["hand_order"]:
            raise ValueError("Require completed left/right workspace output")
        robot_settings = workspace_report["settings"]
        assets = Path(asset_root or workspace_report["asset_root"]).resolve()
        robot = load_robot(verify_asset_source(assets, robot_settings), robot_settings["base_frame"])
        target_frames = robot_settings.get("target_frames", robot_settings["tool_frames"])
        for hand, arm in enumerate(workspace_report["arms"]):
            if arm.get("target_frame", arm["tool_frame"]) != target_frames[hand]:
                raise ValueError("Workspace endpoint disagrees with its settings; rebuild the workspace")
        locked = {joint.name: 0. for joint in robot.joint_list}
        for hand in range(2):
            chain, tool, _ = arm_parameters(robot, robot_settings["tool_frames"][hand], robot_settings["arm_joints"][hand])
            active, _ = position_target(chain, tool, target_frames[hand])
            for link in active:
                locked.pop(link.joint.name)
        grid = WorkspaceGrid.load(Path(workspace_directory) / "workspace_grid.npz")
        if grid.spacing_m != robot_settings["voxel_size_m"]:
            raise ValueError("Workspace grid spacing disagrees with its recorded settings")
        report.update(asset_root=str(assets), robot_settings=robot_settings, target_frames=target_frames,
                      locked_joint_positions_rad=locked,
                      source_run_id=alignment_report["source_run_id"],
                      prepared_video=alignment_report["inputs"]["prepared_video"]["path"],
                      packages={p: importlib.metadata.version(p) for p in ("scikit-robot", "numpy", "scipy", "torch", "viser", "Pillow")})
        times, valid = arrays["timestamp_s"], arrays["export_valid"] & ~arrays["motion_infilled"]
        observed, edges = valid.any(axis=1), frame_edges(times)
        wrists = arrays["wrist_position_aligned_m"].copy()
        wrists[~valid] = np.nan
        smooth, seeds = camera_segments(arrays["camera_position_aligned_m"], times, settings)
        report["timing"] = {"loading_s": time.perf_counter() - started}
        solve_started = time.perf_counter()
        candidates, evaluations, transforms = [], [], []
        for seed_index, seed in enumerate(seeds):
            if not seed["retained"]:
                continue
            if not observed[seed["start"]:seed["stop"]].any():
                seed["reason"] = "no_observed_wrists"
                continue
            sl = slice(seed["start"], seed["stop"])
            transform, optimization = optimize_base(wrists[sl], valid[sl], grid, settings, seed_index)
            evaluation = evaluate_placement(wrists, valid, transform, grid, settings["workspace_margin_m"])
            expanded = (interval_metrics(seed["start"], seed["stop"], evaluation["frame_passed"], observed, edges, settings)
                        if regions_only else expand_region(seed, evaluation["frame_passed"], observed, edges, settings))
            candidate = {"candidate_id": len(candidates), "seed_index": seed_index, "seed": seed,
                         "optimization": optimization, "expanded": expanded,
                         "selection": "no_qualifying_expansion" if expanded is None else "pending"}
            candidates.append(candidate)
            evaluations.append(evaluation)
            transforms.append(transform)
            print(f"Seed {seed_index} [{seed['start']}, {seed['stop']}): expanded {expanded}", flush=True)
        report["timing"]["placement_s"] = time.perf_counter() - solve_started
        if regions_only:
            selected = candidates
            for candidate in selected:
                candidate.update(retained=candidate["expanded"], selection="heuristic_region")
        else:
            selected = select_disjoint_regions(candidates, evaluations, observed, edges, settings)
        ik_started = time.perf_counter()
        n, joints = len(times), len(robot_settings["arm_joints"][0])
        derived = {"retarget_valid": valid, "camera_position_smoothed_m": smooth,
                   "episode_id": np.full(n, -1, np.int32), "wrist_position_base_m": np.full((n, 2, 3), np.nan),
                   "joint_angles_rad": np.full((n, 2, joints), np.nan), "tcp_position_base_m": np.full((n, 2, 3), np.nan),
                   "target_position_base_m": np.full((n, 2, 3), np.nan),
                   "ik_residual_m": np.full((n, 2), np.nan), "ik_success": np.zeros((n, 2), bool),
                   "ik_attempts": np.zeros((n, 2), np.int32), "joint_step_rad": np.full((n, 2), np.nan),
                   "joint_jump": np.zeros((n, 2), bool)}
        episodes = []
        for episode_id, candidate in enumerate(selected):
            cid, region = candidate["candidate_id"], candidate["retained"]
            sl = slice(region["start"], region["stop"])
            points = evaluations[cid]["wrist_position_base_m"][sl]
            ik = solve_trajectory(robot, points, valid[sl], robot_settings, settings)
            passed = observed[sl] & (ik["ik_success"] | ~valid[sl]).all(axis=1)
            ik_metrics = interval_metrics(0, len(passed), passed, observed[sl], edges[region["start"]:region["stop"] + 1], settings)
            ik_metrics.update(start=region["start"], stop=region["stop"])
            combined = interval_metrics(0, len(passed), passed & evaluations[cid]["frame_passed"][sl],
                                        observed[sl], edges[region["start"]:region["stop"] + 1], settings)
            combined.update(start=region["start"], stop=region["stop"])
            episode = {"episode_id": episode_id, "candidate_id": cid, "sdf": region, "ik": ik_metrics,
                       "combined": combined, "demonstrated": bool(region["accepted"] and ik_metrics["accepted"] and combined["accepted"]),
                       "observed_hand_frames": valid[sl].sum(axis=0).tolist(),
                       "ik_successful_hand_frames": ik["ik_success"].sum(axis=0).tolist(),
                       "max_fk_residual_m": float(np.nanmax(ik["ik_residual_m"])) if ik["ik_success"].any() else None,
                       "joint_jump_frames": int(ik["joint_jump"].any(axis=1).sum())}
            episodes.append(episode)
            derived["episode_id"][sl] = episode_id
            derived["wrist_position_base_m"][sl] = points
            for key, value in ik.items():
                derived[key][sl] = value
            print(f"Episode {episode_id}: SDF {region['passing_fraction']:.3%}, IK {ik_metrics['passing_fraction']:.3%}, demonstrated={episode['demonstrated']}", flush=True)
        transform_array = np.array(transforms).reshape(-1, 4, 4)
        world_to_aligned = np.eye(4)
        world_to_aligned[:3, :3] = arrays["rotation_aligned_from_world"]
        derived.update(transform_base_from_aligned=transform_array,
                       transform_base_from_world=transform_array @ world_to_aligned,
                       transform_aligned_from_base=np.linalg.inv(transform_array),
                       candidate_distance_m=np.array([e["distance_m"] for e in evaluations]).reshape(-1, n, 2),
                       candidate_query_valid=np.array([e["query_valid"] for e in evaluations], dtype=bool).reshape(-1, n, 2),
                       candidate_hand_passed=np.array([e["hand_passed"] for e in evaluations], dtype=bool).reshape(-1, n, 2),
                       candidate_frame_passed=np.array([e["frame_passed"] for e in evaluations], dtype=bool).reshape(-1, n))
        report["timing"].update(ik_s=time.perf_counter() - ik_started, solve_s=time.perf_counter() - solve_started)
        report.update(seeds=seeds, candidates=candidates, episodes=episodes,
                      demo_accepted=any(e["demonstrated"] for e in episodes),
                      source_fields_preserved=list(arrays), frame_count=n)
        save_retargeting(output, dict(arrays, **derived), report, clip, render_video=render_video)
        report.update(status="completed", finished_at=utc_now(), wall_time_s=time.perf_counter() - started)
        write_json(output / "retargeting_report.json", report, overwrite=True)
        return report
    except Exception as error:
        report.update(status="failed", error=f"{type(error).__name__}: {error}", finished_at=utc_now())
        write_json(output / "retargeting_report.json", report, overwrite=True)
        raise
