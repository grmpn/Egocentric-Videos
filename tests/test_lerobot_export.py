"""Production writers, readers, annotation CLI and standalone human reuse."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import sys
import threading

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

pytest.importorskip('lerobot')
from lerobot.datasets.lerobot_dataset import LeRobotDataset

from egocentric_pipeline.datasets.lerobot_export import (
    append_human_episode, append_robot_regions, read_card, read_episode, CAMERA)
from egocentric_pipeline.datasets.human_episode import materialize_human_alignment
from egocentric_pipeline.datasets.annotations import annotate_dataset
from egocentric_pipeline.datasets.training import ActionTrainingDataset
from egocentric_pipeline.datasets.statistics import numeric_stats
from egocentric_pipeline.retargeting.trajectory import load_alignment
from egocentric_pipeline.video.clip_request import ClipRequest
from egocentric_pipeline.video.video_preparation import prepare_clip
from egocentric_pipeline.run_metadata import read_json, write_json, sha256_file
from test_clip_preparation import make_video, decode_video


@pytest.fixture
def runs(tmp_path):
    result = []
    for number in range(2):
        run = tmp_path / f'run-{number}'
        run.mkdir()
        video = make_video(run / 'source.mp4', count=30, rate=30, filters=f'eq=brightness={number / 10}')
        prepared = prepare_clip(ClipRequest.from_video(video), run / 'prepared')
        n = 30
        valid = np.ones((n, 2), bool)
        valid[15, 1] = False
        infill = np.zeros((n, 2), bool)
        infill[9, 0] = True
        translation = np.full((n, 2, 3), .1, np.float32)
        translation[~valid] = np.nan
        orientation = np.tile(np.array([.1, .2, .3], np.float32), (n, 2, 1))
        orientation[~valid] = np.nan
        arrays = dict(frame_index=np.arange(n), timestamp_s=np.arange(n)/30, source_timestamp_s=np.arange(n)/30,
            root_translation_world_m=translation.copy(), root_translation_aligned_m=translation.copy(),
            root_orientation_world_axis_angle=orientation.copy(), root_orientation_aligned_axis_angle=orientation.copy(),
            wrist_position_world_m=translation + .01, wrist_position_aligned_m=translation + .01,
            mano_root_offset_m=np.full_like(translation, .01), hand_pose_axis_angle=np.zeros((n, 2, 45), np.float32),
            mano_betas=np.zeros((n, 2, 10), np.float32), export_valid=valid, hawor_valid=valid.copy(),
            motion_infilled=infill, direct_detection=np.ones_like(valid), detector_confidence=np.ones((n,2), np.float32),
            rotation_aligned_from_world=np.eye(3), camera_position_world_m=np.zeros((n,3)),
            camera_position_aligned_m=np.zeros((n,3)), camera_rotation_world_from_camera=np.tile(np.eye(3),(n,1,1)),
            camera_rotation_aligned_from_camera=np.tile(np.eye(3),(n,1,1)))
        alignment = run / 'alignment'
        alignment.mkdir()
        np.savez(alignment / 'trajectory_aligned.npz', **arrays)
        models = []
        for side in ('left', 'right'):
            model = tmp_path / f'{side}.model'
            model.write_text(side)
            models.append(model)
        report = dict(status='completed', hand_order=['left','right'], source_run_id=run.name,
            inputs={'prepared_video': {'path': str(prepared.video_path)}, 'clip_metadata': {'path': str(prepared.metadata_path)},
                    **{f'mano_{side}': {'path': str(path), 'sha256': sha256_file(path)}
                       for side,path in zip(('left','right'),models)}})
        write_json(alignment / 'alignment_report.json', report)
        robot = read_json('configs/defaults/robot_workspace.json')
        names = sum(robot['arm_joints'], []) + ['neck_0','neck_1','left_gripper','right_gripper']
        trajectory = run / 'robot' / 'trajectory'
        trajectory.mkdir(parents=True)
        regions = [dict(start=i, stop=i+10) for i in (0,10,20)]
        q = np.tile(.1 + .01 * np.arange(18), (n, 1))
        observed = valid & ~infill
        arrays.update(joint_solution_rad=q, gripper_action=np.full((n,2), .75), episode_id=np.repeat(np.arange(3),10),
            ik_success=observed.copy(), retarget_valid=observed, transform_base_from_aligned=np.tile(np.eye(4),(3,1,1)),
            transform_base_from_world=np.tile(np.eye(4),(3,1,1)))
        report = dict(status='completed', schema_version=7, hand_order=['left','right'], source_run_id=run.name,
            joint_names=names, robot_settings=robot, settings={'neck_joints': names[14:16]},
            gripper_mapping_settings={'mapping_mode':'wrist_roll'}, regions=regions,
            prepared_video=str(prepared.video_path),
            episodes=[dict(candidate_id=i,region={**region,'accepted':True}) for i,region in enumerate(regions)])
        score = dict(status='completed', definition=dict(source_run_id=run.name, frame_count=n,robot_settings=robot,
            mapping_settings=report['gripper_mapping_settings'], settings={'position_tolerance_m':.01,'orientation_tolerance_degrees':4}),
            limits=dict(joint_names=names,position_lower_rad=[-3.]*18,position_upper_rad=[3.]*18,
                        velocity_limit_rad_s=[5.]*18,acceleration_limit_rad_s2=[10.]*18))
        metrics = dict(timestamp_s=arrays['timestamp_s'],source_timestamp_s=arrays['source_timestamp_s'],observed=observed,
            joint_positions_rad=q,frame_max_speed_rad_s=np.zeros_like(q),frame_acceleration_rad_s2=np.zeros_like(q),
            gripper_opening=np.full((n,2), .75),tcp_pose_base=np.tile([.2,.3,.4,0,0,0,1.],(n,2,1)),position_error_m=np.zeros((n,2)),
            orientation_error_rad=np.zeros((n,2)),joint_feasible=np.ones(n,bool),collision_free=np.ones(n,bool),evaluated=np.ones(n,bool))
        metrics['collision_free'][15:20] = False
        # A huge invalid prediction must never enter statistics.
        arrays['joint_solution_rad'][9,0] = 1000
        write_json(trajectory / 'retargeting_report.json',report)
        write_json(trajectory.parent / 'score.json',score)
        np.savez(trajectory / 'trajectory_retargeted.npz',**arrays)
        np.savez(trajectory.parent / 'benchmark_frame_metrics.npz',**metrics)
        result.append((alignment,trajectory,prepared.video_path,models))
    return result


def files(root):
    return {str(p.relative_to(root)): sha256_file(p) for p in root.rglob('*') if p.is_file()}


def export_pair(tmp_path, run, *, threshold=.85, suffix=''):
    human, robot = tmp_path / ('human'+suffix), tmp_path / ('robot'+suffix)
    result = append_human_episode(run[0], human, task='Move block')
    output = append_robot_regions(human,result['episode_index'],[run[1]],robot,task='Move block',
        diagnostic_path=tmp_path / ('regions'+suffix+'.json'),min_episode_valid_ratio=threshold)
    return human,robot,output


def test_structured_human_robot_regions_and_rgb(tmp_path,runs):
    human,robot,result = export_pair(tmp_path,runs[0])
    assert result['episode_indices']==[0,1] and result['rejected_regions']==1
    diagnostics=read_json(tmp_path/'regions.json')
    assert [r['valid_ratio'] for r in diagnostics['regions']]==[.9,.5,1.]
    source_rgb=decode_video(runs[0][2])
    h=LeRobotDataset('local/human',root=human,video_backend='pyav')
    r=LeRobotDataset('local/robot',root=robot,video_backend='pyav')
    assert len(h)==30 and h.num_episodes==1 and len(r)==20 and r.num_episodes==2
    assert h[0]['observation.hands.root_pose_aligned'].shape==(2,7)
    assert h[0]['observation.hands.pose_axis_angle'].shape==(2,45)
    assert h[0]['observation.hands.betas'].shape==(2,10)
    assert h[9]['observation.hands.source_status'].tolist()==[1,2]
    assert h[15]['observation.hands.source_status'].tolist()==[2,0]
    expected=Rotation.from_rotvec([.1,.2,.3]).as_matrix()
    np.testing.assert_allclose(Rotation.from_quat(h[0]['observation.hands.root_pose_aligned'][0,3:]).as_matrix(),expected,atol=1e-7)
    for i in range(20):
        row=r[i]
        source=i if i<10 else i+10
        assert int(row['source_frame_index'])==source and int(row['source_episode_index'])==0
        assert int(row['frame_index'])==i%10
        assert float(row['timestamp'])==pytest.approx((i%10)/30)
        assert row['action'].dtype.__str__()=='torch.float32'
        assert row['action.ee'].shape==(2,8)
        if i != 9:
            np.testing.assert_allclose(row['action'][:16], .1 + .01 * np.arange(16), atol=1e-7)
        np.testing.assert_allclose(row['action'][-2:], [.75, .75])
        assert abs(float(row[CAMERA].mean())*255-source_rgb[source].mean())<3
    assert not r[9]['quality.action_valid'][:7].any()
    training = ActionTrainingDataset(robot, target='joint')[9]
    assert not training['action_valid'][:7].any()
    assert (training['action'][:7] == 0).all()
    assert np.isfinite(training['action'].numpy()).all()
    stats=read_json(robot/'meta/stats.json')
    assert stats['action']['mean'][0]==pytest.approx(.1)
    assert np.asarray(stats['action.ee']['mean']).shape==(2,8)
    for root in (human,robot):
        assert {p.name for p in root.iterdir()}=={'README.md','data','meta','videos'}
        assert {p.name for p in (root/'meta').iterdir()}=={'info.json','stats.json','tasks.parquet','episodes'}
    assert set(read_json(robot/'meta/info.json')['features'])=={
        CAMERA,'action','action.ee','quality.action_valid','quality.hand_status','source_episode_index','source_frame_index',
        'language_persistent','language_events','timestamp','frame_index','episode_index','index','task_index'}


def test_constraint_threshold_preserves_tracking_masks_and_training(tmp_path,runs):
    human,robot,result=export_pair(tmp_path,runs[0],threshold=.91)
    assert result['accepted_regions']==1
    _,_,lower=export_pair(tmp_path,runs[0],threshold=.5,suffix='-lower')
    assert lower['accepted_regions']==3
    dataset=ActionTrainingDataset(robot,target='ee',offsets=[0.,1/30,2/30])
    row=dataset[len(dataset)-1]
    assert row['action'].shape==(3,16) and not row['action_valid'][1:].any()
    assert np.isfinite(row['action'].numpy()).all()
    path=runs[0][1]/'retargeting_report.json'
    report=read_json(path)
    for episode in report['episodes']: episode['region']['accepted']=False
    write_json(path,report,overwrite=True)
    path=runs[0][1]/'trajectory_retargeted.npz'
    with np.load(path) as saved: arrays=dict(saved)
    arrays['ik_success'][:10]=False
    np.savez(path,**arrays)
    output=append_robot_regions(human,0,[runs[0][1]],tmp_path/'tracking-failures',task='Move',
                               diagnostic_path=tmp_path/'tracking.json')
    assert output['accepted_regions']==2
    regions=read_json(tmp_path/'tracking.json')['regions']
    assert regions[0]['exported'] and regions[0]['valid_ratio']==.9
    assert regions[0]['action_valid_ratio']==0
    assert not regions[0]['pose_acceptance']['region']['accepted']
    assert regions[1]['rejection_reason']=='constraint_valid_ratio'
    data=read_episode(tmp_path/'tracking-failures',0)
    assert not data['quality.action_valid'].any()
    training=ActionTrainingDataset(tmp_path/'tracking-failures',target='joint')[0]
    assert not training['action_valid'].any() and (training['action']==0).all()
    output=append_robot_regions(human,0,[runs[0][1]],tmp_path/'test-all',task='Move',
                               diagnostic_path=tmp_path/'test-all.json',include_rejected_regions=True)
    assert output['accepted_regions']==2 and output['rejected_regions']==1
    assert output['exported_regions']==3 and output['overridden_regions']==1
    overridden=read_json(tmp_path/'test-all.json')['regions'][1]
    assert overridden['exported'] and overridden['export_override'] and not overridden['acceptance_passed']
    assert overridden['valid_ratio']==.5 and overridden['rejection_reason']=='constraint_valid_ratio'
    assert read_card(tmp_path/'test-all')['test_dataset']
    data=read_episode(tmp_path/'test-all',1)
    assert not data['quality.action_valid'][5:].any()


def test_append_rollback_source_pin_and_standalone_human(tmp_path,runs,monkeypatch):
    human,robot,_=export_pair(tmp_path,runs[0])
    old_human=files(human)
    with pytest.raises(ValueError,match='already exists'):
        append_human_episode(runs[0][0],human,task='Repeat')
    assert files(human)==old_human
    old=files(robot)
    with pytest.raises(ValueError,match='already exists'):
        append_robot_regions(human,0,[runs[0][1]],robot,task='Repeat',diagnostic_path=tmp_path/'repeat.json')
    assert files(robot)==old
    old_shards={p:p.read_bytes() for p in human.glob('data/*/*.parquet')}
    append_human_episode(runs[1][0],human,task='Second')
    assert all(p.read_bytes()==content for p,content in old_shards.items())
    from egocentric_pipeline.datasets.lerobot_export import episode_revision
    assert episode_revision(human, 0) == read_card(human)['episodes'][0]['revision']
    output=append_robot_regions(human,1,[runs[1][1]],robot,task='Second',diagnostic_path=tmp_path/'second.json')
    assert output['episode_indices']==[2,3]
    saved=files(robot)
    def fail(*args,**kwargs): raise RuntimeError('encoding failure')
    with monkeypatch.context() as context:
        context.setattr(LeRobotDataset,'save_episode',fail)
        with pytest.raises(RuntimeError,match='encoding failure'):
            append_robot_regions(human,0,[runs[0][1]],tmp_path/'failed',task='Fail',diagnostic_path=tmp_path/'failed.json')
    assert not (tmp_path/'failed').exists() and files(robot)==saved
    # Remove access to original processing artifacts; standalone reuse still works.
    runs[0][0].rename(runs[0][0].with_name('hidden-alignment'))
    runs[0][2].rename(runs[0][2].with_name('hidden-video.mp4'))
    restored=tmp_path/'restored'
    materialize_human_alignment(human,0,restored,runs[0][3])
    aligned,_,_=load_alignment(restored)
    data=read_episode(human,0)
    np.testing.assert_allclose(aligned['wrist_position_aligned_m'],data['observation.hands.wrist_position_aligned_m'],equal_nan=True)
    assert (restored/'prepared.mp4').exists()
    # Robot RGB comes from the human dataset, even when the old video is absent.
    output = append_robot_regions(human, 0, [runs[0][1]], tmp_path/'independent-robot',
        task='Move', diagnostic_path=tmp_path/'independent.json')
    assert output['accepted_regions'] == 2


def test_numeric_statistics_exclude_masks_and_preserve_axes():
    data=np.array([[[1.,2.],[3.,np.nan]],[[5.,999.],[7.,8.]]])
    valid=np.isfinite(data)
    valid[1,0,1]=False
    stats=numeric_stats(data,valid)
    np.testing.assert_array_equal(stats['mean'],[[3.,2.],[5.,8.]])


def test_actual_annotation_cli_preserves_shared_shard_and_features(tmp_path,runs):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_POST(self):
            self.rfile.read(int(self.headers['Content-Length']))
            answer={'description':'A block is moved.','subtasks':[{'start':0.,'end':.3,'text':'Move block'}]}
            response={'id':'fixture','object':'chat.completion','created':0,'model':'fixture',
                      'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(answer)}}]}
            body=json.dumps(response).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    human,robot,_=export_pair(tmp_path,runs[0])
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    endpoint=f'http://127.0.0.1:{server.server_port}/v1'
    try:
        before=[read_episode(robot,i) for i in range(2)]
        annotate_dataset(robot,model='fixture',api_base=endpoint,episodes=[0],record_path=tmp_path/'annotation0.json')
        reader=LeRobotDataset('local/robot',root=robot,video_backend='pyav')
        assert reader.meta.get_data_file_path(0) == reader.meta.get_data_file_path(1)
        atoms=reader[0]['language_persistent']
        assert {a['style'] for a in atoms}=={'plan','subtask'}
        del reader
        annotate_dataset(robot,model='fixture',api_base=endpoint,episodes=[1],record_path=tmp_path/'annotation1.json')
        reader=LeRobotDataset('local/robot',root=robot,video_backend='pyav')
        assert reader[0]['language_persistent']==atoms
        assert reader[10]['language_persistent']
        for i in range(2):
            after=read_episode(robot,i)
            for key in before[i]: np.testing.assert_array_equal(after[key],before[i][key])
        assert not (robot/'.annotate_staging').exists()
        saved=files(robot)
        with pytest.raises(ValueError,match='already contain'):
            annotate_dataset(robot,model='fixture',api_base=endpoint,episodes=[0],record_path=tmp_path/'repeat-annotation.json')
        assert files(robot)==saved
        append_human_episode(runs[1][0],human,task='second')
        append_robot_regions(human,1,[runs[1][1]],robot,task='second',diagnostic_path=tmp_path/'append.json')
        assert LeRobotDataset('local/robot',root=robot,video_backend='pyav')[0]['language_persistent']==atoms
    finally:
        server.shutdown();server.server_close();thread.join(timeout=3)


def test_cli_export_and_source_revision_guard(tmp_path, runs):
    human, robot = tmp_path/'cli-human', tmp_path/'cli-robot'
    environment = {**os.environ, 'PYTHONPATH': 'src'}
    command = [sys.executable, 'pipeline/export_dataset.py', 'human', '--alignment-directory', str(runs[0][0]),
               '--dataset-root', str(human), '--task', 'Move', '--result', str(tmp_path/'human-result.json')]
    completed = subprocess.run(command, env=environment, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    command = [sys.executable, 'pipeline/export_dataset.py', 'robot', '--human-dataset-root', str(human),
               '--source-episode-index', '0', '--trajectory-directory', str(runs[0][1]), '--dataset-root', str(robot),
               '--task', 'Move', '--diagnostics', str(tmp_path/'cli-regions.json'), '--result', str(tmp_path/'robot-result.json')]
    completed = subprocess.run(command, env=environment, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert read_json(tmp_path/'robot-result.json')['episode_indices'] == [0, 1]
    card_path = human/'README.md'
    card_path.write_text(card_path.read_text().replace('revision: ', 'revision: changed-'))
    saved = files(robot)
    with pytest.raises(ValueError, match='revision changed'):
        append_robot_regions(human, 0, [runs[0][1]], robot, task='Move', diagnostic_path=tmp_path/'changed.json')
    assert files(robot) == saved


def test_out_of_range_openings_are_masked_finite_placeholders(tmp_path, runs):
    trajectory = runs[0][1]
    for path, key in ((trajectory/'trajectory_retargeted.npz', 'gripper_action'),
                      (trajectory.parent/'benchmark_frame_metrics.npz', 'gripper_opening')):
        with np.load(path) as saved:
            arrays = dict(saved)
        arrays[key][9, 0] = 1.2
        np.savez(path, **arrays)
    _, robot, _ = export_pair(tmp_path, runs[0])
    row = LeRobotDataset('local/robot', root=robot, video_backend='pyav')[9]
    assert not row['quality.action_valid'][16]
    assert row['action'][16] == 0 and row['action.ee'][0, 7] == 0
