"""Package a completed HaWoR run with the pinned official LeRobot v3.1 API."""

import hashlib
import json
from pathlib import Path

import av
import numpy as np
import pyarrow.parquet as pq

from .canonical import canonicalize, save_canonical_preview
from .dataset_transaction import staged_dataset
from .run_metadata import read_json, sha256_file, utc_now, write_json
from .world_export import WORLD_FIELDS, HAND_ORDER, MASK_FIELDS, load_run


LEROBOT_REVISION = "9a6bb61043bac8c14353fcb6ea513b7473c118e3"
CAMERA = "observation.images.ego"
CONTRACT_VERSION = "1.0"


def write_data_card(root, contract):
    """Refresh the workflow-owned capture/provenance summary, never a quality claim."""
    rows = []
    for episode in contract["episodes"]:
        index = episode["episode_index"]
        record = read_json(root / f"meta/egocentric/episode_{index:06d}.json")
        clip = record["preparation"]
        source = clip["source"]
        label = (source.get("dataset") or "user-provided MP4").replace("|", "\\|")
        task = record["task"].replace("|", "\\|").replace("\n", " ")
        license_text = (source.get("license_reference") or "Not supplied").replace("|", "\\|")
        rows.append(f"| {index} | {label} | {task} | {clip['prepared']['frame_count']} | {license_text} |")
    text = (f"# Egocentric dataset data card\n\nWorkflow-owned summary; dataset revision {contract['version']}.\n\n"
            "| Episode | Capture/source | Task | Frames | License/attribution reference |\n"
            "| --- | --- | --- | --- | --- |\n" + "\n".join(rows) + "\n\n"
            "Each episode preserves its source hash, camera assumptions, selected frame mapping, run hash, "
            "and canonical anchors in `meta/egocentric/episode_NNNNNN.json`. Source-specific attribution "
            "and recording metadata are retained there when supplied. RGB is prepared at 30 FPS, "
            "with unchanged image geometry and H.264 re-encoding. No lens correction is applied.\n\n"
            "World poses use HaWoR's independent clip-local SLAM gauge and claimed metres; metric accuracy "
            "is unverified. Canonical poses use each hand's first export-valid root as a fixed anchor. "
            "Left components precede right components. Articulation/shape remain MANO parameters. "
            "Missing and infilled frames have separate masks; unknown detector confidence remains NaN. "
            "Detector confidence is not geometric accuracy. No robot actions are synthesized.\n\n"
            "Review: reconstruction suitability and annotation semantics require video review; their "
            "presence does not establish acceptance. Annotation execution records are stored separately "
            "under `meta/egocentric/annotation_vNNNN.json`, with review pending. This dataset is not by "
            "itself evidence of an accepted iPhone pilot, safe robot trajectories, or training readiness.\n")
    (root / "DATA_CARD.md").write_text(text, encoding="utf-8")


def episode_features(clip, arrays):
    from lerobot.datasets.language import language_feature_info

    features = {CAMERA: {"dtype": "video", "shape": (clip["prepared"]["height"], clip["prepared"]["width"], 3),
                         "names": ["height", "width", "channels"]}}
    for key, value in arrays.items():
        features[key] = {"dtype": str(value.dtype), "shape": (value.shape[1],), "names": None}
    return {**features, **language_feature_info()}


def episode_arrays(world):
    """Flatten numeric fields hand-major: all left components, then all right."""
    count = len(world["frame_index"])
    arrays = {f"observation.hands.{key}": world[key].reshape(count, -1)
              for key in (*[f[0] for f in WORLD_FIELDS], *MASK_FIELDS, "detector_confidence")}
    p, r, anchors = canonicalize(world["root_translation_world_m"], world["root_orientation_world_axis_angle"],
                                  world["export_valid"])
    arrays["observation.hands.root_translation_canonical_m"] = p.reshape(count, 6)
    arrays["observation.hands.root_orientation_canonical_axis_angle"] = r.reshape(count, 6)
    arrays["observation.clip_timestamp_s"] = world["timestamp_s"].reshape(count, 1)
    arrays["observation.source_timestamp_s"] = world["source_timestamp_s"].reshape(count, 1)
    return arrays, anchors


def validate_compatibility(root, features):
    info = read_json(root / "meta/info.json")
    if info["codebase_version"] != "v3.1" or info["fps"] != 30:
        raise ValueError("Append requires LeRobot v3.1 at 30 FPS")
    contract = read_json(root / "meta/egocentric.json")
    if contract["schema_version"] != CONTRACT_VERSION or contract["lerobot_revision"] != LEROBOT_REVISION:
        raise ValueError("Incompatible egocentric dataset contract")
    if contract["hand_order"] != HAND_ORDER:
        raise ValueError("Dataset hand order must remain left, right")
    expected = set(features) - {"language_persistent", "language_events"}
    automatic = {"timestamp", "frame_index", "episode_index", "index", "task_index"}
    language = {"language_persistent", "language_events"}
    if (set(info["features"]) - automatic - language != expected
            or not set(features) <= set(info["features"])):
        raise ValueError("Dataset features differ from this trajectory contract")
    for key, feature in features.items():
        saved = info["features"][key]
        if saved["dtype"] != feature["dtype"] or tuple(saved["shape"]) != tuple(feature["shape"]) or saved["names"] != feature["names"]:
            raise ValueError(f"Incompatible feature or image geometry: {key}")
    if info["total_episodes"] != len(contract["episodes"]):
        raise ValueError("Dataset episode count differs from provenance; repair before appending")
    return info, contract


def append_run(manifest_path, root, *, task, repo_id="local/egocentric-pilot", source_metadata=None):
    """Create or append one distinct episode; reject repeats before any mutation.

    RGB keeps prepared frame order and image geometry (H.264 re-encoding).
    Native geometry/confidence retain float32 including NaN; masks remain bool.
    Full preparation/world metadata and reversible anchors accompany each episode.
    """
    from lerobot.configs import RGBEncoderConfig
    from lerobot.datasets.dataset_metadata import CODEBASE_VERSION
    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    if CODEBASE_VERSION != "v3.0":
        raise RuntimeError("Use the pinned environment/lerobot requirements for v3.1")
    if not isinstance(task, str) or not task.strip():
        raise ValueError("Supply a nonempty task label for annotation")
    manifest, artifacts, clip, world_meta, world = load_run(manifest_path)
    arrays, anchors = episode_arrays(world)
    features = episode_features(clip, arrays)
    identity = {"source_sha256": clip["source"]["sha256"],
                "source_timestamps_s": world["source_timestamp_s"].tolist()}
    episode_id = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    with staged_dataset(root) as stage:
        options = dict(root=stage, video_backend="pyav", encoder_threads=2,
                       rgb_encoder=RGBEncoderConfig(vcodec="h264", crf=18, preset="fast"))
        if stage.exists():
            info, contract = validate_compatibility(stage, features)
            if any(e["episode_id"] == episode_id for e in contract["episodes"]):
                raise ValueError("This source interval already exists; repeated additions are rejected")
            repo_id = contract["repo_id"]
            dataset = LeRobotDataset.resume(repo_id, **options)
        else:
            contract = {"schema_version": CONTRACT_VERSION, "lerobot_revision": LEROBOT_REVISION,
                        "repo_id": repo_id, "version": 0, "hand_order": HAND_ORDER, "episodes": []}
            dataset = LeRobotDataset.create(repo_id, fps=30, features=features, **options)
            # Upstream's storage floor still says v3.0 although it implements
            # the v3.1 language schema. Explicitly version our schema-bearing
            # output; do not change upstream globals or the installed package.
            dataset.meta.info.codebase_version = "v3.1"
        episode_index = len(contract["episodes"])
        try:
            count = 0
            with av.open(str(artifacts["prepared_video"])) as video:
                for count, frame in enumerate(video.decode(video=0), start=1):
                    index = count - 1
                    if index >= len(world["frame_index"]) or abs(float(frame.pts * frame.time_base) - index / 30) > 1e-9:
                        raise ValueError("Decoded RGB frame count/timestamp differs from trajectory")
                    row = {key: value[index].copy() for key, value in arrays.items()}
                    row.update({key: None for key in dataset.features if key.startswith("language_")})
                    row.update({CAMERA: frame.to_ndarray(format="rgb24"), "task": task.strip()})
                    dataset.add_frame(row)
            if count != len(world["frame_index"]):
                raise ValueError("Decoded RGB ended before the trajectory")
            dataset.save_episode()
        finally:
            dataset.finalize()
        provenance = {"episode_index": episode_index, "episode_id": episode_id, "task": task.strip(),
                      "created_at": utc_now(), "source_metadata": source_metadata,
                      "run_manifest_sha256": sha256_file(manifest_path), "run_id": manifest["run_id"],
                      "preparation": clip, "world_metadata": world_meta,
                      "world_sha256": sha256_file(artifacts["trajectory_world"]),
                      "canonical": {"definition": "first export-valid MANO root pose per hand; fixed episode anchors",
                                    "world_from_canonical": anchors}}
        write_json(stage / f"meta/egocentric/episode_{episode_index:06d}.json", provenance)
        save_canonical_preview(stage / f"meta/egocentric/episode_{episode_index:06d}_canonical.png",
                               world["timestamp_s"],
                               arrays["observation.hands.root_translation_canonical_m"].reshape(count, 2, 3),
                               world["motion_infilled"])
        contract["episodes"].append({"episode_index": episode_index, "episode_id": episode_id})
        contract["version"] += 1
        write_json(stage / "meta/egocentric.json", contract, overwrite=True)
        write_data_card(stage, contract)
        # Reload through the production reader, including RGB at both boundaries.
        reader = LeRobotDataset(repo_id, root=stage, video_backend="pyav")
        if reader.num_episodes != episode_index + 1:
            raise ValueError("LeRobot reload lost an episode")
        start = len(reader) - count
        for index in (0, count - 1):
            row = reader[start + index]
            if int(row["episode_index"]) != episode_index or int(row["frame_index"]) != index:
                raise ValueError("Reloaded episode/frame indexing differs")
            if tuple(row[CAMERA].shape) != (3, clip["prepared"]["height"], clip["prepared"]["width"]):
                raise ValueError("Reloaded RGB geometry differs")
            for key, values in arrays.items():
                actual = row[key].numpy().reshape(-1)
                # The upstream reader converts Python float scalars to Torch
                # float32. Check that conversion here, and exact storage below.
                expected = values[index].astype(actual.dtype)
                if not np.array_equal(actual, expected, equal_nan=True):
                    raise ValueError(f"Reload changed trajectory values: {key}")
        episode = reader.meta.episodes[episode_index]
        data_path = stage / reader.meta.data_path.format(chunk_index=episode["data/chunk_index"],
                                                        file_index=episode["data/file_index"])
        table = pq.read_table(data_path, filters=[("episode_index", "=", episode_index)])
        for key, values in arrays.items():
            actual = np.asarray(table[key].to_pylist(), dtype=values.dtype).reshape(values.shape)
            if not np.array_equal(actual, values, equal_nan=True):
                raise ValueError(f"Parquet storage changed trajectory values: {key}")
        del reader, dataset
    return {"dataset_root": str(Path(root).resolve()), "episode_index": episode_index,
            "episode_id": episode_id, "dataset_version": contract["version"]}
