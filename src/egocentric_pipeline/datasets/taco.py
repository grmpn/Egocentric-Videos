"""Read the official TACO V1 RGB, camera and MANO reference records.

Source files stay unchanged. Downloads use ZIP range reads through the existing
fsspec HTTP dependency, avoiding the unrelated recordings in large archives.
"""

from pathlib import Path
import shutil
import zipfile
import zlib


ARCHIVE_FILES = {
    "Egocentric_Camera_Parameters": ("egocentric_intrinsic.txt", "egocentric_frame_extrinsic.npy"),
    "Hand_Poses": ("left_hand.pkl", "left_hand_shape.pkl", "right_hand.pkl", "right_hand_shape.pkl"),
    "Egocentric_RGB_Videos": ("color.mp4",),
}


def download_sequences(clips, destination, revision, *, timeout_s=60):
    """Fetch selected official members, checking ZIP CRC on reuse and download.

    clips contain triplet and sequence_id; the returned paths retain the release
    layout. Existing mismatching inputs raise instead of being overwritten.
    Requires the maintained HaWoR environment's fsspec[http] installation.
    """
    import aiohttp
    import fsspec

    destination = Path(destination).resolve()
    records = []
    for archive_name, filenames in ARCHIVE_FILES.items():
        url = f"https://huggingface.co/datasets/leolyliu/TACO/resolve/{revision}/{archive_name}.zip"
        print(f"Opening {archive_name}.zip", flush=True)
        with fsspec.open(url, "rb", block_size=1024 * 1024,
                         client_kwargs={"trust_env": True, "timeout": aiohttp.ClientTimeout(total=timeout_s)}).open() as remote:
            with zipfile.ZipFile(remote) as archive:
                for clip in clips:
                    for filename in filenames:
                        member = f"{archive_name}/{clip['triplet']}/{clip['sequence_id']}/{filename}"
                        info = archive.getinfo(member)
                        target = destination / member
                        if not target.resolve().is_relative_to(destination):
                            raise ValueError(f"Invalid archive path: {member}")
                        reused = target.exists()
                        if reused:
                            checksum = 0
                            with target.open("rb") as stream:
                                for block in iter(lambda: stream.read(1024 * 1024), b""):
                                    checksum = zlib.crc32(block, checksum)
                            if target.stat().st_size != info.file_size or checksum != info.CRC:
                                raise ValueError(f"Source differs from official ZIP member; preserve and inspect: {target}")
                        else:
                            target.parent.mkdir(parents=True, exist_ok=True)
                            import os
                            import tempfile
                            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
                                temporary = Path(stream.name)
                                try:
                                    with archive.open(info) as source:
                                        shutil.copyfileobj(source, stream, length=1024 * 1024)
                                    stream.flush()
                                    # archive.open validates CRC at EOF. Publish without replacing an input.
                                    os.link(temporary, target)
                                finally:
                                    temporary.unlink(missing_ok=True)
                        print(f"{'Reused' if reused else 'Downloaded'} {member} ({info.file_size} bytes)", flush=True)
                        records.append({"path": str(target), "archive": archive_name + ".zip",
                                        "member": member, "size_bytes": info.file_size, "reused": reused})
    return {"repository": "leolyliu/TACO", "revision": revision, "files": records}


def source_paths(source_root, clip):
    """Locations of immutable source files for one sequence."""
    source_root = Path(source_root)
    suffix = Path(clip["triplet"]) / clip["sequence_id"]
    return {"video": source_root / "Egocentric_RGB_Videos" / suffix / "color.mp4",
            "hands": source_root / "Hand_Poses" / suffix,
            "intrinsics": source_root / "Egocentric_Camera_Parameters" / suffix / "egocentric_intrinsic.txt",
            "extrinsics": source_root / "Egocentric_Camera_Parameters" / suffix / "egocentric_frame_extrinsic.npy"}


def prepare_reference(settings, clip, prepared_root, reference_root, taco_root, model_paths):
    """Prepare a synchronized clip and reference using TACO's own MANO layer.

    MANO assets stay at their existing licensed locations. GT hand_trans denotes
    the wrist because the upstream layer is centered at joint 0 before adding it.
    TACO extrinsics are world-to-camera; all exported transforms are their inverse.
    """
    import pickle
    import sys

    import numpy as np
    import torch
    from scipy.spatial.transform import Rotation

    from egocentric_pipeline.evaluation.hand_trajectory import JOINT_ORDER, validate_trajectory
    from egocentric_pipeline.run_metadata import write_json
    from egocentric_pipeline.video.clip_request import ClipRequest
    from egocentric_pipeline.video.video_preparation import prepare_clip

    sys.path.insert(0, str(Path(taco_root).resolve() / "dataset_utils"))
    from manopth.manopth.manolayer import ManoLayer

    paths = source_paths(settings["source_root"], clip)
    intrinsics = np.loadtxt(paths["intrinsics"])
    extrinsics = np.load(paths["extrinsics"], allow_pickle=False)
    if intrinsics.shape != (3, 3) or extrinsics.ndim != 3 or extrinsics.shape[1:] != (4, 4):
        raise ValueError("Unexpected TACO camera arrays")
    start, count, fps = clip["start_frame"], settings["frame_count"], settings["fps"]
    request = ClipRequest.from_video(paths["video"], dataset="TACO V1", video_id=clip["sequence_id"],
        interval=(start / fps, (start + count) / fps), clip_id=clip["sequence_id"],
        task_label=clip["triplet"], license_reference="https://creativecommons.org/licenses/by/4.0/",
        focal_length_px=float((intrinsics[0, 0] + intrinsics[1, 1]) / 2))
    prepared = prepare_clip(request, Path(prepared_root))
    meta = prepared.metadata
    indices = np.array([row["source_frame_index"] for row in meta.frames["mapping"]])
    source_times = np.array([row["source_timestamp_s"] for row in meta.frames["mapping"]])
    times = np.array([row["timestamp_s"] for row in meta.frames["mapping"]])
    if (meta.source["frame_count"] != len(extrinsics)
            or not np.array_equal(indices, np.arange(start, start + count))
            or not np.allclose(source_times, indices / fps, atol=settings["timestamp_tolerance_s"], rtol=0)):
        raise ValueError("TACO RGB, camera arrays and requested consecutive frames are not synchronized")
    joints = np.full((count, 2, 21, 3), np.nan)
    rotations = np.full((count, 2, 3, 3), np.nan)
    valid = np.zeros((count, 2), bool)
    source_keys = []
    torch.set_num_threads(4)
    for h, side in enumerate(("left", "right")):
        with (paths["hands"] / f"{side}_hand.pkl").open("rb") as stream:
            poses = pickle.load(stream)
        with (paths["hands"] / f"{side}_hand_shape.pkl").open("rb") as stream:
            betas = pickle.load(stream)["hand_shape"].detach().cpu().numpy().reshape(10)
        keys = sorted(poses)
        if keys != [f"{i + 1:05d}" for i in range(len(extrinsics))]:
            raise ValueError(f"{side} reference frame keys disagree with camera/RGB indexing")
        source_keys.append([keys[i] for i in indices])
        pose = np.stack([poses[keys[i]]["hand_pose"].detach().cpu().numpy() for i in indices])
        translation = np.stack([poses[keys[i]]["hand_trans"].detach().cpu().numpy() for i in indices])
        valid[:, h] = np.isfinite(pose).all(axis=1) & np.isfinite(translation).all(axis=1)
        if not np.isfinite(betas).all():
            raise ValueError(f"Nonfinite {side} GT shape")
        layer = ManoLayer(mano_root=str(Path(model_paths[h]).resolve().parent), use_pca=False,
                          ncomps=45, side=side, center_idx=0)
        keep = valid[:, h]
        with torch.no_grad():
            _, output, _ = layer(torch.from_numpy(pose[keep].astype(np.float32)),
                                  torch.from_numpy(np.repeat(betas[None], keep.sum(), axis=0).astype(np.float32)))
        joints[keep, h] = output.numpy() / 1000 + translation[keep, None]
        np.testing.assert_allclose(joints[keep, h, 0], translation[keep], atol=1e-7, rtol=0)
        rotations[keep, h] = Rotation.from_rotvec(pose[keep, :3]).as_matrix()
    if source_keys[0] != source_keys[1]:
        raise ValueError("Left/right reference frame identities disagree")
    w2c = extrinsics[indices].astype(float)
    camera_valid = np.isfinite(w2c).all(axis=(1, 2))
    c2w = np.full_like(w2c, np.nan)
    c2w[camera_valid] = np.linalg.inv(w2c[camera_valid])
    local = np.einsum("tij,thkj->thki", w2c[:, :3, :3], joints) + w2c[:, None, None, :3, 3]
    valid &= camera_valid[:, None]
    data = {"timestamp_s": times, "frame_index": indices, "joint_order": np.array(JOINT_ORDER),
            "joints_camera_m": local, "joints_world_m": joints, "wrist_rotation_world": rotations,
            "camera_to_world": c2w, "hand_valid": valid, "camera_valid": camera_valid,
            "direct_valid": valid.copy(), "infilled": np.zeros_like(valid),
            "up_world": np.asarray(settings["gt_up_world"], dtype=float)}
    validate_trajectory(data)
    output = Path(reference_root) / clip["sequence_id"]
    output.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(output / "reference.npz", **data)
    camera_positions = c2w[camera_valid, :3, 3]
    camera_rotations = c2w[camera_valid, :3, :3]
    excursion = {"translation_range_m": np.ptp(camera_positions, axis=0).tolist(),
                 "max_translation_from_start_m": float(np.linalg.norm(camera_positions - camera_positions[0], axis=1).max()),
                 "max_rotation_from_start_deg": float(np.degrees(Rotation.from_matrix(camera_rotations[0].T @ camera_rotations).magnitude()).max())}
    info = {"clip": clip, "dataset_revision": settings["dataset_revision"],
            "video": str(prepared.video_path), "clip_metadata": str(prepared.metadata_path),
            "source_frame_count": len(extrinsics), "frame_count": count, "intrinsics": intrinsics.tolist(),
            "gt_up_world": settings["gt_up_world"], "source_hand_frame_keys": source_keys[0],
            "camera_motion": excursion, "gt_valid_hand_frames": int(valid.sum()),
            "validity_note": "Finite released fitted MANO poses; no independent joint-accuracy/confidence labels provided.",
            "hawor_calibration_limit": "Native single focal uses mean(fx,fy); native principal point is image center. Full released K is retained for reference projection and backends that accept it."}
    write_json(output / "input.json", info)
    return info
