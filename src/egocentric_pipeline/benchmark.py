"""Report one finalized clip attempt; never discover or aggregate other runs."""

from pathlib import Path
from zipfile import BadZipFile

import numpy as np

from .run_metadata import read_json, redact, sha256_file, utc_now, write_json


ROLES = ("setup_smoke", "ego4d", "other_test")
FAILURE_LABELS = (
    "missed/false hand detection", "left/right identity error", "implausible hand depth or scale",
    "temporal jitter", "infiller discontinuity", "SLAM drift/failure", "world-trajectory jump",
    "mesh/image misalignment", "rendering failure", "other",
)


def _metric(value, reason):
    return {"value": value, "unavailable_reason": reason if value is None else None}


def _longest_span(mask):
    edges = np.diff(np.r_[False, mask, False].astype(np.int8))
    starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
    return int(np.max(ends - starts)) if starts.size else 0


def build_benchmark(manifest_path, role, *, review_status="pending", failure_labels=None,
                    notes=None, overwrite=False):
    """Generate the run's automatic report, or explicitly update its later review.

    Review is independent of execution status. A completed process is not a
    claim of trajectory accuracy, manual acceptance, or milestone completion.
    """
    if role not in ROLES:
        raise ValueError(f"Run role must be one of {ROLES}")
    if review_status not in ("pending", "complete", "not_possible"):
        raise ValueError("Review status must be pending, complete, or not_possible")
    labels = list(failure_labels or [])
    if any(label not in FAILURE_LABELS for label in labels):
        raise ValueError(f"Failure labels must be from {FAILURE_LABELS}")
    manifest_path = Path(manifest_path).resolve()
    manifest = read_json(manifest_path)
    run_directory = manifest_path.parent
    if manifest_path.name != "run_manifest.json" or manifest["run_id"] != run_directory.name:
        raise ValueError("Manifest identity must match its containing run directory")
    if manifest["status"] not in ("completed", "failed") or not manifest.get("finished_at"):
        raise ValueError("Benchmark requires a finalized successful or failed run manifest")
    paths = {"benchmark": run_directory / "benchmark.json", "report": run_directory / "benchmark_report.md"}
    if not overwrite and any(path.exists() for path in paths.values()):
        raise FileExistsError("This run already has a benchmark; explicitly update its review instead of overwriting it silently")
    if overwrite and paths["benchmark"].exists() and read_json(paths["benchmark"])["run_id"] != manifest["run_id"]:
        raise ValueError("Existing benchmark belongs to a different run")

    artifacts = manifest.get("artifacts", {})
    prep = manifest.get("preparation", {})
    resources = manifest.get("resources", {})
    count = prep.get("prepared", {}).get("frame_count")
    wall = manifest.get("wall_time_s")
    metrics = {
        "wall_time_s": _metric(wall, "Run duration unavailable"),
        "effective_fps": _metric(count / wall if count and wall and manifest["status"] == "completed" else None,
                                  "Requires a completed run and measured prepared frame count/duration"),
        "peak_process_tree_rss_bytes": _metric(resources.get("peak_process_tree_rss_bytes"), "Pipeline process RAM was not sampled"),
        "peak_process_gpu_memory_bytes": _metric(resources.get("peak_process_gpu_memory_bytes"), resources.get("process_gpu_memory_unavailable_reason", "GPU process memory was not sampled")),
        "peak_device_gpu_memory_bytes": _metric(resources.get("peak_device_gpu_memory_bytes"), resources.get("gpu_sampling_error") or "GPU device memory was not sampled"),
        "peak_device_gpu_utilization_percent": _metric(resources.get("peak_device_gpu_utilization_percent"), "GPU device utilization was not sampled"),
        "preparation_timing": _metric(prep.get("frames", {}).get("metrics"), "Preparation did not produce validated timing metadata"),
        "focal_length": _metric(prep.get("hawor_camera"), "Preparation did not produce camera metadata"),
    }
    violations = []
    failure = manifest.get("failure") or {}
    if failure.get("stage") in ("export", "validation"):
        violations.append("Pipeline structural validation failed: " + failure["message"])
    coverage = None
    export = artifacts.get("trajectory_world")
    export_reason = "No world export exists for this attempt"
    if export is not None:
        path = Path(export["path"]).resolve()
        if not path.is_relative_to(run_directory):
            raise ValueError("Trajectory artifact points outside this run; reports cannot consume another run's export")
        if not path.is_file() or sha256_file(path) != export["sha256"]:
            violations.append("Trajectory export is missing or its hash differs from the finalized manifest")
            export_reason = violations[-1]
        else:
            try:
                with np.load(path, allow_pickle=False) as arrays:
                    for name in ("direct_detection", "motion_infilled", "export_valid", "hawor_valid"):
                        if arrays[name].dtype != np.bool_ or arrays[name].shape != (count, 2):
                            raise ValueError(f"{name} must be a boolean array of shape ({count}, 2)")
                    coverage = {}
                    for hand_index, hand in enumerate(("left", "right")):
                        direct = arrays["direct_detection"][:, hand_index]
                        infilled = arrays["motion_infilled"][:, hand_index]
                        valid = arrays["export_valid"][:, hand_index]
                        native_valid = arrays["hawor_valid"][:, hand_index]
                        coverage[hand] = {
                            "frame_count": len(valid), "direct_detection_frames": int(direct.sum()),
                            "motion_infilled_frames": int(infilled.sum()), "hawor_invalid_frames": int((~native_valid).sum()),
                            "export_invalid_frames": int((~valid).sum()),
                            "longest_no_detection_s": _longest_span(~direct) / 30,
                            "longest_infilled_s": _longest_span(infilled) / 30,
                            "valid_provenance_coverage_fraction": float(((direct | infilled) & valid).sum() / valid.sum()) if valid.any() else None,
                            "coverage_unavailable_reason": None if valid.any() else "No export-valid frames for this hand",
                        }
            except (OSError, ValueError, KeyError, IndexError, TypeError, BadZipFile) as error:
                violations.append(f"Cannot read trajectory coverage: {error}")
                coverage = None
                export_reason = violations[-1]
    metrics["trajectory_coverage"] = _metric(coverage, export_reason)
    overlay = artifacts.get("overlay")
    overlay_verified = False
    if overlay is not None:
        try:
            path = Path(overlay["path"]).resolve()
            if not path.is_relative_to(run_directory):
                raise ValueError("Overlay artifact points outside this run")
            if not path.is_file() or sha256_file(path) != overlay["sha256"]:
                raise ValueError("Overlay is missing or its hash differs from the finalized manifest")
            overlay_verified = any(stage["name"] == "visualization" and stage["status"] == "completed"
                                   for stage in manifest.get("stages", []))
        except (OSError, ValueError, KeyError, TypeError) as error:
            violations.append(str(error))
    if not overlay_verified:
        review_status = "not_possible"
    limitations = [
        "World coordinates retain HaWoR's clip-local SLAM gauge; different clips are not aligned.",
        "No calibration or lens-distortion correction was performed; a default focal value is approximate.",
        "Validity and provenance describe pipeline output, not measured reconstruction accuracy.",
        "Resource peaks are sampled; GPU device samples include other applications. Process-tree RSS can double-count shared pages.",
    ]
    if review_status != "complete":
        limitations.append("Manual review is incomplete; this attempt is not accepted milestone evidence.")
    source = manifest.get("source") or manifest.get("request", {}).get("source")
    if not manifest.get("request", {}).get("license_reference"):
        limitations.append("No license reference is recorded; dataset-deliverable eligibility remains unverified.")
    benchmark = {
        "schema_version": "1.0", "created_at": utc_now(), "run_id": manifest["run_id"],
        "clip_id": manifest.get("clip_id"), "source": source, "role": role,
        "status": manifest["status"], "failure": manifest.get("failure"),
        "stages": manifest.get("stages", []), "upstream_stages": manifest.get("inference", {}).get("stages", []),
        "metrics": metrics, "structural_violations": violations,
        "resource_measurement_scope": resources.get("scope", "Not recorded"),
        "timing": manifest.get("timing", {}),
        "validation": manifest.get("validation", {}), "artifacts": artifacts,
        "manual_review": {"status": review_status, "failure_labels": labels, "notes": notes or ""},
        "environment": manifest.get("environment", {}),
        "environment_deviations": manifest.get("warnings", []) + ["Stock interactive viewer is disabled; the project calls HaWoR's rendering helpers separately."],
        "limitations": limitations, "manifest_sha256": sha256_file(manifest_path),
    }
    benchmark = redact(benchmark)
    report = _render_report(benchmark)
    write_json(paths["benchmark"], benchmark, overwrite=overwrite)
    with paths["report"].open("w" if overwrite else "x", encoding="utf-8") as stream:
        stream.write(report)
    return {key: str(path) for key, path in paths.items()}


def _render_report(benchmark):
    metrics = benchmark["metrics"]

    def display(name, scale=1, suffix=""):
        metric = metrics[name]
        return f"{metric['value'] / scale:.3f}{suffix}" if metric["value"] is not None else f"Unavailable: {metric['unavailable_reason']}"

    source = benchmark["source"] or {}
    lines = [f"# HaWoR baseline — {benchmark['run_id']}", "",
             f"Status: **{benchmark['status']}** · Role: `{benchmark['role']}` · Review: **{benchmark['manual_review']['status']}**", "",
             f"Clip: `{benchmark['clip_id']}` · Source: `{source.get('path', 'unavailable')}`", "",
             "| Measurement | Result |", "| --- | --- |",
             f"| Elapsed runtime (monotonic) | {display('wall_time_s', suffix=' s')} |",
             f"| Effective throughput | {display('effective_fps', suffix=' FPS')} |",
             f"| Peak sampled process-tree RAM | {display('peak_process_tree_rss_bytes', 1024**3, ' GiB')} |",
             f"| Peak sampled device GPU memory | {display('peak_device_gpu_memory_bytes', 1024**3, ' GiB')} |",
             f"| Peak sampled device GPU utilization | {display('peak_device_gpu_utilization_percent', suffix='%')} |", ""]
    focal = metrics["focal_length"]["value"]
    if focal:
        lines.append(f"Focal length: {focal['focal_length_px']} px; {focal.get('provenance', focal.get('quality', 'see JSON'))}. Calibration and lens correction were not applied.")
    timing = metrics["preparation_timing"]["value"]
    if timing:
        lines.append(f"Preparation: {timing['repeated_source_frame_count']} reused frames, {timing['dropped_source_frame_count']} dropped frames; maximum selection error {timing['max_absolute_timestamp_error_s']:.6f} s, maximum source gap {timing['max_source_frame_gap_s']:.6f} s.")
    lines.extend(["", "| Phase | Status | Elapsed time |", "| --- | --- | ---: |"])
    for stage in benchmark["stages"]:
        elapsed = stage.get("wall_time_s")
        duration = f"{elapsed:.3f} s" if elapsed is not None else "Not run" if stage["status"] == "not_run" else "Unavailable"
        lines.append(f"| {stage['name']} | {stage['status']} | {duration} |")
    lines.extend(["", "Phase durations use the monotonic clock. Total pipeline time also includes validation and bookkeeping; report generation and any prior source trimming are excluded."])
    lines.append("Resource scope: " + benchmark["resource_measurement_scope"] + ".")
    if benchmark["failure"]:
        lines.extend(["", f"Failure at **{benchmark['failure']['stage']}**: {benchmark['failure']['message']}"])
    coverage = metrics["trajectory_coverage"]["value"]
    if coverage:
        lines.extend(["", "| Hand | Detected | Infilled | Export-invalid | Longest infill |", "| --- | ---: | ---: | ---: | ---: |"])
        for hand, values in coverage.items():
            lines.append(f"| {hand} | {values['direct_detection_frames']} | {values['motion_infilled_frames']} | {values['export_invalid_frames']} | {values['longest_infilled_s']:.3f} s |")
    else:
        lines.extend(["", "Trajectory coverage: " + metrics["trajectory_coverage"]["unavailable_reason"] + "."])
    review = benchmark["manual_review"]
    lines.extend(["", "Review labels: " + (", ".join(review["failure_labels"]) or "none supplied") + ".",
                  review["notes"], "", "Limitations: " + " ".join(benchmark["limitations"]), ""])
    if benchmark["structural_violations"]:
        lines.append("Contract violations: " + "; ".join(benchmark["structural_violations"]))
    lines.extend(["", "Full stage timings, environment, hashes, unavailable-value reasons, and artifact paths: [benchmark.json](benchmark.json) and [run_manifest.json](run_manifest.json).", ""])
    return "\n".join(lines)
