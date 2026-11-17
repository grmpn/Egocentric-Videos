"""Licensed MANO reconstruction through the exported quaternion representation."""
from pathlib import Path

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from egocentric_pipeline.datasets.human_episode import human_arrays, aligned_from_human, source_status
from egocentric_pipeline.geometry.hand_geometry import align_hand_geometry, load_mano_model, reconstruct_mano


def test_provenance_usable_infill_takes_precedence_over_unused_detection():
    arrays={'export_valid':np.array([[True,True],[False,False]]),
            'motion_infilled':np.array([[True,False],[True,False]]),
            'direct_detection':np.ones((2,2),bool)}
    np.testing.assert_array_equal(source_status(arrays),[[1,2],[0,0]])


def test_full_mano_geometry_round_trip_both_hands():
    pytest.importorskip('smplx')
    models=[Path('external/HaWoR/_DATA/data_left/mano_left/MANO_LEFT.pkl'),
            Path('external/HaWoR/_DATA/data/mano/MANO_RIGHT.pkl')]
    if not all(p.exists() for p in models): pytest.skip('Licensed MANO assets are local inputs')
    rng=np.random.default_rng(8)
    world={key:rng.normal(scale=scale,size=(4,2,width)).astype(np.float32) for key,width,scale in
           [('root_translation_world_m',3,.3),('root_orientation_world_axis_angle',3,.3),
            ('hand_pose_axis_angle',45,.1),('mano_betas',10,.05)]}
    world.update(export_valid=np.ones((4,2),bool),motion_infilled=np.zeros((4,2),bool))
    world['motion_infilled'][1,0]=True
    world['export_valid'][3,1]=False
    rotation=Rotation.from_euler('xyz',[.4,-.2,.7]).as_matrix()
    derived,_=align_hand_geometry(world,rotation,models)
    aligned={**world,**derived,'camera_rotation_aligned_from_camera':np.tile(rotation,(4,1,1)),
             'camera_position_aligned_m':np.zeros((4,3))}
    exported=human_arrays(aligned)
    restored=aligned_from_human(exported)
    np.testing.assert_array_equal(exported['observation.hands.pose_axis_angle'],world['hand_pose_axis_angle'])
    np.testing.assert_array_equal(exported['observation.hands.betas'],world['mano_betas'])
    for hand,path in enumerate(models):
        valid=world['export_valid'][:,hand]
        model=load_mano_model(path,hand)
        args=[world[key][valid,hand] for key in ('root_translation_world_m','root_orientation_world_axis_angle','hand_pose_axis_angle','mano_betas')]
        joints,vertices=reconstruct_mano(model,*args)
        new=[restored[key][valid,hand] for key in ('root_translation_aligned_m','root_orientation_aligned_axis_angle','hand_pose_axis_angle','mano_betas')]
        aligned_joints,aligned_vertices=reconstruct_mano(model,*new)
        np.testing.assert_allclose(aligned_joints,joints@rotation.T,atol=2e-6,rtol=0)
        np.testing.assert_allclose(aligned_vertices,vertices@rotation.T,atol=2e-6,rtol=0)
        np.testing.assert_allclose(aligned_joints[:,0],exported['observation.hands.wrist_position_aligned_m'][valid,hand],atol=2e-6,rtol=0)
        offset=derived['mano_root_offset_m'][valid,hand]
        native_t=(new[0]+offset)@rotation-offset
        np.testing.assert_allclose(native_t,args[0],atol=2e-6,rtol=0)
