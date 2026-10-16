"""Source-timed position-only IK witnesses; failed/missing samples remain NaN."""

import numpy as np

from .robot_workspace import arm_parameters


def solve_trajectory(robot, wrists, valid, robot_settings, settings):
    """Solve [T,2,3] TCP targets in the fixed base, with [T,2] validity.

    Returns [T,2,J] radians and [T,2,3] FK positions. Previous successes seed
    each arm; deterministic random restarts are attempted only after failure.
    Other joints remain at the model's verified locked settings.
    """
    from skrobot.coordinates import Coordinates

    n, joints = len(wrists), len(robot_settings["arm_joints"][0])
    q = np.full((n, 2, joints), np.nan)
    fk = np.full((n, 2, 3), np.nan)
    residual = np.full((n, 2), np.nan)
    success = np.zeros((n, 2), bool)
    attempts = np.zeros((n, 2), np.int32)
    for hand in range(2):
        chain, tool, parameters = arm_parameters(robot, robot_settings["tool_frames"][hand], robot_settings["arm_joints"][hand])
        lower, upper = parameters["joint_limits_lower"], parameters["joint_limits_upper"]
        previous = np.zeros(joints)
        rng = np.random.default_rng(np.random.SeedSequence([settings["seed"], hand]))
        for frame in range(n):
            if not valid[frame, hand]:
                continue
            target = wrists[frame, hand]
            if not np.isfinite(target).all():
                raise ValueError("Valid IK targets must be finite base-frame metres")
            world_target = robot.root_link.worldrot() @ target + robot.root_link.worldpos()
            for attempt in range(settings["ik_attempts"]):
                initial = previous if attempt == 0 else rng.uniform(lower, upper)
                for link, angle in zip(chain, initial):
                    link.joint.joint_angle(float(angle))
                result = robot.inverse_kinematics(Coordinates(pos=world_target), link_list=chain, move_target=tool,
                            position_mask=True, rotation_mask=False, stop=settings["ik_iterations"],
                            thre=settings["ik_tolerance_m"] * .5, revert_if_fail=True)
                attempts[frame, hand] += 1
                if result is False:
                    continue
                angles = np.array([link.joint.joint_angle() for link in chain])
                position = (tool.worldpos() - robot.root_link.worldpos()) @ robot.root_link.worldrot()
                error = np.linalg.norm(position - target)
                if (np.isfinite(angles).all() and np.all(angles >= lower) and np.all(angles <= upper)
                        and error <= settings["ik_tolerance_m"]):
                    q[frame, hand], fk[frame, hand] = angles, position
                    residual[frame, hand], success[frame, hand] = error, True
                    previous = angles.copy()
                    break
    step = np.full((n, 2), np.nan)
    for hand in range(2):
        adjacent = success[1:, hand] & success[:-1, hand]
        step[1:, hand][adjacent] = np.max(np.abs(np.diff(q[:, hand], axis=0)[adjacent]), axis=1)
    return {"joint_angles_rad": q, "tcp_position_base_m": fk, "ik_residual_m": residual,
            "ik_success": success, "ik_attempts": attempts, "joint_step_rad": step,
            "joint_jump": step > settings["joint_jump_report_rad"]}
