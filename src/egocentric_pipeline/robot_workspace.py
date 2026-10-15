"""Robot-model FK sampling and reloadable positional workspace preparation."""

import importlib.metadata
from pathlib import Path
import resource
import subprocess
import sys
import time

import numpy as np

from .run_metadata import utc_now, write_json
from .workspace import WorkspaceGrid, build_grid


HAND_ORDER = ("left", "right")


def validate_settings(settings):
    for key in ("samples_per_arm", "fk_batch_size", "held_out_samples_per_arm", "fk_check_samples_per_arm",
                "padding_cells", "viewer_max_points_per_arm"):
        if type(settings[key]) is not int or settings[key] < 1:
            raise ValueError(f"{key} must be a positive integer")
    if settings["samples_per_arm"] > 1_000_000:
        raise ValueError("samples_per_arm exceeds the approved 1,000,000 maximum")
    if type(settings["seed"]) is not int or settings["seed"] < 0:
        raise ValueError("seed must be a nonnegative integer")
    for key in ("voxel_size_m", "fk_tolerance_m"):
        if not np.isfinite(settings[key]) or settings[key] <= 0:
            raise ValueError(f"{key} must be positive and finite")
    if len(settings["tool_frames"]) != 2 or len(set(settings["tool_frames"])) != 2:
        raise ValueError("Specify distinct left/right tool frames")
    if len(settings["arm_joints"]) != 2 or any(len(j) != 7 for j in settings["arm_joints"]):
        raise ValueError("Specify seven joints in base-to-tool order for each arm")


def load_robot(urdf_path, base_frame):
    """Load native metre/radian URDF geometry; fix root and movable joints at zero."""
    from skrobot.model import RobotModel

    robot = RobotModel()
    robot.load_urdf_file(str(urdf_path))
    if robot.root_link.name != base_frame:
        raise ValueError(f"Expected fixed root {base_frame}, found {robot.root_link.name}")
    for joint in robot.joint_list:
        if not np.isfinite([joint.min_angle, joint.max_angle]).all() or not joint.min_angle <= 0 <= joint.max_angle:
            raise ValueError(f"Joint {joint.name} needs finite bounds containing the locked zero pose")
        joint.joint_angle(0.)
    return robot


def verify_asset_source(asset_root, settings):
    """Use the same pinned, unmodified model for numerical work and its viewer."""
    asset_root = Path(asset_root).resolve()
    revision = subprocess.check_output(["git", "-C", str(asset_root), "rev-parse", "HEAD"], text=True).strip()
    if revision != settings["asset_revision"]:
        raise ValueError(f"Robot assets must be checked out at {settings['asset_revision']}, found {revision}")
    result = subprocess.run(["git", "-C", str(asset_root), "diff", "--exit-code", "HEAD", "--", "assets"],
                            capture_output=True)
    if result.returncode:
        raise ValueError("Robot assets have tracked changes or cannot be checked; use a clean pinned checkout")
    return asset_root / settings["urdf"]


def arm_parameters(robot, tool_frame, joint_names):
    """Extract library FK parameters after checking the actual base-to-tool chain."""
    from skrobot.kinematics.differentiable import extract_fk_parameters

    links = {link.name: link for link in robot.link_list}
    if tool_frame not in links:
        raise ValueError(f"Missing tool frame {tool_frame}; check the configured URDF")
    tool = links[tool_frame]
    chain = []
    link = tool
    while link is not robot.root_link:
        joint = link.joint
        if joint.joint_type != "fixed":
            if joint.joint_type != "revolute" or getattr(joint, "mimic", None):
                raise ValueError("Workspace arm chains require independent bounded revolute joints")
            chain.append(link)
        link = joint.parent_link
    chain.reverse()
    if [link.joint.name for link in chain] != list(joint_names):
        raise ValueError(f"Configured arm joints do not match the chain to {tool_frame}")
    parameters = extract_fk_parameters(robot, chain, tool)
    lower, upper = np.asarray(parameters["joint_limits_lower"]), np.asarray(parameters["joint_limits_upper"])
    if not np.isfinite([lower, upper]).all() or np.any(lower >= upper):
        raise ValueError("All sampled joints need finite nondegenerate position bounds")
    return chain, tool, parameters


def sample_arm(robot, parameters, sample_count, seed, batch_size):
    """Uniform joint-space samples → [N,J] radians and [N,3] base-frame metres.

    Use the library's position-only batched FK. Its ReachabilityMap computes
    extra manipulability and chooses separate unpadded origins per arm, so the
    common lattice is constructed separately with NumPy.
    """
    from skrobot.kinematics.differentiable import forward_kinematics_ee_batched_numpy

    rng = np.random.default_rng(seed)
    angles = rng.uniform(parameters["joint_limits_lower"], parameters["joint_limits_upper"],
                         (sample_count, parameters["n_joints"]))
    positions = np.empty((sample_count, 3), dtype=np.float64)
    base = robot.root_link
    for start in range(0, sample_count, batch_size):
        world, _ = forward_kinematics_ee_batched_numpy(angles[start:start + batch_size], parameters)
        positions[start:start + batch_size] = (world - base.worldpos()) @ base.worldrot()
    if not np.isfinite(positions).all():
        raise ValueError("FK returned nonfinite positions; no workspace can be accepted")
    return angles, positions


def verify_fk(robot, chain, tool, parameters, angles, tolerance_m):
    """Compare batch FK with the ordinary mutable model, including joint bounds."""
    from skrobot.kinematics.differentiable import forward_kinematics_ee_batched_numpy

    lower, upper = parameters["joint_limits_lower"], parameters["joint_limits_upper"]
    checks = np.vstack((np.zeros(len(chain)), lower, upper, angles))
    batched, _ = forward_kinematics_ee_batched_numpy(checks, parameters)
    ordinary = []
    try:
        for q in checks:
            for link, angle in zip(chain, q):
                link.joint.joint_angle(float(angle))
            ordinary.append(tool.worldpos().copy())
    finally:
        for link in chain:
            link.joint.joint_angle(0.)
    error = float(np.max(np.linalg.norm(batched - ordinary, axis=1)))
    if error > tolerance_m:
        raise ValueError(f"Batched/ordinary FK mismatch {error:.3g} m exceeds {tolerance_m:g} m")
    return {"configurations_checked": len(checks), "max_position_error_m": error, "tolerance_m": tolerance_m}


def build_workspace(asset_root, output_directory, settings):
    """Run FK → occupancy → EDT, validate/reload, and save independent artifacts."""
    import torch

    validate_settings(settings)
    asset_root, output = Path(asset_root).resolve(), Path(output_directory).resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    report = {"status": "running", "started_at": utc_now(), "settings": settings,
              "command": [sys.executable, *sys.argv], "base_frame": settings["base_frame"],
              "hand_order": list(HAND_ORDER), "units": {"position": "metres", "joint_angles": "radians"},
              "packages": {p: importlib.metadata.version(p) for p in ("scikit-robot", "numpy", "scipy", "torch", "viser", "trimesh")},
              "limitations": "Sampled positional occupancy only; collision, orientation, simultaneous bimanual and trajectory feasibility are unverified."}
    write_json(output / "workspace_report.json", report)
    try:
        urdf = verify_asset_source(asset_root, settings)
        report["asset_root"], report["asset_revision"], report["urdf"] = str(asset_root), settings["asset_revision"], str(urdf)
        robot = load_robot(urdf, settings["base_frame"])
        report["locked_joint_positions_rad"] = {j.name: 0. for j in robot.joint_list
                                               if j.name not in sum(settings["arm_joints"], [])}
        clouds, held_out, arm_reports = [], [], []
        for hand, name in enumerate(HAND_ORDER):
            chain, tool, parameters = arm_parameters(robot, settings["tool_frames"][hand], settings["arm_joints"][hand])
            arm_started = time.perf_counter()
            q, points = sample_arm(robot, parameters, settings["samples_per_arm"],
                                   np.random.SeedSequence([settings["seed"], hand, 0]), settings["fk_batch_size"])
            hq, hp = sample_arm(robot, parameters, settings["held_out_samples_per_arm"],
                               np.random.SeedSequence([settings["seed"], hand, 1]), settings["fk_batch_size"])
            ids = np.linspace(0, len(q) - 1, min(len(q), settings["fk_check_samples_per_arm"]), dtype=int)
            check = verify_fk(robot, chain, tool, parameters, q[ids], settings["fk_tolerance_m"])
            arrays = {"positions_base_m": points, "joint_angles_rad": q,
                      "held_out_positions_base_m": hp, "held_out_joint_angles_rad": hq,
                      "joint_names": np.array(settings["arm_joints"][hand])}
            with (output / f"samples_{name}.npz").open("xb") as stream:
                np.savez(stream, **arrays)
            with np.load(output / f"samples_{name}.npz", allow_pickle=False) as reloaded:
                if any(not np.array_equal(value, reloaded[key]) for key, value in arrays.items()):
                    raise ValueError(f"{name} sample export failed exact reload verification")
            arm_reports.append({"hand": name, "tool_frame": tool.name, "joint_names": settings["arm_joints"][hand],
                                "lower_rad": parameters["joint_limits_lower"].tolist(),
                                "upper_rad": parameters["joint_limits_upper"].tolist(),
                                "samples": len(q), "held_out_samples": len(hp), "fk_check": check,
                                "wall_time_s": time.perf_counter() - arm_started})
            clouds.append(points)
            held_out.append(hp)
            print(f"{name}: {len(q):,} FK samples, max FK check error {check['max_position_error_m']:.3g} m", flush=True)
        grid = build_grid(clouds, settings["voxel_size_m"], settings["padding_cells"])
        report["arms"] = arm_reports
        for hand, points in enumerate(clouds):
            indices, valid = grid.indices(points)
            if not valid.all() or not grid.occupancy[(hand, *indices.T)].all():
                raise ValueError("Sample-to-voxel membership check failed")
            error = float(np.max(np.abs(grid.centers(indices) - points)))
            if error > grid.spacing_m / 2 + 1e-12:
                raise ValueError("Base/index center reconstruction exceeds half a voxel")
            arm_reports[hand]["max_center_reconstruction_error_m"] = error
        report["coverage_by_sample_count"] = []
        for count in sorted({min(100_000, len(clouds[0])), len(clouds[0])}):
            for hand in range(2):
                occupancy = np.zeros_like(grid.occupancy[hand])
                indices, _ = grid.indices(clouds[hand][:count])
                occupancy[tuple(indices.T)] = True
                test_indices, valid = grid.indices(held_out[hand])
                hits = np.zeros(len(valid), bool)
                hits[valid] = occupancy[tuple(test_indices[valid].T)]
                report["coverage_by_sample_count"].append({"hand": HAND_ORDER[hand], "samples": count,
                    "occupied_voxels": int(occupancy.sum()), "occupied_volume_m3": float(occupancy.sum() * grid.spacing_m**3),
                    "held_out_hit_fraction": float(hits.mean()), "held_out_misses": int((~hits).sum()),
                    "held_out_out_of_grid": int((~valid).sum())})
        grid.save(output / "workspace_grid.npz")
        restored = WorkspaceGrid.load(output / "workspace_grid.npz")
        for key in ("origin_m", "spacing_m", "occupancy", "distance_m"):
            if not np.array_equal(getattr(grid, key), getattr(restored, key)):
                raise ValueError(f"Grid reload differs in {key}")
        query_points = torch.tensor(np.concatenate([p[:32] for p in clouds]), dtype=torch.float64)
        expected, valid = grid.query(query_points)
        actual, reloaded_valid = restored.query(query_points)
        if not valid.all() or not torch.equal(valid, reloaded_valid) or not torch.equal(actual, expected):
            raise ValueError("Reloaded trilinear queries differ")
        report["grid"] = {"shape_xyz": grid.shape.tolist(), "origin_lower_corner_base_m": grid.origin_m.tolist(),
                          "spacing_m": grid.spacing_m, "axis_order": "hand,x,y,z", "sign": "negative inside occupied cells",
                          "reload_exact": True, "reloaded_queries_checked": len(query_points)}
        report["status"] = "completed"
    except (Exception, KeyboardInterrupt) as error:
        report.update(status="failed", error=str(error) or type(error).__name__)
        raise
    finally:
        report.update(finished_at=utc_now(), wall_time_s=time.perf_counter() - started,
                      peak_process_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
        write_json(output / "workspace_report.json", report, overwrite=True)
    return report
