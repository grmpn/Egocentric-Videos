"""Timestamp-based camera seeds and contiguous positional-feasibility intervals.

Intervals are half-open frame indices [start, stop). Each frame owns the time
until the next timestamp; the last frame uses the median sample interval.
Unknown frames never pass and count toward gap duration, not observed coverage.
"""

import numpy as np
from scipy.ndimage import gaussian_filter1d


SEGMENTATION_SETTINGS = ("camera_smoothing_sigma_s", "camera_displacement_m", "camera_sustain_s",
                         "minimum_episode_s", "merge_adjacent_regions")


def frame_edges(timestamps):
    times = np.asarray(timestamps, dtype=np.float64)
    if times.ndim != 1 or len(times) < 2 or not np.isfinite(times).all() or np.any(np.diff(times) <= 0):
        raise ValueError("Need at least two finite, strictly increasing timestamps in seconds")
    return np.r_[times, times[-1] + np.median(np.diff(times))]


def camera_segments(camera, timestamps, settings):
    """Smooth only the seed signal; crossing frame closes the preceding segment."""
    edges = frame_edges(timestamps)
    camera = np.asarray(camera, dtype=np.float64)
    if camera.shape != (len(edges) - 1, 3) or not np.isfinite(camera).all():
        raise ValueError("Camera positions must be finite aligned-frame metres [T,3]")
    sigma = settings["camera_smoothing_sigma_s"]
    if sigma:
        dt = np.diff(timestamps)
        if not np.allclose(dt, np.median(dt), atol=1e-7, rtol=1e-5):
            raise ValueError("Camera smoothing requires uniform prepared timestamps; use sigma 0 for irregular samples")
        smooth = gaussian_filter1d(camera, sigma / np.median(dt), axis=0, mode="nearest")
    else:
        smooth = camera.copy()
    segments, start, n = [], 0, len(camera)
    while start < n:
        displacement = np.linalg.norm(smooth[start:, :2] - smooth[start, :2], axis=1)
        crossing, stop = None, n
        for offset, value in enumerate(displacement):
            frame = start + offset
            if value < settings["camera_displacement_m"]:
                crossing = None
            elif crossing is None:
                crossing = frame
            if crossing is not None and edges[frame + 1] - edges[crossing] >= settings["camera_sustain_s"] - 1e-10:
                stop = crossing + 1
                break
        duration = float(edges[stop] - edges[start])
        segments.append({"start": start, "stop": stop, "duration_s": duration,
                         "retained": duration >= settings["minimum_episode_s"] - 1e-10})
        start = stop
    return smooth, segments


def retained_regions(seeds, timestamps, merge_adjacent=False):
    """Merge exact adjacency only after duration filtering; retain seed indices.

    The original segmentation diagnostics (including discarded intervals) stay
    untouched. The first seed index also preserves RNG seeds for unmerged runs.
    """
    edges = frame_edges(timestamps)
    regions = []
    for index, seed in enumerate(seeds):
        if not seed["retained"]:
            continue
        if merge_adjacent and regions and regions[-1]["stop"] == seed["start"]:
            region = regions[-1]
            region["stop"] = seed["stop"]
            region["seed_indices"].append(index)
            region["duration_s"] = float(edges[region["stop"]] - edges[region["start"]])
        else:
            regions.append(dict(seed, seed_indices=[index]))
    return regions


def validate_selection(selection):
    """Optional manual review in zero-based source frames, with exclusive stop."""
    if selection is None:
        return
    if not isinstance(selection, dict) or set(selection) - {"frame_range", "excluded_hand_frames"}:
        raise ValueError("Selection supports frame_range and excluded_hand_frames only")
    bounds = selection.get("frame_range")
    if bounds is not None and (not isinstance(bounds, list) or len(bounds) != 2
            or any(type(x) is not int for x in bounds) or not 0 <= bounds[0] < bounds[1]):
        raise ValueError("frame_range must be [start, exclusive_stop] with nonnegative integers")
    excluded = selection.get("excluded_hand_frames", [])
    if not isinstance(excluded, list):
        raise ValueError("excluded_hand_frames must be a list of frame/hand entries")
    for item in excluded:
        if (not isinstance(item, dict) or set(item) != {"frame", "hand"}
                or type(item["frame"]) is not int or item["frame"] < 0
                or item["hand"] not in ("left", "right")):
            raise ValueError("Each excluded hand frame needs a nonnegative frame and left/right hand")


def select_manipulation_data(regions, observed, timestamps, selection=None):
    """Clip retained regions and copy eligibility; never edit source observations.

    Eligibility is [T,2] in left/right order. Apply before target smoothing in
    both fitting and evaluation so rejected samples cannot affect nearby targets.
    """
    validate_selection(selection)
    if selection is None:
        return regions, observed
    edges = frame_edges(timestamps)
    start, stop = selection.get("frame_range", [0, len(timestamps)])
    if stop > len(timestamps):
        raise ValueError("Selection frame_range exceeds the source frame count")
    selected = []
    for region in regions:
        a, b = max(start, region["start"]), min(stop, region["stop"])
        if a >= b:
            continue
        if b - a < 3:
            raise ValueError("Selected regions need at least three frames for acceleration scoring")
        selected.append(dict(region, start=a, stop=b, duration_s=float(edges[b] - edges[a])))
    if not selected:
        raise ValueError("Selection does not overlap any retained manipulation region")
    valid = observed.copy()
    for item in selection.get("excluded_hand_frames", []):
        frame = item["frame"]
        if not any(r["start"] <= frame < r["stop"] for r in selected):
            raise ValueError("Excluded hand frame must lie within a selected manipulation region")
        valid[frame, ("left", "right").index(item["hand"])] = False
    return selected, valid


def interval_metrics(start, stop, passed, observed, edges, settings):
    """Assess a contiguous interval; the percentage comparison is strictly >."""
    if not 0 <= start < stop <= len(passed):
        raise ValueError("Expected a nonempty in-bounds half-open interval")
    observed_count = int(np.count_nonzero(observed[start:stop]))
    passing_count = int(np.count_nonzero(passed[start:stop] & observed[start:stop]))
    mask = np.asarray(passed[start:stop]) & np.asarray(observed[start:stop])
    changes = np.diff(np.r_[False, ~mask, False].astype(int))
    begins, ends = np.flatnonzero(changes == 1) + start, np.flatnonzero(changes == -1) + start
    gap = float(np.max(edges[ends] - edges[begins], initial=0.))
    duration = float(edges[stop] - edges[start])
    fraction = passing_count / observed_count if observed_count else None
    return {"start": int(start), "stop": int(stop), "duration_s": duration,
            "observed_frames": observed_count, "passing_frames": passing_count,
            "observed_fraction": observed_count / (stop - start), "passing_fraction": fraction,
            "longest_nonpassing_s": gap,
            "accepted": bool(observed_count and passing_count > settings["minimum_feasible_fraction"] * observed_count
                             and gap <= settings["maximum_gap_s"] + 1e-10
                             and duration >= settings["minimum_episode_s"] - 1e-10)}
