# Milestone 2 integration and Eidon validation

Historical laptop validation below was verified 2026-09-23 against implementation
`5ef3b56` and the [approved plan](../plans/milestone-2-lerobot-pilot.md).
**Milestone acceptance remains open:** the iPhone demonstrations are not recorded.
Real VLM annotation subsequently passed on the bundled desktop example on
2026-09-24 and the two eligible Eidon clips on 2026-09-25. Cooking's generated
object label is questionable; human review remains pending. See the desktop retry below and
the [desktop setup evidence](../../../environment/README.md#native-desktop-and-annotation-environments).

## Selection and reproducibility

The three four-second intervals in [the fixed selection](../../../configs/eidon-validation.json)
were chosen before inference across cooking, laundry and cleaning, with contributors
2 and 5. Only their full source MP4s were downloaded from `eidon-ai/tracker-pov` at
revision `47c55ccc6d0308894ab482009c6fa91569057a08`; CC-BY-4.0 attribution and metadata
are retained. [Local source records](../../../outputs/hawor/milestone-2/eidon-validation/sources.json)
include hashes, byte counts and ffprobe results. Inputs and generated evidence are
ignored/local-only and unavailable in a fresh clone.

Source midpoint samples were inspected before inference. No obvious strong fisheye
curvature was observed, but these are uncalibrated sources: unchanged HaWoR used its approximate
600 px focal length and no distortion correction. This does not establish camera
calibration, metric scale or reconstruction accuracy. Each successful interval has
120 prepared frames at 30 FPS and unchanged 1920×1080 image geometry.

## All three attempts

| Recording / contributor | Task and source interval | HaWoR result / wall time | Direct / infilled / invalid frames, left; right |
| --- | --- | --- | --- |
| 56 / 2 | Slice vegetable, 20–24 s | Completed, 436.70 s | 3 / 116 / 1; 120 / 0 / 0 |
| 204 / 5 | Fold laundry, 60–64 s | Preparation failed, 61.09 s | No inference/export |
| 1566 / 2 | Wipe helmet, 45–49 s | Completed, 1043.96 s | 56 / 64 / 0; 97 / 23 / 0 |

Laundry exceeded the unchanged maximum source/target timestamp error: **33.53 ms**
versus **16.67 ms** allowed. Its fixed interval was not replaced or made to pass by
weakening the gate. Cooking's maximum error was 12.54 ms; cleaning's was 2.07 ms.
Neither successful preparation repeated source frames; cleaning dropped one of
121 considered source frames. Exact mappings remain in the dataset provenance.

Cooking/cleaning sampled peak process-tree RSS was **8.34 / 6.75 GiB**;
whole-device GPU memory was **7.82 / 7.81 GiB**, respectively. Device totals include
other processes; process-attributed GPU memory was unavailable and sampling can
miss spikes. HaWoR therefore ran locally, but these four-second examples took
about 7.3 and 17.4 minutes including preparation and rendering. No real-time or
long-clip performance claim follows.

Both originally launched dataset parents crashed on importing modern Torch after
HaWoR completed because they inherited legacy library paths. The corrected CLI in
`5ef3b56` recovered both through `--run-manifest`, without repeating inference.
The [original batch outcomes](../../../outputs/hawor/milestone-2/eidon-validation/execution-results.json)
retain these crashes; per-source `packaging-retry.log` records recovery. The
[local review index](../../../outputs/hawor/milestone-2/README.md) links each manifest,
benchmark, overlay, preview and source record.

## Visual review and suitability

Agent review inspected a 30-frame contact sheet for each successful run, detailed
boundary/transition frames, and world/canonical previews. These checks are not a
frame-by-frame ground-truth evaluation or user acceptance.

- **Cooking:** the left track is almost entirely infilled and disappears at the
  last frame despite a visible hand. At frame 77, the overlay visibly reverses
  hand association; the right root steps about 0.117 HaWoR metres in one frame.
  Mesh alignment and temporal continuity are poor.
- **Cleaning:** frame 0 reverses mesh/hand association; frames 40, 101 and 108 show
  large alignment errors. Infill often misses the visible wiping motion. Root
  steps reach about 0.294 m left and 0.425 m right between adjacent frames in
  HaWoR's unverified scale. Complete validity masks do not imply accurate poses.

Both reconstructions are unsuitable as evidence of deliberate high-quality pilot
acceptance. The detector, infiller and camera pipeline remain unchanged within
the approved scope. Finger articulation and shape are preserved, but grasp/contact
accuracy and robot suitability are unverified.

## Integration evidence and remaining acceptance

The local dataset contains cooking then cleaning, 240 total frames at revision 2.
The official pinned reader reloads both. Independent validation checks every stored
world/mask/confidence value, exact source/clip timestamps, all encoded video frame
timestamps, source/run hashes, and canonical inversion. It checks RGB and official
reader indexing at frames 0/60/119 per episode. Cooking's prior Parquet, video,
provenance and canonical preview retain their hashes after append. See
[validation details](../../../outputs/hawor/milestone-2/eidon-validation/dataset-validation.json),
[append preservation](../../../outputs/hawor/milestone-2/eidon-validation/append-preservation.json),
and the generated [data card](../../../outputs/hawor/milestone-2/eidon-validation/dataset/DATA_CARD.md).

The implementation passed 88 full-suite tests, followed by six focused checks
after final plotting/annotation changes and targeted CLI/compatibility checks.
Tests exercise the real annotation command with a loopback HTTP fixture; **no real
VLM inference or semantic annotation review has run**. Dependency, syntax, CLI and
documentation checks passed. CI was configured but not run remotely.

The [LeRobot contract](../topics/lerobot-pipeline.md) records the upstream version
metadata discrepancy, empty-annotation detection, shared-shard preservation and
library isolation. It also records why the default 27B model does not fit this
8 GiB GPU; smaller/offloaded models remain untested. Next acceptance work is the
1–2 unrecorded iPhone demonstrations and real plan/subtask annotation on a suitable
Linux desktop, followed by timestamp/video review. No Milestone 3 work is started.

## Desktop annotation retry — 2026-09-25

The user requested another validation with manually inspectable outputs. Restored
all three original MP4s to `data/source/eidon/recordings/` from the same pinned
revision, totaling 766,650,813 bytes. Byte counts match the fixed selection;
[source records](../../../outputs/hawor/milestone-2/eidon-annotation-20260925/sources.json)
retain new SHA-256 measurements and ffprobe output. Historical laptop hashes are
not available on this desktop for a direct comparison.

The existing `prepare_clip.py` CLI passed cooking 20–24 s and cleaning 45–49 s,
each with 120 frames at 30 FPS and unchanged 1920×1080 geometry. Laundry 60–64 s
again failed at 33.53 ms maximum timestamp error versus the unchanged 16.67 ms
limit. Its interval was not substituted and the gate was not weakened.

The initial attempt stopped before GPU inference: the loaded NVIDIA kernel module
was 580.159.03 while updated libraries were 580.178.04. After the user restarted
the desktop, `nvidia-smi` succeeded with the RTX 4090 and driver 580.178.04.
The existing `video_to_dataset.py` CLI then completed both HaWoR runs and dataset
creation/append without implementation changes:

| Recording | HaWoR pipeline time | Peak RSS / device GPU memory | Direct / infilled / invalid frames, left; right |
| --- | --- | --- | --- |
| 56, cooking | 83.369 s | 8.476 / 12.542 GiB | 3 / 116 / 1; 119 / 1 / 0 |
| 1566, cleaning | 131.885 s | 8.364 / 13.300 GiB | 56 / 63 / 1; 88 / 32 / 0 |

Times include preparation, inference, export, rendering and pipeline validation;
LeRobot packaging follows afterward. Memory is sampled and device totals include
other processes. These results are distinct from the historical laptop runs.
Four pre-existing cooking artifacts retained their hashes after append.

The actual `annotate_dataset.py` wrapper invoked the pinned annotation CLI against
local `QuantTrio/Qwen3.6-27B-AWQ`, revision
`9b507bdc9afafb87b7898700cc2a591aa6639461`. Plan/subtask generation took **13.3 s**;
the upstream validator reported **zero errors and zero warnings**. Publication
produced dataset revision **3**, with two episodes and 240 frames. Independent
checks confirm unchanged non-language data, videos and episode provenance;
exact source timestamps and frame indexing; valid plan/subtask boundaries; and
official reader reload with RGB at frames 0/60/119 per episode.

| Episode | Generated subtask at clip time 0 s | Agent semantic review |
| --- | --- | --- |
| 0, cooking | `slice the meat` | Slicing is supported, but the visible object appears to be a tuber/vegetable. The noun is likely wrong; exact food identity needs human confirmation. |
| 1, cleaning | `wipe the helmet` | Matches the visible action. |

Each plan contains its single subtask. Both four-second clips received one label
from frame zero; this does not validate multi-step transition timing. Labels are
preserved as generated and remain `review_status: pending`.

Six representative overlays per clip plus both world/canonical plots were
inspected. Cooking's left infill projects a large displaced mesh, with an early
root discontinuity; cleaning shows reversed association at frame zero, displaced
meshes and large trajectory jumps. Both omit a visible left hand at the final
frame. These reconstructions remain unsuitable as high-quality pilot evidence.
The VLM uses RGB/task text rather than these trajectories.

Local-only inspection outputs are in
[`outputs/hawor/milestone-2/eidon-annotation-20260925/`](../../../outputs/hawor/milestone-2/eidon-annotation-20260925/):

- [Review page](../../../outputs/hawor/milestone-2/eidon-annotation-20260925/review.html): video with active labels, RGB/overlay switch, speed and seek controls, trajectories, raw label JSONL and reproduced VLM contact sheets. Chrome checks verified both videos, labels, seeking/source-time display, speed and overlay switching.
- [Commands and outputs](../../../outputs/hawor/milestone-2/eidon-annotation-20260925/README.md): `dataset/` contains the annotated LeRobot result; the server is stopped, with 408 MiB GPU memory used afterward.
- [Annotation/reload evidence](../../../outputs/hawor/milestone-2/eidon-annotation-20260925/annotation-validation.json), [annotation log](../../../outputs/hawor/milestone-2/eidon-annotation-20260925/annotation.log), and [browser checks](../../../outputs/hawor/milestone-2/eidon-annotation-20260925/browser-check.json).
- [Preparation results](../../../outputs/hawor/milestone-2/eidon-annotation-20260925/preparation-results.json), [initial GPU failure](../../../outputs/hawor/milestone-2/eidon-annotation-20260925/gpu-preflight.json), and [restart verification](../../../outputs/hawor/milestone-2/eidon-annotation-20260925/gpu-after-restart.json).

The wrapper's arguments, sampling behavior and output fields are explained in the
[annotation topic](../topics/lerobot-pipeline.md#mutation-and-annotation-preservation).
This validation establishes end-to-end execution, dataset preservation and
inspectable real model outputs. The cooking label needs review; neither general
annotation quality, metric trajectory accuracy nor iPhone pilot acceptance is established.
