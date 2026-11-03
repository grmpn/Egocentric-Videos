"""Robot episode boundaries, source alignment and invalid action semantics."""

import numpy as np
import pytest

from egocentric_pipeline.datasets.robot_episode import ALIGNED_FIELDS, CAMERA_FIELDS, load_robot_episode
from egocentric_pipeline.run_metadata import write_json


def make_robot_regions(tmp_path, world=None, source_run_id="same-video", clip=None):
    count = 6
    times = np.arange(count) / 30
    world = world if world is not None else {'frame_index': np.arange(count), 'timestamp_s': times,
             'source_timestamp_s': 2 + times, 'export_valid': np.ones((count, 2), bool),
             'motion_infilled': np.zeros((count, 2), bool)}
    clip = clip if clip is not None else {'selection': {'resolved_interval_s': [2, 2.2]},
            'frames': {'mapping': [{'source_frame_index': 120 + 2 * i} for i in range(count)]}}
    times = world['timestamp_s']
    names = [f'{side}_{i}' for side in ('left', 'right') for i in range(7)] + ['neck_0', 'neck_1', 'left_gripper', 'right_gripper']
    robot = {'arm_joints': [names[:7], names[7:14]]}
    settings = {'neck_joints': names[14:16]}
    paths = []
    for region_index, (start, stop) in enumerate([(0, 2), (4, 6)]):
        directory = tmp_path / str(region_index) / 'trajectory'
        directory.mkdir(parents=True)
        sl = slice(start, stop)
        q = np.full((count, 18), np.nan)
        q[sl] = region_index + .1
        transform = np.eye(4)
        transform[0, 3] = 3 * region_index
        episode_ids = np.full(count, -1, np.int32)
        episode_ids[sl] = 0
        observed = world['export_valid'] & ~world['motion_infilled']
        if region_index == 0:
            observed[1, 0] = False
        report = {'status': 'completed', 'schema_version': 7, 'hand_order': ['left', 'right'],
                  'source_run_id': source_run_id, 'joint_names': names, 'robot_settings': robot,
                  'settings': settings, 'gripper_mapping_settings': {'mapping_mode': 'wrist_roll'},
                  'regions': [{'start': start, 'stop': stop}],
                  'episodes': [{'candidate_id': 0, 'region': {'start': start, 'stop': stop}}]}
        score = {'status': 'completed', 'definition': {'source_run_id': source_run_id, 'frame_count': count,
                 'robot_settings': robot, 'mapping_settings': report['gripper_mapping_settings'],
                 'settings': {'position_tolerance_m': .01, 'orientation_tolerance_degrees': 4}},
                 'limits': {'joint_names': names}}
        arrays = {**world, 'joint_solution_rad': q, 'gripper_action': np.full((count, 2), .75),
                  'episode_id': episode_ids, 'ik_success': observed, 'retarget_valid': observed,
                  'transform_base_from_aligned': transform[None], 'transform_base_from_world': transform[None],
                  'rotation_aligned_from_world': np.eye(3)}
        arrays.update({k: np.zeros((count, 2, 3)) for k in ALIGNED_FIELDS})
        if 'root_translation_world_m' in world:
            arrays['root_translation_aligned_m'] = world['root_translation_world_m'].copy()
            arrays['root_orientation_aligned_axis_angle'] = world['root_orientation_world_axis_angle'].copy()
            arrays['wrist_position_world_m'] = world['root_translation_world_m'].copy()
            arrays['wrist_position_aligned_m'] = world['root_translation_world_m'].copy()
        arrays.update({k: np.tile(np.eye(3), (count, 1, 1)) if 'rotation' in k else np.zeros((count, 3))
                       for k in CAMERA_FIELDS})
        metrics = {'timestamp_s': times, 'source_timestamp_s': world['source_timestamp_s'],
                   'observed': observed, 'joint_positions_rad': q,
                   'position_error_m': np.zeros((count, 2)), 'orientation_error_rad': np.zeros((count, 2)),
                   'joint_feasible': np.ones(count, bool), 'collision_free': np.ones(count, bool),
                   'evaluated': episode_ids >= 0}
        if region_index == 1:
            metrics['collision_free'][5] = False
        write_json(directory / 'retargeting_report.json', report)
        write_json(directory.parent / 'score.json', score)
        np.savez(directory / 'trajectory_retargeted.npz', **arrays)
        np.savez(directory.parent / 'benchmark_frame_metrics.npz', **metrics)
        paths.append(directory)
    return paths, world, clip


@pytest.fixture
def robot_regions(tmp_path):
    return make_robot_regions(tmp_path)


def test_full_timeline_gaps_hand_validity_and_changed_bases(robot_regions):
    paths, world, clip = robot_regions
    arrays, metadata = load_robot_episode(paths, world, clip, 'same-video')
    assert arrays['action'].shape == (6, 18)
    np.testing.assert_array_equal(arrays['observation.robot.region_id'][:, 0], [0, 0, -1, -1, 1, 1])
    assert np.isnan(arrays['action'][2:4]).all()
    assert not arrays['observation.robot.solved'][2:4].any()
    assert np.isnan(arrays['action'][1, :7]).all()  # missing left observation
    assert np.isfinite(arrays['action'][1, 7:16]).all()
    assert np.isnan(arrays['action'][5]).all()  # collision keeps a diagnostic prediction
    assert np.isfinite(arrays['observation.robot.joint_solution_rad'][5]).all()
    np.testing.assert_allclose(arrays['action'][0, -2:], [.75, .75])
    assert metadata['regions'][0]['episode_frame_interval'] == [0, 2]
    assert metadata['regions'][1]['episode_time_interval_s'] == [4 / 30, 6 / 30]
    assert metadata['regions'][1]['source_frame_interval'] == [128, 131]
    assert metadata['regions'][1]['source_time_interval_s'] == [2 + 4 / 30, 2.2]
    assert metadata['regions'][0]['transform_base_from_aligned'][0][3] == 0
    assert metadata['regions'][1]['transform_base_from_aligned'][0][3] == 3


def test_overlap_and_foreign_source_are_rejected(robot_regions):
    paths, world, clip = robot_regions
    with pytest.raises(ValueError, match='overlap'):
        load_robot_episode([paths[0], paths[0]], world, clip, 'same-video')
    with pytest.raises(ValueError, match='this HaWoR run'):
        load_robot_episode(paths, world, clip, 'different-video')


@pytest.mark.parametrize('failure', ['timestamps', 'joints', 'transform'])
def test_stale_evaluation_and_transform_direction_fail(robot_regions, failure):
    paths, world, clip = robot_regions
    path = paths[0] / 'trajectory_retargeted.npz' if failure == 'transform' else paths[0].parent / 'benchmark_frame_metrics.npz'
    with np.load(path) as saved:
        data = dict(saved)
    if failure == 'timestamps':
        data['source_timestamp_s'] += .01
    elif failure == 'joints':
        data['joint_positions_rad'][0, 0] += .01
    else:
        data['transform_base_from_world'][0, 0, 3] += .1
    np.savez(path, **data)
    with pytest.raises(ValueError, match={'timestamps': 'timeline', 'joints': 'different joint predictions', 'transform': 'composition'}[failure]):
        load_robot_episode(paths, world, clip, 'same-video')
