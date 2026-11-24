"""Per-trial evidence and equal-hand, equal-clip benchmark summaries."""

import csv
from pathlib import Path

import numpy as np

from egocentric_pipeline.evaluation.hand_trajectory import (
    HANDS, evaluate_trajectory, level_world, load_trajectory, metric_support,
)
from egocentric_pipeline.run_metadata import read_json, write_json
from egocentric_pipeline.visualization.hand_benchmark import wrist_trajectories


LABELS = {
    "initial_wrist_error": "Initial wrist (mm)", "gt_camera_wrist_error": "GT-camera wrist (mm)",
    "rpe_0.5s": "RPE 0.5 s (mm)", "rpe_2s": "RPE 2 s (mm)", "rpe_4s": "RPE 4 s (mm)",
    "scale_ratio": "Scale ratio", "finger_pa_mpjpe": "Finger PA-MPJPE (mm)",
    "completeness": "Complete (%)", "direct_completeness": "Direct (%)",
    "infilled_completeness": "Infilled (%)", "camera_completeness": "Camera (%)",
    "end_to_end_fps": "End-to-end FPS", "peak_vram_gib": "Peak VRAM (GiB)",
}


def average(values):
    """Missing values remain absent; population SD describes these selected clips."""
    available = np.array([v for v in values if v is not None], dtype=float)
    if not np.isfinite(available).all():
        raise ValueError("Reports must use null, not nonfinite metric values")
    return {"mean": float(available.mean()) if len(available) else None,
            "std": float(available.std()) if len(available) else None,
            "count": len(available)}


def aggregate_trials(trials, methods, expected_clips):
    """Mean of hand scores per clip, then mean of clip scores per method."""
    result = {}
    for method in methods:
        selected = [row for row in trials if row["method"] == method]
        if len(selected) != expected_clips or len({row["sequence_id"] for row in selected}) != expected_clips:
            raise ValueError("Every method must account for each configured clip exactly once")
        metric_rows = {}
        for support in ("method", "common"):
            metric_rows[support] = {}
            for key in LABELS:
                if key in ("end_to_end_fps", "peak_vram_gib"):
                    continue
                values = []
                for row in selected:
                    report = row.get("scores", {}).get(support)
                    values.append(None if report is None else average(
                        [report["hands"][hand][key]["value"] for hand in HANDS])["mean"])
                metric_rows[support][key] = average(values)
        completed = [row for row in selected if row["status"] == "completed"]
        performance = {key: average([row["performance"].get(key) for row in completed])
                       for key in ("end_to_end_fps", "peak_vram_gib")}
        duration = sum(row["performance"]["wall_time_s"] for row in completed)
        peaks = [row["performance"]["peak_vram_gib"] for row in completed
                 if row["performance"].get("peak_vram_gib") is not None]
        result[method] = {"expected_clips": expected_clips, "completed_clips": len(completed),
            "status_counts": {status: sum(row["status"] == status for row in selected)
                              for status in sorted({row["status"] for row in selected})},
            **metric_rows, "performance": performance,
            "completed_run_throughput_fps": sum(row["frame_count"] for row in completed) / duration if duration else None,
            "worst_peak_vram_gib": max(peaks) if peaks else None,
            "all_attempt_wall_time_s": sum(row.get("performance", {}).get("wall_time_s", 0) for row in selected)}
    return result


def write_csv(path, rows, fields):
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def evaluate_benchmark(output_root, settings):
    """Score saved predictions; keep absent/failed trials explicit, including common support."""
    output_root = Path(output_root)
    methods = list(settings["methods"])
    comparison_methods = settings.get("comparison_methods", methods)
    if not comparison_methods or not set(comparison_methods).issubset(methods):
        raise ValueError("Common-support comparison must name configured methods")
    trials, hand_rows, component_rows, plot_curves = [], [], [], {}
    for clip in settings["clips"]:
        seq = clip["sequence_id"]
        reference = load_trajectory(output_root / "reference" / seq / "reference.npz")
        predictions, runs = {}, {}
        for method in methods:
            directory = output_root / method / seq
            report_path = directory / "run.json"
            run = read_json(report_path) if report_path.exists() else {"status": "not_run"}
            runs[method] = run
            if run["status"] == "completed":
                predictions[method] = load_trajectory(directory / "prediction.npz")
        # A missing comparison method provides no common support. The comparison
        # set is explicit, including the interim two-method report requested here.
        common = {name: np.ones_like(reference["hand_valid"]) for name in ("world", "local")}
        for method in comparison_methods:
            support = metric_support(predictions[method], reference) if method in predictions else {
                name: np.zeros_like(reference["hand_valid"]) for name in common}
            common = {name: common[name] & support[name] for name in common}
        for method in methods:
            run = runs[method]
            trial = {"method": method, "sequence_id": seq, "status": run["status"],
                     "frame_count": len(reference["timestamp_s"]), "failure": run.get("failure"),
                     "performance": run.get("performance", {}), "scores": {}}
            if method in predictions:
                for support_name, mask in (("method", None), ("common", common)):
                    report, curves = evaluate_trajectory(predictions[method], reference, settings, common_support=mask)
                    trial["scores"][support_name] = report
                    directory = output_root / method / seq
                    np.savez_compressed(directory / f"curves-{support_name}.npz", **curves)
                    for hand in HANDS:
                        for metric_name, values in report["hands"][hand].items():
                            hand_rows.append({"method": method, "sequence_id": seq, "support": support_name,
                                "hand": hand, "metric": metric_name, "low_motion_pairs": values.get("low_motion_pairs"),
                                **{key: values[key] for key in ("value", "samples", "unit", "reduction")}})
                    if seq == settings["plot_sequence_id"] and support_name == "method":
                        plot_curves[method] = curves
            for stage in run.get("components", []):
                component_rows.append({"method": method, "sequence_id": seq,
                    **{key: stage.get(key) for key in ("name", "wall_time_s", "effective_fps", "processed_frames", "frame_unit", "status", "timing_note")}})
            trials.append(trial)
    summary = aggregate_trials(trials, methods, len(settings["clips"]))
    setup_attempts = []
    for path in sorted((output_root / "setup-attempts").glob("*/run.json")):
        attempt = read_json(path)
        setup_attempts.append({"directory": str(path.parent),
            **{key: attempt.get(key) for key in ("method", "sequence_id", "status", "performance")},
            "failure": attempt.get("native_inference", {}).get("failure", attempt.get("failure"))})
    component_summary = []
    for method in methods:
        names = sorted({row["name"] for row in component_rows if row["method"] == method})
        for name in names:
            values = [row["effective_fps"] for row in component_rows
                      if row["method"] == method and row["name"] == name and row["status"] == "completed"]
            component_summary.append({"method": method, "component": name, **average(values)})
    report = {"settings": settings,
              "aggregation": "Mean of available hand metrics, then equal-weight clip mean; count and population SD retained. Missing is null.",
              "common_support_methods": comparison_methods, "trials": trials, "summary": summary,
              "component_summary": component_summary, "setup_attempts": setup_attempts}
    write_json(output_root / "evaluation.json", report, overwrite=True)
    write_csv(output_root / "per-hand.csv", hand_rows, ["method", "sequence_id", "support", "hand", "metric", "value", "samples", "unit", "reduction", "low_motion_pairs"])
    write_csv(output_root / "components.csv", component_rows, ["method", "sequence_id", "name", "wall_time_s", "effective_fps", "processed_frames", "frame_unit", "status", "timing_note"])
    write_csv(output_root / "component-averages.csv", component_summary, ["method", "component", "mean", "std", "count"])
    averages = [{"method": method, "support": support, "metric": key, **values}
                for method, result in summary.items() for support in ("method", "common", "performance")
                for key, values in result[support].items()]
    write_csv(output_root / "averages.csv", averages, ["method", "support", "metric", "mean", "std", "count"])
    per_clip = [{"method": row["method"], "sequence_id": row["sequence_id"], "status": row["status"],
                 "support": support, "metric": name,
                 **average([row["scores"][support]["hands"][hand][name]["value"] for hand in HANDS])}
                for row in trials for support in ("method", "common") if support in row["scores"]
                for name in row["scores"][support]["hands"]["left"]]
    write_csv(output_root / "per-clip.csv", per_clip, ["method", "sequence_id", "status", "support", "metric", "mean", "std", "count"])
    lines = ["# TACO hand-trajectory benchmark", "", f"{len(settings['clips'])} clips. Values are mean ± population SD [number of clips]; incomplete counts are explicit.",
             "Geometry averages hands within each clip first. Peak VRAM is sampled whole-device use, including its recorded idle baseline.", ""]
    for support in ("method", "common"):
        title = "Method valid support" if support == "method" else "Common valid support: " + ", ".join(comparison_methods)
        lines.extend([f"## {title}", "", "| Method | Completed | " + " | ".join(LABELS.values()) + " |",
                      "| --- | --- | " + " | ".join("---" for _ in LABELS) + " |"])
        for method, values in summary.items():
            cells = []
            for name in LABELS:
                stats = values["performance" if name in values["performance"] else support][name]
                cells.append("— [0]" if stats["mean"] is None else f"{stats['mean']:.2f} ± {stats['std']:.2f} [{stats['count']}]")
            lines.append(f"| {method} | {values['completed_clips']}/{values['expected_clips']} | " + " | ".join(cells) + " |")
        lines.append("")
    lines.extend(["## Component effective FPS", "", "Each component uses 150 / stage seconds. Actual processed frame counts and timing boundaries are in components.csv.",
                  "", "| Method | Component | Mean FPS | SD | Clips |", "| --- | --- | --- | --- | --- |"])
    for row in component_summary:
        mean = "—" if row["mean"] is None else f"{row['mean']:.2f}"
        std = "—" if row["std"] is None else f"{row['std']:.2f}"
        lines.append(f"| {row['method']} | {row['component']} | {mean} | {std} | {row['count']} |")
    lines.extend(["", "## Trial accounting", "", "| Method | Clip | Status | Failure |", "| --- | --- | --- | --- |"])
    for row in trials:
        lines.append(f"| {row['method']} | {row['sequence_id']} | {row['status']} | {str(row['failure'] or '').replace('|', '/')} |")
    if setup_attempts:
        lines.extend(["", "## Preserved setup attempts", "",
            "Setup failures are excluded from completed-trial means. Their full logs, timing and resource samples remain available; successful retries start from RGB again.", "",
            "| Method | Clip | Status | Seconds | Peak VRAM (GiB) | Failure | Evidence |",
            "| --- | --- | --- | --- | --- | --- | --- |"])
        for row in setup_attempts:
            performance = row["performance"] or {}
            lines.append(f"| {row['method']} | {row['sequence_id']} | {row['status']} | "
                f"{performance.get('wall_time_s')} | {performance.get('peak_vram_gib')} | "
                f"{str(row['failure'] or '').replace('|', '/')} | {row['directory']} |")
    (output_root / "comparison.md").write_text("\n".join(lines) + "\n")
    seq = settings["plot_sequence_id"]
    reference = level_world(load_trajectory(output_root / "reference" / seq / "reference.npz"))
    ground_truth = np.where((reference["hand_valid"] & reference["camera_valid"][:, None])[..., None],
                            reference["joints_world_m"][:, :, 0], np.nan)
    if plot_curves:
        wrist_trajectories(seq, ground_truth, plot_curves, output_root / "wrist-trajectories")
    return report
