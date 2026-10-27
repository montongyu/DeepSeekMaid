"""Check actual native palm motion, layer exclusivity and joint continuity."""
import json
import hashlib
from pathlib import Path
import numpy as np
from reference_palm import JOINTS,S

ROOT=Path(__file__).resolve().parents[1]
rig=json.loads((ROOT/'assets/animation/maid.spine-json').read_text())
meta=json.loads((ROOT/'assets/animation/reference-palm.json').read_text())
poses=json.loads((ROOT/'work/spine-mesh-samples.json').read_text())
attack=sorted((s for s in poses if s['animation']=='attack'),key=lambda s:s['phase'])
indices={b['name']:i for i,b in enumerate(rig['bones'])}
parts=['body_front','body_back','leg_front','leg_back','arm_front','arm_back','hand_front','hand_back']
for sample in attack:
    for part in parts:
        alpha=[sample['slots'][f'ref_{part}_{view}'][1] for view in range(3)]
        assert abs(sum(alpha)-1)<.0001 and sum(a>.001 for a in alpha)==1,(part,sample['phase'],alpha)
    assert sample['slots']['torso'][1]<.001,'Old whole figure overlaps the new attack'
hand=np.array([s['bones'][indices['ref_hand_front']][4:6] for s in attack])
distinct=len(np.unique(np.round(hand,5),axis=0))
assert distinct>75,('Hand is stepping between only a few fixed poses',distinct)
dt=np.diff([s['phase']*meta['duration'] for s in attack])
distance=np.linalg.norm(np.diff(hand,axis=0),axis=1)
speed=distance[dt>.00001]/dt[dt>.00001]
assert speed.max()<1800,('Hand teleports instead of moving continuously',float(speed.max()))
maximum_connection_error=0
for side in ['front','back']:
    chains=[('upper','shoulder','elbow','fore'),('thigh','hip','knee','shin'),('shin','knee','ankle','foot')]
    for bone,start,end,child in chains:
        length=float(np.linalg.norm(np.array(JOINTS[0][end+'_'+side])-JOINTS[0][start+'_'+side])*S)
        for sample in attack:
            a,b,c,d,x,y=sample['bones'][indices['ref_'+bone+'_'+side]]
            target=np.array(sample['bones'][indices['ref_'+child+'_'+side]][4:6])
            error=np.linalg.norm(np.array([x+a*length,y+c*length])-target)
            maximum_connection_error=max(maximum_connection_error,float(error))
assert maximum_connection_error<.03,('Sleeve or knee detached from its next joint',maximum_connection_error)
idle=[s for s in poses if s['animation']=='idle_loop']
head=np.array([s['bones'][indices['ref_head']][4:6] for s in idle])
assert np.count_nonzero(np.linalg.norm(np.diff(head,axis=0),axis=1)>.0001)>340,'Visible idle body is not continuously breathing'
report={'rig_sha256':hashlib.sha256((ROOT/'assets/animation/maid.spine-json').read_bytes()).hexdigest(),'native_attack_samples':len(attack),'distinct_hand_positions':distinct,'maximum_hand_speed_bone_units_per_second':float(speed.max()),
        'maximum_connected_joint_error':maximum_connection_error,'one_painted_view_per_part':True,'full_figure_crossfade_in_attack':False,
        'visible_reference_idle_continuous':True,'source_key_times':meta['key_times'],'attack_duration_seconds':meta['duration'],
        'runtime':'native Spine continuous skinning; painted viewpoint substitutions are stepped',
        'not_verified':['Full combat scene/GPU rendering and game FPS','Pixel-identical reproduction of the supplied painting after transparent extraction and body-layer reconstruction']}
(ROOT/'work/reference-palm-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
