"""Repeat both production solvers on identical unexpanded camera regions."""

from pathlib import Path
import platform
import time

import numpy as np
from scipy.spatial.transform import Rotation

from .joint_retargeting import joint_retarget_trajectory
from .pose_retargeting import PoseModel, rotation_error
from .retargeting import retarget_trajectory
from .robot_workspace import load_robot, verify_asset_source
from .run_metadata import read_json, utc_now, write_json


def finite_summary(values):
    values = np.asarray(values)
    values = values[np.isfinite(values)]
    return {"samples": int(values.size), "rms": float(np.sqrt(np.mean(values**2))) if values.size else None,
            "median": float(np.median(values)) if values.size else None,
            "p95": float(np.percentile(values, 95)) if values.size else None,
            "max": float(np.max(values)) if values.size else None}


def compare_quality(directory, model, palm_offsets, settings):
    """Measure both outputs against the same wrist-pose gate without refitting."""
    report = read_json(Path(directory) / "retargeting_report.json")
    with np.load(Path(directory) / "trajectory_retargeted.npz", allow_pickle=False) as f:
        a = dict(f)
    observed = a["export_valid"] & (a["episode_id"][:, None] >= 0)
    solved = np.isfinite(a["joint_angles_rad"]).all(axis=-1) & observed
    orientation_error = np.full(observed.shape, np.nan)
    camera_error = np.full(len(observed), np.nan)
    camera_position_error = np.full(len(observed), np.nan)
    q = np.full((len(observed), 16), np.nan)
    q[:, :14] = a["joint_angles_rad"].reshape(-1, 14)
    for e in report["episodes"]:
        frames = np.flatnonzero(a["episode_id"] == e["episode_id"])
        cid = e["candidate_id"]
        rotation = a["transform_base_from_aligned"][cid, :3, :3]
        q[frames, 14:] = a["neck_joint_angles_rad"][frames] if "neck_joint_angles_rad" in a else 0.
        # Fill only for FK evaluation. Missing/failed samples remain excluded
        # from pose evidence and from derivative statistics below.
        _, actual, _, head_position, head = model.forward(np.nan_to_num(q[frames]))
        for h in range(2):
            mask = solved[frames, h]
            target = rotation @ Rotation.from_rotvec(
                a["root_orientation_aligned_axis_angle"][frames[mask], h]).as_matrix() @ palm_offsets[h]
            orientation_error[frames[mask], h] = rotation_error(actual[mask, h], target)
        camera_error[frames] = rotation_error(head, rotation @ a["camera_rotation_aligned_from_camera"][frames])
        target_position = (a["camera_position_aligned_m"][frames] @ rotation.T
                           + a["transform_base_from_aligned"][cid, :3, 3])
        camera_position_error[frames] = np.linalg.norm(head_position - target_position, axis=-1)
    passing = solved & (a["ik_residual_m"] <= settings["ik_tolerance_m"]) & (
        orientation_error <= settings["orientation_tolerance_rad"])
    frame_passed = observed.any(axis=1) & (passing | ~observed).all(axis=1)
    dt = np.diff(a["timestamp_s"])
    velocity = np.diff(q, axis=0) / dt[:, None]
    velocity[a["episode_id"][1:] != a["episode_id"][:-1]] = np.nan
    acceleration = np.diff(velocity, axis=0) / ((dt[1:] + dt[:-1]) / 2)[:, None]
    return {"frames_processed": int((a["episode_id"] >= 0).sum()),
            "observed_hand_frames": int(observed.sum()), "solved_observed_hand_frames": int(solved.sum()),
            "common_pose_passing_frames": int(frame_passed.sum()),
            "observed_frames": int(observed.any(axis=1).sum()),
            "position_m": finite_summary(a["ik_residual_m"][solved]),
            "orientation_deg": finite_summary(np.rad2deg(orientation_error)),
            "head_orientation_deg": finite_summary(np.rad2deg(camera_error)),
            "camera_position_m": finite_summary(camera_position_error),
            "posture_deviation_rad": finite_summary(np.abs(q - model.neutral)),
            "joint_velocity_rad_s": finite_summary(velocity),
            "joint_acceleration_rad_s2": finite_summary(acceleration),
            "motion_samples": "finite consecutive joint samples within regions; predictions included for joint method"}


def compare_retargeting(alignment, workspace, output_directory, joint_settings, baseline_settings,
                        robot_settings, asset_root, repeats=3):
    """Sequential alternating runs; loading/rendering excluded from solve time."""
    if type(repeats) is not int or repeats < 3:
        raise ValueError("The approved comparison requires at least three runs per method")
    for key in ("camera_smoothing_sigma_s", "camera_displacement_m", "camera_sustain_s", "minimum_episode_s"):
        if joint_settings[key] != baseline_settings[key]:
            raise ValueError(f"Both methods must use identical segmentation settings: {key}")
    workspace_report = read_json(Path(workspace) / "workspace_report.json")
    for key in ("asset_revision", "urdf", "base_frame", "target_frames", "tool_frames", "arm_joints"):
        if workspace_report["settings"].get(key) != robot_settings[key]:
            raise ValueError(f"Comparison requires the same robot convention: {key}")
    output = Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    report = {"status": "running", "started_at": utc_now(), "repeats": repeats,
              "machine": {"platform": platform.platform(), "processor": platform.processor()},
              "runs": [], "workspace_construction_s": workspace_report["wall_time_s"],
              "workspace_construction_source": str(Path(workspace).resolve() / "workspace_report.json"),
              "workspace_construction_note": "Historical one-time build on this machine; reused, not timed again.",
              "comparison_boundary": "Same heuristic regions and input; different objectives: baseline position-only SDF+IK versus wrist/camera pose and temporal optimization. Not an optimizer-only speed benchmark."}
    write_json(output / "comparison_report.json", report)
    try:
        expected_regions = None
        for repeat in range(repeats):
            order = ("joint", "workspace") if repeat % 2 == 0 else ("workspace", "joint")
            for method in order:
                directory = output / f"{method}-{repeat + 1:02d}"
                if method == "joint":
                    run = joint_retarget_trajectory(alignment, directory, joint_settings, robot_settings,
                                                     asset_root, render_video=repeat == 0)
                else:
                    run = retarget_trajectory(alignment, workspace, directory, baseline_settings, asset_root,
                                              regions_only=True, render_video=repeat == 0)
                regions = [(s["start"], s["stop"]) for s in run["seeds"] if s["retained"]]
                if expected_regions is None:
                    expected_regions = regions
                if regions != expected_regions:
                    raise ValueError("The two methods processed different heuristic regions")
                report["runs"].append({"method": method, "repeat": repeat + 1,
                    "directory": str(directory), "timing": run["timing"], "demo_accepted": run["demo_accepted"]})
                write_json(output / "comparison_report.json", report, overwrite=True)
        robot = load_robot(verify_asset_source(asset_root, robot_settings), robot_settings["base_frame"])
        model = PoseModel(robot, robot_settings, joint_settings)
        with np.load(output / "joint-01/trajectory_retargeted.npz", allow_pickle=False) as arrays:
            offsets = arrays["rotation_mano_from_palm"]
        for run in report["runs"]:
            run["quality"] = compare_quality(run["directory"], model, offsets, joint_settings)
        counts = {run["quality"]["frames_processed"] for run in report["runs"]}
        if len(counts) != 1:
            raise ValueError("The two methods solved different frame counts")
        report["solve_time_s"] = {}
        for method in ("joint", "workspace"):
            times = [r["timing"]["solve_s"] for r in report["runs"] if r["method"] == method]
            report["solve_time_s"][method] = {"median": float(np.median(times)), "min": min(times), "max": max(times)}
        report.update(status="completed", finished_at=utc_now(), wall_time_s=time.perf_counter() - started,
                      regions=expected_regions, frames_processed=counts.pop())
        write_json(output / "comparison_report.json", report, overwrite=True)
        return report
    except (Exception, KeyboardInterrupt) as error:
        report.update(status="failed", error=f"{type(error).__name__}: {error}", finished_at=utc_now())
        write_json(output / "comparison_report.json", report, overwrite=True)
        raise
