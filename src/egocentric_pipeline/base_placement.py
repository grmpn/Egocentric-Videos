"""Fit one rigid Z-up base pose to physical wrists and sampled positional SDFs."""

import numpy as np
from scipy.optimize import differential_evolution


def base_transform(pose):
    """Base XYZ/yaw in aligned coordinates → column-vector T_base_from_aligned."""
    x, y, z, yaw = pose
    c, s = np.cos(yaw), np.sin(yaw)
    rotation = np.array([[c, s, 0.], [-s, c, 0.], [0., 0., 1.]])
    transform = np.eye(4)
    transform[:3, :3] = rotation
    transform[:3, 3] = -rotation @ [x, y, z]
    return transform


def transform_points(points, transform):
    """[...,3] metre positions transformed with a destination-from-source matrix."""
    return np.asarray(points) @ transform[:3, :3].T + transform[:3, 3]


def evaluate_placement(wrists, valid, transform, grid, margin):
    """Per-hand distances [T,2]; missing/out-of-domain hands never pass."""
    import torch

    points = transform_points(wrists, transform)
    all_distances, domain = grid.query(torch.as_tensor(points.reshape(-1, 3), dtype=torch.float64))
    distances = all_distances.numpy()[np.arange(points.shape[0] * 2), np.tile([0, 1], len(points))].reshape(-1, 2)
    domain = domain.numpy().reshape(-1, 2) & valid
    distances[~domain] = np.nan
    hand_passed = domain & (distances <= -margin)
    observed = valid.any(axis=1)
    passed = observed & (hand_passed | ~valid).all(axis=1)
    return {"wrist_position_base_m": points, "distance_m": distances, "query_valid": domain,
            "hand_passed": hand_passed, "frame_passed": passed}


def optimize_base(wrists, valid, grid, settings, seed_index=0):
    """Seeded four-variable search, ranked primarily by observed frame count.

    Bounded distance penalties break integer-count ties and guide the search.
    Invalid queries receive a penalty, never extrapolated reachability evidence.
    """
    points = np.asarray(wrists)[valid]
    if len(points) == 0:
        raise ValueError("Cannot fit a base without any valid wrist estimates")
    lower = grid.origin_m + .5 * grid.spacing_m
    upper = grid.origin_m + (grid.shape - .5) * grid.spacing_m
    radius = np.linalg.norm(np.maximum(np.abs(lower[:2]), np.abs(upper[:2])))
    bounds = [(points[:, axis].min() - radius, points[:, axis].max() + radius) for axis in (0, 1)]
    bounds += [(points[:, 2].min() - upper[2], points[:, 2].max() - lower[2]), (-np.pi, np.pi)]
    observed = valid.any(axis=1)

    def objective(pose):
        result = evaluate_placement(wrists, valid, base_transform(pose), grid, settings["workspace_margin_m"])
        base = result["wrist_position_base_m"]
        outside = np.linalg.norm(np.maximum(lower - base, 0) + np.maximum(base - upper, 0), axis=-1)
        distance = np.where(result["query_valid"], result["distance_m"], 1 + outside)
        worst = np.max(np.where(valid, distance, -np.inf), axis=1)[observed]
        violation = np.mean(np.minimum(np.maximum(worst + settings["workspace_margin_m"], 0), 1))
        depth = np.mean(np.clip(-worst, 0, 1))
        return float(np.count_nonzero(observed & ~result["frame_passed"]) + .25 * violation - .001 * depth)

    result = differential_evolution(objective, bounds, seed=settings["seed"] + seed_index,
                                    maxiter=settings["optimizer_iterations"], popsize=settings["optimizer_population"],
                                    tol=0, atol=0, polish=False, workers=1)
    return base_transform(result.x), {"base_xyz_yaw": result.x.tolist(), "bounds_xyz_yaw": bounds,
            "objective": float(result.fun), "evaluations": int(result.nfev), "iterations": int(result.nit),
            "seed": settings["seed"] + seed_index, "solver_message": str(result.message),
            "global_optimum_claimed": False}
