# Milestone 1 baseline acceptance

Accepted on 2026-09-18. Migrated from the prior project status on 2026-09-22;
historical execution and review claims below were not rerun during migration.
The original record is recoverable at Git revision
`908ea97bfd2b75f762b747aefc395eed383c1b18:knowledge/agent/PROJECT_STATUS.md`.

## Deliverable and verification

The reproducible unchanged-HaWoR baseline processes the bundled example and an
Ego4D MP4 segment, exports native world trajectories with validity/provenance,
and produces overlays, world previews, and per-attempt benchmark/failure reports.
The [approved plan](../plans/milestone-1-hawor-baseline.md) retains original scope.

The acceptance record reports all 88 checked run artifacts retaining their hashes.
Hosted [CPU tests run 35381886887](https://github.com/grmpn/Egocentric-Videos/actions/runs/35381886887)
passed for implementation commit `e7ef68c9f22441dd342cddd07c8fbb5ac2419d11`;
82 local tests also passed. The implementation was merged through PR #1 in commit
`a37fdbb3c8d4817ff351611498b2f06c1ca937c5`. These are historical checks, not tests
of every later revision. Environment recreation and earlier implementation checks
are retained in the [action history](../logs/2026-09.jsonl).

## Acceptance and source provenance

On 2026-09-18 the user confirmed that both supplied videos were obtained through approved Ego4D access and are covered by their Ego4D license agreement: “Yes, for both Ego4D videos.” License reference: [Ego4D License Agreement and official access documentation](https://ego4d-data.org/docs/start-here/#ego4d-license-agreement). This records the user's attestation; no credentials or private signed documents were collected.

| Supplied source | User-supplied Ego4D UID | Verified source SHA-256 |
| --- | --- | --- |
| `Ego4D-cooking.mp4` | `002c3b5c-ed86-4af3-99a1-4b497b7c8a86` | `a5d1e917021aff07196c8c8e6abd3d021bf03937ae47eda0db5e0107f8cc7014` |
| `Ego4D-bike-trim.mp4` | `01aed4ae-486e-41eb-91f8-4d2e8a46db7d` | `c59f1ea2301fe6e23485b23d0f4899632a2d73731943c0ea2340cd1e0e635989` |

The required Ego4D acceptance example is cooking interval **20:00–20:04**, run `20260918T171726548487Z-01f003922c21`. Its separate input `cooking-1200-1204.mp4` has SHA-256 `edb9567defa02e842d37118b59e3cb8b63196c21bed0fe701aadd1583bda4152`; add 1200 seconds to exported timestamps to recover the original cooking-video timestamps. The [trim evidence](../../../outputs/hawor/milestone-1/ego4d-evaluation-20260918-01/trimming.json) records the command and source chain. The accepted bundled example is run `20260916T202520659122Z-b078a74f8804`. Both runs have reviewed overlays, world previews, unchanged native-world exports, finalized manifests, and per-run benchmark reports. The bicycle evaluation is supplementary; its unknown full-recording offset does not affect the cooking acceptance example.

This is a dated post-run provenance addendum. Original manifests, requests, benchmarks, and evaluation summaries remain unchanged, including their execution-time missing-license warnings. This record resolves that missing source-access/license evidence for both supplied sources without rewriting run history or rerunning inference. The machine-readable acceptance record has SHA-256 `922a42a62d4ba57bde23a0b9ba15f7675aa5f65e1a4f928ad97e77d8261ed00d`.

Acceptance establishes a reproducible unchanged-HaWoR baseline with documented failure modes. Approximate intrinsics, residual alignment/jitter, and unreliable infilling remain recorded limitations; metric reconstruction accuracy is not an acceptance claim. Licensed inputs, model assets, and generated evidence remain local and untracked.


## Limitations and interrupted attempts

- No remaining Milestone 1 acceptance blockers. The following are retained execution/quality limitations and historical failure evidence.
- GPU execution requires host access outside the sandbox. All ten completed Ego4D runs fit the local 8 GB GPU, with sampled device-wide memory of 7.78–7.81 GiB; feasibility for longer or different inputs is not established.
- Earlier recreated-environment attempts `20260916T171924714596Z-263ebb797b15` and `20260916T172604203202Z-5d6f4c6dcbcf` have stale running manifests and logs ending during SLAM. No corresponding processes remain on the host. Their termination cause, exit time, runtime, and resource peaks are unknown; raw evidence is preserved. They have no finalized automatic reports and are not accepted validation runs.
- Both Ego4D sources have user-confirmed approved access and the license reference recorded above. The bicycle file's offset within the full recording remains unknown; its supplementary evaluation timestamps map only to the supplied trimmed source.
- The first 43:20 evaluation attempt (`20260918T172544016517Z-f3e6d3ac5632`) was interrupted at SLAM startup; launcher exit 143, cause unknown. Host checks found no remaining corresponding processes. Raw evidence is preserved in the evaluation directory, and a fresh retry completed; the interrupted attempt is excluded from completed-run timing.


## Evidence locations

- [Machine-readable acceptance](../../../outputs/hawor/milestone-1/milestone-1-acceptance-20260918-01.json).
- [Five cooking evaluations](../../../outputs/hawor/milestone-1/ego4d-evaluation-20260918-01/SUMMARY.md).
- [Five bicycle evaluations](../../../outputs/hawor/milestone-1/ego4d-bike-evaluation-20260918-01/SUMMARY.md).
- [Local Milestone 1 summary](../../agent/summaries/MILESTONE_1_SUMMARY.md) and [Week 1 report](../../agent/summaries/reports/Week-1.md).

Outputs, reports, licensed inputs, and figures remain local and ignored by Git.
Their links resolve only where the corresponding evidence is retained. Historical
warnings in original run artifacts remain unchanged; the dated acceptance addendum
above owns their resolution. Current workflow and contracts live in the
[HaWoR pipeline topic](../topics/hawor-pipeline.md).
