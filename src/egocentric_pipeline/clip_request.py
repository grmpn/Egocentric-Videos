"""Normalize local MP4 intent without probing media or estimating calibration."""

from __future__ import annotations

import argparse
import math
import re
from dataclasses import dataclass, field
from numbers import Real
from pathlib import Path
from typing import Any


def _optional_text(value: str | None, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty text when supplied")
    return value.strip()


def _finite_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


@dataclass(frozen=True)
class LocalVideoSource:
    """Immutable source reference; existence and decoding are checked in preparation."""

    path: Path
    dataset: str | None = None
    video_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.path, (str, Path)) or not str(self.path).strip():
            raise ValueError("source path must identify a local MP4")
        path = Path(self.path).expanduser().resolve()
        if path.suffix.lower() != ".mp4":
            raise ValueError("Milestone 1 accepts only local .mp4 videos")
        object.__setattr__(self, "path", path)
        for name in ("dataset", "video_id"):
            object.__setattr__(self, name, _optional_text(getattr(self, name), name))

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "local_mp4", "path": str(self.path), "dataset": self.dataset,
                "video_id": self.video_id}


@dataclass(frozen=True)
class ClipRequest:
    """Source-relative seconds use [start, end); focal length is in image pixels."""

    source: LocalVideoSource
    interval: tuple[float, float] | None = None
    clip_id: str | None = None
    task_label: str | None = None
    license_reference: str | None = None
    focal_length_px: float | None = None
    constructor: str = "direct_video"
    _focal_length_supplied: bool = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.source, LocalVideoSource):
            raise ValueError("source must be a LocalVideoSource")
        if self.interval is not None:
            if not isinstance(self.interval, (tuple, list)) or len(self.interval) != 2:
                raise ValueError("interval must contain start_s and end_s")
            start = _finite_number(self.interval[0], "start_s")
            end = _finite_number(self.interval[1], "end_s")
            if start < 0 or end <= start:
                raise ValueError("interval requires 0 <= start_s < end_s in source seconds")
            object.__setattr__(self, "interval", (start, end))
        for name in ("clip_id", "task_label", "license_reference"):
            object.__setattr__(self, name, _optional_text(getattr(self, name), name))
        if self.clip_id is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", self.clip_id):
            raise ValueError("clip_id must be 1–128 letters, digits, dots, underscores or hyphens, starting with a letter/digit")
        if self.constructor not in ("direct_video", "milestone1_baseline"):
            raise ValueError("constructor must be direct_video or milestone1_baseline")
        supplied = self.focal_length_px is not None
        focal = _finite_number(self.focal_length_px, "focal_length_px") if supplied else 600.0
        if focal <= 0:
            raise ValueError("focal_length_px must be positive in source/prepared pixels")
        object.__setattr__(self, "_focal_length_supplied", supplied)
        object.__setattr__(self, "focal_length_px", focal)

    @property
    def focal_length_provenance(self) -> str:
        return "user_supplied" if self._focal_length_supplied else "hawor_default"

    @classmethod
    def from_video(cls, path: str | Path, *, dataset: str | None = None,
                   video_id: str | None = None, **kwargs: Any) -> ClipRequest:
        return cls(LocalVideoSource(Path(path), dataset, video_id), **kwargs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source.to_dict(),
            "interval": None if self.interval is None else list(self.interval),
            "clip_id": self.clip_id,
            "task_label": self.task_label,
            "license_reference": self.license_reference,
            "focal_length_px": self.focal_length_px,
            "focal_length_provenance": self.focal_length_provenance,
            "constructor": self.constructor,
        }

    def as_dict(self) -> dict[str, Any]:
        return self.to_dict()


def add_request_arguments(parser: argparse.ArgumentParser) -> None:
    """Add shared request options; the entry point owns --video/source selection."""
    parser.add_argument("--start-s", type=float, help="Inclusive start in source seconds; supply with --end-s")
    parser.add_argument("--end-s", type=float, help="Exclusive end in source seconds; supply with --start-s")
    parser.add_argument("--clip-id")
    parser.add_argument("--dataset")
    parser.add_argument("--video-id")
    parser.add_argument("--task-label")
    parser.add_argument("--license-reference")
    parser.add_argument("--focal-length-px", type=float, help="Positive scalar focal in pixels; default: approximate HaWoR 600 px")


def request_from_arguments(args: argparse.Namespace, constructor: str = "direct_video") -> ClipRequest:
    start, end = args.start_s, args.end_s
    if (start is None) != (end is None):
        raise ValueError("Supply both --start-s and --end-s, or neither for the complete video")
    return ClipRequest.from_video(
        args.video, dataset=args.dataset, video_id=args.video_id,
        interval=None if start is None else (start, end), clip_id=args.clip_id,
        task_label=args.task_label, license_reference=args.license_reference,
        focal_length_px=args.focal_length_px, constructor=constructor,
    )
