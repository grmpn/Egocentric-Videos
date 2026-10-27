"""Palm-rooted EZGrippers from the pinned robot asset; ordinary FK only."""

import copy
import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

from .robot_workspace import verify_asset_source


def detached_gripper_xml(urdf_path, side):
    """Keep the palm's descendants, including fingers/mimics and nominal TCP.

    Mesh references become absolute local paths so the derived URDF can live in
    a run directory. The source URDF and its mesh files are never modified.
    """
    if side not in ("left", "right"):
        raise ValueError("Gripper side must be left or right")
    urdf_path = Path(urdf_path).resolve()
    source = ET.parse(urdf_path).getroot()
    links = {f"{side}_ezgripper_palm_link"}
    joints = []
    frontier = list(links)
    while frontier:
        parent = frontier.pop()
        for joint in source.findall("joint"):
            if joint.find("parent").get("link") == parent:
                child = joint.find("child").get("link")
                links.add(child)
                frontier.append(child)
                joints.append(copy.deepcopy(joint))
    result = ET.Element("robot", name=f"{side}_ezgripper_detached")
    for link in source.findall("link"):
        if link.get("name") in links:
            result.append(copy.deepcopy(link))
    result.extend(joints)
    if len(result.findall("link")) != 6 or len(joints) != 5:
        raise ValueError("Expected EZGripper palm, four finger links and nominal TCP; check the pinned URDF")
    for mesh in result.iter("mesh"):
        path = (urdf_path.parent / mesh.get("filename")).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Gripper mesh missing: {path}")
        mesh.set("filename", str(path))
    ET.indent(result)
    return ET.tostring(result, encoding="unicode") + "\n"


class EZGripper:
    """One freely posed gripper with a continuous closed=0/open=1 command.

    Pose matrices use column vectors, metres and proper rotations. The nominal
    TCP is a fixed URDF reference, not an opening-dependent contact estimate.
    """

    def __init__(self, xml, side, opening_command):
        from skrobot.model import RobotModel

        self.side = side
        self.xml = xml
        self.model = RobotModel.from_urdf(xml)
        self.links = {link.name: link for link in self.model.link_list}
        self.joints = {joint.name: joint for joint in self.model.joint_list}
        self.tcp = self.links[f"{side.upper()}_EZGRIPPER_TCP_LINK"]
        self.opening_command = opening_command
        self.set_opening(1.)
        self.transform_palm_from_tcp = self.tcp.worldcoords().T().copy()

    def set_opening(self, action):
        """Use the asset's two-leader rule; the URDF library propagates mimics."""
        targets = self.opening_command(float(action), self.side)
        for name, angle in targets.items():
            joint = self.joints[name]
            if not joint.min_angle <= angle <= joint.max_angle:
                raise ValueError(f"Opening command exceeds URDF bounds for {name}")
            joint.joint_angle(angle)
        return {name: float(joint.joint_angle()) for name, joint in self.joints.items()}

    def place_tcp(self, transform_aligned_from_tcp):
        """Position/orient the free palm so its nominal TCP matches this pose."""
        from skrobot.coordinates import Coordinates

        transform = np.asarray(transform_aligned_from_tcp, dtype=float)
        if (transform.shape != (4, 4) or not np.isfinite(transform).all()
                or not np.allclose(transform[3], [0, 0, 0, 1])
                or not np.allclose(transform[:3, :3].T @ transform[:3, :3], np.eye(3), atol=1e-7)
                or not np.isclose(np.linalg.det(transform[:3, :3]), 1., atol=1e-7)):
            raise ValueError("Gripper TCP pose must be a finite rigid transform")
        palm = transform @ np.linalg.inv(self.transform_palm_from_tcp)
        self.model.newcoords(Coordinates(pos=palm[:3, 3], rot=palm[:3, :3]))
        return palm


def load_grippers(asset_root, robot_settings):
    """Reuse the pinned asset's pure-Python command helper without Isaac Lab."""
    asset_root = Path(asset_root).resolve()
    urdf = verify_asset_source(asset_root, robot_settings)
    helper = asset_root / "src/ihmc_alex_isaaclab/end_effectors/sake_ezgripper.py"
    spec = importlib.util.spec_from_file_location("ezgripper_asset_commands", helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return [EZGripper(detached_gripper_xml(urdf, side), side, module.alex_purdue_ezgripper_targets)
            for side in ("left", "right")]
