"""Timestamp-based camera seeds and contiguous positional-feasibility intervals.

Intervals are half-open frame indices [start, stop). Each frame owns the time
until the next timestamp; the last frame uses the median sample interval.
Unknown frames never pass and count toward gap duration, not observed coverage.
"""

import numpy as np
from scipy.ndimage import gaussian_filter1d


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


def expand_region(seed, passed, observed, edges, settings):
    """Longest qualifying interval containing the seed; ties prefer earlier start.

    Long nonpassing runs bound the search. Enumerate endpoints only inside those
    bounds; prefix counts evaluate percentages without repeatedly scanning frames.
    Seed failure can be rescued by surrounding evidence but not by removing it.
    """
    n, start, stop = len(passed), seed["start"], seed["stop"]
    good = np.asarray(passed) & np.asarray(observed)
    changes = np.diff(np.r_[False, ~good, False].astype(int))
    begins, ends = np.flatnonzero(changes == 1), np.flatnonzero(changes == -1)
    lower, upper = 0, n
    for a, b in zip(begins, ends):
        if edges[b] - edges[a] <= settings["maximum_gap_s"] + 1e-10:
            continue
        if a < stop and b > start:
            # A seed may include just the short end of an otherwise long gap.
            a_inside, b_inside = max(a, start), min(b, stop)
            if edges[b_inside] - edges[a_inside] > settings["maximum_gap_s"] + 1e-10:
                return None
        if b <= start:
            lower = max(lower, int(np.searchsorted(edges, edges[b] - settings["maximum_gap_s"] - 1e-10)))
        elif a >= stop:
            upper = min(upper, int(np.searchsorted(edges, edges[a] + settings["maximum_gap_s"] + 1e-10, side="right") - 1))
    counts = np.r_[0, np.cumsum(good)]
    observations = np.r_[0, np.cumsum(observed)]
    best = None
    for a in range(lower, start + 1):
        # Descending stops find the longest admissible end for this start.
        for b in range(upper, stop - 1, -1):
            duration = edges[b] - edges[a]
            if best is not None and duration <= best["duration_s"] + 1e-10:
                break
            seen, hits = observations[b] - observations[a], counts[b] - counts[a]
            if not seen or hits <= settings["minimum_feasible_fraction"] * seen:
                continue
            metrics = interval_metrics(a, b, passed, observed, edges, settings)
            if metrics["accepted"]:
                best = metrics
                break
    return best


def select_disjoint_regions(candidates, evaluations, observed, edges, settings):
    """Prefer longest expansion, then observed count, then earliest seed.

    Remove already assigned frames and keep the longest qualifying remainder
    intersecting this seed. Recheck every trimmed interval and record the choice;
    each selected episode has one fixed transform and no overlapping frames.
    """
    eligible = [c for c in candidates if c["expanded"] is not None]
    ranked = sorted(eligible, key=lambda c: (-c["expanded"]["duration_s"],
                    -c["expanded"]["observed_frames"], c["seed"]["start"]))
    selected = []
    for candidate in ranked:
        region = candidate["expanded"]
        available = np.zeros(len(observed), bool)
        available[region["start"]:region["stop"]] = True
        for previous in selected:
            interval = previous["retained"]
            available[interval["start"]:interval["stop"]] = False
        changes = np.diff(np.r_[False, available, False].astype(int))
        choices = []
        for a, b in zip(np.flatnonzero(changes == 1), np.flatnonzero(changes == -1)):
            if a >= candidate["seed"]["stop"] or b <= candidate["seed"]["start"]:
                continue
            metrics = interval_metrics(a, b, evaluations[candidate["candidate_id"]]["frame_passed"], observed, edges, settings)
            if metrics["accepted"]:
                choices.append(metrics)
        candidate["retained"] = max(choices, key=lambda m: (m["duration_s"], -m["start"])) if choices else None
        candidate["selection"] = "selected" if choices else "overlapping_alternative"
        if choices:
            selected.append(candidate)
    return sorted(selected, key=lambda c: c["retained"]["start"])
