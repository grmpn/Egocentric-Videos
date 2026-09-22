# HaWoR pipeline

Current behavior summarized from static source inspection on 2026-09-22 at
implementation revision `908ea97bfd2b75f762b747aefc395eed383c1b18`. Historical
execution evidence and limitations belong to the
[Milestone 1 acceptance record](../experiments/milestone-1-baseline.md).

## Stage boundaries

The supported path is local MP4 → timestamp-based preparation → unchanged HaWoR
inference → native-world export → visual review and run reporting. Preparation
returns the same typed metadata contract whether the clip was newly prepared or
loaded from its saved metadata. HaWoR owns reconstruction, SLAM, metric scaling,
and infilling; project code preserves and validates its result.

Original inputs stay under `data/source/`; prepared RGB and source/frame mappings
live under `data/prepared/`. Each attempt receives its own directory under
`outputs/hawor/`, containing native evidence, exported trajectories, a run manifest,
and review artifacts. The Milestone 1 entry point creates a report for that attempt,
including reportable failures. Input files and previous runs must not be overwritten.

Use the [README](../../../README.md) for commands and the
[environment guide](../../../environment/README.md) for setup. Those documents own
operating instructions; this page owns the conceptual boundaries and conventions.

## Coordinates, time, and validity

- Preparation selects frames by presentation timestamp on a 30 FPS grid without
  changing image geometry. Metadata retains the selected source-frame mapping.
- Exported `timestamp_s` is relative to the prepared clip; `source_timestamp_s`
  refers to the supplied source MP4. For a separately trimmed MP4, its original
  recording offset must be retained separately and added when mapping back.
- Exports are frame-major with hand order `[left, right]`. World translations use
  HaWoR's claimed metres in its clip-local SLAM frame; axes/origins cannot be assumed
  comparable between clips. Canonicalization, alignment, smoothing, and robot-frame
  conversion are outside the implemented baseline.
- The exporter requires native float32 arrays and preserves their bytes apart
  from hand/frame axis reordering. The current implementation rejects a dtype
  mismatch rather than converting it.
- `direct_detection`, `motion_infilled`, `hawor_valid`, and `export_valid` have
  distinct meanings. Infill is native validity without saved direct estimation;
  export validity additionally requires finite values and successful upstream
  stages. A detection alone does not establish direct estimation.
- Detector confidence is absent (`NaN`) without a direct detection. Provenance
  follows native majority track-to-hand assignment, with raw disagreements saved.
  Detector confidence does not establish geometric accuracy.

The [request contract](../../../src/egocentric_pipeline/clip_request.py),
[preparation and metadata](../../../src/egocentric_pipeline/video_preparation.py),
[world export](../../../src/egocentric_pipeline/world_export.py), and
[pipeline](../../../src/egocentric_pipeline/pipeline.py) are the executable definitions.
Generated clip/trajectory metadata describes each actual artifact. Update this page
when those shared boundaries change; avoid duplicating every schema field here.

## Validation limits

CPU tests exercise project contracts. GPU inference, real input processing, and
overlay/trajectory inspection require separate evidence. A stale `running` manifest
or an existing output file cannot establish successful completion. Current accepted
scope and known interrupted runs are recorded on the acceptance page.
