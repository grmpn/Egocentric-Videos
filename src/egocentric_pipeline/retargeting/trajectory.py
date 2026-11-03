"""Aligned-trajectory loading and lossless solved-trajectory exports."""

from pathlib import Path
import time

import numpy as np

from egocentric_pipeline.retargeting.manipulation_regions import frame_edges
from egocentric_pipeline.run_metadata import read_json


def load_alignment(directory):
    """Consume the completed Part 1 contract and verify its prepared RGB timeline."""
    directory = Path(directory).resolve()
    report = read_json(directory / "alignment_report.json")
    if report["status"] != "completed" or report["hand_order"] != ["left", "right"]:
        raise ValueError("Require a completed left/right Part 1 alignment; inspect its report")
    with np.load(directory / "trajectory_aligned.npz", allow_pickle=False) as data:
        arrays = {key: data[key] for key in data.files}
    times, valid = arrays["timestamp_s"], arrays["export_valid"]
    frame_edges(times)
    n = len(times)
    if valid.shape != (n, 2) or valid.dtype != bool:
        raise ValueError("export_valid must be boolean [T,2] in left/right order")
    infilled = arrays.get("motion_infilled")
    if infilled is None or infilled.shape != (n, 2) or infilled.dtype != bool:
        raise ValueError("motion_infilled must be boolean [T,2]; regenerate alignment with hand provenance")
    wrists = arrays["wrist_position_aligned_m"]
    if wrists.shape != (n, 2, 3) or not np.isfinite(wrists[valid & ~infilled]).all() or not np.isnan(wrists[~valid]).all():
        raise ValueError("Physical wrists must be finite for non-infilled observations and NaN where export-invalid")
    rotation = arrays["rotation_aligned_from_world"]
    if (rotation.shape != (3, 3) or not np.allclose(rotation @ rotation.T, np.eye(3), atol=1e-8)
            or not np.isclose(np.linalg.det(rotation), 1, atol=1e-8)):
        raise ValueError("Aligned-from-world rotation must be proper and orthonormal")
    clip = read_json(report["inputs"]["clip_metadata"]["path"])
    mapping = clip["frames"]["mapping"]
    if (clip["prepared"]["frame_count"] != n or not np.array_equal(arrays["frame_index"], np.arange(n))
            or not np.array_equal(times, [f["timestamp_s"] for f in mapping])
            or not np.array_equal(arrays["source_timestamp_s"], [f["source_timestamp_s"] for f in mapping])):
        raise ValueError("Aligned trajectories and prepared RGB/source timestamps disagree")
    return arrays, report, clip


def save_retargeting(output, arrays, report, clip, *, render_video=True):
    """Shared lossless export and optional source-synchronized review artifacts."""
    from egocentric_pipeline.visualization.retargeting_visualization import annotate_video

    started = time.perf_counter()
    with (Path(output) / "trajectory_retargeted.npz").open("xb") as stream:
        np.savez_compressed(stream, **arrays)
    with np.load(Path(output) / "trajectory_retargeted.npz", allow_pickle=False) as restored:
        if any(restored[key].dtype != value.dtype or restored[key].tobytes() != value.tobytes()
               for key, value in arrays.items()):
            raise ValueError("Retargeted export failed exact reload verification")
    report["export_reload_exact"] = True
    report.setdefault("timing", {})["export_s"] = time.perf_counter() - started
    started = time.perf_counter()
    if render_video:
        annotate_video(output, arrays, report, clip)
    report["timing"]["visualization_s"] = time.perf_counter() - started
    report["video_rendered"] = render_video
