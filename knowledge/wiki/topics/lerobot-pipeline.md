# Full-video robot LeRobot episodes and annotation

The [integrated workflow](integrated-pipeline.md) uses the official LeRobot writer,
reader and annotator pinned to `9a6bb61043bac8c14353fcb6ea513b7473c118e3`.
`pipeline/export_dataset.py` creates or appends one **complete input video per
episode** from a completed HaWoR run and independently evaluated robot regions.
Trimming, incompatible appends, overlapping region solves and duplicate sources
are rejected. Historical hand-only contract 1.0 datasets remain preserved evidence;
the supported robot workflow uses project contract **2.0** and LeRobot **v3.1**.

## Dataset contract

The pinned upstream creator reports storage floor `v3.0`, although it implements
the v3.1 language features. Creation explicitly sets v3.1 on its metadata object
and declares those language features; the installed dependency is unchanged.
The official reader, resumed writer and annotator exercise this output in
[production integration tests](../../../tests/test_lerobot_export.py).

| Data | Representation |
| --- | --- |
| RGB | `observation.images.ego`, 30 FPS, prepared dimensions, H.264 CRF 18 |
| World pose | `observation.hands.root_translation_world_m` (6), `root_orientation_world_axis_angle` (6) |
| Articulation / shape | `observation.hands.hand_pose_axis_angle` (90), `mano_betas` (20) |
| Canonical pose | `observation.hands.root_translation_canonical_m` (6), `root_orientation_canonical_axis_angle` (6) |
| Z-up geometry | `observation.hands.root_translation_aligned_m`, `root_orientation_aligned_axis_angle`, `wrist_position_world_m`, `wrist_position_aligned_m`, `mano_root_offset_m` (6 each) |
| Camera | `observation.camera_position_{world,aligned}_m` (3), `camera_rotation_{world,aligned}_from_camera` (9, row-major) |
| Hand provenance | `observation.hands.{direct_detection,motion_infilled,hawor_valid,export_valid}` (2 bools), `detector_confidence` (2 float32) |
| Robot actions | `action` (18 float64): left arm 7 rad, right arm 7 rad, neck 2 rad, left/right normalized gripper opening (0 closed, 1 open) |
| Action validity | `observation.robot.action_valid` (18 bools); invalid action components are NaN |
| Solver diagnostics | `observation.robot.joint_solution_rad` (18 float64, including the two gripper leader joints in radians), `solved` (1 bool), `ik_success` (2 bools) |
| Independent evaluation | `observation.robot.observed_hand` (2 bools), `joint_feasible`, `collision_free` (1 bool each), position error in metres and orientation error in radians (2 each) |
| Region | `observation.robot.region_id` (1 int32), −1 outside retained regions |
| Timing | LeRobot indices/timestamp plus exact float64 `observation.{clip_timestamp_s,source_timestamp_s}` |

Hand fields flatten left before right; original float32 world/articulation/shape
values and NaNs remain exact. MANO root translation differs from the derived wrist.
Unknown confidence stays NaN. The official reader casts scalar floats to Torch
float32; exact source timestamps remain in Parquet and preparation metadata.
Upstream normalization statistics may contain NaNs and are not validity-aware.

Robot actions require observed (non-infilled) hands, finite solved predictions,
independent smoothed-target tracking within the saved evaluation tolerances,
joint position/velocity/acceleration limits, and discrete self-collision checks.
Each arm and its gripper share validity; neck commands require at least one valid
hand. Failed predictions remain diagnostic fields. These masks do not certify
scene collisions, dynamics, continuous collision clearance or hardware safety.
The existing [acceleration proxy](../decisions/ik-benchmark-limits.md) remains explicit.

## Regions and provenance

`meta/egocentric.json` owns contract/dependency revisions and source identities.
`meta/egocentric/episode_NNNNNN.json` preserves complete preparation/world metadata,
source attribution, hashes, canonical anchors, and robot settings. Its `robot`
record contains the action/joint names, gravity rotation, source solve paths and
benchmark selections. Every retained region records:

- Half-open `[start, stop)` episode frame/time and original source frame/time intervals.
- Fixed `transform_base_from_aligned`, mapping Z-up points into that region's robot base; compose it with the stored gravity rotation for world-to-base conversion.
- Evaluated or unsolved outcome, original pose-acceptance report, and solved/feasible/collision-free/valid-component counts.

Frames retain full-video indices. Gaps and unsolved frames have NaN actions and
false validity; no interpolation or derivative spans a gap or base change. World,
canonical and aligned hand geometry continue through those frames with their
original missing/infill masks. A repeated source hash and source timestamps is an
error even under another run name. [Robot export](../../../src/egocentric_pipeline/datasets/robot_episode.py)
checks source arrays, evaluation synchronization, joint predictions and transform
direction before any dataset mutation.

## Canonical transform

Each hand independently anchors to its first export-valid MANO root pose,
`(R0, t0)`. For every valid pose:

`p_canonical = R0.T @ (p_world - t0)`; `R_canonical = R0.T @ R_world`.

The inverse is `p_world = R0 @ p_canonical + t0` and
`R_world = R0 @ R_canonical`. Anchors remain fixed through the episode, preserving
motion. Axis-angle values are radians. The world values remain primary; local
MANO articulation and shape are unchanged. Hands are not mirrored. Missing hands
have no anchor, invalid canonical poses are NaN, and an infilled first valid pose
can be the anchor. Stored masks expose that limitation. Inversion tests compare
rotation matrices because axis-angle encodings are not unique.

## Mutation and annotation preservation

Creation/append and annotation operate on a full sibling copy. A sibling advisory
lock serializes project writers. On Linux/WSL, `renameat2(RENAME_EXCHANGE)` publishes
an existing dataset atomically after validation; failed operations leave the prior
directory untouched. Existing episodes and annotations are preserved. This costs
temporary disk space approximately equal to a second dataset, appropriate for the
small pilot. External writers must not edit the same root concurrently, and readers
should reopen after an update. The workflow does not promise power-loss durability.

Append requires contract 2.0, the same pinned robot/joint order and action units, matching features, dependency revision, 30 FPS and image geometry;
incompatible inputs need another dataset directory. The official writer resumes
into a new data shard, retaining previous Parquet files. Every new numeric field is
checked over the entire episode after writing; the official reader also decodes
the boundary frames before publication.

`annotate_dataset.py` invokes the actual `lerobot-annotate` module against an
already-running OpenAI-compatible VLM server. It disables interjections, VQA,
memory, task rephrasings and task re-derivation; plans and subtasks remain enabled.
Thinking is disabled for the intended Qwen backend. It selects only unannotated
episodes and refuses an explicit selection containing existing annotations.

The wrapper accepts these arguments:

| Argument | Meaning |
| --- | --- |
| `--dataset-root PATH` | Required existing project LeRobot dataset; successful annotation updates this directory atomically. |
| `--model ID` | Required model name exposed by the running VLM server. |
| `--api-base URL` | OpenAI-compatible endpoint; default `http://localhost:8000/v1`. |
| `--episodes 0 1` | Optional episode indices; omitted means every unannotated episode. |

The pinned annotator samples RGB at **2 frames/s**, packs timestamped frames into
contact sheets, and uses up to 60 sampled frames per prompt. Longer episodes are
split into windows. It first describes the visible activity, then segments it
into subtasks, with a configured minimum duration of 1.5 s. At each subtask
boundary it writes the current subtask and a plan of remaining steps, snapping
boundaries to real dataset frame timestamps. These are upstream defaults, not
additional wrapper arguments. The existing task label guides prompts; HaWoR
trajectories are preserved but are not the VLM's input.

There is no separate output-directory argument: language atoms are saved in
the dataset's `data/*/*.parquet` under `language_persistent`, and the model,
selected episodes, command and pending review status go into
`meta/egocentric/annotation_vNNNN.json`. Console logs must be redirected to the
chosen validation output directory. The wrapper neither starts the server nor
uploads the dataset. See the [workflow and recovery command](integrated-pipeline.md#reuse-and-failure-recovery)
and [server setup](../../../environment/README.md#native-desktop-and-annotation-environments).

The pinned upstream writer replaces language columns and can clear unselected
episodes sharing a shard. This wrapper restores those episodes' prior language
values, checks all non-language data, requires nonempty plan/subtask coverage from
frame zero at real timestamps, and reloads through LeRobot before publication.
The real CLI regression covers two episodes sharing one file and checks preserved
labels on every frame of the older episode.
An upstream run that exits successfully with empty annotations fails this check.
The annotation record remains `review_status: pending`: a human/video-grounded
review is required before acceptance.

The upstream annotator infers nested Arrow language types. Annotated timestamps
can therefore be float64 while newly recorded language columns declare float32;
null camera/tool-call fields can also have different physical types. The official
reader supports these files. Direct Arrow concatenation requires type promotion
when combining annotated and unannotated shards.

## Runtime and evidence

Dataset I/O uses `.venv-lerobot`; the VLM uses `.venv-vlm`. The shell runner starts
the pinned local server only after GPU trajectory processing, or accepts an
existing endpoint. The [environment guide](../../../environment/README.md#native-desktop-and-annotation-environments)
owns installation and model-capacity constraints. Direct Python callers must
clear HaWoR's legacy `LD_LIBRARY_PATH` and use a writable Hugging Face cache.

Historical Milestone 2 results remain under `outputs/milestone-2/` and in the
[Eidon acceptance record](../experiments/milestone-2-eidon-validation.md). They do
not establish current robot-schema or iPhone pilot acceptance. Current cleanup
validation is recorded in [project status](../status.md) and `outputs/cleanup/`.
Synthetic HTTP responses test annotation integration, not model quality; real
annotation labels still require video review.
