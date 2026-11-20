"""Initial-pose alignment and pairwise disagreement, without trajectory fitting."""

from itertools import combinations

import numpy as np


def initial_basis(up_camera):
    """Map initial OpenCV camera vectors to Z-up, horizontal-forward +X."""
    up = np.asarray(up_camera, dtype=float)
    if up.shape != (3,) or not np.isfinite(up).all() or np.linalg.norm(up) < 1e-8:
        raise ValueError("Expected a finite nonzero camera UP vector")
    up = up / np.linalg.norm(up)
    forward = np.array([0., 0., 1.])
    x = forward - np.dot(forward, up) * up
    fallback = np.linalg.norm(x) < 1e-6
    if fallback:
        right = np.array([1., 0., 0.])
        x = right - np.dot(right, up) * up
    x /= np.linalg.norm(x)
    return np.stack([x, np.cross(up, x), up]), fallback


def align_trajectory(poses, scale, up_camera, joints_camera_m, observed):
    """Return camera/hand geometry in the common initial frame.

    poses: [T,4,4] camera-to-world with raw translation units; scale: metres/unit.
    joints_camera_m: [T,2,J,3], already metric; never scale hand dimensions.
    observed: [T,2]. Missing cameras/hands stay NaN. Reference frame is always 0.
    """
    poses = np.asarray(poses, dtype=float)
    joints = np.asarray(joints_camera_m, dtype=float)
    observed = np.asarray(observed)
    if (poses.ndim != 3 or poses.shape[1:] != (4, 4) or joints.ndim != 4
            or joints.shape[:2] != (len(poses), 2) or joints.shape[-1] != 3
            or observed.shape != (len(poses), 2) or observed.dtype != bool):
        raise ValueError("Mismatched camera, joint or observation shapes")
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError("Metric scale must be finite and positive")
    camera_valid = np.isfinite(poses).all(axis=(1, 2))
    if not camera_valid[0]:
        raise ValueError("Initial camera pose is missing; do not silently shift the reference frame")
    rotation = poses[camera_valid, :3, :3]
    if (not np.allclose(rotation @ rotation.transpose(0, 2, 1), np.eye(3), atol=2e-4, rtol=0)
            or not np.allclose(np.linalg.det(rotation), 1, atol=2e-4, rtol=0)
            or not np.allclose(poses[camera_valid, 3], [0, 0, 0, 1], atol=1e-6, rtol=0)):
        raise ValueError("Camera transforms must be proper rigid transforms")
    basis, fallback = initial_basis(up_camera)
    world_to_aligned = basis @ poses[0, :3, :3].T
    aligned = np.full_like(poses, np.nan)
    aligned[camera_valid] = np.eye(4)
    aligned[camera_valid, :3, :3] = world_to_aligned @ rotation
    aligned[camera_valid, :3, 3] = (poses[camera_valid, :3, 3] - poses[0, :3, 3]) @ world_to_aligned.T * scale
    hand_valid = observed & camera_valid[:, None] & np.isfinite(joints).all(axis=(2, 3))
    aligned_joints = np.einsum("tij,thkj->thki", aligned[:, :3, :3], joints) + aligned[:, None, None, :3, 3]
    aligned_joints[~hand_valid] = np.nan
    return {"camera_pose": aligned, "camera_valid": camera_valid, "joints_m": aligned_joints,
            "hand_valid": hand_valid, "basis": basis, "heading_fallback": fallback}


def pairwise_disagreement(trajectories, timestamps):
    """Compare all pairs on one common support per camera/hand channel.

    Sums/means/RMSE are Euclidean position distances in metres, not ground-truth
    errors or path length. No missing-data interpolation or best-fit registration.
    """
    times = np.asarray(timestamps, dtype=float)
    if times.ndim != 1 or not np.isfinite(times).all() or np.any(np.diff(times) <= 0):
        raise ValueError("Timestamps must be finite and strictly increasing")
    names = list(trajectories)
    if len(names) < 2:
        raise ValueError("At least two trajectories are required")
    for item in trajectories.values():
        if len(item["camera_pose"]) != len(times):
            raise ValueError("Trajectories must match the complete shared timeline")
    camera_common = np.logical_and.reduce([v["camera_valid"] for v in trajectories.values()])
    hands_common = np.logical_and.reduce([v["hand_valid"] for v in trajectories.values()])
    records, curves = [], {}
    for channel, support in [("camera", camera_common), ("left_wrist", hands_common[:, 0]),
                             ("right_wrist", hands_common[:, 1])]:
        for a, b in combinations(names, 2):
            if channel == "camera":
                pa, pb = [trajectories[n]["camera_pose"][:, :3, 3] for n in (a, b)]
            else:
                hand = int(channel == "right_wrist")
                pa, pb = [trajectories[n]["joints_m"][:, hand, 0] for n in (a, b)]
            distance = np.full(len(times), np.nan)
            distance[support] = np.linalg.norm(pa[support] - pb[support], axis=1)
            values = distance[support]
            if not np.isfinite(values).all():
                raise ValueError("Valid samples contain nonfinite positions")
            records.append({"channel": channel, "method_a": a, "method_b": b,
                            "samples": len(values), "coverage": len(values) / len(times),
                            "sum_m": float(values.sum()) if len(values) else None,
                            "mean_m": float(values.mean()) if len(values) else None,
                            "rmse_m": float(np.sqrt(np.mean(values ** 2))) if len(values) else None})
            curves[f"{channel}__{a}__{b}"] = distance
    return records, curves


def depth_to_droid_grid(depth, source_shape):
    """Match DROID's resize then bottom/right crop, preserving ray coordinates."""
    import cv2

    height, width = source_shape
    ratio = np.sqrt((384 * 512) / (height * width))
    resized_h, resized_w = int(height * ratio), int(width * ratio)
    return cv2.resize(np.asarray(depth), (resized_w, resized_h))[:resized_h - resized_h % 8, :resized_w - resized_w % 8]


def evaluate(settings, output, report):
    """Write numeric comparison, inspectable artifacts and static review figures."""
    import csv
    import time
    from egocentric_pipeline.run_metadata import read_json, write_json
    from egocentric_pipeline.visualization.trajectory_comparison import plot_comparison, plot_shared_hands

    started = time.perf_counter()
    inputs, gravity, scales = [read_json(output / name) for name in ("input.json", "gravity.json", "scales.json")]
    hand = np.load(output / "hands.npz")
    trajectories = {}
    for name in ("hawor", "lingbot", "amb3r"):
        raw = np.load(output / f"{name}_raw.npz")
        if not np.array_equal(raw["frame_index"], inputs["frame_index"]):
            raise ValueError(f"{name} frame indices do not match the input")
        trajectories[name] = align_trajectory(raw["poses"], scales[name]["scale"], gravity["up_camera"],
                                               hand["joints_camera_m"], hand["valid"])
        np.savez(output / f"{name}_aligned.npz", **trajectories[name],
                 frame_index=inputs["frame_index"], timestamp_s=inputs["timestamp_s"],
                 source_timestamp_s=inputs["source_timestamp_s"])
    records, curves = pairwise_disagreement(trajectories, inputs["timestamp_s"])
    with (output / "disagreement.csv").open("x") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    np.savez(output / "disagreement_curves.npz", timestamp_s=inputs["timestamp_s"], **curves)
    numeric_s = time.perf_counter() - started
    timings = {stage: read_json(output / f"{stage}_timing.json")
               for stage in ("hands", "gravity", "hawor", "metric_depth", "lingbot", "amb3r", "scale")}
    shared_s = timings["hands"]["wall_time_s"] + timings["gravity"]["wall_time_s"]
    runtime = []
    for name in trajectories:
        depth_s = timings["metric_depth"]["wall_time_s"] if name != "amb3r" else 0
        backend_s = timings[name]["wall_time_s"]
        scale_s = scales[name]["fit_time_s"]
        total = shared_s + depth_s + backend_s + scale_s
        runtime.append({"method": name, "backend_stage_s": backend_s, "shared_hands_gravity_s": shared_s,
                        "metric3d_s": depth_s, "scale_fit_s": scale_s, "assembled_total_s": total,
                        "backend_effective_fps": len(inputs["frame_index"]) / backend_s,
                        "assembled_effective_fps": len(inputs["frame_index"]) / total})
    write_json(output / "comparison.json", {"disagreement": records, "runtime": runtime, "scales": scales,
               "timing_scope": "Single runs; assembled stage totals; downloads, input verification, plots and this evaluation excluded.",
               "shared_work": "Hands and initial-frame gravity once; Metric3D once, charged to HaWoR and LingBot only.",
               "limitations": ["Pairwise disagreement is not ground-truth accuracy.", "Metric depth and focal length are model/prior estimates.",
                               "Initial-frame leveling does not correct later gravity drift.", "Native model input sizes/preprocessing differ; no precision or quality tuning sweep."]})
    with (output / "runtime.csv").open("x") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(runtime[0])); writer.writeheader(); writer.writerows(runtime)
    plot_comparison(output, trajectories, np.asarray(inputs["timestamp_s"]), curves, runtime)
    plot_shared_hands(output, hand, settings["focal_px"])
    report.update(numeric_evaluation_s=numeric_s, rendering_s=time.perf_counter() - started - numeric_s,
                  pair_channel_comparisons=len(records))
