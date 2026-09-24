# Video to LeRobot and annotation

Implemented for the [approved Milestone 2 plan](../plans/milestone-2-lerobot-pilot.md).
Commands live in the [README](../../../README.md#milestone-2-dataset-workflow).
Tests use the official LeRobot writer/reader and annotation command at revision
`9a6bb61043bac8c14353fcb6ea513b7473c118e3`. Synthetic annotation responses test
integration, not inference quality. Real capture acceptance remains separate.

## Dataset contract

`video_to_dataset.py` accepts an MP4 and local dataset directory, invokes unchanged
HaWoR through a separate Python interpreter, benchmarks the attempt, and appends
only completed exports. `--run-manifest` reuses a verified completed run, including
relocated Milestone 1 evidence. It verifies source/frame mappings, artifact hashes,
geometry dtypes, handedness, confidence and validity before writing.

The dataset is LeRobot v3.1, with the official optional language features declared
from creation. The pinned upstream creator still defaults to `codebase_version:
v3.0`; this integration explicitly sets `v3.1` on its metadata object when creating
the dataset with those language features. The installed dependency is unchanged.
The official reader and resumed writer support these outputs. This discrepancy
between the upstream storage floor and language documentation is intentional and
covered by integration tests; it is not evidence that arbitrary v3 datasets are
compatible with this project's trajectory contract.

| Data | Representation |
| --- | --- |
| RGB | `observation.images.ego`, 30 FPS, original prepared dimensions, H.264 CRF 18 |
| World pose | `observation.hands.root_translation_world_m` (6 floats), `root_orientation_world_axis_angle` (6) |
| Finger articulation / shape | `observation.hands.hand_pose_axis_angle` (90), `mano_betas` (20) |
| Canonical pose | `observation.hands.root_translation_canonical_m` (6), `root_orientation_canonical_axis_angle` (6) |
| Validity/provenance | `observation.hands.{direct_detection,motion_infilled,hawor_valid,export_valid}` (2 bools each) |
| Confidence | `observation.hands.detector_confidence` (2 float32, NaN without detection) |
| Timing | LeRobot frame/episode/global indices and timestamp; exact float64 `observation.{clip_timestamp_s,source_timestamp_s}` in Parquet |

Hand fields flatten all left components followed by all right components; native
float32 world, articulation and shape values are preserved. Translation is the
MANO root parameter, not an independently derived wrist joint. Units and clip-local
world limitations follow [HaWoR's contract](hawor-pipeline.md). There are no robot
actions, fabricated grippers, or cross-clip world alignment.

The official reader casts Python scalar timestamps to Torch float32. Exact
timestamps remain in the float64 Parquet columns and preparation metadata; use
those for original-frame alignment. Unknown confidence and invalid geometry remain
NaN, never invented zero confidence. Upstream normalization statistics can therefore
contain NaNs; do not treat them as a validity-aware training normalizer.

`meta/egocentric.json` owns the contract version, dependency revision, dataset
revision counter, and source-interval identities. Per-episode JSON under
`meta/egocentric/` retains complete preparation/world metadata, camera assumptions,
source attribution, run/trajectory hashes and canonical anchors. Repeating the
same source hash and selected timestamps is an error, even under a new run name.
Each append also generates a canonical preview in that directory. It highlights
infill and missing data; it does not certify reconstruction quality.

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

Append requires matching schema, dependency revision, 30 FPS and image geometry;
incompatible inputs need another dataset directory. The official writer resumes
into a new data shard, retaining previous Parquet files. Every new numeric field is
checked over the entire episode after writing; the official reader also decodes
the boundary frames before publication.

`annotate_dataset.py` invokes the actual `lerobot-annotate` module against an
already-running OpenAI-compatible VLM server. It disables interjections, VQA,
memory, task rephrasings and task re-derivation; plans and subtasks remain enabled.
Thinking is disabled for the intended Qwen backend. It selects only unannotated
episodes and refuses an explicit selection containing existing annotations.

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

## Local inference feasibility

Historical laptop evidence: on 2026-09-23 the WSL machine exposed an RTX 3070 Laptop GPU with **8192 MiB**
VRAM (5977 MiB free at preflight) and about 15 GiB system RAM. The documented default
[Qwen3.6-27B](https://huggingface.co/Qwen/Qwen3.6-27B) has 27 billion language-model
parameters: roughly 54 GB at 16 bits or 13.5 GB at 4 bits for those weights alone,
before vision/runtime/cache overhead. Thus the default model does not fit this GPU;
this is a capacity bound, not an attempted OOM benchmark. Smaller quantized models
and CPU offloading have not been validated here.

The current annotator supports an OpenAI-compatible server; its previous in-process
`transformers`/`vllm` backends are explicitly rejected. vLLM is not installed by the
annotation extra. The 2026-09-24 native desktop setup uses a separate server
environment, with an RTX 4090 and community 4-bit Qwen3.6-27B checkpoint. Its
GPU runtime, package checks, and real three-image request through LeRobot's client
pass. The bundled 121-frame video also passes HaWoR, LeRobot creation, actual
plan/subtask annotation and reload. Its labels agree with representative video
frames; the unrecorded iPhone pilot and its full review remain separate gates.
[The environment guide](../../../environment/README.md#native-desktop-and-annotation-environments)
owns versions, installation commands, model provenance, and current setup evidence.
The 2026-09-23 statement that no weights had been downloaded applies only to the
laptop session. No cloud job or dataset upload has been started.

The first real Eidon packaging attempt exposed a library-loader conflict:
inheriting HaWoR's `LD_LIBRARY_PATH` made modern CPU Torch crash during import
with SIGSEGV. A controlled import reproduces the crash with legacy paths and
succeeds without them. Both dataset CLIs now re-execute with a clean library path;
the video command configures the pinned CUDA 11.7/HaWoR paths only for its inference
child. Programmatic callers must likewise use the isolated dataset runtime. The
[historical reproduction](../../../outputs/hawor/milestone-2/setup/library-isolation.json)
is local to the laptop and absent from this desktop clone.
On the native desktop, the child also needs Conda's `lib` directory for its newer
C++ runtime. Torch-library discovery resolves Python-directory symlinks so Conda
aliases do not count as separate installations. The environment guide owns these
desktop settings and the required writable Hugging Face cache.
