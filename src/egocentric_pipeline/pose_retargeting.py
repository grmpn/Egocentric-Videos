"""Shared-base pose fitting followed by source-timed joint trajectory smoothing.

All transforms act on column vectors. FK uses metres/radians in the pedestal
frame; observations use the gravity-aligned frame. Joint order is left arm (7),
right arm (7), neck (2). Camera optical rotation is fitted; translation is not.
"""

import time

import numpy as np
from scipy import sparse
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from .base_placement import base_transform
from .manipulation_regions import frame_edges, interval_metrics
from .robot_workspace import arm_parameters


class PoseModel:
    """Reuse scikit-robot's URDF FK/Jacobians for wrists, tools and head."""

    def __init__(self, robot, robot_settings, settings):
        self.joint_names = sum(robot_settings["arm_joints"], []) + settings["neck_joints"]
        joints = [robot.__dict__[name] for name in self.joint_names]
        self.lower = np.array([j.min_angle for j in joints])
        self.upper = np.array([j.max_angle for j in joints])
        self.neutral = np.asarray(settings["neutral_joint_angles_rad"], dtype=float)
        if (self.neutral.shape != (16,) or not np.isfinite(self.neutral).all()
                or np.any(self.neutral < self.lower) or np.any(self.neutral > self.upper)):
            raise ValueError("Neutral posture must contain 16 finite, joint-limit-valid angles")
        self.wrists, self.tools = [], []
        self.wrist_offset = np.asarray(settings.get("wrist_offset_tool_m", [0., 0., 0.]))
        for hand in range(2):
            names = robot_settings["arm_joints"][hand]
            self.wrists.append(arm_parameters(robot, robot_settings["target_frames"][hand], names[:6])[2])
            self.tools.append(arm_parameters(robot, robot_settings["tool_frames"][hand], names)[2])
        self.head = arm_parameters(robot, settings["camera_mount_frame"], settings["neck_joints"])[2]
        self.optical = np.asarray(settings["rotation_mount_from_optical"], dtype=float)
        if (self.optical.shape != (3, 3) or not np.isfinite(self.optical).all()
                or not np.allclose(self.optical.T @ self.optical, np.eye(3), atol=1e-8)
                or not np.isclose(np.linalg.det(self.optical), 1)):
            raise ValueError("Camera mount-from-optical must be a proper rotation")

    def forward(self, angles, jacobian=False):
        """Return wrist match points, tool rotations/positions and optical poses.

        With jacobian=True, append three lists of geometric [T,6,J] Jacobians.
        Match point = physical wrist + R_base_from_tool @ wrist_offset_tool_m.
        Its linear Jacobian includes the rotating offset for all seven joints.
        """
        from skrobot.kinematics.differentiable import (
            compute_geometric_jacobian_batched_numpy, forward_kinematics_ee_batched_numpy)

        positions, rotations, tools, wrist_j, tool_j = [], [], [], [], []

        def fk(q, params):
            if jacobian:
                j, p, r = compute_geometric_jacobian_batched_numpy(q, params)
                return p, r, j
            p, r = forward_kinematics_ee_batched_numpy(q, params)
            return p, r, None

        for hand in range(2):
            q = angles[:, hand * 7:hand * 7 + 7]
            p, _, j = fk(q[:, :6], self.wrists[hand])
            tp, r, tj = fk(q, self.tools[hand])
            offset = r @ self.wrist_offset
            positions.append(p + offset)
            rotations.append(r)
            tools.append(tp)
            if jacobian:
                shifted_j = np.zeros_like(tj)
                shifted_j[:, :3, :6] = j[:, :3]
                shifted_j[:, :3] += np.cross(tj[:, 3:].transpose(0, 2, 1),
                                             offset[:, None, :]).transpose(0, 2, 1)
                shifted_j[:, 3:] = tj[:, 3:]
                wrist_j.append(shifted_j)
            tool_j.append(tj)
        hp, hr, hj = fk(angles[:, 14:], self.head)
        result = (np.stack(positions, axis=1), np.stack(rotations, axis=1),
                  np.stack(tools, axis=1), hp, hr @ self.optical)
        return (*result, wrist_j, tool_j, hj) if jacobian else result


def initialize_base(camera_positions, camera_rotations, model, heading_min_norm):
    """Median horizontal optical direction; median camera centre minus neutral FK.

    Take component-wise medians of unit forward vectors, not wrapped yaw angles.
    This handles +/-pi wraparound and reduces outlier influence. A vertical or
    cancelling median direction is an explicit error.
    """
    directions = np.asarray(camera_rotations)[:, :2, 2]
    lengths = np.linalg.norm(directions, axis=1)
    usable = lengths > heading_min_norm
    if not usable.any():
        raise ValueError("No horizontal camera heading; inspect the camera poses")
    direction = np.median(directions[usable] / lengths[usable, None], axis=0)
    if np.linalg.norm(direction) < heading_min_norm:
        raise ValueError("Camera headings cancel; choose a shorter manipulation region")
    yaw = float(np.arctan2(direction[1], direction[0]))
    rotation = Rotation.from_euler("z", yaw).as_matrix()
    offset = model.forward(model.neutral[None])[3][0]
    representative = np.median(camera_positions, axis=0)
    return np.r_[representative - rotation @ offset, yaw]


def temporal_operators(timestamps, joints=16):
    """Sparse first/second derivatives at interval centres, seconds retained."""
    dt = np.diff(timestamps)
    if len(dt) < 1 or not np.isfinite(dt).all() or np.any(dt <= 0):
        raise ValueError("Trajectory timestamps must be finite and strictly increasing")
    n = len(timestamps)
    velocity = sparse.diags([-1 / dt, 1 / dt], [0, 1], shape=(n - 1, n), format="csr")
    acceleration = (sparse.diags([-2 / (dt[1:] + dt[:-1]), 2 / (dt[1:] + dt[:-1])],
                                [0, 1], shape=(n - 2, n - 1), format="csr") @ velocity)
    return tuple(sparse.kron(d, sparse.eye(joints), format="csr") for d in (velocity, acceleration))


def motion_metrics(q, timestamps):
    velocity, acceleration = temporal_operators(timestamps, q.shape[1])
    v, a = velocity @ q.ravel(), acceleration @ q.ravel()
    return {"velocity_rms_rad_s": float(np.sqrt(np.mean(v**2))),
            "acceleration_rms_rad_s2": float(np.sqrt(np.mean(a**2))) if len(a) else 0.,
            "max_joint_step_rad": float(np.max(np.abs(np.diff(q, axis=0))))}


def rotation_error(predicted, target):
    """Geodesic angular error in radians, including rotations near pi."""
    shape = predicted.shape[:-2]
    relative = predicted @ np.swapaxes(target, -1, -2)
    return Rotation.from_matrix(relative.reshape(-1, 3, 3)).magnitude().reshape(shape)


class PoseProblem:
    """Sparse bounded least-squares objective with library geometric Jacobians."""

    def __init__(self, model, wrists, orientations, cameras, valid, times, settings,
                 *, fixed_base=None, smooth=False, base_reference=None):
        self.model, self.settings = model, settings
        self.wrists, self.orientations, self.cameras = wrists, orientations, cameras
        self.valid, self.n = valid, len(times)
        self.fixed_base = fixed_base
        self.base_reference = base_reference
        self.base_variables = 4 if fixed_base is None else 0
        self.width = self.n * 16 + self.base_variables
        if smooth:
            velocity, acceleration = temporal_operators(times)
        self.regularizer = sparse.vstack([
            settings["neutral_weight"] * sparse.eye(self.n * 16),
            settings["velocity_weight"] * velocity if smooth else sparse.csr_matrix((0, self.n * 16)),
            settings["acceleration_weight"] * acceleration if smooth else sparse.csr_matrix((0, self.n * 16)),
        ], format="csr")
        self.regularizer_target = np.r_[
            settings["neutral_weight"] * np.tile(model.neutral, self.n),
            np.zeros(self.regularizer.shape[0] - self.n * 16)]
        self.cached_x = None

    def base_prior(self, base):
        """Weighted XYZ/metres and wrapped yaw/radians; absent in fixed-base IK."""
        weight = self.settings.get("base_initialization_weight", 0.) if self.base_variables else 0.
        if not weight:
            return np.empty(0), np.empty(0)
        if self.base_reference is None:
            raise ValueError("Base prior requires the median-camera initialization as base_reference")
        delta = base - self.base_reference
        delta[3] = np.arctan2(np.sin(delta[3]), np.cos(delta[3]))
        scales = np.array([self.settings.get("base_prior_translation_scale_m", 1.)] * 3
                          + [self.settings.get("base_prior_yaw_scale_rad", 1.)])
        return weight * delta / scales, weight / scales

    def unpack(self, x):
        return (x[:4] if self.base_variables else self.fixed_base,
                x[self.base_variables:].reshape(self.n, 16))

    def evaluate(self, x):
        if self.cached_x is not None and np.array_equal(x, self.cached_x):
            return self.cached_result
        base, q = self.unpack(x)
        rotation = base_transform(base)[:3, :3].T
        p, r, _, _, hr, pj, rj, hj = self.model.forward(q, jacobian=True)
        residuals, rows, cols, values = [], [], [], []
        row_start = 0

        def append(error, derivative, base_derivative, frames):
            nonlocal row_start
            size = error.shape[1]
            residuals.append(error.ravel())
            rr = row_start + np.arange(len(frames) * size).reshape(-1, size, 1)
            cc = self.base_variables + frames[:, None, None] * 16 + np.arange(16)
            rows.append(np.broadcast_to(rr, derivative.shape).ravel())
            cols.append(np.broadcast_to(cc, derivative.shape).ravel())
            values.append(derivative.ravel())
            if self.base_variables:
                rows.append(np.broadcast_to(rr, base_derivative.shape).ravel())
                cols.append(np.broadcast_to(np.arange(4), base_derivative.shape).ravel())
                values.append(base_derivative.ravel())
            row_start += error.size

        def position_term(pred, target, linear_j, joint_start, frames, scale):
            aligned = pred @ rotation.T
            derivative = np.zeros((len(frames), 3, 16))
            derivative[:, :, joint_start:joint_start + linear_j.shape[-1]] = (
                np.einsum("ij,tjk->tik", rotation, linear_j) / scale)
            bd = np.zeros((len(frames), 3, 4))
            bd[:, :, :3] = np.eye(3) / scale
            bd[:, :, 3] = np.cross([0., 0., 1.], aligned) / scale
            append((aligned + base[:3] - target) / scale, derivative, bd, frames)

        def rotation_term(pred, target, angular_j, joint_start, frames, scale):
            aligned = rotation @ pred
            # For spatial angular velocity w, dR[:,k] = w cross R[:,k].
            axes = np.einsum("ij,tjk->tik", rotation, angular_j)
            derivative = np.cross(axes.transpose(0, 2, 1)[:, :, None, :],
                                  aligned.transpose(0, 2, 1)[:, None, :, :])
            derivative = derivative.transpose(0, 3, 2, 1).reshape(len(frames), 9, -1)
            full = np.zeros((len(frames), 9, 16))
            full[:, :, joint_start:joint_start + derivative.shape[-1]] = derivative / scale
            bd = np.zeros((len(frames), 9, 4))
            bd[:, :, 3] = np.cross([0., 0., 1.], aligned.transpose(0, 2, 1)).transpose(0, 2, 1).reshape(-1, 9) / scale
            append((aligned - target).reshape(-1, 9) / scale, full, bd, frames)

        for hand in range(2):
            frames = np.flatnonzero(self.valid[:, hand])
            if not len(frames):
                continue
            position_term(p[frames, hand], self.wrists[frames, hand], pj[hand][frames, :3],
                          hand * 7, frames, self.settings["position_scale_m"] / self.settings["hand_position_weight"])
            rotation_term(r[frames, hand], self.orientations[frames, hand], rj[hand][frames, 3:],
                          hand * 7, frames, np.sqrt(2) * self.settings["orientation_scale_rad"]
                          / self.settings["hand_orientation_weight"])
        rotation_term(hr, self.cameras, hj[:, 3:], 14, np.arange(self.n),
                      np.sqrt(2) * self.settings["camera_rotation_scale_rad"])
        reg = self.regularizer
        residuals.append(reg @ q.ravel() - self.regularizer_target)
        reg = reg.tocoo()
        rows.append(reg.row + row_start)
        cols.append(reg.col + self.base_variables)
        values.append(reg.data)
        prior, prior_derivative = self.base_prior(base)
        if len(prior):
            residuals.append(prior)
            rows.append(row_start + reg.shape[0] + np.arange(4))
            cols.append(np.arange(4))
            values.append(prior_derivative)
        residual = np.concatenate(residuals)
        jac = sparse.coo_matrix((np.concatenate(values), (np.concatenate(rows), np.concatenate(cols))),
                                shape=(len(residual), self.width)).tocsr()
        jac.eliminate_zeros()
        self.cached_x = x.copy()
        self.cached_result = residual, jac
        return residual, jac

    def solve(self, initial_base, initial_q, max_evaluations):
        if self.base_variables:
            self.base_reference = np.asarray(initial_base).copy()
            self.cached_x = None
            radius = np.array([self.settings["base_translation_radius_m"]] * 3 + [np.pi])
            lower = np.r_[initial_base - radius, np.tile(self.model.lower, self.n)]
            upper = np.r_[initial_base + radius, np.tile(self.model.upper, self.n)]
            initial = np.r_[initial_base, initial_q.ravel()]
        else:
            lower, upper = np.tile(self.model.lower, self.n), np.tile(self.model.upper, self.n)
            initial = initial_q.ravel()
        started = time.perf_counter()
        backend = self.settings.get("solver_backend", "cpu")
        if backend == "cuda":
            from .gpu_least_squares import least_squares_cuda
            result = least_squares_cuda(self.evaluate, initial, lower, upper,
                                        max_evaluations, self.settings["solver_tolerance"])
        elif backend == "cpu":
            result = least_squares(lambda x: self.evaluate(x)[0], initial,
                                   jac=lambda x: self.evaluate(x)[1], bounds=(lower, upper),
                                   max_nfev=max_evaluations, ftol=self.settings["solver_tolerance"],
                                   xtol=self.settings["solver_tolerance"], gtol=self.settings["solver_tolerance"],
                                   x_scale="jac", tr_options={"atol": 1e-8, "btol": 1e-8})
        else:
            raise ValueError("solver_backend must be 'cpu' or 'cuda'")
        base, q = self.unpack(result.x)
        prior, _ = self.base_prior(base)
        return base, q, {"wall_time_s": time.perf_counter() - started, "evaluations": result.nfev,
                        "jacobian_evaluations": result.njev, "cost": float(result.cost),
                        "optimality": float(result.optimality), "converged": bool(result.success),
                        "message": str(result.message), "global_optimum_claimed": False,
                        "base_prior_cost": float(.5 * prior @ prior),
                        "solver_backend": backend, **({"gpu": result.gpu} if backend == "cuda" else {})}


def fit_region(model, wrists, orientations, cameras, valid, timestamps, initial_base, settings,
               *, seed_index=0, raw_wrists=None, raw_orientations=None):
    """Fit alternate frames, freeze base, interpolate seeds and refine all frames."""
    rng = np.random.default_rng(np.random.SeedSequence([settings["seed"], seed_index]))
    raw_wrists = wrists if raw_wrists is None else raw_wrists
    raw_orientations = orientations if raw_orientations is None else raw_orientations
    sampled = np.arange(0, len(timestamps), settings["base_frame_stride"])
    attempts, best, best_rank = [], None, None
    for attempt in range(settings["fit_attempts"]):
        # One posture per region avoids independent random branches at every frame.
        initial_q = model.neutral if attempt == 0 else rng.uniform(.8 * model.lower, .8 * model.upper)
        q0 = np.tile(initial_q, (len(sampled), 1))
        problem = PoseProblem(model, wrists[sampled], orientations[sampled], cameras[sampled],
                              valid[sampled], timestamps[sampled], settings)
        base, sampled_q, first = problem.solve(initial_base, q0, settings["base_max_evaluations"])
        # Interpolation preserves bounds. An unsampled final frame holds the
        # last pose until the full-resolution solve; no source data is filled.
        before = np.column_stack([np.interp(timestamps, timestamps[sampled], sampled_q[:, j])
                                  for j in range(16)])
        problem = PoseProblem(model, wrists, orientations, cameras, valid, timestamps, settings,
                              fixed_base=base, smooth=True)
        _, after, second = problem.solve(base, before, settings["trajectory_max_evaluations"])
        p, r, *_ = model.forward(after)
        rotation = base_transform(base)[:3, :3].T
        pe = np.linalg.norm(p @ rotation.T + base[:3] - raw_wrists, axis=-1)
        oe = np.full(valid.shape, np.nan)
        oe[valid] = rotation_error((rotation @ r)[valid], raw_orientations[valid])
        passed = valid.any(axis=1) & ((valid & (pe <= settings["ik_tolerance_m"])
                                      & (oe <= settings["orientation_tolerance_rad"])) | ~valid).all(axis=1)
        metrics = interval_metrics(0, len(timestamps), passed, valid.any(axis=1), frame_edges(timestamps), settings)
        info = {"attempt": attempt, "initial_joint_angles_rad": initial_q.tolist(),
                "base_sample_indices": sampled.tolist(),
                "trajectory_frame_count": len(timestamps),
                "trajectory_initialization": "source-time linear joint interpolation; endpoint hold",
                "joint_base": first, "fixed_base_trajectory": second, "pose": metrics,
                "base_drift_translation_m": float(np.linalg.norm(base[:3] - initial_base[:3])),
                "base_drift_yaw_rad": float(np.arctan2(np.sin(base[3] - initial_base[3]), np.cos(base[3] - initial_base[3]))),
                "before_smoothing": motion_metrics(before, timestamps),
                "after_smoothing": motion_metrics(after, timestamps)}
        attempts.append(info)
        smooth = info["after_smoothing"]["acceleration_rms_rad_s2"] < info["before_smoothing"]["acceleration_rms_rad_s2"]
        rank = (metrics["accepted"] and smooth, metrics["passing_frames"], -second["cost"])
        if best_rank is None or rank > best_rank:
            best, best_rank = (base, before, after, info), rank
        if metrics["accepted"] and smooth:
            break
    base, before, after, selected = best
    return base, before, after, dict(selected, attempts=attempts, selected_attempt=selected["attempt"])
