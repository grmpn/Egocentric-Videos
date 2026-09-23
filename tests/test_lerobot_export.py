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
import pyarrow.parquet as pq
from lerobot.datasets.lerobot_dataset import LeRobotDataset

from egocentric_pipeline.clip_request import ClipRequest
from egocentric_pipeline.lerobot_export import append_run, CAMERA
from egocentric_pipeline.run_metadata import artifact_record, read_json, sha256_file, write_json
from egocentric_pipeline.video_preparation import prepare_clip
from egocentric_pipeline.world_export import export_world
from egocentric_pipeline.annotations import annotate_dataset
from test_clip_preparation import make_video
from test_world_export import native_fixture


@pytest.fixture
def runs(tmp_path, native_fixture):
    native, _, _, _ = native_fixture
    manifests = []
    for number in range(2):
        run = tmp_path / f"run-{number}"
        run.mkdir()
        video = make_video(run / 'source.mp4', count=6 + number, rate=30)
        prepared = prepare_clip(ClipRequest.from_video(video, interval=(0, .2)), run / 'prepared')
        exported = export_world(native, prepared, run / 'export', upstream_stages_completed=True)
        artifacts = {name: artifact_record(exported[name]) for name in ('trajectory_world', 'trajectory_metadata')}
        artifacts.update(clip_metadata=artifact_record(prepared.metadata_path), prepared_video=artifact_record(prepared.video_path))
        manifest = run / 'run_manifest.json'
        write_json(manifest, {'status': 'completed', 'run_directory': str(run), 'run_id': run.name,
                             'stages': [{'status': 'completed'}], 'artifacts': artifacts})
        manifests.append(manifest)
    return manifests


def files(root):
    return {str(p.relative_to(root)): sha256_file(p) for p in root.rglob('*') if p.is_file()}


def test_cli_create_reopen_append_and_native_values(tmp_path, runs):
    root = tmp_path / 'dataset'
    command = [sys.executable, 'scripts/video_to_dataset.py', '--run-manifest', str(runs[0]),
               '--dataset-root', str(root), '--task', 'Move the block']
    result = subprocess.run(command, env={**os.environ, 'PYTHONPATH': 'src'}, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert read_json(root / 'meta/info.json')['codebase_version'] == 'v3.1'
    reader = LeRobotDataset('local/egocentric-pilot', root=root, video_backend='pyav')
    assert len(reader) == 6
    del reader
    old_shards = {p: p.read_bytes() for p in root.glob('data/*/*.parquet')}
    append_run(runs[1], root, task='Move the block again')
    assert all(p.read_bytes() == content for p, content in old_shards.items())
    reader = LeRobotDataset('local/egocentric-pilot', root=root, video_backend='pyav')
    assert reader.num_episodes == 2 and len(reader) == 12
    for episode in range(2):
        world_path = read_json(runs[episode])['artifacts']['trajectory_world']['path']
        with np.load(world_path) as world:
            for i in range(6):
                row = reader[episode * 6 + i]
                assert int(row['episode_index']) == episode
                assert int(row['frame_index']) == i
                assert int(row['index']) == episode * 6 + i
                assert abs(float(row['timestamp']) - i / 30) < 1e-7
                assert row[CAMERA].shape == (3, 24, 32)
                assert abs(float(row[CAMERA].mean()) * 255 - (20 + 10 * i)) < 3
                for key in ('root_translation_world_m', 'hand_pose_axis_angle', 'mano_betas',
                            'export_valid', 'direct_detection', 'detector_confidence'):
                    np.testing.assert_array_equal(row['observation.hands.' + key].numpy(), world[key][i].reshape(-1))
    table = pq.read_table(sorted(root.glob('data/*/*.parquet'))[0])
    assert table['observation.clip_timestamp_s'].to_pylist() == [i / 30 for i in range(6)]


def test_repeated_incompatible_and_failed_appends_are_non_mutating(tmp_path, runs, monkeypatch):
    root = tmp_path / 'dataset'
    append_run(runs[0], root, task='Move the block')
    original = files(root)
    with pytest.raises(ValueError, match='already exists'):
        append_run(runs[0], root, task='Repeated')
    assert files(root) == original
    def fail(*args, **kwargs):
        raise RuntimeError('simulated encoding failure')
    monkeypatch.setattr(LeRobotDataset, 'save_episode', fail)
    with pytest.raises(RuntimeError, match='encoding failure'):
        append_run(runs[1], root, task='Second')
    assert files(root) == original
    assert len(LeRobotDataset('local/egocentric-pilot', root=root, video_backend='pyav')) == 6
    info = read_json(root / 'meta/info.json')
    info['fps'] = 60
    write_json(root / 'meta/info.json', info, overwrite=True)
    changed = files(root)
    with pytest.raises(ValueError, match='30 FPS'):
        append_run(runs[1], root, task='Wrong rate')
    assert files(root) == changed
    info['fps'] = 30
    info['features'][CAMERA]['shape'][0] *= 2
    write_json(root / 'meta/info.json', info, overwrite=True)
    changed = files(root)
    with pytest.raises(ValueError, match='image geometry'):
        append_run(runs[1], root, task='Wrong dimensions')
    assert files(root) == changed
    contract = read_json(root / 'meta/egocentric.json')
    contract['hand_order'] = ['right', 'left']
    write_json(root / 'meta/egocentric.json', contract, overwrite=True)
    changed = files(root)
    with pytest.raises(ValueError, match='hand order'):
        append_run(runs[1], root, task='Swapped identity')
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
        append_run(runs[0], root, task='Move the block')
        annotate_dataset(root, model='integration-test-fixture', api_base=endpoint)
        old_shard = next(root.glob('data/*/*.parquet'))
        original = old_shard.read_bytes()
        reader = LeRobotDataset('local/egocentric-pilot', root=root, video_backend='pyav')
        atoms = reader[0]['language_persistent']
        assert {atom['style'] for atom in atoms} == {'plan', 'subtask'}
        assert all(atom['timestamp'] == 0 for atom in atoms)
        del reader
        append_run(runs[1], root, task='Move a second block')
        assert old_shard.read_bytes() == original
        annotate_dataset(root, model='integration-test-fixture', api_base=endpoint)
        reader = LeRobotDataset('local/egocentric-pilot', root=root, video_backend='pyav')
        assert reader[0]['language_persistent'] == atoms
        assert reader[6]['language_persistent']
        saved = files(root)
        with pytest.raises(ValueError, match='already contain'):
            annotate_dataset(root, model='integration-test-fixture', api_base=endpoint, episodes=[0])
        assert files(root) == saved
        failed_root = tmp_path / 'failed-annotation'
        append_run(runs[0], failed_root, task='Move the block')
        saved = files(failed_root)
        Handler.empty = True
        with pytest.raises(ValueError, match='missing or inconsistent'):
            annotate_dataset(failed_root, model='integration-test-fixture', api_base=endpoint)
        assert files(failed_root) == saved
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
