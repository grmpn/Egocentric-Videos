"""Exercise real FFmpeg preparation without HaWoR, Torch, or downloaded data."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from egocentric_pipeline.clip_request import (
    ClipRequest, LocalVideoSource, add_request_arguments, request_from_arguments,
)
from egocentric_pipeline.run_metadata import sha256_file
from egocentric_pipeline.video_preparation import (
    PreparationQualityPolicy, load_prepared_clip, prepare_clip,
)


def make_video(path: Path, *, count: int = 12, rate: int = 60,
               width: int = 32, height: int = 24, filters: str | None = None,
               extra: list[str] | None = None) -> Path:
    pixels = np.stack([np.full((height, width, 3), 20 + index * 10, np.uint8) for index in range(count)])
    command = ["ffmpeg", "-v", "error", "-n", "-f", "rawvideo", "-pixel_format", "rgb24",
               "-video_size", f"{width}x{height}", "-framerate", str(rate), "-i", "pipe:0"]
    if filters:
        command += ["-vf", filters]
    command += ["-c:v", "libx264", "-crf", "0", "-preset", "ultrafast", "-bf", "0",
                "-pix_fmt", "yuv444p", *(extra or []), str(path)]
    result = subprocess.run(command, input=pixels.tobytes(), capture_output=True)
    assert result.returncode == 0, result.stderr.decode()
    return path


def decode_video(path: Path) -> np.ndarray:
    result = subprocess.run(["ffmpeg", "-v", "error", "-noautorotate", "-i", str(path),
                             "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"],
                            capture_output=True, check=True)
    return np.frombuffer(result.stdout, dtype=np.uint8).reshape(-1, 24, 32, 3)


def test_request_normalizes_intent_without_reading_video(tmp_path: Path) -> None:
    request = ClipRequest.from_video(tmp_path / "missing.MP4", dataset=" sample ")
    assert request.source.path == tmp_path / "missing.MP4"
    assert request.source.dataset == "sample"
    assert request.focal_length_px == 600
    assert request.focal_length_provenance == "hawor_default"
    assert request.to_dict() == request.as_dict()
    supplied = ClipRequest.from_video(tmp_path / "missing.mp4", focal_length_px=600)
    assert supplied.focal_length_provenance == "user_supplied"
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, required=True)
    add_request_arguments(parser)
    args = parser.parse_args(["--video", str(tmp_path / "test.mp4"), "--start-s", "0"])
    with pytest.raises(ValueError, match="both --start-s and --end-s"):
        request_from_arguments(args)


@pytest.mark.parametrize("field,value", [
    ("interval", (0, 0)), ("interval", (-1, 2)), ("interval", (0, float("nan"))),
    ("interval", (0, 1, 2)), ("focal_length_px", 0), ("focal_length_px", float("inf")),
    ("focal_length_px", True), ("clip_id", "../escape"), ("task_label", " "),
])
def test_invalid_request_fields(tmp_path: Path, field: str, value: object) -> None:
    with pytest.raises(ValueError):
        ClipRequest.from_video(tmp_path / "source.mp4", **{field: value})


def test_non_mp4_request_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="only local .mp4"):
        LocalVideoSource(tmp_path / "frames.tar")


def test_renamed_container_and_multiple_video_streams_are_rejected(tmp_path: Path) -> None:
    source = make_video(tmp_path / "source.mp4", count=3, rate=30)
    renamed = tmp_path / "renamed.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-n", "-i", str(source), "-c", "copy",
                    "-f", "matroska", str(renamed)], check=True)
    with pytest.raises(ValueError, match="not an MP4 container"):
        prepare_clip(ClipRequest.from_video(renamed), tmp_path / "renamed-out")
    multiple = tmp_path / "multiple.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-n", "-i", str(source), "-map", "0:v",
                    "-map", "0:v", "-c", "copy", str(multiple)], check=True)
    with pytest.raises(ValueError, match="exactly one usable"):
        prepare_clip(ClipRequest.from_video(multiple), tmp_path / "multiple-out")


def test_cfr_drop_half_open_mapping_and_reload(tmp_path: Path) -> None:
    source = make_video(tmp_path / "source.mp4")
    source_hash = sha256_file(source)
    request = ClipRequest.from_video(source, interval=(1 / 30, 5 / 30), focal_length_px=700,
                                     task_label="synthetic", dataset="fixture", video_id="cfr",
                                     license_reference="generated synthetic fixture")
    prepared = prepare_clip(request, tmp_path / "prepared")
    metadata = prepared.metadata
    assert prepared.metadata_path.is_file()
    assert metadata.to_dict() == json.loads(prepared.metadata_path.read_text())
    assert load_prepared_clip(prepared.metadata_path) == prepared
    assert prepare_clip(request, tmp_path / "prepared") == prepared
    assert sha256_file(source) == source_hash == metadata.source["sha256"]
    assert sha256_file(prepared.video_path) == metadata.prepared["sha256"]
    assert metadata.prepared["frame_count"] == 4
    assert (metadata.prepared["width"], metadata.prepared["height"]) == (32, 24)
    rows = metadata.frames["mapping"]
    assert [row["source_frame_index"] for row in rows] == [2, 4, 6, 8]
    assert metadata.selection["source_frame_bounds_inclusive"] == [2, 9]
    assert [row["timestamp_s"] for row in rows] == [index / 30 for index in range(4)]
    assert metadata.frames["metrics"]["dropped_source_frame_count"] == 4
    assert metadata.frames["metrics"]["repeated_source_frame_count"] == 0
    assert metadata.hawor_camera == {"focal_length_px": 700, "provenance": "user_supplied",
                                      "quality": "provided", "calibration_loaded": False,
                                      "lens_distortion_corrected": False}
    actual = decode_video(prepared.video_path).astype(float)
    expected = decode_video(source)[[2, 4, 6, 8]].astype(float)
    assert np.max(np.abs(actual - expected)) <= 2
    assert all(value is False for value in metadata.preparation["spatial_transforms_applied"].values())


def test_cfr_full_video_preserves_frame_count_and_duration(tmp_path: Path) -> None:
    source = make_video(tmp_path / "source.mp4", count=7, rate=30)
    prepared = prepare_clip(ClipRequest.from_video(source), tmp_path / "prepared")
    assert prepared.metadata.prepared["frame_count"] == 7
    assert prepared.metadata.prepared["duration_s"] == 7 / 30
    assert prepared.metadata.frames["metrics"]["duration_error_s"] == 0
    assert prepared.metadata.hawor_camera["quality"] == "approximate"
    assert prepared.metadata.hawor_camera["provenance"] == "hawor_default"
    assert prepared.metadata.frames["metrics"]["max_absolute_timestamp_error_s"] == 0


def test_vfr_output_pixels_use_mathematically_nearest_pts(tmp_path: Path) -> None:
    # PTS .025 and .043 both round to output tick1 in FFmpeg's fps filter.
    # Nearest to1/30 is .025; choosing the last rounded source would be wrong.
    expression = "if(eq(N,0),0,if(eq(N,1),25,if(eq(N,2),43,if(eq(N,3),65,if(eq(N,4),95,130)))))"
    source = make_video(tmp_path / "variable.mp4", count=6, rate=1000,
                        filters=f"setpts='{expression}'",
                        extra=["-fps_mode", "vfr", "-enc_time_base", "1:1000", "-video_track_timescale", "30000"])
    prepared = prepare_clip(ClipRequest.from_video(source), tmp_path / "prepared")
    assert prepared.metadata.source["timing_mode"] == "variable"
    rows = prepared.metadata.frames["mapping"]
    assert [row["source_frame_index"] for row in rows] == [0, 1, 3, 4]
    assert [row["source_timestamp_s"] for row in rows] == [0, .025, .065, .095]
    assert prepared.metadata.frames["metrics"]["duration_error_s"] < 1 / 30
    expected = decode_video(source)[[0, 1, 3, 4]].astype(float)
    actual = decode_video(prepared.video_path).astype(float)
    assert np.max(np.abs(actual - expected)) <= 2
    assert load_prepared_clip(prepared.metadata_path) == prepared


def test_repeated_frames_are_measured_and_policy_is_configurable(tmp_path: Path) -> None:
    source = make_video(tmp_path / "slow.mp4", count=3, rate=15)
    request = ClipRequest.from_video(source)
    with pytest.raises(ValueError, match="repeated_source_frame_fraction"):
        prepare_clip(request, tmp_path / "rejected")
    assert not (tmp_path / "rejected").exists()
    policy = PreparationQualityPolicy(max_repeated_frame_fraction=.5, max_timestamp_selection_error_s=1 / 30)
    prepared = prepare_clip(request, tmp_path / "allowed", policy)
    rows = prepared.metadata.frames["mapping"]
    assert [row["source_frame_index"] for row in rows] == [0, 0, 1, 1, 2, 2]
    assert [row["source_frame_reused"] for row in rows] == [False, True, False, True, False, True]
    assert prepared.metadata.frames["metrics"]["repeated_source_frame_fraction"] == .5
    assert load_prepared_clip(prepared.metadata_path) == prepared
    original_metadata = prepared.metadata_path.read_bytes()
    with pytest.raises(ValueError, match="repeated_source_frame_fraction"):
        load_prepared_clip(prepared.metadata_path, policy=PreparationQualityPolicy())
    assert load_prepared_clip(prepared.metadata_path, policy=policy) == prepared
    assert prepared.metadata_path.read_bytes() == original_metadata


def test_source_gap_and_selection_error_are_separate_limits(tmp_path: Path) -> None:
    slow = make_video(tmp_path / "slow.mp4", count=3, rate=5)
    with pytest.raises(ValueError, match="max_source_frame_gap_s"):
        prepare_clip(ClipRequest.from_video(slow), tmp_path / "gap",
                     PreparationQualityPolicy(max_repeated_frame_fraction=1, max_timestamp_selection_error_s=1))
    with pytest.raises(ValueError, match="max_source_frame_gap_s"):
        prepare_clip(ClipRequest.from_video(slow, interval=(0, .09)), tmp_path / "edge-gap",
                     PreparationQualityPolicy(max_repeated_frame_fraction=1, max_timestamp_selection_error_s=1))
    ordinary = make_video(tmp_path / "source.mp4", count=6, rate=30)
    with pytest.raises(ValueError, match="max_absolute_timestamp_error_s"):
        prepare_clip(ClipRequest.from_video(ordinary, interval=(.01, .15)), tmp_path / "error",
                     PreparationQualityPolicy(max_repeated_frame_fraction=1))
    with pytest.raises(ValueError, match="exceeds source duration"):
        prepare_clip(ClipRequest.from_video(ordinary, interval=(0, 3)), tmp_path / "bounds")


@pytest.mark.parametrize("geometry", ["non_square", "rotation", "odd_width"])
def test_spatial_correction_inputs_are_rejected(tmp_path: Path, geometry: str) -> None:
    source = make_video(tmp_path / "source.mp4", width=31 if geometry == "odd_width" else 32,
                        filters="setsar=2/1" if geometry == "non_square" else None)
    if geometry == "rotation":
        rotated = tmp_path / "rotated.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-n", "-display_rotation", "90", "-i", str(source),
                        "-c", "copy", str(rotated)], check=True)
        source = rotated
    with pytest.raises(ValueError, match="spatial|even"):
        prepare_clip(ClipRequest.from_video(source), tmp_path / "prepared")


def test_overwrite_and_changed_hash_refusal(tmp_path: Path) -> None:
    source = make_video(tmp_path / "source.mp4", rate=30)
    request = ClipRequest.from_video(source, clip_id="stable")
    prepared = prepare_clip(request, tmp_path / "prepared")
    original_metadata = prepared.metadata_path.read_bytes()
    with pytest.raises(FileExistsError, match="differs"):
        prepare_clip(replace(request, task_label="different"), tmp_path / "prepared")
    assert prepared.metadata_path.read_bytes() == original_metadata
    with prepared.video_path.open("ab") as handle:
        handle.write(b"tampered")
    with pytest.raises(ValueError, match="hash or probed"):
        load_prepared_clip(prepared.metadata_path)


def test_loader_checks_original_and_offline_mapping(tmp_path: Path) -> None:
    source = make_video(tmp_path / "source.mp4", rate=30)
    prepared = prepare_clip(ClipRequest.from_video(source), tmp_path / "prepared")
    with source.open("ab") as handle:
        handle.write(b"changed original")
    with pytest.raises(ValueError, match="Original source hash"):
        load_prepared_clip(prepared.metadata_path)
    source.rename(tmp_path / "source-offline.mp4")
    assert load_prepared_clip(prepared.metadata_path) == prepared
    data = prepared.metadata.to_dict()
    data["frames"]["mapping"][1]["source_frame_reused"] = True
    prepared.metadata_path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="reuse flags"):
        load_prepared_clip(prepared.metadata_path)


@pytest.mark.parametrize("group,key,value", [
    ("source", "kind", "frame_directory"),
    ("hawor_camera", "calibration_loaded", True),
    ("preparation", "commands", []),
    ("selection", "semantics", "closed"),
    ("frames", "mapping", []),
])
def test_loader_rejects_inconsistent_metadata_when_source_is_offline(
    tmp_path: Path, group: str, key: str, value: object,
) -> None:
    source = make_video(tmp_path / "source.mp4", count=3, rate=30)
    prepared = prepare_clip(ClipRequest.from_video(source), tmp_path / "prepared")
    source.rename(tmp_path / "source-offline.mp4")
    data = prepared.metadata.to_dict()
    data[group][key] = value
    prepared.metadata_path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_prepared_clip(prepared.metadata_path)


def test_standalone_cli_direct_video_without_sidecar(tmp_path: Path) -> None:
    source = make_video(tmp_path / "source.mp4", count=4, rate=30)
    repository = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, "scripts/prepare_clip.py", "--video", str(source),
                             "--prepared-root", str(tmp_path / "prepared"), "--clip-id", "cli"],
                            cwd=repository, env={**os.environ, "PYTHONPATH": str(repository / "src")},
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    prepared = load_prepared_clip(Path(result.stdout.strip()))
    assert prepared.metadata.request["constructor"] == "direct_video"
    assert prepared.metadata.prepared["frame_count"] == 4
