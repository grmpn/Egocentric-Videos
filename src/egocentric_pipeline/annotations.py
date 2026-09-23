"""Run official plan/subtask annotation with atomic publication and preservation."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pyarrow as pa
import pyarrow.parquet as pq

from .dataset_transaction import staged_dataset
from .lerobot_export import write_data_card
from .run_metadata import read_json, utc_now, write_json


LANGUAGE = ("language_persistent", "language_events")


def _numeric_digest(table):
    data = table.select([key for key in table.column_names if key not in LANGUAGE]).to_pydict()
    return hashlib.sha256(json.dumps(data, sort_keys=True, allow_nan=True).encode()).hexdigest()


def validate_annotation_rows(table, selected):
    """Check real frame timestamps, plan/subtask coverage, and no extra styles."""
    rows = table.to_pylist()
    for episode in selected:
        frames = [row for row in rows if row["episode_index"] == episode]
        if not frames:
            continue
        times = {row["timestamp"] for row in frames}
        atoms = frames[0]["language_persistent"] or []
        if not atoms or any(row["language_persistent"] != atoms for row in frames):
            raise ValueError(f"Episode {episode}: missing or inconsistent persistent annotations")
        if any(row["language_events"] for row in frames):
            raise ValueError("Plan/subtask annotation unexpectedly produced events")
        for atom in atoms:
            if (atom["style"] not in {"plan", "subtask"} or atom["timestamp"] not in times
                    or not isinstance(atom["content"], str) or not atom["content"].strip()
                    or atom.get("camera") is not None or atom.get("tool_calls")):
                raise ValueError(f"Episode {episode}: invalid plan/subtask atom")
        for style in ("plan", "subtask"):
            boundaries = [a["timestamp"] for a in atoms if a["style"] == style]
            if not boundaries or min(boundaries) != min(times) or len(set(boundaries)) != len(boundaries):
                raise ValueError(f"Episode {episode}: {style} must start at frame zero with unique boundaries")


def annotate_dataset(root, *, model, api_base, episodes=None):
    """Annotate unannotated episodes using an already running VLM endpoint.

    Existing nonempty annotations are never overwritten. Validation establishes
    structure and synchronization only; every output still needs video review.
    No model is auto-downloaded, server started, or dataset uploaded.
    """
    from lerobot.datasets.io_utils import write_table_one_row_group_per_episode
    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    with staged_dataset(root) as stage:
        contract = read_json(stage / "meta/egocentric.json")
        before = {path.relative_to(stage): pq.read_table(path) for path in stage.glob("data/*/*.parquet")}
        existing = set()
        all_episodes = set()
        for table in before.values():
            for row in table.to_pylist():
                episode = row["episode_index"]
                all_episodes.add(episode)
                if any(row.get(key) for key in LANGUAGE):
                    existing.add(episode)
        selected = all_episodes - existing if episodes is None else set(episodes)
        if not selected or not selected <= all_episodes:
            raise ValueError("Select existing, unannotated episodes; none are eligible")
        if selected & existing:
            raise ValueError("Selected episodes already contain annotations; preserve them or use a separate dataset copy")
        command = [sys.executable, "-m", "lerobot.scripts.lerobot_annotate", f"--root={stage}",
                   f"--only_episodes={json.dumps(sorted(selected))}", "--push_to_hub=false",
                   f"--vlm.model_id={model}", f"--vlm.api_base={api_base}", "--vlm.auto_serve=false",
                   '--vlm.chat_template_kwargs={"enable_thinking": false}',
                   "--vlm.camera_key=observation.images.ego", "--vlm.client_concurrency=1",
                   "--executor.episode_parallelism=1", "--video_backend=pyav", "--plan.enabled=true",
                   "--plan.emit_plan=true", "--plan.emit_memory=false", "--plan.n_task_rephrasings=0",
                   "--plan.derive_task_from_video=off", "--interjections.enabled=false", "--vqa.enabled=false"]
        result = subprocess.run(command)
        if result.returncode:
            raise RuntimeError(f"lerobot-annotate failed (exit {result.returncode}); original dataset unchanged")
        for relative, original in before.items():
            path = stage / relative
            updated = pq.read_table(path)
            if _numeric_digest(updated) != _numeric_digest(original):
                raise ValueError("Annotation changed non-language frame data")
            episode_ids = original["episode_index"].to_pylist()
            # The pinned upstream writer empties unstaged episodes in a shared
            # shard. Restore exactly their previous language values before commit.
            for key in LANGUAGE:
                values = updated[key].to_pylist()
                previous = original[key].to_pylist()
                for i, episode in enumerate(episode_ids):
                    if episode not in selected:
                        values[i] = previous[i]
                updated = updated.set_column(updated.schema.get_field_index(key), key, pa.array(values))
            validate_annotation_rows(updated, selected)
            write_table_one_row_group_per_episode(updated, path)
        reader = LeRobotDataset(contract["repo_id"], root=stage, video_backend="pyav")
        for episode in selected:
            index = reader.meta.episodes[episode]["dataset_from_index"]
            if not reader[index]["language_persistent"]:
                raise ValueError("LeRobot reload lost saved annotations")
        contract["version"] += 1
        record = {"created_at": utc_now(), "model": model, "api_base": api_base,
                  "episodes": sorted(selected), "review_status": "pending",
                  "command": [arg if not arg.startswith("--root=") else "--root=<staged_dataset>" for arg in command]}
        write_json(stage / f"meta/egocentric/annotation_v{contract['version']:04d}.json", record)
        write_json(stage / "meta/egocentric.json", contract, overwrite=True)
        write_data_card(stage, contract)
        del reader
    return {"episodes": sorted(selected), "dataset_version": contract["version"], "review_status": "pending"}
