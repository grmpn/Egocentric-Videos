"""Filtering contracts: physical units, rotation geometry and observation gaps."""

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from egocentric_pipeline.hand_pose_filtering import smooth_hand_targets
from egocentric_pipeline.manipulation_regions import retained_regions


def signal(n=31):
    times = np.arange(n) / 30
    positions = np.tile(np.column_stack([times**2, times, 1 + times**2])[:, None], (1, 2, 1))
    # Cross global pi while remaining locally smooth; the two hands differ.
    angles = 3. + .4 * times**2
    rotations = np.stack([Rotation.from_euler('z', angles).as_matrix(),
                          Rotation.from_euler('x', -angles).as_matrix()], axis=1)
    return positions, rotations, np.ones((n, 2), bool), times


def test_polynomial_recovery_including_endpoints_wraparound_and_sign():
    p, r, v, t = signal()
    settings = dict(hand_position_window_s=.3, hand_orientation_window_s=.3, hand_filter_polyorder=2)
    regions = [dict(start=0, stop=len(t))]
    fp, fr, info = smooth_hand_targets(p, r, v, t, regions, settings)
    np.testing.assert_allclose(fp, p, atol=2e-14)
    np.testing.assert_allclose(fr, r, atol=2e-14)
    np.testing.assert_allclose(fr.transpose(0, 1, 3, 2) @ fr, np.broadcast_to(np.eye(3), fr.shape), atol=2e-14)
    np.testing.assert_allclose(np.linalg.det(fr), 1., atol=2e-14)
    quaternions = Rotation.from_matrix(r.reshape(-1, 3, 3)).as_quat()
    quaternions[::2] *= -1
    signed = Rotation.from_quat(quaternions).as_matrix().reshape(r.shape)
    _, again, _ = smooth_hand_targets(p, signed, v, t, regions, settings)
    np.testing.assert_allclose(again, fr, atol=2e-14)
    assert info['window_samples'] == dict(position=9, orientation=9)
    assert not info['ambiguous_rotation_samples']


def test_missing_hands_short_spans_and_region_gaps_are_isolated():
    p, r, v, t = signal(45)
    v[8:13, 0] = False
    p[~v], r[~v] = np.nan, np.nan
    regions = [dict(start=0, stop=22), dict(start=25, stop=35), dict(start=35, stop=45)]
    settings = dict(hand_position_window_s=.3, hand_orientation_window_s=.3)
    before_p, before_r = p.copy(), r.copy()
    fp, fr, info = smooth_hand_targets(p, r, v, t, regions, settings)
    np.testing.assert_array_equal(p, before_p)
    np.testing.assert_array_equal(r, before_r)
    np.testing.assert_array_equal(fp[:8, 0], p[:8, 0])
    np.testing.assert_array_equal(fr[:8, 0], r[:8, 0])
    assert info['spans'][0]['position'] == 'too_short'
    p[13:22, 0] += 100
    r[13:22, 0] = Rotation.from_euler('y', 1.).as_matrix()
    p[35:, :] -= 100
    p[22:25] = 1e6
    pp, rr, _ = smooth_hand_targets(p, r, v, t, regions, settings)
    np.testing.assert_array_equal(pp[:13], fp[:13])
    np.testing.assert_array_equal(rr[:13], fr[:13])
    np.testing.assert_array_equal(pp[25:35], fp[25:35])
    np.testing.assert_array_equal(pp[13:22, 1], fp[13:22, 1])
    assert np.isnan(pp[~v]).all() and np.isnan(rr[~v]).all()
    np.testing.assert_array_equal(pp[22:25], p[22:25])


def test_disabled_equivalence_and_irregular_rejection():
    p, r, v, t = signal()
    t[1:] += .01
    fp, fr, _ = smooth_hand_targets(p, r, v, t, [dict(start=0, stop=len(t))], {})
    np.testing.assert_array_equal(fp, p)
    np.testing.assert_array_equal(fr, r)
    with pytest.raises(ValueError, match='uniform.*0 for irregular'):
        smooth_hand_targets(p, r, v, t, [], dict(hand_orientation_window_s=.3))
    with pytest.raises(ValueError, match='more samples'):
        smooth_hand_targets(p, r, v, np.arange(len(t)) / 30, [], dict(hand_position_window_s=.01))


def test_pi_relative_rotation_is_reported_without_invalid_output():
    p, r, v, t = signal()
    r[15, 0] = r[14, 0] @ Rotation.from_euler('x', np.pi).as_matrix()
    _, filtered, info = smooth_hand_targets(p, r, v, t, [dict(start=0, stop=len(t))],
                                           dict(hand_orientation_window_s=.3))
    assert {'frame': 15, 'hand': 0} in info['ambiguous_rotation_samples']
    np.testing.assert_array_equal(filtered[15, 0], r[15, 0])
    np.testing.assert_allclose(np.linalg.det(filtered), 1., atol=1e-12)


def test_exact_chained_adjacency_after_duration_filtering():
    seeds = [dict(start=a, stop=b, retained=keep, duration_s=(b-a)/30) for a, b, keep in
             [(0, 40, True), (40, 45, False), (45, 80, True), (80, 110, True), (110, 150, True),
              (151, 190, True)]]
    regions = retained_regions(seeds, np.arange(190)/30, True)
    assert [(r['start'], r['stop']) for r in regions] == [(0, 40), (45, 150), (151, 190)]
    assert regions[1]['seed_indices'] == [2, 3, 4]
    assert regions[1]['duration_s'] == pytest.approx(3.5)
    assert seeds[2]['stop'] == 80 and not seeds[1]['retained']
    assert [r['seed_indices'] for r in retained_regions(seeds, np.arange(190)/30)] == [[0], [2], [3], [4], [5]]
