"""Perception stages for the controlled camera/wrist comparison.

Executed in isolated upstream environments by scripts/compare_trajectories.py.
All poses are camera-to-world, OpenCV camera axes, dense prepared-frame order.
Raw camera translations/depths retain model units until explicit metric scaling.
Shared MANO joints are metres, [frame, left/right, joint, xyz], without infilling.
"""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
import time

import numpy as np

from egocentric_pipeline.run_metadata import read_json, write_json


@contextmanager
def measure(report, name):
    """Time completed GPU work, including any host work inside the scope."""
    import torch

    cuda = torch.cuda.is_available()
    if cuda:
        torch.cuda.synchronize()
    started = time.perf_counter()
    try:
        yield
    finally:
        if cuda:
            torch.cuda.synchronize()
        report[name] = time.perf_counter() - started


def use_upstream(root):
    root = Path(root).resolve()
    sys.path.insert(0, str(root))
    os.chdir(root)


def image_paths(output):
    return sorted(map(str, (output / "input/rgb/extracted_images").glob("*.jpg")))


def hands(settings, output, report):
    """Run the native detector and camera-space estimator exactly once."""
    import torch
    from scipy.spatial.transform import Rotation
    from types import SimpleNamespace

    use_upstream(settings["hawor_root"])
    with measure(report, "imports_s"):
        from scripts.scripts_test_video.detect_track_video import detect_track_video
        from scripts.scripts_test_video.hawor_video import hawor_motion_estimation
        from egocentric_pipeline.tracking.world_export import _provenance
        from egocentric_pipeline.geometry.hand_geometry import load_mano_model, reconstruct_mano
    args = SimpleNamespace(video_path=str(output / "input/rgb.mp4"),
                           img_focal=settings["focal_px"],
                           checkpoint=str(Path(settings["hawor_root"]) / "weights/hawor/checkpoints/hawor.ckpt"))
    with measure(report, "detection_tracking_s"):
        start, end, native, _ = detect_track_video(args)
    if start != 0 or end != settings["expected_frames"]:
        raise ValueError("Extracted frames differ from the verified input timeline")
    with measure(report, "hand_estimation_s"):
        chunks, _ = hawor_motion_estimation(args, start, end, native)
    with measure(report, "geometry_export_s"):
        native = Path(native)
        direct, confidence, estimated, disagreements, _ = _provenance(native, end)
        joints = np.full((end, 2, 16, 3), np.nan, np.float32)
        vertices = np.full((end, 2, 778, 3), np.nan, np.float32)
        roots = np.full((end, 2, 3, 3), np.nan, np.float32)
        for hand, model_path in enumerate(("_DATA/data_left/mano_left/MANO_LEFT.pkl",
                                           "_DATA/data/mano/MANO_RIGHT.pkl")):
            model = load_mano_model(Path(settings["hawor_root"]) / model_path, hand)
            for indices in chunks.get(hand, []):
                data = read_json(native / "cam_space" / str(hand) / f"{indices[0]}_{indices[-1]}.json")
                trans = np.asarray(data["init_trans"], np.float32)[0]
                root = np.asarray(data["init_root_orient"], np.float32)[0]
                articulation = np.asarray(data["init_hand_pose"], np.float32)[0]
                beta = np.asarray(data["init_betas"], np.float32)[0]
                j, v = reconstruct_mano(model, trans, Rotation.from_matrix(root).as_rotvec(),
                                       Rotation.from_matrix(articulation.reshape(-1, 3, 3)).as_rotvec().reshape(-1, 45), beta)
                joints[indices, hand], vertices[indices, hand], roots[indices, hand] = j, v, root
        valid = direct & estimated & np.isfinite(joints).all(axis=(2, 3))
        np.savez(output / "hands.npz", joints_camera_m=joints, vertices_camera_m=vertices,
                 root_rotation_camera=roots, direct_detection=direct, estimated=estimated,
                 valid=valid, detector_confidence=confidence)
        report.update(observed_frames=valid.sum(axis=0).tolist(), handedness_disagreements=disagreements,
                      timing_note="Native detector and hand-estimator times include their model loading; no infiller run.")


def gravity(settings, output, report):
    """One shared first-frame gravity estimate, independent of all SLAM poses."""
    import torch
    import cv2
    from egocentric_pipeline.geometry.gravity_estimation import CHECKPOINT_SHA256
    from egocentric_pipeline.run_metadata import sha256_file

    with measure(report, "loading_s"):
        from geocalib import GeoCalib
        if sha256_file(settings["geocalib_checkpoint"]) != CHECKPOINT_SHA256:
            raise ValueError("Unexpected GeoCalib weights")
        model = GeoCalib(weights=settings["geocalib_checkpoint"]).cuda().eval()
        rgb = cv2.cvtColor(cv2.imread(image_paths(output)[0]), cv2.COLOR_BGR2RGB)
        image = torch.from_numpy(rgb).permute(2, 0, 1).cuda().float() / 255
    with measure(report, "inference_s"):
        result = model.calibrate(image, camera_model="pinhole",
                                 priors={"focal": torch.tensor(settings["focal_px"], device="cuda")})
    up = result["gravity"].vec3d[0].cpu().numpy().astype(float)
    if not np.isfinite(up).all() or np.linalg.norm(up) < 1e-8:
        raise ValueError("Invalid initial-frame gravity estimate")
    write_json(output / "gravity.json", {"reference_frame": 0, "up_camera": (up / np.linalg.norm(up)).tolist(),
                                          "pitch_deg": float(result["gravity"].pitch[0].cpu()) * 180 / np.pi,
                                          "roll_deg": float(result["gravity"].roll[0].cpu()) * 180 / np.pi})


def hawor(settings, output, report):
    """Unmodified HaWoR masked DROID-SLAM, separated from Metric3D inference."""
    import torch
    from scipy.spatial.transform import Rotation

    use_upstream(settings["hawor_root"])
    with measure(report, "imports_s"):
        from lib.pipeline import masked_droid_slam
    native_droid = masked_droid_slam.Droid
    def load_droid(args):
        with measure(report, "loading_s"):
            return native_droid(args)
    masked_droid_slam.Droid = load_droid
    paths = image_paths(output)
    metadata = read_json(output / "input.json")
    calib = np.array([settings["focal_px"], settings["focal_px"], metadata["width"] / 2, metadata["height"] / 2])
    masks = torch.from_numpy(np.load(output / f"input/rgb/tracks_0_{len(paths)}/model_masks.npy"))
    with measure(report, "tracking_with_loading_s"):
        droid, trajectory = masked_droid_slam.run_slam(paths, masks=masks, calib=calib)
    report["inference_s"] = report["tracking_with_loading_s"] - report["loading_s"]
    count = droid.video.counter.value
    indices = droid.video.tstamp[:count].cpu().numpy().astype(int)
    disparities = droid.video.disps_up[:count].cpu().numpy()
    poses = np.tile(np.eye(4), (len(trajectory), 1, 1))
    poses[:, :3, :3] = Rotation.from_quat(trajectory[:, 3:]).as_matrix()
    poses[:, :3, 3] = trajectory[:, :3]
    np.savez(output / "hawor_raw.npz", poses=poses, frame_index=np.arange(len(poses)),
             keyframe_index=indices, depth=1 / disparities, calib=calib)
    report.update(keyframes=len(indices), native_shape=list(disparities.shape[1:]),
                  timing_note="DROID constructor timed separately; inference_s excludes loading_s. Standard masked HaWoR settings.")


def metric_depth(settings, output, report):
    """Cache one Metric3D pass at each DROID keyframe for both scale fits."""
    import cv2

    use_upstream(settings["hawor_root"])
    raw = np.load(output / "hawor_raw.npz")
    indices, calib = raw["keyframe_index"], raw["calib"]
    paths = image_paths(output)
    metadata = read_json(output / "input.json")
    with measure(report, "loading_s"):
        sys.path.insert(0, str(Path(settings["hawor_root"]) / "thirdparty/Metric3D"))
        from metric import Metric3D
        model = Metric3D(str(Path(settings["hawor_root"]) / "thirdparty/Metric3D/weights/metric_depth_vit_large_800k.pth"))
    depths = []
    with measure(report, "inference_s"):
        for index in indices:
            depth = model(paths[index], calib.copy())
            depths.append(depth)
            print(f"Metric3D {len(depths)}/{len(indices)} frame {index}", flush=True)
    np.savez(output / "metric_depth.npz", frame_index=indices, depth_m=np.asarray(depths, np.float32))
    report["inference_frames"] = indices.tolist()


def lingbot(settings, output, report):
    """Native streaming LingBot, retaining every predicted camera pose."""
    import torch

    use_upstream(settings["lingbot_root"])
    with measure(report, "loading_s"):
        from lingbot_map.models.gct_stream import GCTStream
        from lingbot_map.utils.load_fn import load_and_preprocess_images
        from lingbot_map.utils.pose_enc import pose_encoding_to_extri_intri
        model = GCTStream(img_size=settings["lingbot_image_size"], patch_size=14,
                          enable_3d_rope=True, max_frame_num=1024, kv_cache_sliding_window=64,
                          kv_cache_scale_frames=settings["lingbot_scale_frames"],
                          kv_cache_cross_frame_special=True, kv_cache_include_scale_frames=True,
                          use_sdpa=True, camera_num_iterations=4)
        checkpoint = torch.load(settings["lingbot_checkpoint"], map_location="cpu", weights_only=True)
        model.load_state_dict(checkpoint.get("model", checkpoint), strict=True)
        del checkpoint
        model = model.cuda().eval()
    with measure(report, "preprocessing_s"):
        images = load_and_preprocess_images(image_paths(output), mode="crop",
                                            image_size=settings["lingbot_image_size"], patch_size=14)
    with measure(report, "inference_s"), torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
        predictions = model.inference_streaming(images, num_scale_frames=settings["lingbot_scale_frames"],
                                                keyframe_interval=settings["lingbot_keyframe_interval"],
                                                output_device=torch.device("cpu"))
    with measure(report, "export_s"):
        # LingBot's camera head is C2W, unlike the original VGGT/AMB3R head.
        c2w, intrinsics = pose_encoding_to_extri_intri(predictions["pose_enc"], images.shape[-2:])
        poses = np.tile(np.eye(4), (len(images), 1, 1))
        poses[:, :3] = c2w[0].float().numpy()
        indices = np.load(output / "hawor_raw.npz")["keyframe_index"]
        np.savez(output / "lingbot_raw.npz", poses=poses, frame_index=np.arange(len(poses)),
                 keyframe_index=indices, depth=predictions["depth"][0, indices, ..., 0].float().numpy(),
                 intrinsics=intrinsics[0].float().numpy())
        report.update(native_shape=list(images.shape[-2:]), attention="torch SDPA", precision="bfloat16",
                      keyframe_interval=settings["lingbot_keyframe_interval"], scale_frames=settings["lingbot_scale_frames"])


def amb3r(settings, output, report):
    """Native AMB3R-VO with read-only capture of its learned metric depth."""
    import torch

    use_upstream(settings["amb3r_root"])
    with measure(report, "loading_s"):
        from amb3r.model import AMB3R
        from slam.pipeline import AMB3R_VO
        from slam.datasets.demo import DemoDataset
        model = AMB3R()
        model.load_weights(settings["amb3r_checkpoint"])
        model = model.cuda().eval()
        pipeline = AMB3R_VO(model)
    with measure(report, "preprocessing_s"):
        _, views = DemoDataset(ROOT=str(output / "input/rgb/extracted_images"),
                               resolution=tuple(settings["amb3r_resolution"]))[0]
        images = views["images"].unsqueeze(0)
    indices = np.load(output / "hawor_raw.npz")["keyframe_index"]
    selected = set(map(int, indices))
    metric = {}
    active_indices = []
    decode_heads = model.front_end.decode_heads
    local_mapping = pipeline.local_mapping

    def capture_heads(*args, **kwargs):
        predictions = decode_heads(*args, **kwargs)
        for local, global_index in enumerate(active_indices):
            if global_index in selected:
                metric[global_index] = predictions["depth_metric"][0, local, ..., 0].detach().float().cpu().numpy().copy()
        return predictions

    def capture_mapping(views_all, cfg, init=False):
        nonlocal active_indices
        active_indices = (list(range(views_all["images"].shape[1])) if init else
                          pipeline.keyframe_memory.cur_kf_idx.tolist() +
                          list(range(views_all["start_idx"], views_all["end_idx"] + 1)))
        return local_mapping(views_all, cfg, init=init)

    # Instrument outputs only: never alter model predictions or keyframe updates.
    model.front_end.decode_heads = capture_heads
    pipeline.local_mapping = capture_mapping
    with measure(report, "inference_s"), torch.inference_mode():
        result = pipeline.run(images)
    with measure(report, "export_s"):
        if any(int(i) not in metric for i in indices):
            raise ValueError("AMB3R metric head did not cover all scale frames")
        poses = result.poses.cpu().numpy()
        depth = []
        for index in indices:
            points = result.pts[index].cpu().numpy()
            # z of R_c2w.T @ (point_world - t_c2w), paired to this image's pixels.
            depth.append((points - poses[index, :3, 3]) @ poses[index, :3, 2])
        np.savez(output / "amb3r_raw.npz", poses=poses, frame_index=np.arange(len(poses)),
                 keyframe_index=indices, depth=np.asarray(depth), depth_m=np.stack([metric[int(i)] for i in indices]),
                 map_update_count=result.iter.cpu().numpy())
        report.update(native_shape=list(images.shape[-2:]), precision="bfloat16",
                      metric_capture="Last front-end/backend depth_metric prediction for each selected frame; final VO geometry supplies matching raw depth.",
                      mapped_frames=int((result.iter > 0).sum()))


def scale(settings, output, report):
    """Shared Metric3D samples/procedure; one scalar for each complete camera path."""
    import cv2
    use_upstream(settings["hawor_root"])
    from lib.pipeline.est_scale import est_scale_hybrid
    from egocentric_pipeline.evaluation.trajectory_comparison import depth_to_droid_grid

    inputs = read_json(output / "input.json")
    raw = {name: np.load(output / f"{name}_raw.npz") for name in ("hawor", "lingbot", "amb3r")}
    metric = np.load(output / "metric_depth.npz")
    indices = metric["frame_index"]
    for name, arrays in raw.items():
        if not np.array_equal(arrays["keyframe_index"], indices):
            raise ValueError(f"{name} scale-frame indices differ")
    masks = np.load(output / f"input/rgb/tracks_0_{inputs['frame_count']}/model_masks.npy", mmap_mode="r")
    source_shape = (inputs["height"], inputs["width"])
    scales = {name: {"per_frame": [], "fit_time_s": 0.0} for name in raw}
    with measure(report, "fit_s"):
        for local, frame in enumerate(indices):
            target = depth_to_droid_grid(metric["depth_m"][local], source_shape)
            prediction = {"hawor": raw["hawor"]["depth"][local],
                          "lingbot": depth_to_droid_grid(raw["lingbot"]["depth"][local], source_shape)}
            mask = depth_to_droid_grid(masks[frame].astype(np.float32), source_shape) >= .5
            good = np.isfinite(target) & (target > 0)
            for p in prediction.values():
                good &= np.isfinite(p) & (p > 0)
            mask |= ~good
            near, far = settings["scale_near_m"], settings["scale_far_m"]
            for attempt in range(settings["scale_max_expansions"] + 1):
                values = {}
                if np.count_nonzero(~mask & (target > near) & (target < far)) >= 32:
                    for name, p in prediction.items():
                        started = time.perf_counter()
                        values[name] = est_scale_hybrid(np.where(good, p, 1).astype(np.float32),
                                                        np.where(good, target, 1).astype(np.float32),
                                                        sigma=settings["scale_sigma_m"], msk=mask.astype(np.uint8),
                                                        near_thresh=near, far_thresh=far)
                        scales[name]["fit_time_s"] += time.perf_counter() - started
                    if all(np.isfinite(v) and v > 0 for v in values.values()):
                        break
                near -= .1; far += .1
            else:
                raise ValueError(f"No valid shared depth scale on frame {frame}")
            for name, value in values.items():
                scales[name]["per_frame"].append({"frame": int(frame), "scale": float(value), "near_m": near, "far_m": far,
                                                "pixels": int(np.count_nonzero(~mask & (target > near) & (target < far)))})
            # AMB3R uses its own learned metric signal and its native cropped FOV.
            started = time.perf_counter()
            p, target = raw["amb3r"]["depth"][local], raw["amb3r"]["depth_m"][local]
            width, height = settings["amb3r_resolution"]
            crop_width = round(source_shape[0] * width / height)
            left = (source_shape[1] - crop_width) // 2
            hand_mask = cv2.resize(masks[frame, :, left:left + crop_width].astype(np.uint8), (width, height), interpolation=cv2.INTER_NEAREST)
            good = np.isfinite(p) & np.isfinite(target) & (p > 0) & (target > 0) & (hand_mask == 0)
            if good.sum() < 32:
                raise ValueError(f"Insufficient AMB3R metric support on frame {frame}")
            value = float(np.median(target[good] / p[good]))
            scales["amb3r"]["fit_time_s"] += time.perf_counter() - started
            scales["amb3r"]["per_frame"].append({"frame": int(frame), "scale": value, "pixels": int(good.sum())})
    for name, item in scales.items():
        item["scale"] = float(np.median([row["scale"] for row in item["per_frame"]]))
        item["source"] = "AMB3R learned metric depth" if name == "amb3r" else "shared Metric3D"
    write_json(output / "scales.json", scales)


def evaluate(settings, output, report):
    from egocentric_pipeline.evaluation.trajectory_comparison import evaluate as run_evaluation
    run_evaluation(settings, output, report)


STAGES = {"hands": hands, "gravity": gravity, "hawor": hawor, "metric_depth": metric_depth,
          "lingbot": lingbot, "amb3r": amb3r, "scale": scale, "evaluate": evaluate}
