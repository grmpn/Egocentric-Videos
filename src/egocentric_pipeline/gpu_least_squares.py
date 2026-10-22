"""Bounded TRF with CUDA sparse normal-equation solves, in float64.

The driver is adapted from SciPy 1.15.3's ``trf_bounds``. Its bound reflection,
scaling, trust-region and termination routines are reused from that pinned
version. Only the expensive LSMR subproblem is replaced with CuPy assembly and
NVIDIA cuDSS factorization. Objective/FK evaluation and small trust-region
operations remain on CPU. There is no implicit CPU fallback.

SciPy's high-level least_squares API does not accept a custom linear solver.
Keep this limited driver aligned with the pinned SciPy dependency; it supports
only the linear loss and Jacobian scaling used by trajectory IK.
"""

# Adapted from SciPy 1.15.3, scipy/optimize/_lsq/trf.py (trf_bounds).
# Copyright (c) 2001-2002 Enthought, Inc. 2003-2024, SciPy Developers.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import importlib.metadata
import time

import numpy as np
from numpy.linalg import norm
from scipy.linalg import qr
from scipy.optimize import OptimizeResult
from scipy.optimize._lsq.common import (
    CL_scaling_vector, build_quadratic_1d, check_termination, compute_jac_scale,
    make_strictly_feasible, minimize_quadratic_1d, solve_trust_region_2d,
    update_tr_radius,
)
from scipy.optimize._lsq.trf import select_step


class CudaNormalSolver:
    """Solve (D J.T J D + diag(c)) p = g using CUDA sparse float64 arrays."""

    def __init__(self):
        try:
            import cupy as cp
            import cupyx.scipy.sparse as sparse
            from nvmath.sparse.advanced import DirectSolver
        except ImportError as exc:
            raise RuntimeError("CUDA IK requires environment/workspace-gpu-requirements.txt; "
                               "see environment/README.md") from exc
        try:
            device = cp.cuda.Device()
            properties = cp.cuda.runtime.getDeviceProperties(device.id)
            cp.zeros(1, dtype=cp.float64)
            device.synchronize()
        except cp.cuda.runtime.CUDARuntimeError as exc:
            raise RuntimeError("CUDA IK cannot access an NVIDIA GPU; check driver/device "
                               "permissions or explicitly select solver_backend='cpu'") from exc
        self.cp, self.sparse, self.DirectSolver = cp, sparse, DirectSolver
        self.threading_library = str(importlib.metadata.distribution("nvidia-cudss-cu12").locate_file(
            "nvidia/cu12/lib/libcudss_mtlayer_gomp.so.0"))
        self.device_name = properties["name"].decode()
        self.wall_time_s = 0.
        self.solves = 0
        self.max_backward_error = 0.

    def solve(self, jacobian, scale, diagonal, gradient):
        cp, sparse = self.cp, self.sparse
        started = time.perf_counter()
        j = sparse.csr_matrix(jacobian).multiply(cp.asarray(scale)[None, :]).tocsr()
        normal = (j.T @ j + sparse.diags(cp.asarray(diagonal), format="csr")).tocsr()
        normal.sort_indices()
        rhs = cp.asarray(gradient)
        with self.DirectSolver(normal, rhs, options={"multithreading_lib": self.threading_library}) as solver:
            solver.plan()
            solver.factorize()
            solution = solver.solve()
        # Normal equations square conditioning. Check backward error on every
        # solve, and fail explicitly rather than accepting an invalid direction.
        denominator = cp.max(cp.abs(rhs)) + cp.max(abs(normal).sum(axis=1)) * cp.max(cp.abs(solution))
        error = float(cp.max(cp.abs(normal @ solution - rhs)) / cp.maximum(denominator, 1e-300))
        result = cp.asnumpy(solution)
        self.wall_time_s += time.perf_counter() - started
        self.solves += 1
        self.max_backward_error = max(self.max_backward_error, error)
        if not np.isfinite(result).all() or not np.isfinite(error) or error > 1e-8:
            raise RuntimeError(f"CUDA normal-equation solve failed accuracy check: {error:g}")
        return result


def least_squares_cuda(evaluate, initial, lower, upper, max_evaluations, tolerance):
    """TRF with hard bounds; evaluations count residual calls just as in SciPy.

    ``evaluate(x)`` returns a NumPy residual and a SciPy sparse Jacobian. Joint
    angles are radians; the caller owns the residual's units and weighting.
    """
    linear = CudaNormalSolver()
    x = make_strictly_feasible(initial, lower, upper)
    residual, jacobian = evaluate(x)
    if not np.isfinite(residual).all():
        raise ValueError("Residuals are not finite at the initial point")
    evaluations = jacobian_evaluations = 1
    cost = .5 * residual @ residual
    gradient = jacobian.T @ residual
    scale, scale_inverse = compute_jac_scale(jacobian)
    distance, derivative = CL_scaling_vector(x, gradient, lower, upper)
    distance[derivative != 0] *= scale_inverse[derivative != 0]
    radius = norm(x * scale_inverse / np.sqrt(distance)) or 1.
    status = 0

    while True:
        distance, derivative = CL_scaling_vector(x, gradient, lower, upper)
        optimality = norm(gradient * distance, ord=np.inf)
        if optimality < tolerance:
            status = 1
        if status or evaluations >= max_evaluations:
            break
        distance[derivative != 0] *= scale_inverse[derivative != 0]
        scaling = np.sqrt(distance) * scale
        diagonal = gradient * derivative * scale
        scaled_gradient = scaling * gradient
        scaled_jacobian = jacobian.multiply(scaling).tocsr()
        a, b = build_quadratic_1d(scaled_jacobian, scaled_gradient, -scaled_gradient, diag=diagonal)
        regularization = -minimize_quadratic_1d(a, b, 0, radius / norm(scaled_gradient))[1] / radius**2
        gauss_newton = linear.solve(jacobian, scaling, diagonal + regularization, scaled_gradient)
        subspace, _ = qr(np.column_stack((scaled_gradient, gauss_newton)), mode="economic")
        projected_jacobian = scaled_jacobian @ subspace
        projected_hessian = projected_jacobian.T @ projected_jacobian + (subspace.T * diagonal) @ subspace
        projected_gradient = subspace.T @ scaled_gradient
        theta = max(.995, 1 - optimality)

        reduction = -1.
        while reduction <= 0 and evaluations < max_evaluations:
            small_step, _ = solve_trust_region_2d(projected_hessian, projected_gradient, radius)
            scaled_step = subspace @ small_step
            step, scaled_step, prediction = select_step(
                x, scaled_jacobian, diagonal, scaled_gradient, scaling * scaled_step,
                scaled_step, scaling, radius, lower, upper, theta)
            trial_x = make_strictly_feasible(x + step, lower, upper, rstep=0)
            trial_residual, trial_jacobian = evaluate(trial_x)
            evaluations += 1
            scaled_norm = norm(scaled_step)
            if not np.isfinite(trial_residual).all():
                radius = .25 * scaled_norm
                continue
            trial_cost = .5 * trial_residual @ trial_residual
            reduction = cost - trial_cost
            new_radius, ratio = update_tr_radius(radius, reduction, prediction, scaled_norm,
                                                 scaled_norm > .95 * radius)
            status = check_termination(reduction, cost, norm(step), norm(x), ratio,
                                       tolerance, tolerance) or 0
            if status:
                break
            radius = new_radius
        if reduction > 0:
            x, residual, jacobian, cost = trial_x, trial_residual, trial_jacobian, trial_cost
            gradient = jacobian.T @ residual
            jacobian_evaluations += 1
            scale, scale_inverse = compute_jac_scale(jacobian, scale_inverse)

    messages = {0: "The maximum number of function evaluations is exceeded.",
                1: "`gtol` termination condition is satisfied.",
                2: "`ftol` termination condition is satisfied.",
                3: "`xtol` termination condition is satisfied.",
                4: "Both `ftol` and `xtol` termination conditions are satisfied."}
    return OptimizeResult(x=x, cost=cost, optimality=float(optimality), success=status > 0,
                          message=messages[status], nfev=evaluations, njev=jacobian_evaluations,
                          gpu={"device": linear.device_name, "precision": "float64",
                               "linear_solves": linear.solves, "linear_solve_wall_time_s": linear.wall_time_s,
                               "max_linear_backward_error": linear.max_backward_error,
                               "execution": "CUDA normal assembly/factorization; CPU objective and TRF control"})
