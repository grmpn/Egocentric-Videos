"""Structured, embodiment-independent MANO data and a reusable alignment boundary."""

from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from egocentric_pipeline.run_metadata import sha256_file, write_json


def source_status(arrays):
    """Invalidity takes precedence over provenance; infill beats unused detections.

    HaWoR motion_infilled = hawor_valid AND NOT direct_estimation. A detection
    may exist without a retained estimation chunk and does not override infill.
    """
    valid = arrays['export_valid']
    return np.where(valid, np.where(arrays['motion_infilled'], 1, 2), 0).astype(np.uint8)


def human_arrays(aligned):
    valid = aligned['export_valid']
    if valid.ndim != 2 or valid.shape[1] != 2 or valid.dtype != bool:
        raise ValueError('Hand usability must be boolean [T,2], left then right')
    if aligned['motion_infilled'].shape != valid.shape or aligned['motion_infilled'].dtype != bool:
        raise ValueError('Hand provenance must be boolean [T,2]')
    for key, width in (('root_translation_aligned_m', 3), ('root_orientation_aligned_axis_angle', 3),
                       ('wrist_position_aligned_m', 3), ('hand_pose_axis_angle', 45), ('mano_betas', 10)):
        values = aligned[key]
        if values.shape != (*valid.shape, width) or values.dtype != np.float32:
            raise ValueError(f'{key} must be float32 [T,2,{width}]')
        if not np.isfinite(values[valid]).all():
            raise ValueError(f'Usable hand geometry must be finite: {key}')
    camera_rotation = aligned['camera_rotation_aligned_from_camera']
    camera_position = aligned['camera_position_aligned_m']
    if (camera_rotation.shape != (len(valid), 3, 3) or camera_position.shape != (len(valid), 3)
            or not np.isfinite(camera_position).all()
            or not np.allclose(camera_rotation @ camera_rotation.swapaxes(-1, -2), np.eye(3), atol=1e-6, rtol=0)
            or not np.allclose(np.linalg.det(camera_rotation), 1., atol=1e-6, rtol=0)):
        raise ValueError('Camera poses must be finite proper aligned transforms')
    status = source_status(aligned)
    root = np.full((*status.shape, 7), np.nan, np.float32)
    valid = status > 0
    root[..., :3] = aligned['root_translation_aligned_m']
    root[valid, 3:] = Rotation.from_rotvec(aligned['root_orientation_aligned_axis_angle'][valid]).as_quat()
    camera = np.tile(np.eye(4, dtype=np.float32), (len(status), 1, 1))
    camera[:, :3, :3] = aligned['camera_rotation_aligned_from_camera']
    camera[:, :3, 3] = aligned['camera_position_aligned_m']
    return {
        'observation.hands.root_pose_aligned': root,
        'observation.hands.pose_axis_angle': aligned['hand_pose_axis_angle'].copy(),
        'observation.hands.betas': aligned['mano_betas'].copy(),
        'observation.hands.wrist_position_aligned_m': aligned['wrist_position_aligned_m'].copy(),
        'observation.hands.source_status': status,
        'observation.camera.pose_aligned': camera,
    }


def aligned_from_human(data):
    """Restore the existing processing boundary, choosing aligned space as world.

    Original native timing/gauge is unnecessary for new retargeting: source indices
    now refer to the prepared human episode. All calibrated geometry is retained.
    """
    root = data['observation.hands.root_pose_aligned']
    status = data['observation.hands.source_status']
    valid = status > 0
    rotation = np.full((*status.shape, 3), np.nan, np.float32)
    rotation[valid] = Rotation.from_quat(root[valid, 3:]).as_rotvec()
    wrist = data['observation.hands.wrist_position_aligned_m']
    camera = data['observation.camera.pose_aligned']
    n = len(root)
    arrays = {
        'frame_index': np.arange(n, dtype=np.int64), 'timestamp_s': np.arange(n) / 30,
        'source_timestamp_s': np.arange(n) / 30, 'export_valid': valid,
        'hawor_valid': valid.copy(), 'motion_infilled': status == 1,
        'direct_detection': status == 2, 'detector_confidence': np.full(status.shape, np.nan, np.float32),
        'hand_pose_axis_angle': data['observation.hands.pose_axis_angle'], 'mano_betas': data['observation.hands.betas'],
        'root_translation_aligned_m': root[..., :3].copy(), 'root_orientation_aligned_axis_angle': rotation,
        'wrist_position_aligned_m': wrist.copy(), 'mano_root_offset_m': wrist - root[..., :3],
        'rotation_aligned_from_world': np.eye(3), 'rotation_world_from_aligned': np.eye(3), 'up_world': np.array([0., 0., 1.]),
        'camera_position_aligned_m': camera[:, :3, 3].astype(np.float64),
        'camera_rotation_aligned_from_camera': camera[:, :3, :3].astype(np.float64),
    }
    for key in ('root_translation_aligned_m', 'root_orientation_aligned_axis_angle', 'wrist_position_aligned_m',
                'camera_position_aligned_m', 'camera_rotation_aligned_from_camera'):
        arrays[key.replace('aligned', 'world')] = arrays[key].copy()
    return arrays


def materialize_human_alignment(root, episode_index, output, model_paths):
    """Create ordinary run artifacts using only a human dataset and licensed models.

    No HaWoR inference, SLAM files, original videos or original absolute paths are
    read. Model files may live anywhere; their identities must match the README.
    """
    import av
    from egocentric_pipeline.datasets.lerobot_export import read_card, read_episode, episode_revision, CAMERA
    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    root, output = Path(root), Path(output).resolve()
    card = read_card(root, 'human')
    if len(model_paths) != 2:
        raise ValueError('Provide left and right licensed MANO models')
    for path, expected in zip(model_paths, card['mano_models']):
        if sha256_file(path) != expected['sha256']:
            raise ValueError('MANO model differs from the human dataset reconstruction convention')
    data = read_episode(root, episode_index)
    arrays = aligned_from_human(data)
    revision = episode_revision(root, episode_index)
    if revision != card['episodes'][episode_index]['revision']:
        raise ValueError('Human source revision changed; use the original source dataset')
    output.mkdir(parents=True, exist_ok=False)
    video_path = output / 'prepared.mp4'
    reader = LeRobotDataset(card['repo_id'], root=root, video_backend='pyav')
    episode = reader.meta.episodes[episode_index]
    height, width = reader.features[CAMERA]['shape'][:2]
    with av.open(str(video_path), 'w') as container:
        stream = container.add_stream('libx264', rate=30)
        stream.width, stream.height, stream.pix_fmt = width, height, 'yuv420p'
        stream.options = {'crf': '18', 'preset': 'fast'}
        for index in range(episode['dataset_from_index'], episode['dataset_to_index']):
            rgb = (reader[index][CAMERA].numpy().transpose(1, 2, 0) * 255).round().astype(np.uint8)
            for packet in stream.encode(av.VideoFrame.from_ndarray(rgb, format='rgb24')):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    n = len(arrays['frame_index'])
    clip = {'prepared': {'frame_count': n, 'fps': 30, 'width': width, 'height': height},
            'source': {'duration_s': n / 30, 'sha256': sha256_file(video_path)},
            'selection': {'resolved_interval_s': [0, n / 30]},
            'frames': {'mapping': [{'frame_index': i, 'timestamp_s': i / 30,
                       'source_frame_index': i, 'source_timestamp_s': i / 30} for i in range(n)]}}
    write_json(output / 'clip_metadata.json', clip)
    np.savez_compressed(output / 'trajectory_aligned.npz', **arrays)
    report = {'status': 'completed', 'hand_order': ['left', 'right'],
              'source_run_id': f"human-{card['dataset_id']}-{episode_index}-{revision}",
              'source_human': {'dataset_id': card['dataset_id'], 'episode_index': episode_index, 'revision': revision},
              'inputs': {'prepared_video': {'path': str(video_path)},
                         'clip_metadata': {'path': str(output / 'clip_metadata.json')},
                         **{f'mano_{side}': {'path': str(Path(path).resolve()), 'sha256': sha256_file(path)}
                            for side, path in zip(('left', 'right'), model_paths)}},
              'transform': {'rotation_aligned_from_world': np.eye(3).tolist()},
              'limitations': ['No measured floor/scale; camera-relative base-height initialization remains a proxy.']}
    write_json(output / 'alignment_report.json', report)
    return report
