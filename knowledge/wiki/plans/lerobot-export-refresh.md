# Separate human reconstruction and robot training datasets

Approved · revision 1 · 2026-11-12 · User: “Approve revision 1 and implement”.
Approval event: `20261112-export-refresh-003` in the [November log](../logs/2026-11.jsonl).
Scope source: the user's 2026-11-12 implementation specification, attachment
`2c9d55b5-9f66-4b58-9327-b5ca2a3f2dc4/pasted-text-1.txt`.

## Objective and deliverable

Refresh the Milestone 3 export into two clean, independently loadable
LeRobotDataset v3.1 outputs: embodiment-independent human reconstruction and
embodiment-specific robot demonstrations. This supersedes the completed cleanup
plan's full-video robot episode contract and retirement of hand-only export.

## Scope and boundaries

- Export one complete prepared video per human episode, retaining every frame,
  synchronized RGB, structured left/right MANO root poses, articulation, shape,
  physical wrists and categorical observation/infill/invalid provenance. Preserve
  normalized xyzw quaternions, metres and a consistent gravity-aligned frame;
  document model conventions and indispensable calibration. Retain one aligned
  camera transform only where required by reusable downstream processing.
- Make the human dataset usable for reconstruction and subsequent retargeting
  without original HaWoR directories. Preserve any floor reference needed for
  base placement and distinguish an existing height proxy from measured floor
  calibration. Reuse the existing robot pipeline; do not introduce a new robot
  solver or embodiment implementation.
- Export one contiguous fixed-base region per robot episode, with local timestamps,
  matching RGB, stable source human episode/frame references and a documented
  source revision. Preserve unique actuator commands and add absolute base-frame
  TCP actions from accepted joint-solution FK. Keep per-component feasibility and
  hand provenance, including isolated invalid frames. Accept regions at a configurable
  default 85% fully valid frames without weakening geometric constraints; record
  rejected regions and reasons in run diagnostics.
- Make statistics and training-target selection explicitly mask-aware for joint
  and EE actions. Keep robot geometry/solver diagnostics in processing artifacts.
  Use standard dataset metadata and root README documentation; remove custom
  export metadata and annotation staging from final datasets. Annotate only the
  new robot regions with the pinned `lerobot-annotate` plan/subtask workflow.
- Update `pipeline/run.sh`, affected commands, consumers and documentation for
  both outputs, threshold selection and region annotation. Preserve compatible
  create/append behavior, original processing artifacts and historical datasets,
  including `outputs/old/`. Upstream perception changes, solver retuning, hardware
  execution and actual policy training are excluded.

## Acceptance

Use focused production-workflow tests and a small representative video containing
observed, infilled and invalid hands. Verify MANO reconstruction and aligned wrists,
multidimensional Parquet round trips, FK consistency, actuator order, validity and
temporal limit checks, 85% acceptance/rejection, source/RGB alignment, local times,
mask-aware statistics and training loss handling. Exercise official readers,
create/append and annotation preservation, plus export from independently retained
human data. Run the updated shell workflow using representative saved stages;
inspect decoded frames and geometry views. Save logs, reports and review artifacts
under `outputs/lerobot-export-refresh/`. Report limitations explicitly; this export
refresh does not establish physical calibration, annotation semantic acceptance,
hardware safety or completion of the broader simulation milestone.
