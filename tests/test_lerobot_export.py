"""Real LeRobot writer/reader integration; skipped in the legacy Torch-free job."""

import os
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import sys
import threading

import numpy as np
import pytest

pytest.importorskip("lerobot")
import pyarrow as pa
import pyarrow.parquet as pq
from lerobot.datasets.io_utils import write_table_one_row_group_per_episode
from lerobot.datasets.lerobot_dataset import LeRobotDataset

from egocentric_pipeline.video.clip_request import ClipRequest
from egocentric_pipeline.datasets.lerobot_export import append_robot_episode, CAMERA
from egocentric_pipeline.run_metadata import artifact_record, read_json, sha256_file, write_json
from egocentric_pipeline.video.video_preparation import prepare_clip
from egocentric_pipeline.tracking.world_export import export_world
from egocentric_pipeline.datasets.annotations import annotate_dataset
from test_clip_preparation import make_video, decode_video
from test_world_export import native_fixture
from test_robot_episode import make_robot_regions


@pytest.fixture
def runs(tmp_path, native_fixture):
    native, _, _, _ = native_fixture
    manifests = []
    for number in range(2):
        run = tmp_path / f"run-{number}"
        run.mkdir()
        video = make_video(run / 'source.mp4', count=6, rate=30, filters=f'eq=brightness={number / 10}')
        prepared = prepare_clip(ClipRequest.from_video(video), run / 'prepared')
        exported = export_world(native, prepared, run / 'export', upstream_stages_completed=True)
        artifacts = {name: artifact_record(exported[name]) for name in ('trajectory_world', 'trajectory_metadata')}
        artifacts.update(clip_metadata=artifact_record(prepared.metadata_path), prepared_video=artifact_record(prepared.video_path))
        manifest = run / 'run_manifest.json'
        write_json(manifest, {'status': 'completed', 'run_directory': str(run), 'run_id': run.name,
                             'stages': [{'status': 'completed'}], 'artifacts': artifacts})
        with np.load(exported['trajectory_world']) as stored:
            world = dict(stored)
        paths, _, _ = make_robot_regions(run / 'robot', world, run.name, prepared.metadata.to_dict())
        manifests.append((manifest, paths))
    return manifests


def files(root):
    return {str(p.relative_to(root)): sha256_file(p) for p in root.rglob('*') if p.is_file()}


def test_trimmed_input_cannot_create_a_robot_episode(tmp_path, native_fixture):
    video = make_video(tmp_path / 'source.mp4', count=9, rate=30)
    prepared = prepare_clip(ClipRequest.from_video(video, interval=(.1, .3)), tmp_path / 'prepared')
    exported = export_world(native_fixture[0], prepared, tmp_path / 'export', upstream_stages_completed=True)
    artifacts = {name: artifact_record(exported[name]) for name in ('trajectory_world', 'trajectory_metadata')}
    artifacts.update(clip_metadata=artifact_record(prepared.metadata_path), prepared_video=artifact_record(prepared.video_path))
    manifest = tmp_path / 'run_manifest.json'
    write_json(manifest, {'status': 'completed', 'run_directory': str(tmp_path), 'run_id': 'trimmed',
                         'stages': [{'status': 'completed'}], 'artifacts': artifacts})
    root = tmp_path / 'dataset'
    with pytest.raises(ValueError, match='full input video'):
        append_robot_episode(manifest, [], root, task='Trimmed input')
    assert not root.exists()


def test_cli_create_reopen_append_and_native_values(tmp_path, runs):
    root = tmp_path / 'dataset'
    command = [sys.executable, 'pipeline/export_dataset.py', '--run-manifest', str(runs[0][0]),
               *[argument for path in runs[0][1] for argument in ('--trajectory-directory', str(path))],
               '--dataset-root', str(root), '--task', 'Move the block']
    result = subprocess.run(command, env={**os.environ, 'PYTHONPATH': 'src'}, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert read_json(root / 'meta/info.json')['codebase_version'] == 'v3.1'
    reader = LeRobotDataset('local/egocentric-pilot', root=root, video_backend='pyav')
    assert len(reader) == 6
    del reader
    old_shards = {p: p.read_bytes() for p in root.glob('data/*/*.parquet')}
    append_robot_episode(runs[1][0], runs[1][1], root, task='Move the block again')
    assert all(p.read_bytes() == content for p, content in old_shards.items())
    reader = LeRobotDataset('local/egocentric-pilot', root=root, video_backend='pyav')
    assert reader.num_episodes == 2 and len(reader) == 12
    for episode in range(2):
        artifacts = read_json(runs[episode][0])['artifacts']
        world_path = artifacts['trajectory_world']['path']
        original_rgb = decode_video(Path(artifacts['prepared_video']['path']))
        metadata = read_json(root / f'meta/egocentric/episode_{episode:06d}.json')['robot']
        assert [r['episode_frame_interval'] for r in metadata['regions']] == [[0, 2], [4, 6]]
        with np.load(world_path) as world:
            for i in range(6):
                row = reader[episode * 6 + i]
                assert int(row['episode_index']) == episode
                assert int(row['frame_index']) == i
                assert int(row['index']) == episode * 6 + i
                assert abs(float(row['timestamp']) - i / 30) < 1e-7
                assert row[CAMERA].shape == (3, 24, 32)
                assert row['action'].shape == (18,)
                if i in (2, 3):
                    assert np.isnan(row['action'].numpy()).all()
                    assert not row['observation.robot.action_valid'].any()
                    assert int(row['observation.robot.region_id']) == -1
                assert abs(float(row[CAMERA].mean()) * 255 - original_rgb[i].mean()) < 3
                for key in ('root_translation_world_m', 'hand_pose_axis_angle', 'mano_betas',
                            'export_valid', 'direct_detection', 'detector_confidence'):
                    np.testing.assert_array_equal(row['observation.hands.' + key].numpy(), world[key][i].reshape(-1))
    table = pq.read_table(sorted(root.glob('data/*/*.parquet'))[0])
    assert table['observation.clip_timestamp_s'].to_pylist() == [i / 30 for i in range(6)]


def test_repeated_incompatible_and_failed_appends_are_non_mutating(tmp_path, runs, monkeypatch):
    root = tmp_path / 'dataset'
    append_robot_episode(runs[0][0], runs[0][1], root, task='Move the block')
    original = files(root)
    with pytest.raises(ValueError, match='already exists'):
        append_robot_episode(runs[0][0], runs[0][1], root, task='Repeated')
    assert files(root) == original
    provenance_path = root / 'meta/egocentric/episode_000000.json'
    provenance = read_json(provenance_path)
    provenance['robot']['contract']['robot_settings']['asset_revision'] = 'foreign-robot'
    write_json(provenance_path, provenance, overwrite=True)
    changed = files(root)
    with pytest.raises(ValueError, match='robot embodiment'):
        append_robot_episode(runs[1][0], runs[1][1], root, task='Different robot')
    assert files(root) == changed
    del provenance['robot']['contract']['robot_settings']['asset_revision']
    write_json(provenance_path, provenance, overwrite=True)
    assert files(root) == original
    def fail(*args, **kwargs):
        raise RuntimeError('simulated encoding failure')
    monkeypatch.setattr(LeRobotDataset, 'save_episode', fail)
    with pytest.raises(RuntimeError, match='encoding failure'):
        append_robot_episode(runs[1][0], runs[1][1], root, task='Second')
    assert files(root) == original
    assert len(LeRobotDataset('local/egocentric-pilot', root=root, video_backend='pyav')) == 6
    info = read_json(root / 'meta/info.json')
    info['fps'] = 60
    write_json(root / 'meta/info.json', info, overwrite=True)
    changed = files(root)
    with pytest.raises(ValueError, match='30 FPS'):
        append_robot_episode(runs[1][0], runs[1][1], root, task='Wrong rate')
    assert files(root) == changed
    info['fps'] = 30
    info['features'][CAMERA]['shape'][0] *= 2
    write_json(root / 'meta/info.json', info, overwrite=True)
    changed = files(root)
    with pytest.raises(ValueError, match='image geometry'):
        append_robot_episode(runs[1][0], runs[1][1], root, task='Wrong dimensions')
    assert files(root) == changed
    contract = read_json(root / 'meta/egocentric.json')
    contract['hand_order'] = ['right', 'left']
    write_json(root / 'meta/egocentric.json', contract, overwrite=True)
    changed = files(root)
    with pytest.raises(ValueError, match='hand order'):
        append_robot_episode(runs[1][0], runs[1][1], root, task='Swapped identity')
    assert files(root) == changed
    contract['schema_version'] = '1.0'
    write_json(root / 'meta/egocentric.json', contract, overwrite=True)
    changed = files(root)
    with pytest.raises(ValueError, match='Incompatible egocentric dataset contract'):
        append_robot_episode(runs[1][0], runs[1][1], root, task='Historical hand-only schema')
    assert files(root) == changed


def test_actual_annotation_cli_and_append_preserve_annotations(tmp_path, runs):
    """A deterministic local HTTP fixture exercises the real CLI, not VLM quality."""
    class Handler(BaseHTTPRequestHandler):
        empty = False
        def log_message(self, *args):
            pass

        def do_POST(self):
            request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            assert request['model'] == 'integration-test-fixture'
            answer = {'description': 'A block is moved.',
                      'subtasks': [{'start': 0.0, 'end': 0.167, 'text': 'Move the block'}]}
            if self.empty:
                answer = {'description': '', 'subtasks': []}
            response = {'id': 'fixture', 'object': 'chat.completion', 'created': 0,
                        'model': 'integration-test-fixture', 'choices': [
                            {'index': 0, 'finish_reason': 'stop',
                             'message': {'role': 'assistant', 'content': json.dumps(answer)}}]}
            body = json.dumps(response).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    root = tmp_path / 'dataset'
    endpoint = f'http://127.0.0.1:{server.server_port}/v1'
    try:
        append_robot_episode(runs[0][0], runs[0][1], root, task='Move the block')
        annotate_dataset(root, model='integration-test-fixture', api_base=endpoint)
        old_shard = next(root.glob('data/*/*.parquet'))
        original = old_shard.read_bytes()
        reader = LeRobotDataset('local/egocentric-pilot', root=root, video_backend='pyav')
        atoms = reader[0]['language_persistent']
        assert {atom['style'] for atom in atoms} == {'plan', 'subtask'}
        assert all(atom['timestamp'] == 0 for atom in atoms)
        del reader
        append_robot_episode(runs[1][0], runs[1][1], root, task='Move a second block')
        assert old_shard.read_bytes() == original
        # The upstream annotator replaces language columns for an entire file.
        # Put both episodes in one valid shard to exercise preservation of an
        # unselected episode sharing the selected episode's rewritten file.
        shards = sorted(root.glob('data/*/*.parquet'))
        assert len(shards) == 2
        # Upstream infers annotated language timestamps as float64; the
        # recording writer declares float32. Promote those nested field types.
        shared = pa.concat_tables([pq.read_table(p) for p in shards], promote_options='permissive')
        write_table_one_row_group_per_episode(shared, shards[0])
        shards[1].unlink()
        for path in root.glob('meta/episodes/*/*.parquet'):
            table = pq.read_table(path)
            column = table.schema.get_field_index('data/file_index')
            table = table.set_column(column, table.schema.field(column),
                                     pa.array([0] * len(table), type=table.column(column).type))
            pq.write_table(table, path)
        reader = LeRobotDataset('local/egocentric-pilot', root=root, video_backend='pyav')
        assert reader.meta.get_data_file_path(0) == reader.meta.get_data_file_path(1)
        assert len(reader) == 12 and reader[0]['language_persistent'] == atoms
        del reader
        annotate_dataset(root, model='integration-test-fixture', api_base=endpoint)
        reader = LeRobotDataset('local/egocentric-pilot', root=root, video_backend='pyav')
        for i in range(6):
            assert reader[i]['language_persistent'] == atoms
            assert {atom['style'] for atom in reader[6 + i]['language_persistent']} == {'plan', 'subtask'}
        saved = files(root)
        with pytest.raises(ValueError, match='already contain'):
            annotate_dataset(root, model='integration-test-fixture', api_base=endpoint, episodes=[0])
        assert files(root) == saved
        failed_root = tmp_path / 'failed-annotation'
        append_robot_episode(runs[0][0], runs[0][1], failed_root, task='Move the block')
        saved = files(failed_root)
        Handler.empty = True
        with pytest.raises(ValueError, match='missing or inconsistent'):
            annotate_dataset(failed_root, model='integration-test-fixture', api_base=endpoint)
        assert files(failed_root) == saved
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
