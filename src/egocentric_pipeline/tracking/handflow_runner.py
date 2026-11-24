"""HandFlow's released inference functions, two hand passes and one native ViPE track.

The left pass mirrors RGB and intrinsics into the right-hand model's convention.
Inverse reflection recovers camera-space joints and proper MANO-root rotations.
No GT pose, shape, depth, mask or scale is loaded.
"""

import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

from egocentric_pipeline.run_metadata import read_json, write_json
from egocentric_pipeline.tracking.hand_benchmark import component


def undo_left_mirror(joints, rotations):
    """Reflect camera X and canonical MANO X; conjugation keeps det(R)=+1."""
    reflection = np.diag([-1., 1., 1.])
    return joints @ reflection, reflection @ rotations @ reflection


def combine_hand_stages(stages, frame_count):
    """Charge both hand passes before computing a component's effective FPS."""
    combined = {}
    for stage in stages:
        name = stage["name"]
        if name.startswith(("left_", "right_")):
            name = name.split("_", 1)[1]
        if name not in combined:
            combined[name] = {**stage, "name": name}
        else:
            row = combined[name]
            row["wall_time_s"] += stage["wall_time_s"]
            row["status"] = "completed" if row["status"] == stage["status"] == "completed" else "failed"
            row["processed_frames"] = (row["processed_frames"] + stage["processed_frames"]
                                       if row["processed_frames"] is not None and stage["processed_frames"] is not None else None)
    for row in combined.values():
        row["effective_fps"] = frame_count / row["wall_time_s"] if row["status"] == "completed" else None
    return list(combined.values())


def run_native(video, intrinsics, output, root, seed, frame_count):
    """Worker entry point in the isolated HandFlow environment; preserves raw arrays."""
    import cv2
    import torch
    from omegaconf import OmegaConf
    from scipy.spatial.transform import Rotation

    engine = root / "external/HandFlow"
    sys.path.insert(0, str(engine))
    from utils.checkpoint_utils import load_denoiser_from_ckpt
    from utils.inference_utils import run_fm_inference_with_overlap, split_sequence_into_windows
    from utils.mano_utils import MANOForwardKinematics
    from utils.online_hamer import OnlineHaMeRPipeline
    from visualization.video_io import read_video_frames

    output.mkdir(parents=True, exist_ok=False)
    report = {"status": "running", "components": [], "seed": seed,
              "adaptations": ["Two right-model passes, with mirrored RGB/intrinsics for left hand and inverse-reflected output.",
                              "One shared original-RGB ViPE camera track; native default configuration with supplied intrinsics.",
                              "Denoiser eval mode and no-grad for inference; native demo omits eval although its evaluation helper uses it.",
                              "Rendering omitted; all native inference and both hand passes timed."]}
    count = frame_count
    try:
        with component(report, "rgb_decode_and_slam_images", count, processed_frames=count):
            frames, fps, (height, width) = read_video_frames(str(video))
            if len(frames) != count:
                raise ValueError("Decoded frame count differs from the prepared clip")
            images = output / "images"
            images.mkdir()
            for index, frame in enumerate(frames):
                if not cv2.imwrite(str(images / f"{index:06d}.jpg"), frame):
                    raise ValueError("Failed to prepare native ViPE image input")
        with component(report, "slam_metric_depth", count, processed_frames=count,
                       timing_note="Native ViPE worker, including startup/loading and metric3d-small depth; supplied intrinsics"):
            command = [str(root / ".venv-vipe/bin/python"), str(engine / "utils/vipe_worker.py"), "--worker",
                       "--img_dir", str(images), "--seq_name", output.parent.name, "--variant", "gt_intr",
                       "--gt_intr_str", ",".join(map(str, intrinsics)), "--output", str(output / "slam_result.json")]
            with (output / "vipe.log").open("w") as log:
                subprocess.run(command, cwd=engine, stdout=log, stderr=subprocess.STDOUT, check=True)
            slam = read_json(output / "slam_result.json")
            if not slam.get("ok"):
                raise RuntimeError(f"Native ViPE failed: {slam.get('error')}")
            camera = np.asarray(slam["poses"], dtype=float)
            if camera.shape != (count, 4, 4):
                raise ValueError("ViPE must return one camera pose for every original frame")
        with component(report, "model_loading", count):
            device = torch.device("cuda")
            torch.manual_seed(seed)
            np.random.seed(seed)
            cfg = OmegaConf.load(engine / "configs/inference.yaml")
            model_cfg = OmegaConf.load(engine / cfg.model_yaml)
            denoiser = load_denoiser_from_ckpt(OmegaConf.merge(model_cfg, cfg),
                str(root / "data/models/handflow/handflow_denoiser.pt"), device).eval()
            online = OnlineHaMeRPipeline(device=str(device))
            mano = MANOForwardKinematics(os.environ["MANO_ROOT"], device)
            torch.cuda.synchronize()
        local = np.full((count, 2, 21, 3), np.nan)
        roots = np.full((count, 2, 3, 3), np.nan)
        direct = np.zeros((count, 2), bool)
        for hand, side in enumerate(("left", "right")):
            with component(report, f"{side}_rgb_mirror", count, processed_frames=count):
                hand_frames = [cv2.flip(frame, 1) for frame in frames] if hand == 0 else frames
                hand_intrinsics = np.array(intrinsics, dtype=np.float32)
                if hand == 0:
                    hand_intrinsics[2] = width - 1 - hand_intrinsics[2]
            # Native online timing synchronizes via CPU copies and includes crop
            # generation in HaMeR time. Preserve those boundaries for inspection.
            observed = online.process_sequence(hand_frames, [hand_intrinsics] * count, target_side="right")
            torch.cuda.synchronize()
            direct[:, hand] = observed["detection_valid"].numpy()
            for name, seconds, processed, unit in (("detection", observed["det_time_s"], count, "RGB frames"),
                ("hand_features", observed["hamer_time_s"], int(direct[:, hand].sum()), "detected hand frames")):
                report["components"].append({"name": f"{side}_{name}", "status": "completed", "wall_time_s": seconds,
                    "effective_fps": count / seconds, "processed_frames": processed, "frame_unit": unit,
                    "timing_note": "Native OnlineHaMeR timer; CPU copies synchronize GPU; hand_features includes crop generation"})
            with component(report, f"{side}_trajectory_prediction", count, processed_frames=count, frame_unit="hand frames"):
                with torch.no_grad():
                    tokens = denoiser.frame_compressor(observed["backbone_features"].to(device).unsqueeze(0)).squeeze(0)
                    batch = {"mano_params": torch.zeros((1, count, 48)), "mano_trans": torch.zeros((1, count, 3)),
                             "mano_betas": torch.zeros((1, 10)), "padding_mask": torch.zeros((1, count), dtype=torch.bool),
                             "images": observed["crop_images"].unsqueeze(0),
                             "hamer_landmarks": observed["hamer_landmarks"].unsqueeze(0),
                             "crop_intrinsics": observed["crop_intrinsics"].unsqueeze(0),
                             "hamer_confidence": observed["hamer_confidence"].unsqueeze(0),
                             "image_tokens": tokens.unsqueeze(0), "side": ["right"], "source": ["custom"]}
                    window, overlap = int(cfg.inference.window_size), int(cfg.inference.overlap_size)
                    windows, _ = split_sequence_into_windows(batch, window, window - overlap, device)
                    windows = {key: value.to(device) if isinstance(value, torch.Tensor) else value for key, value in windows.items()}
                    pose, trans, betas = run_fm_inference_with_overlap(denoiser, denoiser, windows, window,
                        overlap, int(cfg.inference.ode_steps), device, overlap_method=cfg.inference.overlap_method)
                    torch.cuda.synchronize()
                    if len(pose) != count:
                        raise ValueError("Native window stitching did not preserve the original frame count")
            with component(report, f"{side}_geometry_export", count, processed_frames=count, frame_unit="hand frames"):
                joints = mano.joints(pose, betas, trans, ["right"] * count).cpu().numpy() / 1000
                rotation = Rotation.from_rotvec(pose[:, :3].cpu().numpy()).as_matrix()
                np.savez_compressed(output / f"{side}-native.npz", pose=pose.cpu().numpy(), trans=trans.cpu().numpy(),
                    betas=betas.cpu().numpy(), joints_m=joints, detection_valid=direct[:, hand],
                    detector_confidence=observed["bbox_conf"].numpy(), bbox_xyxy=observed["bbox_xyxy"].numpy(),
                    intrinsics=hand_intrinsics, mirrored=hand == 0)
                if hand == 0:
                    joints, rotation = undo_left_mirror(joints, rotation)
                local[:, hand], roots[:, hand] = joints, rotation
                del observed, windows, batch, tokens, pose, trans, betas
                torch.cuda.empty_cache()
        valid = np.isfinite(local).all(axis=(2, 3))
        world = np.einsum("tij,thkj->thki", camera[:, :3, :3], local) + camera[:, None, None, :3, 3]
        np.savez_compressed(output / "geometry.npz", joints_camera_m=local, joints_world_m=world,
            wrist_rotation_world=camera[:, None, :3, :3] @ roots, camera_to_world=camera,
            camera_valid=np.isfinite(camera).all(axis=(1, 2)), hand_valid=valid,
            direct_valid=direct & valid, infilled=~direct & valid)
        report.update(status="completed", frame_count=count, fps=fps)
    except BaseException as error:
        report.update(status="failed", failure={"type": type(error).__name__, "message": str(error)})
        raise
    finally:
        write_json(output / "native_report.json", report)


def handflow_prediction(prepared, output, root, settings, clip, report):
    """Run isolated native worker, without importing incompatible Torch in the parent."""
    from egocentric_pipeline.datasets.taco import source_paths

    engine = root / "external/HandFlow"
    revision = subprocess.check_output(["git", "-C", str(engine), "rev-parse", "HEAD"], text=True).strip()
    if revision != settings["handflow_revision"]:
        raise ValueError("HandFlow source revision differs from benchmark settings")
    dirty = subprocess.check_output(["git", "-C", str(engine), "status", "--porcelain", "--untracked-files=no",
                                     "--ignore-submodules=untracked"], text=True)
    if dirty.strip():
        raise ValueError("HandFlow source or pinned submodules have tracked changes")
    report["engine"] = {"revision": revision, "weights_revision": settings["handflow_weights_revision"],
        "submodules": subprocess.check_output(["git", "-C", str(engine), "submodule", "status", "--recursive"], text=True).splitlines()}
    matrix = np.loadtxt(source_paths(settings["source_root"], clip)["intrinsics"])
    intrinsics = matrix[0, 0], matrix[1, 1], matrix[0, 2], matrix[1, 2]
    environment = os.environ.copy()
    assets = root / "data/models/handflow"
    environment.update(HAMER_CKPT=str(assets / "_DATA/hamer_ckpts/checkpoints/hamer.ckpt"),
        HAMER_DATA=str(assets / "_DATA"), DETECTOR_CKPT=str(root / "external/HaWoR/weights/external/detector.pt"),
        MANO_ROOT=str(assets / "mano"), HANDFLOW_NORMALIZATION_STATS=str(assets / "normalization_stats.npz"),
        TORCH_HOME=str(root / "data/models/handflow/torch"), TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD="1",
        PYTHONUNBUFFERED="1", PYTHONPATH=str(root / "src"), YOLO_AUTOINSTALL="false")
    command = [str(root / ".venv-handflow/bin/python"), str(root / "scripts/run_handflow_native.py"),
        "--video", str(prepared.video_path), "--output", str(output / "native"),
        "--intrinsics", *map(str, intrinsics), "--seed", str(settings["seed"]),
        "--frame-count", str(settings["frame_count"])]
    started = time.monotonic()
    try:
        with (output / "native-console.log").open("w") as log:
            subprocess.run(command, cwd=engine, env=environment, stdout=log, stderr=subprocess.STDOUT, check=True)
    finally:
        elapsed = time.monotonic() - started
        if (output / "native/native_report.json").exists():
            native = read_json(output / "native/native_report.json")
            report["native_inference"] = native
            report["components"].extend(combine_hand_stages(native["components"], settings["frame_count"]))
            overhead = elapsed - sum(row["wall_time_s"] for row in native["components"])
            report["components"].append({"name": "native_startup_shutdown_and_io", "status": native["status"],
                "wall_time_s": overhead, "effective_fps": settings["frame_count"] / overhead if overhead > 0 and native["status"] == "completed" else None,
                "processed_frames": None, "frame_unit": "process", "timing_note": "Subprocess elapsed minus measured native stages"})
    with np.load(output / "native/geometry.npz", allow_pickle=False) as archive:
        return dict(archive)
