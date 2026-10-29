"""Pinned robot joint limits and discrete-pose mesh self-collision evaluation."""

import ast
from itertools import combinations
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

from .robot_workspace import load_robot, verify_asset_source


class RobotConstraints:
    """Ordinary URDF FK, including coupled leaders and URDF mimic followers.

    Position/speed limits come from URDF. Acceleration caps are explicit benchmark
    assumptions in rad/s². Collision exclusions cover rigid assemblies, adjacent
    assemblies and the pinned asset's three documented convex-mesh exclusions.
    """

    def __init__(self, asset_root, robot_settings, settings):
        urdf = verify_asset_source(asset_root, robot_settings)
        self.robot = load_robot(urdf, robot_settings["base_frame"])
        tree = ET.parse(urdf).getroot()
        joints = [j for j in tree.findall("joint") if j.get("type") != "fixed"]
        self.names = [j.get("name") for j in joints]
        self.lower, self.upper, self.velocity = (
            np.array([float(j.find("limit").get(key)) for j in joints]) for key in ("lower", "upper", "velocity"))
        overrides = settings.get("joint_acceleration_limits_rad_s2", {})
        if set(overrides) - set(self.names):
            raise ValueError("Acceleration overrides contain unknown robot joints")
        self.acceleration = np.array([overrides.get(n, settings["acceleration_limit_rad_s2"]) for n in self.names])
        if not np.isfinite(self.acceleration).all() or np.any(self.acceleration <= 0):
            raise ValueError("Benchmark acceleration limits must be positive finite rad/s²")
        # The library clips joint assignments. Geometry must use the supplied
        # trajectory even when invalid; score against the original bounds above.
        for joint in self.robot.joint_list:
            joint.min_angle, joint.max_angle = -np.inf, np.inf
        self.links = {l.name: l for l in self.robot.link_list}
        parent = {j.find("child").get("link"): (j.find("parent").get("link"), j.get("type"))
                  for j in tree.findall("joint")}

        def assembly(link):
            while link in parent and parent[link][1] == "fixed":
                link = parent[link][0]
            return link

        adjacent = {frozenset((assembly(child), assembly(p))) for child, (p, kind) in parent.items()
                    if kind != "fixed"}
        source = Path(asset_root) / "src/ihmc_alex_isaaclab/robots/purdue_physics.py"
        module = ast.parse(source.read_text())
        pairs = next(ast.literal_eval(n.value) for n in module.body if isinstance(n, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == "ALEX_PURDUE_SELF_COLLISION_FILTER_PAIRS" for t in n.targets))
        explicit = {frozenset(map(assembly, p)) for p in pairs}
        collision_links = [n for n, l in self.links.items() if l.collision_mesh is not None]
        self.exclusions = {}
        for a, b in combinations(sorted(collision_links), 2):
            groups = frozenset((assembly(a), assembly(b)))
            reason = ("same rigid assembly" if len(groups) == 1 else "adjacent assemblies" if groups in adjacent
                      else "pinned asset convex exclusion" if groups in explicit else None)
            if reason:
                self.exclusions[(a, b)] = reason

    def set_pose(self, names, angles, coupled=None):
        """Set every independent joint; absent joints are the baseline's locked zero."""
        values = dict(zip(names, angles))
        if len(values) != len(names) or set(values) - set(self.names):
            raise ValueError("Trajectory joint names must be unique known robot joints")
        if not np.isfinite(angles).all():
            raise ValueError("Cannot evaluate a nonfinite robot pose")
        for second, first in (coupled or {}).items():
            values[second] = values[first]
        for joint in self.robot.joint_list:
            if not getattr(joint, "mimic", None):
                # Disable clipping: an invalid predicted angle must fail scoring,
                # not become an apparently feasible pose during evaluation.
                joint.joint_angle(float(values.get(joint.name, 0.)))
        return np.array([self.robot.__dict__[n].joint_angle() for n in self.names])

    def collision_pairs(self):
        """Mesh intersections at the current pose; no scene/inter-frame claim."""
        _, pairs = self.robot.self_collision_check()
        return sorted(tuple(sorted(p)) for p in pairs if tuple(sorted(p)) not in self.exclusions)

    def metadata(self):
        return {"joint_names": self.names, "position_lower_rad": self.lower.tolist(),
                "position_upper_rad": self.upper.tolist(), "velocity_limit_rad_s": self.velocity.tolist(),
                "acceleration_limit_rad_s2": self.acceleration.tolist(),
                "acceleration_source": "benchmark proxy; not verified Alex hardware limits",
                "collision_exclusions": [{"links": list(pair), "reason": reason} for pair, reason in self.exclusions.items()],
                "collision_method": "scikit-robot self_collision_check / trimesh / python-fcl; URDF collision meshes; discrete frames"}
