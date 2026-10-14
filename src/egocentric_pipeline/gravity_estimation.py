"""Sharp-frame GeoCalib inference; RGB pixels are never geometrically modified."""

import importlib.metadata
import json
from pathlib import Path

import cv2
import numpy as np

from .run_metadata import sha256_file


GEOCALIB_REVISION = "747054d743ca64bf4b0055c26ab709fa6d234996"
CHECKPOINT_SHA256 = "86d6aeacd8bbd974c59ce39f61854e00d36911c732ad89be471476fd708722ac"


def select_sharp_frames(scores, fraction, minimum):
    """HuRo's count rule with deterministic ties (earlier prepared frame wins)."""
    scores = np.asarray(scores, dtype=np.float64)
    if (scores.ndim != 1 or not len(scores) or not np.isfinite(scores).all()
            or not 0 < fraction <= 1 or not isinstance(minimum, int) or minimum < 1):
        raise ValueError("Invalid sharpness scores or frame-selection settings")
    count = max(int(len(scores) * fraction), min(minimum, len(scores)))
    return np.sort(np.argsort(-scores, kind="stable")[:count])


def read_video_frames(video, frame_count, indices=None):
    """Yield exact decoded frame indices; reject truncation or extra frames."""
    selected = set(range(frame_count)) if indices is None else set(map(int, indices))
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise ValueError(f"Cannot open prepared video: {video}")
    try:
        for index in range(frame_count):
            success, bgr = capture.read()
            if not success:
                raise ValueError(f"Prepared video truncated at frame {index}")
            if index in selected:
                yield index, bgr
        if capture.read()[0]:
            raise ValueError("Prepared video has extra frames")
    finally:
        capture.release()


def predict_up(video, clip, checkpoint, settings, diagnostics, *, device="cuda"):
    """Populate diagnostics incrementally, including failed/filtered predictions.

    Single-frame public API preserves HuRo's independent focal-prior calibration
    while keeping memory bounded. No model or checkpoint download occurs here.
    """
    import torch
    from geocalib import GeoCalib

    checkpoint = Path(checkpoint)
    actual_hash = sha256_file(checkpoint)
    if actual_hash != CHECKPOINT_SHA256:
        raise ValueError("GeoCalib checkpoint differs from the pinned v1.0 pinhole model; see environment/README.md")
    distribution = importlib.metadata.distribution("geocalib")
    direct = json.loads(distribution.read_text("direct_url.json") or "{}")
    if direct.get("vcs_info", {}).get("commit_id") != GEOCALIB_REVISION:
        raise ValueError("Install environment/gravity-requirements.txt; GeoCalib revision differs")
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable; check GPU access or select --device cpu")
    torch.set_num_threads(settings["torch_threads"])
    count = clip["prepared"]["frame_count"]
    scores = np.array([cv2.Laplacian(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
                       for _, bgr in read_video_frames(video, count)])
    indices = select_sharp_frames(scores, settings["sharp_fraction"], settings["min_sharp_frames"])
    diagnostics.update(checkpoint={"path": str(checkpoint.resolve()), "sha256": actual_hash},
                       geocalib_revision=GEOCALIB_REVISION, device=device,
                       sharpness=scores.tolist(), selected_frame_indices=indices.tolist(), frames=[])
    model = GeoCalib(weights=str(checkpoint)).to(device).eval()
    focal = torch.tensor(clip["hawor_camera"]["focal_length_px"], device=device)
    for index, bgr in read_video_frames(video, count, indices):
        row = {"frame_index": index, "sharpness": float(scores[index])}
        diagnostics["frames"].append(row)
        if bgr.shape[:2] != (clip["prepared"]["height"], clip["prepared"]["width"]):
            raise ValueError("Decoded frame dimensions differ from prepared geometry")
        image = torch.from_numpy(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)).permute(2, 0, 1).to(device, torch.float32) / 255
        try:
            result = model.calibrate(image, camera_model="pinhole", priors={"focal": focal})
        except Exception as error:
            row.update(accepted=False, reason="inference_failed", error=str(error))
            raise
        gravity = result["gravity"]
        up = gravity.vec3d[0].detach().cpu().numpy().astype(np.float64)
        pitch = float(gravity.pitch[0].cpu())
        roll = float(gravity.roll[0].cpu())
        if not np.isfinite([*up, pitch, roll]).all() or np.linalg.norm(up) < 1e-8:
            row.update(accepted=False, reason="nonfinite_or_degenerate_prediction")
        else:
            reason = "accepted" if pitch < 0 and abs(np.degrees(roll)) <= settings["max_roll_degrees"] else "pitch_or_roll_filter"
            row.update(up_camera=(up / np.linalg.norm(up)).tolist(), pitch_degrees=float(np.degrees(pitch)),
                       roll_degrees=float(np.degrees(roll)), accepted=reason == "accepted", reason=reason)
        print(f"GeoCalib frame {index}: {row['reason']}", flush=True)
    return [row for row in diagnostics["frames"] if row["accepted"]]
