"""Create auditable 30 FPS MP4s by selecting the nearest source presentation frame.

FFmpeg owns decoding and encoding. Python only routes complete RGB frame buffers
according to the recorded PTS map; no spatial or coordinate transform is applied.
"""

from __future__ import annotations

import bisect
import hashlib
import json
import math
import re
import statistics
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any

from .clip_request import ClipRequest
from .run_metadata import read_json, sha256_file, utc_now, write_json


SCHEMA_VERSION = "1.0"
PREPARATION_VERSION = "nearest_pts_v1"
FPS = 30
SPATIAL_TRANSFORMS = {
    name: False for name in ("rectification", "crop", "pad", "resize", "rotation",
                            "undistortion", "other")
}


@dataclass(frozen=True)
class PreparationQualityPolicy:
    """Approved limits; errors and gaps are in unscaled source seconds."""

    max_repeated_frame_fraction: float = 0.05
    max_source_frame_gap_s: float = 0.10
    max_timestamp_selection_error_s: float = 1 / 60

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and nonnegative")
        if self.max_repeated_frame_fraction > 1:
            raise ValueError("max_repeated_frame_fraction must be at most 1")


@dataclass(frozen=True)
class ClipMetadata:
    """Owned schema groups; all timestamps are seconds, dimensions are pixels."""

    request: dict[str, Any]
    source: dict[str, Any]
    selection: dict[str, Any]
    preparation: dict[str, Any]
    prepared: dict[str, Any]
    hawor_camera: dict[str, Any]
    frames: dict[str, Any]
    artifacts: dict[str, Any]
    created_at: str
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PreparedClip:
    video_path: Path
    metadata_path: Path
    metadata: ClipMetadata


@dataclass(frozen=True)
class _Video:
    stream: dict[str, Any]
    timestamps: list[Fraction]
    origin: Fraction
    duration: Fraction
    probe_command: list[str]


def _run(command: list[str]) -> str:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode or result.stderr.strip():
        raise RuntimeError(f"Media command failed: {command!r}\n{result.stderr.strip()}")
    return result.stdout


def _ratio(value: Any) -> Fraction | None:
    if value in (None, "N/A", "0/0", "0:1"):
        return None
    return Fraction(str(value).replace(":", "/"))


def _validate_geometry(stream: dict[str, Any], frames: list[dict[str, Any]]) -> None:
    width, height = stream.get("width"), stream.get("height")
    if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
        raise ValueError("Source has invalid image dimensions")
    if width % 2 or height % 2:
        raise ValueError("Source dimensions must be even for H.264 yuv420p; resizing/padding is outside Milestone 1")
    if _ratio(stream.get("sample_aspect_ratio")) not in (None, Fraction(1)):
        raise ValueError("Non-square source pixels require a spatial correction outside Milestone 1")
    display_ratio = _ratio(stream.get("display_aspect_ratio"))
    if display_ratio is not None and display_ratio != Fraction(width, height):
        raise ValueError("Source display aspect ratio requires a spatial correction outside Milestone 1")
    rotations = [stream.get("tags", {}).get("rotate", 0)]
    for side_data in stream.get("side_data_list", []):
        if "rotation" in side_data:
            rotations.append(side_data["rotation"])
        if "displaymatrix" in side_data:
            matrix = [int(value) for line in side_data["displaymatrix"].strip().splitlines()
                      for value in line.split(":", 1)[1].split()]
            if matrix != [65536, 0, 0, 0, 65536, 0, 0, 0, 1073741824]:
                raise ValueError("Source display matrix requires rotation/mirroring or another spatial correction")
    if any(not math.isfinite(float(rotation)) or float(rotation) % 360 != 0 for rotation in rotations):
        raise ValueError("Source display rotation requires spatial correction outside Milestone 1")
    for frame in frames:
        if (frame.get("width"), frame.get("height")) != (width, height):
            raise ValueError("Source changes image dimensions during decoding")
        if frame.get("interlaced_frame", 0):
            raise ValueError("Interlaced video requires deinterlacing outside Milestone 1")
        if _ratio(frame.get("sample_aspect_ratio")) not in (None, Fraction(1)):
            raise ValueError("Source contains frames with non-square pixels")


def _probe(path: Path) -> _Video:
    if not path.is_file() or path.suffix.lower() != ".mp4":
        raise ValueError(f"Supply an existing readable local .mp4: {path}")
    command = ["ffprobe", "-v", "error", "-select_streams", "v", "-show_streams",
               "-show_format", "-show_frames", "-show_entries",
               "frame=pts,width,height,interlaced_frame,sample_aspect_ratio:stream:format",
               "-of", "json", str(path)]
    data = json.loads(_run(command))
    streams = data.get("streams", [])
    if len(streams) != 1 or streams[0].get("disposition", {}).get("attached_pic", 0):
        raise ValueError("Source must contain exactly one usable video stream")
    if "mp4" not in data.get("format", {}).get("format_name", "").split(","):
        raise ValueError("Source is not an MP4 container; renaming a file is insufficient")
    stream, frames = streams[0], data.get("frames", [])
    if not frames:
        raise ValueError("Source has no decodable video frames")
    _validate_geometry(stream, frames)
    time_base = _ratio(stream.get("time_base"))
    if time_base is None or time_base <= 0 or any(type(frame.get("pts")) is not int for frame in frames):
        raise ValueError("Source needs an explicit positive time base and presentation timestamp for every frame")
    pts = [frame["pts"] * time_base for frame in frames]
    if any(second <= first for first, second in zip(pts, pts[1:])):
        raise ValueError("Source presentation timestamps must be strictly increasing")
    if "start_pts" not in stream or stream["start_pts"] * time_base != pts[0]:
        raise ValueError("Source stream start does not match its first decoded presentation timestamp")
    if type(stream.get("duration_ts")) is not int:
        raise ValueError("Source must provide a video-stream duration in its time base")
    duration = stream["duration_ts"] * time_base
    timestamps = [value - pts[0] for value in pts]
    if duration <= timestamps[-1] or duration <= 0:
        raise ValueError("Source duration does not cover its decoded presentation timestamps")
    if stream.get("nb_frames") not in (None, "N/A") and int(stream["nb_frames"]) != len(frames):
        raise ValueError("Decoded frame count disagrees with the source stream; source may be corrupt")
    return _Video(stream, timestamps, pts[0], duration, command)


def _source_metadata(request: ClipRequest, video: _Video, source_hash: str) -> dict[str, Any]:
    stream = video.stream
    gaps = [float(b - a) for a, b in zip(video.timestamps, video.timestamps[1:])]
    tick = float(_ratio(stream["time_base"]))
    return {
        **request.source.to_dict(), "sha256": source_hash,
        "license_reference": request.license_reference,
        "codec": stream["codec_name"], "pixel_format": stream["pix_fmt"],
        "width": stream["width"], "height": stream["height"],
        "display_rotation_degrees": 0,
        "sample_aspect_ratio": stream.get("sample_aspect_ratio"),
        "display_aspect_ratio": stream.get("display_aspect_ratio"),
        "unspecified_sample_aspect_ratio_assumed_square": _ratio(stream.get("sample_aspect_ratio")) is None,
        "time_base": stream["time_base"], "duration_s": float(video.duration),
        "presentation_timestamp_origin_s": float(video.origin),
        "nominal_frame_rate": stream.get("r_frame_rate"),
        "average_frame_rate": stream.get("avg_frame_rate"),
        "frame_count": len(video.timestamps),
        "timing_mode": "constant" if not gaps or max(gaps) - min(gaps) <= tick + 1e-12 else "variable",
        "median_frame_interval_s": statistics.median(gaps) if gaps else None,
    }


def _select_frames(video: _Video, request: ClipRequest, policy: PreparationQualityPolicy) -> tuple[dict[str, Any], dict[str, Any]]:
    start, end = (Fraction(0), video.duration) if request.interval is None else tuple(Fraction(str(value)) for value in request.interval)
    if end > video.duration and float(end - video.duration) > 1e-12:
        raise ValueError(f"Requested end {float(end):.9g}s exceeds source duration {float(video.duration):.9g}s")
    if abs(float(end - video.duration)) <= 1e-12:
        end = video.duration
    # Account only for binary-float roundoff at exact source timestamp boundaries.
    for value in video.timestamps:
        if abs(float(start - value)) <= 1e-12:
            start = value
        if abs(float(end - value)) <= 1e-12:
            end = value
    indices = [index for index, value in enumerate(video.timestamps) if start <= value < end]
    if not indices:
        raise ValueError("The selected half-open interval contains no source presentation frames")
    considered = [video.timestamps[index] for index in indices]
    count = math.ceil((end - start) * FPS)
    mapping: list[dict[str, Any]] = []
    for frame_index in range(count):
        timestamp = Fraction(frame_index, FPS)
        target = start + timestamp
        following = bisect.bisect_left(considered, target)
        candidates = [index for index in (following - 1, following) if 0 <= index < len(considered)]
        selected = min(candidates, key=lambda index: (abs(considered[index] - target), considered[index]))
        source_index, source_timestamp = indices[selected], considered[selected]
        mapping.append({
            "frame_index": frame_index, "timestamp_s": float(timestamp),
            "source_frame_index": source_index, "source_timestamp_s": float(source_timestamp),
            "timestamp_selection_error_s": float(source_timestamp - target),
            "source_frame_reused": bool(mapping and mapping[-1]["source_frame_index"] == source_index),
        })
    unique = len({row["source_frame_index"] for row in mapping})
    errors = [abs(row["timestamp_selection_error_s"]) for row in mapping]
    # Include source gaps crossing a selection edge: trimming inside a long
    # hold does not make the underlying source timing denser.
    gaps = [float(b - a) for a, b in zip(video.timestamps, video.timestamps[1:])
            if a < end and b > start]
    metrics = {
        "source_frames_considered": len(indices), "unique_source_frames_selected": unique,
        "dropped_source_frame_count": len(indices) - unique,
        "repeated_source_frame_count": count - unique,
        "repeated_source_frame_fraction": (count - unique) / count,
        "median_absolute_timestamp_error_s": statistics.median(errors),
        "max_absolute_timestamp_error_s": max(errors),
        "max_source_frame_gap_s": max(gaps, default=0.0),
        "source_selected_duration_s": float(end - start),
        "prepared_duration_s": count / FPS,
        "duration_error_s": float(Fraction(count, FPS) - (end - start)),
    }
    _check_policy(metrics, policy)
    selection = {
        "requested_interval_s": None if request.interval is None else list(request.interval),
        "resolved_interval_s": [float(start), float(end)], "semantics": "[start_s, end_s)",
        "source_frame_bounds_inclusive": [indices[0], indices[-1]],
        "source_timestamp_bounds_s": [float(considered[0]), float(considered[-1])],
    }
    return selection, {"mapping": mapping, "metrics": metrics}


def _check_policy(metrics: dict[str, Any], policy: PreparationQualityPolicy) -> None:
    checks = (
        ("repeated_source_frame_fraction", policy.max_repeated_frame_fraction),
        ("max_source_frame_gap_s", policy.max_source_frame_gap_s),
        ("max_absolute_timestamp_error_s", policy.max_timestamp_selection_error_s),
    )
    for name, limit in checks:
        value = metrics[name]
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 or value > limit + 1e-12:
            raise ValueError(f"Preparation timing limit exceeded: {name}={value!r}, limit={limit}; select a better-timed interval/source")
    if not 0 <= metrics["duration_error_s"] < 1 / FPS + 1e-12:
        raise ValueError("Prepared duration must differ by less than one 30 FPS frame without changing speed")


def _encode_frames(source: Path, video: _Video, mapping: list[dict[str, Any]], output: Path) -> list[list[str]]:
    first, last = mapping[0]["source_frame_index"], mapping[-1]["source_frame_index"]
    width, height = video.stream["width"], video.stream["height"]
    decode = ["ffmpeg", "-v", "error", "-nostdin", "-xerror", "-noautorotate", "-i", str(source),
              "-map", "0:v:0", "-vf", f"trim=start_frame={first}:end_frame={last + 1}",
              "-fps_mode", "passthrough", "-an", "-sn", "-dn", "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1"]
    encode = ["ffmpeg", "-v", "error", "-nostdin", "-n", "-f", "rawvideo", "-pixel_format", "rgb24",
              "-video_size", f"{width}x{height}", "-framerate", "30/1", "-i", "pipe:0",
              "-an", "-sn", "-dn", "-map_metadata", "-1", "-c:v", "libx264", "-crf", "18",
              "-preset", "medium", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)]
    frame_bytes = width * height * 3
    # Error files avoid pipe deadlocks if a decoder emits many diagnostics.
    with tempfile.TemporaryFile() as decode_error, tempfile.TemporaryFile() as encode_error:
        decoder = subprocess.Popen(decode, stdout=subprocess.PIPE, stderr=decode_error)
        encoder = None
        try:
            encoder = subprocess.Popen(encode, stdin=subprocess.PIPE, stderr=encode_error)
            current, pixels = first - 1, b""
            for row in mapping:
                while current < row["source_frame_index"]:
                    pixels = decoder.stdout.read(frame_bytes)
                    if len(pixels) != frame_bytes:
                        raise RuntimeError("FFmpeg decoder ended before the recorded source frame map")
                    current += 1
                encoder.stdin.write(pixels)
            encoder.stdin.close()
            if decoder.stdout.read(1):
                raise RuntimeError("FFmpeg decoder produced frames beyond the recorded interval")
            decoder.stdout.close()
            decode_status, encode_status = decoder.wait(), encoder.wait()
            decode_error.seek(0)
            encode_error.seek(0)
            errors = decode_error.read() + encode_error.read()
            if decode_status or encode_status or errors.strip():
                raise RuntimeError(f"FFmpeg preparation failed: {errors.decode(errors='replace').strip()}")
        except BaseException as error:
            for process in (decoder, encoder):
                if process is not None and process.poll() is None:
                    process.kill()
                    process.wait()
            decode_error.seek(0)
            encode_error.seek(0)
            details = (decode_error.read() + encode_error.read()).decode(errors="replace").strip()
            if isinstance(error, (OSError, RuntimeError)):
                raise RuntimeError(f"{error}\n{details}") from error
            raise
        finally:
            for pipe in (decoder.stdout, encoder.stdin if encoder is not None else None):
                if pipe is not None and not pipe.closed:
                    pipe.close()
    return [decode, encode]


def _prepared_metadata(path: Path, video: _Video) -> dict[str, Any]:
    if video.stream["codec_name"] != "h264" or video.stream["pix_fmt"] != "yuv420p":
        raise ValueError("Prepared MP4 must be H.264 yuv420p")
    if video.origin != 0 or video.timestamps != [Fraction(index, FPS) for index in range(len(video.timestamps))]:
        raise ValueError("Prepared MP4 must start at zero with exact 30 FPS presentation timestamps")
    if video.duration != Fraction(len(video.timestamps), FPS):
        raise ValueError("Prepared MP4 duration disagrees with its 30 FPS frame count")
    return {
        "path": str(path), "sha256": sha256_file(path),
        "width": video.stream["width"], "height": video.stream["height"],
        "fps": "30/1", "time_base": video.stream["time_base"],
        "duration_s": float(video.duration), "frame_count": len(video.timestamps),
        "codec": "h264", "pixel_format": "yuv420p",
    }


def _camera_metadata(request: ClipRequest) -> dict[str, Any]:
    return {"focal_length_px": request.focal_length_px,
            "provenance": request.focal_length_provenance,
            "quality": "provided" if request.focal_length_provenance == "user_supplied" else "approximate",
            "calibration_loaded": False, "lens_distortion_corrected": False}


def _validate_metadata_fields(metadata: ClipMetadata, request: ClipRequest, metadata_path: Path) -> None:
    """Validate source/encoding claims which cannot be inferred from output pixels."""
    source, preparation = metadata.source, metadata.preparation
    if any(source[name] != value for name, value in request.source.to_dict().items()):
        raise ValueError("Source identity differs from the normalized request")
    if source["license_reference"] != request.license_reference:
        raise ValueError("Source license reference differs from the request")
    for name in ("width", "height", "frame_count"):
        if type(source[name]) is not int or source[name] <= 0:
            raise ValueError(f"Source {name} must be a positive integer")
    if source["width"] % 2 or source["height"] % 2 or source["display_rotation_degrees"] != 0:
        raise ValueError("Source metadata claims unsupported image geometry")
    if (_ratio(source["sample_aspect_ratio"]) not in (None, Fraction(1))
            or _ratio(source["display_aspect_ratio"]) not in (None, Fraction(source["width"], source["height"]))):
        raise ValueError("Source metadata claims non-square image geometry")
    if source["unspecified_sample_aspect_ratio_assumed_square"] != (_ratio(source["sample_aspect_ratio"]) is None):
        raise ValueError("Source sample-aspect assumption is inconsistent")
    for name in ("duration_s", "presentation_timestamp_origin_s"):
        if type(source[name]) not in (int, float) or not math.isfinite(source[name]):
            raise ValueError(f"Source {name} must be finite seconds")
    if source["duration_s"] <= 0 or _ratio(source["time_base"]) is None or _ratio(source["time_base"]) <= 0:
        raise ValueError("Source duration and time base must be positive")
    if source["timing_mode"] not in ("constant", "variable"):
        raise ValueError("Source timing mode must be constant or variable")
    for name in ("codec", "pixel_format"):
        if not isinstance(source[name], str) or not source[name]:
            raise ValueError(f"Source {name} must be recorded")
    for name in ("nominal_frame_rate", "average_frame_rate"):
        rate = _ratio(source[name])
        if rate is not None and rate <= 0:
            raise ValueError(f"Source {name} must be positive when known")
    median = source["median_frame_interval_s"]
    if source["frame_count"] > 1 and (type(median) not in (int, float) or not math.isfinite(median) or median <= 0):
        raise ValueError("Source median frame interval must be positive seconds")
    expected = {
        "implementation": "egocentric_pipeline.video_preparation",
        "implementation_version": PREPARATION_VERSION,
        "output_codec": "libx264", "output_pixel_format": "yuv420p", "audio": "removed",
        "timestamp_origin": "prepared zero corresponds to resolved source interval start",
        "source_timestamp_origin": "first decoded source presentation timestamp",
        "selection_method": "nearest presentation timestamp within half-open interval; ties select earlier frame",
        "spatial_transforms_applied": SPATIAL_TRANSFORMS, "playback_speed_multiplier": 1.0,
        "lossless": False, "original_required_for_reproduction": True,
    }
    if any(preparation[name] != value for name, value in expected.items()):
        raise ValueError("Prepared metadata claims an unsupported preparation operation")
    if preparation["clip_id"] != metadata_path.parent.name or (request.clip_id is not None and preparation["clip_id"] != request.clip_id):
        raise ValueError("Prepared clip_id differs from the directory/request")
    commands = preparation["commands"]
    if (not isinstance(commands, list) or len(commands) != 4
            or any(not isinstance(command, list) or not command
                   or any(not isinstance(argument, str) or not argument for argument in command) for command in commands)):
        raise ValueError("Exact source-probe, decoder, encoder and prepared-probe commands must be recorded")
    if [command[0] for command in commands] != ["ffprobe", "ffmpeg", "ffmpeg", "ffprobe"]:
        raise ValueError("Preparation command sequence is inconsistent")
    for tool in ("ffmpeg", "ffprobe"):
        if not preparation["tool_versions"][tool].startswith(f"{tool} version "):
            raise ValueError(f"{tool} version must be recorded")
    if preparation["version_commands"] != [["ffmpeg", "-version"], ["ffprobe", "-version"]]:
        raise ValueError("Tool version commands are inconsistent")
    if not isinstance(preparation["history"], list) or not preparation["history"]:
        raise ValueError("Preparation history is required")
    created = datetime.fromisoformat(metadata.created_at.replace("Z", "+00:00"))
    if created.tzinfo is None or created.utcoffset() != timezone.utc.utcoffset(created):
        raise ValueError("created_at must record a UTC timestamp")


def prepare_clip(request: ClipRequest, prepared_root: Path = Path("data/prepared"),
                 policy: PreparationQualityPolicy | None = None) -> PreparedClip:
    """Write JSON before returning; an existing matching, verified clip is reused."""
    if not isinstance(request, ClipRequest):
        raise ValueError("prepare_clip requires a normalized ClipRequest")
    policy = policy or PreparationQualityPolicy()
    source_path = request.source.path
    source_hash = sha256_file(source_path)
    source_video = _probe(source_path)
    selection, frames = _select_frames(source_video, request, policy)
    identity = {"source": request.source.to_dict(), "sha256": source_hash,
                "interval_s": selection["resolved_interval_s"]}
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
    clip_id = request.clip_id or f"clip-{digest}"
    output_dir = Path(prepared_root).expanduser().resolve() / clip_id
    output, metadata_path = output_dir / "rgb.mp4", output_dir / "clip_metadata.json"
    if output_dir.exists():
        if not metadata_path.is_file():
            raise FileExistsError(f"Prepared directory already exists without complete metadata: {output_dir}; use a new clip_id")
        existing = load_prepared_clip(metadata_path)
        if (existing.metadata.request != request.to_dict()
                or existing.metadata.source["sha256"] != source_hash
                or existing.metadata.preparation["quality_policy"] != asdict(policy)
                or existing.metadata.preparation["implementation_version"] != PREPARATION_VERSION):
            raise FileExistsError(f"Prepared clip identity/request/policy differs: {output_dir}; use a new clip_id")
        return existing
    output_dir.mkdir(parents=True, exist_ok=False)
    commands = _encode_frames(source_path, source_video, frames["mapping"], output)
    prepared_video = _probe(output)
    prepared = _prepared_metadata(output, prepared_video)
    if prepared["frame_count"] != len(frames["mapping"]) or (prepared["width"], prepared["height"]) != (source_video.stream["width"], source_video.stream["height"]):
        raise ValueError("Encoded output changed geometry or frame count")
    if sha256_file(source_path) != source_hash:
        raise ValueError("Source changed during preparation; preserve the original and retry using a new clip_id")
    metadata = ClipMetadata(
        request=request.to_dict(), source=_source_metadata(request, source_video, source_hash),
        selection=selection,
        preparation={
            "implementation": "egocentric_pipeline.video_preparation",
            "implementation_version": PREPARATION_VERSION,
            "clip_id": clip_id, "quality_policy": asdict(policy), "quality_gate_passed": True,
            "commands": [source_video.probe_command, *commands, prepared_video.probe_command],
            "tool_versions": {tool: _run([tool, "-version"]).splitlines()[0] for tool in ("ffmpeg", "ffprobe")},
            "version_commands": [["ffmpeg", "-version"], ["ffprobe", "-version"]],
            "output_codec": "libx264", "output_pixel_format": "yuv420p", "audio": "removed",
            "timestamp_origin": "prepared zero corresponds to resolved source interval start",
            "source_timestamp_origin": "first decoded source presentation timestamp",
            "selection_method": "nearest presentation timestamp within half-open interval; ties select earlier frame",
            "spatial_transforms_applied": dict(SPATIAL_TRANSFORMS), "playback_speed_multiplier": 1.0,
            "history": ["select source half-open interval", "select nearest source frames on 30/1 FPS grid",
                        "decode to RGB24 without autorotation", "encode H.264 CRF18 medium yuv420p",
                        "remove audio, subtitles, data streams and source metadata"],
            "lossless": False, "original_required_for_reproduction": True,
        },
        prepared=prepared, hawor_camera=_camera_metadata(request), frames=frames,
        artifacts={"source": {"path": str(source_path), "sha256": source_hash},
                   "prepared": {"path": str(output), "sha256": prepared["sha256"]},
                   "metadata_path": str(metadata_path)}, created_at=utc_now(),
    )
    write_json(metadata_path, metadata.to_dict())
    return PreparedClip(output, metadata_path, metadata)


def load_prepared_clip(path: Path, *, policy: PreparationQualityPolicy | None = None) -> PreparedClip:
    """Validate the durable boundary, including locally available source evidence.

    A supplied policy is an additional gate; it never replaces the recorded
    preparation policy or changes the persisted metadata.
    """
    metadata_path = Path(path).expanduser().resolve()
    data = read_json(metadata_path)
    try:
        metadata = ClipMetadata(**data)
        if metadata.schema_version != SCHEMA_VERSION:
            raise ValueError(f"Unsupported clip metadata schema: {metadata.schema_version!r}")
        for name in ("request", "source", "selection", "preparation", "prepared", "hawor_camera", "frames", "artifacts"):
            if not isinstance(getattr(metadata, name), dict):
                raise ValueError(f"Metadata {name} must be an object")
        snapshot = metadata.request
        source = snapshot["source"]
        request = ClipRequest.from_video(
            source["path"], dataset=source["dataset"], video_id=source["video_id"],
            interval=snapshot["interval"], clip_id=snapshot["clip_id"],
            task_label=snapshot["task_label"], license_reference=snapshot["license_reference"],
            focal_length_px=None if snapshot["focal_length_provenance"] == "hawor_default" else snapshot["focal_length_px"],
            constructor=snapshot["constructor"],
        )
        if request.to_dict() != snapshot or metadata.hawor_camera != _camera_metadata(request):
            raise ValueError("Request or focal-length metadata is inconsistent")
        _validate_metadata_fields(metadata, request, metadata_path)
        if metadata.preparation["implementation_version"] != PREPARATION_VERSION:
            raise ValueError("Unsupported preparation implementation version")
        if metadata.preparation["spatial_transforms_applied"] != SPATIAL_TRANSFORMS or metadata.preparation["playback_speed_multiplier"] != 1.0:
            raise ValueError("Prepared metadata claims an unsupported spatial or playback-speed transform")
        if metadata.preparation["quality_gate_passed"] is not True:
            raise ValueError("Prepared metadata does not record a passed quality gate")
        recorded_policy = PreparationQualityPolicy(**metadata.preparation["quality_policy"])
        _check_policy(metadata.frames["metrics"], recorded_policy)
        if policy is not None:
            if not isinstance(policy, PreparationQualityPolicy):
                raise ValueError("policy must be a PreparationQualityPolicy")
            _check_policy(metadata.frames["metrics"], policy)
        video_path = Path(metadata.prepared["path"])
        if not video_path.is_absolute() or video_path != metadata_path.parent / "rgb.mp4":
            raise ValueError("Prepared path must identify rgb.mp4 beside its metadata")
        if metadata.artifacts != {
            "source": {"path": str(request.source.path), "sha256": metadata.source["sha256"]},
            "prepared": {"path": str(video_path), "sha256": metadata.prepared["sha256"]},
            "metadata_path": str(metadata_path),
        }:
            raise ValueError("Prepared artifact identities disagree")
        if any(not re.fullmatch(r"[0-9a-f]{64}", group["sha256"]) for group in (metadata.source, metadata.prepared)):
            raise ValueError("Source/prepared hashes must be SHA-256 hex digests")
        if metadata.prepared != _prepared_metadata(video_path, _probe(video_path)):
            raise ValueError("Prepared video hash or probed media facts disagree with metadata")
        _validate_mapping(metadata)
        if request.source.path.exists():
            source_hash = sha256_file(request.source.path)
            if source_hash != metadata.source["sha256"]:
                raise ValueError("Original source hash does not match prepared metadata")
            source_video = _probe(request.source.path)
            if metadata.source != _source_metadata(request, source_video, source_hash):
                raise ValueError("Original source media facts disagree with prepared metadata")
            selection, frames = _select_frames(source_video, request, recorded_policy)
            if metadata.selection != selection or metadata.frames != frames:
                raise ValueError("Recorded source mapping differs from nearest presentation-timestamp selection")
    except (KeyError, TypeError, AttributeError, ZeroDivisionError) as error:
        raise ValueError(f"Malformed clip metadata: {error}") from error
    return PreparedClip(video_path, metadata_path, metadata)


def _validate_mapping(metadata: ClipMetadata) -> None:
    """Check self-consistency even when the immutable source is currently offline."""
    rows, metrics = metadata.frames["mapping"], metadata.frames["metrics"]
    if not isinstance(rows, list) or len(rows) != metadata.prepared["frame_count"] or not rows:
        raise ValueError("Frame map length must equal the prepared video frame count")
    start, end = metadata.selection["resolved_interval_s"]
    if not 0 <= start < end <= metadata.source["duration_s"] + 1e-12:
        raise ValueError("Resolved source interval is invalid")
    if metadata.selection["requested_interval_s"] != metadata.request["interval"]:
        raise ValueError("Selected interval differs from the request")
    if metadata.selection["semantics"] != "[start_s, end_s)":
        raise ValueError("Selected interval must use half-open semantics")
    if (metadata.source["width"], metadata.source["height"]) != (metadata.prepared["width"], metadata.prepared["height"]):
        raise ValueError("Source and prepared dimensions differ")
    previous_index, previous_timestamp = -1, -1.0
    for index, row in enumerate(rows):
        if any(type(row[name]) not in (int, float) or not math.isfinite(row[name])
               for name in ("timestamp_s", "source_timestamp_s", "timestamp_selection_error_s")):
            raise ValueError("Frame timestamps and errors must be finite seconds")
        source_index, timestamp = row["source_frame_index"], row["source_timestamp_s"]
        if (type(row["frame_index"]) is not int or row["frame_index"] != index
                or not math.isclose(row["timestamp_s"], index / FPS, abs_tol=1e-12, rel_tol=0)
                or type(source_index) is not int or not 0 <= source_index < metadata.source["frame_count"]
                or source_index < previous_index or not start - 1e-12 <= timestamp < end
                or timestamp < previous_timestamp):
            raise ValueError("Frame indices/timestamps violate the prepared/source timeline contract")
        reused = source_index == previous_index
        if type(row["source_frame_reused"]) is not bool or row["source_frame_reused"] != reused:
            raise ValueError("Source-frame reuse flags disagree with source indices")
        if reused != (timestamp == previous_timestamp):
            raise ValueError("Source timestamp and source frame identities disagree")
        error = timestamp - (start + index / FPS)
        if not math.isclose(row["timestamp_selection_error_s"], error, abs_tol=1e-12, rel_tol=0):
            raise ValueError("Timestamp-selection error disagrees with the frame map")
        previous_index, previous_timestamp = source_index, timestamp
    unique = len({row["source_frame_index"] for row in rows})
    errors = [abs(row["timestamp_selection_error_s"]) for row in rows]
    first, last = metadata.selection["source_frame_bounds_inclusive"]
    if type(first) is not int or type(last) is not int or not 0 <= first <= last < metadata.source["frame_count"]:
        raise ValueError("Selected source frame bounds are invalid")
    lower_timestamp, upper_timestamp = metadata.selection["source_timestamp_bounds_s"]
    if (not start - 1e-12 <= lower_timestamp <= upper_timestamp < end
            or rows[0]["source_frame_index"] != first
            or rows[0]["source_timestamp_s"] != lower_timestamp
            or rows[-1]["source_frame_index"] > last or rows[-1]["source_timestamp_s"] > upper_timestamp):
        raise ValueError("Selected source frame/timestamp bounds disagree with the frame map")
    expected_metrics = {
        "source_frames_considered": last - first + 1,
        "unique_source_frames_selected": unique,
        "dropped_source_frame_count": last - first + 1 - unique,
        "repeated_source_frame_count": len(rows) - unique,
        "repeated_source_frame_fraction": (len(rows) - unique) / len(rows),
        "median_absolute_timestamp_error_s": statistics.median(errors),
        "max_absolute_timestamp_error_s": max(errors),
        "source_selected_duration_s": end - start, "prepared_duration_s": len(rows) / FPS,
        "duration_error_s": len(rows) / FPS - (end - start),
    }
    if any(not math.isclose(metrics[name], value, abs_tol=1e-12, rel_tol=0) for name, value in expected_metrics.items()):
        raise ValueError("Frame metrics disagree with source/prepared frame mapping")
