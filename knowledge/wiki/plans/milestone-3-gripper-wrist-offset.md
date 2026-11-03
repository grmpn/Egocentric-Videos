# Milestone 3 — Config 2 wrist offset

Approved revision 1 · 2026-10-29 · User explicitly requested this adjustment
and a separate comparison viewer; authorization recorded as
`20261029-wrist-offset-001` in the action log.

## Objective and deliverable

Update Config 2 so the rear gripper palm origin is 0.025 m backward along
its existing forward axis from the hand wrist. Produce a reloadable full-video
mapping and open a separate viewer alongside the unchanged saved Config 2 run.

## Scope and boundaries

Keep the wrist→fingertip-midpoint forward direction, roll, orientation, opening,
source frames/timestamps, units, hand identity and validity unchanged. Apply
only the translation `hand_wrist - 0.025 * forward_unit_axis` to both hands.
Make the distance a named setting; absent settings retain zero offset for
earlier saved mappings. Keep existing runs and viewers available. No HaWoR,
arm IK, smoothing, new overlay videos or physical-contact validation.

## Acceptance

Focused tests cover shifted ordinary-FK palm placement, unchanged rotation and
opening, rigid-frame equivariance, and legacy zero-offset behavior. Compare all
valid samples against the saved full-video baseline: exactly 25 mm backward,
unchanged orientation/opening/validity and source alignment. Inspect representative
frames in the new viewer and verify both viewer URLs. Save logs and screenshots
under a new local output directory; update the wiki and commit verified changes.
