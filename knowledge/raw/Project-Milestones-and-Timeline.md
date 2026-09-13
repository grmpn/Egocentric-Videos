# Project Milestones and Timeline

## Overall goal

Build a dataset of egocentric RGB videos with:

- 3D hand trajectories in the world frame
- the same trajectories in a hand-centered canonical frame
- language annotations at the subtask level
- hand-to-gripper and end-effector trajectories
- per-frame validity/provenance and a basic confidence score

Keep the world-frame trajectory as the primary geometric output. The canonical frame should be a derived representation for comparing examples and training models; it should not replace the world frame.

## Decisions and open-question feedback

- **LeRobot format:** Define the target schema before running HaWoR so filenames, timestamps, camera metadata, and annotations are captured consistently. Do the full conversion only after the first HaWoR test, when its actual outputs and failure cases are known.
- **HaWoR modifications:** First reproduce and measure the unchanged pipeline. Only then test one modification at a time against the baseline. The best first change is to preserve detection/interpolation provenance and derive a simple confidence score; model-based uncertainty can wait.
- **Missing-hand cutoff:** Do not choose four or six seconds by intuition. Make the threshold configurable and compare a few values on the pilot clips. Reject clips based on task coverage and trajectory quality, not missing duration alone.
- **More-videos milestone:** Use this to test whether the pipeline generalizes beyond the initial task and recording conditions. Keep HaWoR research changes as a separate, optional track so they do not block the dataset pipeline.
- **YouTube filtering:** Begin with a manually labeled evaluation set. Use titles/hashtags only for candidate retrieval, then inspect sampled frames for first-person viewpoint, visible hands, and task relevance. Train a classifier only if manual filtering becomes the bottleneck.

## Milestones

### 1. Validate HaWoR baseline — 1 week

**Scope**

- Run the unmodified HaWoR pipeline on its bundled example, then on one short segment from an ordinary Ego4D MP4 containing one task.
- Build reusable ingestion, execution, visualization, and logging scripts rather than recreating HaWoR.
- Keep Milestone 1 ingestion MP4-only. Dataset-native archives, frame sequences, camera-calibration readers, fisheye correction, and rectification are deferred until a later milestone demonstrates a need for them.
- Preserve and export HaWoR's existing world-frame result without adding canonicalization, alignment, or other coordinate transformations in this milestone.
- Measure completion status, runtime per clip, peak compute/memory use, and visible failure modes.

**Deliverable:** A reproducible baseline package that processes the bundled HaWoR example and one short Ego4D MP4 segment, exports HaWoR's unchanged world-frame trajectory with validity/provenance metadata, produces an overlay visualization, and includes a one-page benchmark/failure report for each attempt.

### 2. Record and annotate a pilot dataset — 3 weeks

**Scope**

- Record at least 10 usable iPhone clips of one simple task under consistent conditions.
- Run hand tracking first, then package the stable outputs in the chosen LeRobot-compatible schema.
- Define and derive the hand-centered canonical representation after the HaWoR world-frame contract is stable.
- Use `lerobot-annotate` for plan/subtask annotations; disable interjections and VQA unless later experiments need them.

**Deliverable:** A versioned pilot dataset containing RGB video, synchronized world- and canonical-frame hand trajectories, metadata, subtask annotations, confidence/provenance fields, and a short data card describing the task and capture setup.

### 3. Retarget hands and trajectories in simulation — 4 weeks

**Scope**

- Map thumb-index motion to a simple virtual gripper.
- Map the wrist trajectory to the robot end effector.
- Replay the result while enforcing workspace, joint, velocity, acceleration, and gripper limits.

**Deliverable:** A repeatable simulation demo for the pilot task, plus exported robot trajectories and a log showing whether every kinematic and control limit was satisfied.

### 4. Transfer the trajectory to the real robot — 2 weeks

**Scope**

- Transfer the validated simulation trajectory without training a policy.
- Start with slow, supervised playback and conservative safety limits.

**Deliverable:** A recorded real-robot demonstration of the selected task, with execution logs and a short comparison of simulated versus real trajectory error and failure points.

### 5. Expand and stress-test the dataset — 2 weeks

**Scope**

- Record the same task with variation in subject, lighting, background, viewpoint, speed, and hand visibility.
- Measure how often HaWoR succeeds and identify the dominant failure categories.
- Freeze a small evaluation split before making pipeline changes.

**Deliverable:** An expanded dataset of at least 30 usable clips, a fixed evaluation split, and a coverage table showing conditions, success rates, and failure categories.

### 6. Prototype YouTube ingestion — 4 weeks

**Scope**

- Retrieve candidates using positive terms such as “POV” and “first person” plus task/job terms, while excluding obvious gaming and skit content.
- Manually label a small candidate set, then filter with sampled frames for egocentric viewpoint, visible hands, and task relevance.
- Add an automated classifier only if the labeled pilot shows that it is necessary.

**Deliverable:** A reproducible discovery and filtering prototype that produces a reviewed set of at least 25 usable videos or segments, with source/license metadata and measured precision on the manually labeled evaluation set.

## Optional research track: improve HaWoR

Start this only after Milestone 5 provides a stable baseline and failure inventory. Prioritize one narrowly scoped change—such as provenance-aware confidence scoring or confidence based on detection gaps—and compare it with unchanged HaWoR on the frozen evaluation split.

**Deliverable:** One controlled baseline-versus-modification experiment with a documented metric, result, and keep/reject decision.

## Timeline and gates

The core plan is approximately **16 weeks**, excluding setup delays and iteration. Each milestone should begin only when the previous deliverable is reproducible. In particular, do not attempt real-robot playback until the simulation trajectory passes all configured limits, and do not scale data collection until the pilot schema is stable.
