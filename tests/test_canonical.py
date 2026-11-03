import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from egocentric_pipeline.canonical import canonicalize
from egocentric_pipeline.dataset_transaction import staged_dataset


def test_independent_hand_anchors_and_pose_inversion():
    rng = np.random.default_rng(40)
    position = rng.normal(size=(12, 2, 3)).astype(np.float32)
    rotation = rng.normal(size=(12, 2, 3)).astype(np.float32)
    valid = np.ones((12, 2), dtype=bool)
    valid[:3, 1] = False
    valid[5:8, 0] = False
    before = position.tobytes(), rotation.tobytes()
    canonical_p, canonical_r, anchors = canonicalize(position, rotation, valid)
    assert [a['frame_index'] for a in anchors] == [0, 3]
    for hand, anchor in enumerate(anchors):
        basis = Rotation.from_matrix(anchor['rotation_world_from_canonical'])
        mask = valid[:, hand]
        np.testing.assert_allclose(basis.apply(canonical_p[mask, hand]) + anchor['translation_world_m'],
                                   position[mask, hand], atol=3e-7)
        np.testing.assert_allclose((basis * Rotation.from_rotvec(canonical_r[mask, hand])).as_matrix(),
                                   Rotation.from_rotvec(rotation[mask, hand]).as_matrix(), atol=3e-7)
        np.testing.assert_allclose(canonical_p[anchor['frame_index'], hand], 0, atol=1e-7)
    assert np.isnan(canonical_p[~valid]).all()
    assert np.isnan(canonical_r[~valid]).all()
    assert before == (position.tobytes(), rotation.tobytes())


def test_absent_hand_and_bad_valid_pose():
    position = np.zeros((3, 2, 3), np.float32)
    valid = np.zeros((3, 2), bool)
    p, r, anchors = canonicalize(position, position, valid)
    assert anchors == [None, None]
    assert np.isnan(p).all() and np.isnan(r).all()
    valid[0, 0] = True
    position[0, 0] = np.nan
    with pytest.raises(ValueError, match='finite'):
        canonicalize(position, position, valid)


def test_atomic_create_append_and_failure_preserve_original(tmp_path):
    root = tmp_path / 'dataset'
    with staged_dataset(root) as stage:
        (stage / 'meta').mkdir(parents=True)
        (stage / 'meta/info.json').write_text('{}')
        (stage / 'episode').write_text('original annotations')
    with pytest.raises(RuntimeError):
        with staged_dataset(root) as stage:
            (stage / 'episode').write_text('damaged')
            raise RuntimeError('encoding failed')
    assert (root / 'episode').read_text() == 'original annotations'
    with staged_dataset(root) as stage:
        (stage / 'second').write_text('new episode')
    assert (root / 'second').read_text() == 'new episode'
    assert (root / 'episode').read_text() == 'original annotations'
