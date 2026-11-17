# Human reconstruction and robot demonstration datasets

Implemented under the [export-refresh plan](../plans/lerobot-export-refresh.md),
with the approved [iPhone export amendment](../plans/iphone-contract3-export.md).
Project contract **3.0** uses LeRobot **v3.1**, pinned to
`9a6bb61043bac8c14353fcb6ea513b7473c118e3`. The upstream creator still reports
storage floor v3.0; the exporter sets its metadata object's version to v3.1.
Historical contracts 1.0/2.0 remain evidence; append requires a new compatible root.
The [integrated workflow](integrated-pipeline.md) owns orchestration and recovery.

## Human contract

One complete prepared video per episode, including invalid/infilled frames.
Every hand axis is `[left, right]`; arrays remain multidimensional in Parquet.
Standard LeRobot indices and synchronized 30 FPS `observation.images.ego` accompany:

| Feature under `observation.hands.` | Shape | Type |
| --- | --- | --- |
| `root_pose_aligned` | 2 × 7 | float32, xyz metres then normalized xyzw quaternion |
| `pose_axis_angle` | 2 × 45 | float32, native MANO articulation radians |
| `betas` | 2 × 10 | float32, original shape coefficients |
| `wrist_position_aligned_m` | 2 × 3 | float32, physical wrist |
| `source_status` | 2 | uint8: unavailable 0, motion-infilled 1, directly estimated 2 |

Invalidity takes precedence over infill, which takes precedence over an unused
raw detector record. HaWoR `motion_infilled` means valid without a retained direct
estimation chunk; `direct_detection` may coexist with it. `export_valid` includes
native validity, finite parameters and successful upstream processing. The compact
status preserves usability; detector confidence is left in processing artifacts.

The single `observation.camera.pose_aligned` is float32 `[4,4]`, column-vector
T_aligned_from_camera. It is retained because current segmentation and base/head
fitting use camera positions and orientations. No duplicated native camera pose
is stored. All geometry shares gravity-aligned Z-up, original SLAM origin and
arbitrary yaw. Scale is claimed metres, not measured. Base-height initialization
uses camera position minus neutral robot camera height; no measured floor exists.

The dataset README documents separate licensed left/right MANO model hashes,
SMPL-X 0.1.28 MANOLayer's matrix interface, native joint ordering and HaWoR's left
shapedirs correction. Root translation is MANO transl, not physical wrist:
`wrist = transl + J(beta)[0]`. A compact per-episode rotation in the README permits
inverting alignment, including this offset. No PCA or extra mean is applied.
[Geometry tests](../../../tests/test_human_episode.py) reconstruct joints and all
778 vertices for both hands, including infill, with a 2 µm numerical tolerance;
this tolerance describes coordinate conversion, not perception accuracy.

`export_dataset.py restore-human` reconstructs the existing alignment boundary
and RGB from only the human dataset and matching licensed MANO assets. Prepared
human frame indices become the new processing source timeline. Original HaWoR
files and absolute paths are unnecessary; no robot is encoded in this boundary.

## Robot contract and acceptance

One contiguous accepted fixed-base manipulation region per episode. Frame indices
start at zero and timestamps are `frame_index / 30`. RGB comes from the linked
human dataset over the identical half-open interval. Standard indexing accompanies:

| Feature | Shape/type |
| --- | --- |
| `action` | float32 `[18]`: left arm 7 rad, right arm 7 rad, neck 2 rad, left/right opening |
| `action.ee` | float32 `[2,8]`: absolute xyz/xyzw/opening, left then right |
| `quality.hand_status` | uint8 `[2]`, same encoding as human data |
| `quality.action_valid` | bool `[18]` |
| `source_episode_index`, `source_frame_index` | scalar int64, prepared human timeline |
| `language_persistent` | standard plan/subtask atoms |

The 18-component action already has one command per gripper; only the old
separate diagnostic vector duplicated gripper angles. The evaluator computes
nominal URDF TCP FK from actual saved joints in `PEDESTAL_LINK`; TCPs are
`LEFT_EZGRIPPER_TCP_LINK` / `RIGHT_EZGRIPPER_TCP_LINK`. Openings come from evaluated
leader angles and must agree with saved gripper actions. Human targets never
substitute for achieved TCP poses.

Validity includes IK acceptance, observed usable hands, finite solutions, tracking
tolerances, per-joint position/velocity/acceleration limits and self-collision.
Finger leader/mimic violations map to their gripper component. Violations in locked
joints or whole-configuration collisions invalidate all actions. Derivatives use
ordered prepared timestamps within each region, never across boundaries. The
existing [10 rad/s² acceleration proxy](../decisions/ik-benchmark-limits.md) remains.
EE pose validity requires all seven arm masks; opening uses its gripper mask;
neck controls do not affect arm FK in the robot base frame.

Export requires at least `min_episode_valid_ratio` (default **0.85**) of all
region frames to have finite solved configurations, no self-collision and no
joint position/velocity/acceleration violations, including coupled fingers and
locked joints. Tracking, hand observation and geometric acceptance do not enter
this gate; their action masks remain unchanged. No frames are removed to raise
the ratio. This policy was explicitly revised on 2026-11-17; the original
November 12 validation used geometric acceptance plus fully valid action frames.

Run-directory `region_export.json` records `valid_ratio` and its constraint-only
basis, separate `action_valid_ratio`, original geometric acceptance,
`acceptance_passed`, `exported` and any `export_override`. The explicit
`--include-rejected-regions` option exports below-threshold regions as test data,
retaining failure reasons and masks; the dataset README labels this override.
Result counts distinguish accepted/rejected gates from exported/overridden
regions. Ordinary exports still reject below-threshold regions.

Finite invalid predictions are retained with false masks. Unavailable joints use
zero and unavailable TCPs use zero translation/identity quaternion; unavailable
openings use zero. These placeholders never participate in training/statistics.

## Statistics and training

The pinned writer supports Array2D storage but its numeric statistics reduce
multidimensional axes incorrectly and do not accept validity masks. A scoped
single-process adapter delegates RGB statistics unchanged and reduces numeric
time axes using finite valid components. It restores the upstream function even
on failure; no dependency source is modified.

Standard scalar `count` cannot describe unequal valid counts per component.
Episode statistics retain row count for compatibility; global numeric statistics
are recomputed exactly from all rows after append instead of averaging masked
means. Empty components receive mean/min/max/quantiles zero and std one. Normal
loading remains supported. Unmodified generic statistics recomputation/merging
is not mask-aware and is outside this workflow.

Use [ActionTrainingDataset](../../../src/egocentric_pipeline/datasets/training.py)
with `target='joint'` or `target='ee'`. It selects the matching statistics,
requests identical temporal offsets for targets/masks, masks episode padding,
flattens EE targets only at the policy boundary, and sanitizes invalid values
before normalization. A policy must use `masked_mse(prediction, batch['action'],
batch['action_valid'])` or an equivalent masked elementwise loss. The adapter
alone does not change a stock policy's loss. No actual policy training is claimed.

## Metadata, append and annotation

Final roots contain README, data, videos and standard meta files only. No custom
metadata directory, DATA_CARD, PNG staging, opaque episode records or extra
episode columns are added. The README owns conventions and the small source
identity/calibration records required for reconstruction and linkage. Per-episode
human revisions cover numeric rows and the associated video shard; append preserves
old shards. Repacking/regenerating a human dataset requires new dependent exports.
Robot cards pin the human dataset identity and used episode revisions without paths.

Dataset changes use the existing sibling-copy transaction and advisory lock.
Schema, image geometry, embodiment, model identity and source consistency are
checked; repeated human sources and overlapping robot source regions are refused.
Numeric rows are checked after writing and boundary RGB is decoded with the
standard reader before publication. Keep external writers out of concurrent
updates; readers should reopen afterward. Failed updates preserve the original.

`annotate_dataset.py --record RUN/annotations.json` annotates newly segmented robot
episodes through the pinned official CLI. Plans/subtasks use episode-local times.
`language_events` remains declared because that CLI writes both language columns;
interjections/VQA/memory are disabled. Prior labels in shared shards are restored
and all non-language data is checked. Execution records/intermediates stay in the
run; `.annotate_staging` is removed from the published dataset. Nonempty plan and
subtask coverage must start at frame zero. Generated semantics require review.

## Verification

Current verification artifacts are local-only under `outputs/lerobot-export-refresh/`.
See [status](../status.md) and the November action log for completed checks and
remaining work. Historical [cleanup evidence](integrated-pipeline.md#cleanup-verification--2026-11-03)
verifies the previous full-video contract, not this replacement schema.

### Export refresh acceptance — 2026-11-12

- [Processing regression](../../../outputs/lerobot-export-refresh/processing-final.log):
  114 passed, including licensed MANO reconstruction, temporal limits, masks and
  existing ingestion/alignment contracts.
- [Official LeRobot integration](../../../outputs/lerobot-export-refresh/integration-final.log):
  16 passed, one missing-MANO-runtime skip covered by the processing checks.
  Tests exercise create/append/rollback, structured schemas, source revisions,
  region thresholds, RGB/local time, training masks and the real annotation CLI
  with a deterministic local HTTP fixture. [Opening regression](../../../outputs/lerobot-export-refresh/opening-final.log)
  passed seven checks; [distinct joint ordering and invalid-target normalization](../../../outputs/lerobot-export-refresh/ordering-final.log)
  is checked separately after strengthening the fixture.
- [Updated shell run](../../../outputs/lerobot-export-refresh/shell-console.log)
  completed from saved stages on the 121-frame bundled MP4, retaining its complete
  [human dataset](../../../outputs/lerobot-export-refresh/real-human/README.md).
  Both candidate regions failed existing geometric acceptance and were correctly
  [rejected](../../../outputs/lerobot-export-refresh/shell-run/region_export.json);
  no robot dataset or VLM server was created for this example. Accepted robot
  episodes and annotations are exercised in `outputs/lerobot-export-refresh/test-runs-final/`.
- [Real geometry audit](../../../outputs/lerobot-export-refresh/geometry-review.json):
  maximum MANO vertex difference 2.03e-7 m; 83 TCP poses agree with independent FK
  after float32 conversion within 1.49e-8 m and 6.98e-8 rotation-matrix error.
  [RGB pairs](../../../outputs/lerobot-export-refresh/real-human-rgb-review.jpg)
  and [wrist trajectories/provenance](../../../outputs/lerobot-export-refresh/real-human-wrists.png)
  were inspected; no frame mismatch or coordinate change was observed.
- [Standalone human reuse](../../../outputs/lerobot-export-refresh/standalone-review.json)
  restored RGB/alignment, retained both region intervals and regenerated gripper
  mapping using only the dataset and licensed models. Maximum landmark difference
  was 1.20e-7 m, palm-transform difference 8.21e-7, opening difference 3.18e-7.

Evidence is local-only and ignored by Git. No new HaWoR inference, IK solve,
real VLM inference, policy training, physical calibration or hardware operation
was performed. The existing demo's geometric failures remain unresolved; this
refresh fulfills the export plan, not broader simulation milestone acceptance.
