"""Standard v3.1 human reconstruction and fixed-base robot demonstration datasets."""

import hashlib
from pathlib import Path
import shutil
import uuid

import av
import numpy as np
import pyarrow.parquet as pq
import yaml

from egocentric_pipeline.datasets.dataset_transaction import staged_dataset
from egocentric_pipeline.datasets.human_episode import human_arrays
from egocentric_pipeline.datasets.robot_episode import load_robot_episode
from egocentric_pipeline.datasets.statistics import masked_writer_statistics, refresh_numeric_statistics
from egocentric_pipeline.retargeting.trajectory import load_alignment
from egocentric_pipeline.run_metadata import read_json, sha256_file, write_json


LEROBOT_REVISION = '9a6bb61043bac8c14353fcb6ea513b7473c118e3'
CAMERA = 'observation.images.ego'
CONTRACT_VERSION = '3.0'


def read_card(root, kind=None):
    path = Path(root) / 'README.md'
    if not path.exists():
        raise ValueError('Incompatible historical dataset; choose a new output root')
    card = yaml.safe_load(path.read_text().split('---', 2)[1])
    if card.get('contract_version') != CONTRACT_VERSION or (kind and card['kind'] != kind):
        raise ValueError('Incompatible dataset contract or kind')
    return card


def write_card(root, card):
    text = ('---\n' + yaml.safe_dump(card, sort_keys=False) + '---\n\n'
            '# Egocentric ' + card['kind'] + ' dataset\n\n'
            'LeRobot v3.1, pinned writer/reader revision `' + LEROBOT_REVISION + '`. '
            'RGB and all features use the prepared 30 FPS timeline. Hand axis 0 is left, then right. '
            'Pose order is [x,y,z,qx,qy,qz,qw], metres and normalized xyzw quaternions. '
            'source_status/hand_status: 0 unavailable (including unusable geometry), 1 motion-infilled, '
            '2 directly estimated by HaWoR. Infill takes precedence over an unused detector record.\n\n')
    if card['kind'] == 'human':
        text += ('One full prepared video per episode; every frame is retained. '
                 'Hands use one shared gravity-aligned Z-up frame per episode, arbitrary yaw and the original SLAM origin. '
                 'HaWoR claims metres; physical scale and floor height are unmeasured. The aligned camera transform '
                 'is T_aligned_from_camera (OpenCV X right, Y down, Z forward). It is required by camera-motion '
                 'segmentation, head orientation fitting and camera-relative base-height initialization. '
                 'That height is a neutral robot camera-height proxy, not measured floor calibration.\n\n'
                 'MANO reconstruction uses smplx==0.1.28 MANOLayer, separate LEFT/RIGHT assets identified above. '
                 'Apply the pinned HaWoR left shapedirs[:,0,:] *= -1 correction. Articulation contains the 15 '
                 'native MANO joint rotations, three axis-angle radians each, in original MANO order; betas are '
                 'the ten original shape coefficients. Convert root quaternion and articulation to rotation matrices '
                 'and call MANOLayer with pose2rot=False; no PCA or additional pose mean. Root translation is the '
                 'MANO transl parameter, not the physical wrist. Wrist = transl + J(beta)[0]. Alignment rotates '
                 'the physical geometry, including this shape-dependent offset. The compact per-episode rotation '
                 'above permits inversion to the native HaWoR gauge: t_world = R.T @ (t_aligned + offset) - offset, '
                 'R_root_world = R.T @ R_root_aligned. Invalid geometry is NaN and source_status=0. '
                 'Reconstruction needs licensed model files, but no original HaWoR run directory.\n\n'
                 'Dataset identity and immutable episode revisions above pin source links. Append only; exporting '
                 'a regenerated source into a new dataset creates a new identity. Source hashes prevent duplicate append.\n')
    else:
        if card.get('test_dataset'):
            text += ('Test dataset: includes regions that failed the export gate under an explicit override. '
                     'Consult processing diagnostics for gate results; action masks remain unchanged.\n\n')
        text += ('One contiguous exported fixed-base region per episode. Local timestamps restart at zero. '
                 'Without the test override, region export requires the configured fraction (default 85%) of frames to have finite solved '
                 'configurations, no self-collision and no joint position/velocity/acceleration violations. '
                 'Tracking and hand-observation failures remain in action masks but do not reject a region. '
                 'source_episode_index/source_frame_index refer to the pinned human dataset prepared timeline; '
                 'the source revisions above include data and synchronized RGB. No absolute source paths are needed.\n\n'
                 'action: left arm seven radians, right arm seven radians, neck two radians, then left/right '
                 'normalized gripper opening (0 closed, 1 open); no duplicate gripper angles. action.ee: [2,8], '
                 'absolute nominal URDF TCP pose in the documented robot base frame, then opening. FK uses the '
                 'evaluated joint solution, never a human target. TCP and base link names are recorded above.\n\n'
                 'quality.action_valid masks each independently controlled action, including IK, finite values, '
                 'joint position/speed/acceleration and discrete self-collision. Collision and invalid locked '
                 'joints invalidate the whole configuration. EE pose validity is the conjunction of its seven '
                 'arm masks; opening validity is its gripper mask. Neck validity does not affect base-frame arm FK. '
                 'Finite invalid predictions are retained; unavailable joints use zero, unavailable TCPs use '
                 'zero translation/identity quaternion. Out-of-range openings use zero. These placeholders always have false masks.\n\n'
                 'Use egocentric_pipeline.datasets.training.ActionTrainingDataset(target="joint" or "ee") '
                 'and masked_mse (or an equivalent elementwise masked loss). The adapter aligns temporal target '
                 'and mask offsets, excludes padding and sanitizes invalid values before normalization/loss. '
                 'Standard policies do not automatically honor quality fields or select action.ee.\n\n'
                 'Statistics reduce only finite, valid components. Global numeric statistics are recomputed '
                 'from rows after append because standard scalar counts cannot aggregate unequal component masks. '
                 'count denotes stored rows; components with no valid samples have mean/min/max/quantiles 0 and '
                 'std 1. Do not recompute normalization with unmodified unmasked dataset tools. '
                 'Annotations contain plan/subtask language; language_events is declared because the pinned '
                 'annotator writes both language columns. Execution logs remain in the run directory.\n')
    text += '\nThese exports do not certify hardware safety, physical calibration or annotation semantics.\n'
    (root / 'README.md').write_text(text)


def episode_features(clip, arrays, *, language=False, action_names=None):
    features = {CAMERA: {'dtype': 'video', 'shape': (clip['prepared']['height'], clip['prepared']['width'], 3),
                         'names': ['height', 'width', 'channels']}}
    for key, value in arrays.items():
        features[key] = {'dtype': str(value.dtype), 'shape': value.shape[1:] or (1,), 'names': None}
    if action_names:
        features['action']['names'] = action_names
        features['quality.action_valid']['names'] = action_names
    if language:
        from lerobot.datasets.language import language_feature_info
        features.update(language_feature_info())
    return features


def read_episode(root, episode_index):
    from lerobot.datasets.dataset_metadata import LeRobotDatasetMetadata

    root = Path(root)
    meta = LeRobotDatasetMetadata('local/dataset', root=root)
    if not 0 <= episode_index < meta.total_episodes:
        raise ValueError('Source episode index is outside the human dataset')
    table = pq.read_table(root / meta.get_data_file_path(episode_index), filters=[('episode_index', '=', episode_index)])
    return {k: np.asarray(table[k].to_pylist(), dtype=v['dtype']).reshape(len(table), *v['shape'])
            for k, v in meta.features.items() if v['dtype'] not in ('video', 'image', 'language', 'string')}


def episode_revision(root, episode_index):
    """Pin numeric frame data and its video shard; ordinary append preserves shards."""
    from lerobot.datasets.dataset_metadata import LeRobotDatasetMetadata

    root = Path(root)
    meta = LeRobotDatasetMetadata('local/dataset', root=root)
    digest = hashlib.sha256()
    for key, array in sorted(read_episode(root, episode_index).items()):
        digest.update(key.encode())
        digest.update(str(array.shape).encode())
        digest.update(array.tobytes())
    digest.update(sha256_file(root / meta.get_video_file_path(episode_index, CAMERA)).encode())
    return digest.hexdigest()


def _check_compatibility(root, features, kind):
    info = read_json(root / 'meta/info.json')
    if info['codebase_version'] != 'v3.1' or info['fps'] != 30:
        raise ValueError('Append requires LeRobot v3.1 at 30 FPS')
    read_card(root, kind)
    automatic = {'timestamp', 'frame_index', 'episode_index', 'index', 'task_index'}
    if set(info['features']) - automatic != set(features):
        raise ValueError('Incompatible feature schema')
    for key, feature in features.items():
        saved = info['features'][key]
        if saved['dtype'] != feature['dtype'] or tuple(saved['shape']) != tuple(feature['shape']) or saved['names'] != feature['names']:
            raise ValueError(f'Incompatible feature or image geometry: {key}')


def _rgb_frames(video_source):
    """Use the human dataset as the authoritative robot RGB source."""
    if isinstance(video_source, tuple):
        from lerobot.datasets.lerobot_dataset import LeRobotDataset
        root, episode_index = video_source
        reader = LeRobotDataset('local/human', root=root, video_backend='pyav')
        record = reader.meta.episodes[episode_index]
        for local, index in enumerate(range(record['dataset_from_index'], record['dataset_to_index'])):
            rgb = (reader[index][CAMERA].numpy().transpose(1, 2, 0) * 255).round().astype(np.uint8)
            yield local, rgb
    else:
        with av.open(str(video_source)) as video:
            for index, frame in enumerate(video.decode(video=0)):
                if abs(float(frame.pts * frame.time_base) - index / 30) > 1e-7:
                    raise ValueError('Prepared RGB timestamps differ from the 30 FPS timeline')
                yield index, frame.to_ndarray(format='rgb24')


def _write_episodes(stage, episodes, video_path, clip, features, card, task):
    from lerobot.configs import RGBEncoderConfig
    from lerobot.datasets.dataset_metadata import CODEBASE_VERSION
    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    if CODEBASE_VERSION != 'v3.0':
        raise RuntimeError('Use the pinned LeRobot environment')
    if not isinstance(task, str) or not task.strip():
        raise ValueError('Supply a nonempty task')
    options = dict(root=stage, video_backend='pyav', encoder_threads=2,
                   rgb_encoder=RGBEncoderConfig(vcodec='h264', crf=18, preset='fast'))
    if stage.exists():
        _check_compatibility(stage, features, card['kind'])
        dataset = LeRobotDataset.resume(card['repo_id'], **options)
    else:
        dataset = LeRobotDataset.create(card['repo_id'], fps=30, features=features,
                                        robot_type='human_mano' if card['kind'] == 'human' else 'purdue_alex', **options)
        dataset.meta.info.codebase_version = 'v3.1'
    first = dataset.meta.total_episodes
    try:
        with masked_writer_statistics():
            for start, stop, arrays in episodes:
                written = 0
                for index, rgb in _rgb_frames(video_path):
                    if index >= stop:
                        break
                    if index < start:
                        continue
                    row = {k: np.array(v[index - start], copy=True).reshape(features[k]['shape']) for k, v in arrays.items()}
                    row.update({k: None for k, v in features.items() if v['dtype'] == 'language'})
                    row.update({CAMERA: rgb, 'task': task.strip()})
                    dataset.add_frame(row)
                    written += 1
                if written != stop - start:
                    raise ValueError('RGB ended before the source region')
                dataset.save_episode()
    finally:
        dataset.finalize()
    # The pinned video writer leaves its temporary PNG directory after encoding.
    if (stage / 'images').exists():
        shutil.rmtree(stage / 'images')
    refresh_numeric_statistics(stage, dataset.features)
    write_card(stage, card)
    reader = LeRobotDataset(card['repo_id'], root=stage, video_backend='pyav')
    for offset, (start, stop, expected) in enumerate(episodes):
        index = first + offset
        actual = read_episode(stage, index)
        for key, values in expected.items():
            if not np.array_equal(actual[key].reshape(values.shape), values, equal_nan=True):
                raise ValueError(f'Parquet changed values or shape: {key}')
        record = reader.meta.episodes[index]
        for local in (0, stop - start - 1):
            row = reader[record['dataset_from_index'] + local]
            if int(row['frame_index']) != local or abs(float(row['timestamp']) - local / 30) > 1e-5:
                raise ValueError('Reader lost episode-local indexing')
            if tuple(row[CAMERA].shape) != (3, clip['prepared']['height'], clip['prepared']['width']):
                raise ValueError('Reader changed RGB geometry')
    return list(range(first, first + len(episodes)))


def append_human_episode(alignment_directory, root, *, task, repo_id='local/egocentric-human'):
    aligned, report, clip = load_alignment(alignment_directory)
    start, stop = clip['selection']['resolved_interval_s']
    if start != 0 or not np.isclose(stop, clip['source']['duration_s'], atol=1e-9, rtol=0):
        raise ValueError('Human episodes require one full input video without trimming')
    arrays = human_arrays(aligned)
    models = [{'hand': side, 'sha256': report['inputs'][f'mano_{side}']['sha256']} for side in ('left', 'right')]
    source_hash = sha256_file(report['inputs']['prepared_video']['path'])
    with staged_dataset(root) as stage:
        card = (read_card(stage, 'human') if stage.exists() else
                dict(library_name='lerobot', contract_version=CONTRACT_VERSION, kind='human', repo_id=repo_id,
                     dataset_id=str(uuid.uuid4()), mano_models=models, episodes=[]))
        if card['mano_models'] != models:
            raise ValueError('Incompatible MANO model identities')
        if any(e['prepared_sha256'] == source_hash for e in card['episodes']):
            raise ValueError('This prepared source already exists in the human dataset')
        episode = len(card['episodes'])
        record = dict(episode_index=episode, prepared_sha256=source_hash,
                      rotation_aligned_from_world=aligned['rotation_aligned_from_world'].tolist())
        card['episodes'].append(record)
        _write_episodes(stage, [(0, len(aligned['frame_index']), arrays)], report['inputs']['prepared_video']['path'],
                        clip, episode_features(clip, arrays), card, task)
        record['revision'] = episode_revision(stage, episode)
        write_card(stage, card)
    return {'dataset_root': str(Path(root).resolve()), 'episode_index': episode, 'revision': record['revision']}


def append_robot_regions(human_root, source_episode_index, trajectory_directories, root, *, task,
                         diagnostic_path, evaluation_directories=None, min_episode_valid_ratio=.85,
                         repo_id='local/egocentric-robot', include_rejected_regions=False):
    if not np.isfinite(min_episode_valid_ratio) or not 0 <= min_episode_valid_ratio <= 1:
        raise ValueError('min_episode_valid_ratio must be between 0 and 1')
    if not trajectory_directories:
        raise ValueError('Supply at least one completed evaluated trajectory')
    human_root, root = Path(human_root), Path(root)
    if root.resolve().is_relative_to(human_root.resolve()) or human_root.resolve().is_relative_to(root.resolve()):
        raise ValueError('Human and robot roots must be separate non-nested datasets')
    diagnostic_path = Path(diagnostic_path)
    if diagnostic_path.resolve().is_relative_to(root.resolve()) or diagnostic_path.resolve().is_relative_to(human_root.resolve()):
        raise ValueError('Export diagnostics must stay in the processing run, outside both datasets')
    if diagnostic_path.exists():
        raise ValueError('Export diagnostics already exist; choose a new run path')
    source_card = read_card(human_root, 'human')
    source = read_episode(human_root, source_episode_index)
    revision = episode_revision(human_root, source_episode_index)
    if revision != source_card['episodes'][source_episode_index]['revision']:
        raise ValueError('Human source revision changed; regenerate its dependent robot dataset')
    directory = Path(trajectory_directories[0])
    report = read_json(directory / 'retargeting_report.json')
    with np.load(directory / 'trajectory_retargeted.npz', allow_pickle=False) as saved:
        solved = dict(saved)
    # Check the actual human representation, not paths or run names. Quaternion
    # round-trip differences from a rehydrated human episode allow float32 tolerance.
    expected = human_arrays(solved)
    for key, values in expected.items():
        if values.shape != source[key].shape or not np.allclose(values, source[key], atol=2e-6, rtol=0, equal_nan=True):
            raise ValueError(f'Robot trajectory differs from source human episode: {key}')
    n = len(source['frame_index'])
    clip = {'prepared': {'height': read_json(human_root / 'meta/info.json')['features'][CAMERA]['shape'][0],
                         'width': read_json(human_root / 'meta/info.json')['features'][CAMERA]['shape'][1]},
            'selection': {'resolved_interval_s': [0, float(solved['source_timestamp_s'][-1] + 1 / 30)]},
            'frames': {'mapping': [{'source_frame_index': i} for i in range(n)]}}
    # Existing loader verifies evaluated predictions, transforms and disjoint regions.
    keys = ['frame_index', 'timestamp_s', 'source_timestamp_s', 'export_valid', 'motion_infilled',
            'hand_pose_axis_angle', 'mano_betas']
    arrays, diagnostics = load_robot_episode(trajectory_directories, {k: solved[k] for k in keys}, clip,
                                            report['source_run_id'], evaluation_directories)
    episodes = []
    for region in diagnostics['regions']:
        start, stop = region['episode_frame_interval']
        valid = arrays['observation.robot.action_valid'][start:stop]
        ratio = region['constraint_valid_frames'] / (stop - start)
        accepted = ratio >= min_episode_valid_ratio
        region.update(valid_ratio=ratio, action_valid_ratio=float(valid.all(axis=1).mean()),
                      acceptance_passed=accepted, exported=accepted or include_rejected_regions,
                      export_override=bool(not accepted and include_rejected_regions),
                      rejection_reason=None if accepted else 'constraint_valid_ratio')
        if not region['exported']:
            continue
        action = np.nan_to_num(arrays['action'][start:stop], nan=0., posinf=0., neginf=0.)
        ee = arrays['action.ee'][start:stop].copy()
        missing = ~np.isfinite(ee[..., :7]).all(axis=-1)
        ee[missing, :7] = [0, 0, 0, 0, 0, 0, 1]
        opening = arrays['action'][start:stop, -2:]
        opening = np.where(np.isfinite(opening) & (opening >= 0) & (opening <= 1), opening, 0.)
        action[:, -2:] = opening
        ee[..., 7] = opening
        values = {'action': action, 'action.ee': ee, 'quality.action_valid': valid,
                  'quality.hand_status': source['observation.hands.source_status'][start:stop],
                  'source_episode_index': np.full((stop - start, 1), source_episode_index, np.int64),
                  'source_frame_index': np.arange(start, stop, dtype=np.int64)[:, None]}
        episodes.append((start, stop, values))
    diagnostics.update(min_episode_valid_ratio=min_episode_valid_ratio,
                       include_rejected_regions=include_rejected_regions,
                       valid_ratio_basis='finite_solved_configuration_and_self_collision_free_and_joint_limits',
                       source_episode_index=source_episode_index,
                       source_revision=revision, episode_indices=[])
    if episodes:
        with staged_dataset(root) as stage:
            embodiment = {k: report['robot_settings'][k] for k in ('asset_revision', 'urdf', 'base_frame', 'tool_frames')}
            card = (read_card(stage, 'robot') if stage.exists() else
                    dict(library_name='lerobot', contract_version=CONTRACT_VERSION, kind='robot', repo_id=repo_id,
                         embodiment=embodiment, source_dataset_id=source_card['dataset_id'], sources={}))
            if card['embodiment'] != embodiment or card['source_dataset_id'] != source_card['dataset_id']:
                raise ValueError('Incompatible robot embodiment or source human dataset')
            previous = card['sources'].get(source_episode_index)
            if previous is not None and previous != revision:
                raise ValueError('Human source revision differs from existing robot episodes')
            if stage.exists():
                for path in stage.glob('data/*/*.parquet'):
                    table = pq.read_table(path, columns=['source_episode_index', 'source_frame_index']).to_pydict()
                    for ep, frame in zip(table['source_episode_index'], table['source_frame_index']):
                        if ep == source_episode_index and any(a <= frame < b for a, b, _ in episodes):
                            raise ValueError('This source region already exists in the robot dataset')
            card['sources'][source_episode_index] = revision
            if include_rejected_regions:
                card['test_dataset'] = True
            features = episode_features(clip, episodes[0][2], language=True, action_names=diagnostics['action_names'])
            diagnostics['episode_indices'] = _write_episodes(stage, episodes, (human_root, source_episode_index), clip, features, card, task)
    write_json(diagnostic_path, diagnostics)
    return {'dataset_root': str(root.resolve()), 'episode_indices': diagnostics['episode_indices'],
            'source_episode_index': source_episode_index, 'source_revision': revision,
            'accepted_regions': sum(r['acceptance_passed'] for r in diagnostics['regions']),
            'rejected_regions': sum(not r['acceptance_passed'] for r in diagnostics['regions']),
            'exported_regions': len(episodes),
            'overridden_regions': sum(r['export_override'] for r in diagnostics['regions'])}
