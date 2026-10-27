"""Defense continuity and layer checks against actual native Spine samples."""
import hashlib
import json
import numpy as np
from puppet_geometry import ROOT,DATA
from reference_guard import PROFILES
from reference_palm import JOINTS,S

samples=json.loads((ROOT/'work/spine-mesh-samples.json').read_text())
indices={b['name']:i for i,b in enumerate(DATA['bones'])}
report={};max_connection=0.;max_floor_drift=0.
for name,(duration,intensity) in PROFILES.items():
    poses=sorted((s for s in samples if s['animation']==name),key=lambda s:s['phase'])
    assert len(poses)>120,name
    palm=np.array([s['bones'][indices['ref_hand_front']][4:6] for s in poses])
    times=np.array([s['phase']*duration for s in poses]);dt=np.diff(times)
    speed=np.linalg.norm(np.diff(palm,axis=0),axis=1)[dt>1e-5]/dt[dt>1e-5]
    distinct=len(np.unique(np.round(palm,5),axis=0))
    assert distinct>95,(name,distinct)
    assert speed.max()<1800,(name,float(speed.max()))
    assert np.linalg.norm(palm[0]-palm[-1])<.002,(name,'ready seam')
    for sample in poses:
        assert sample['slots']['torso'][1]<.001,'Legacy model overlaps defense'
        for part in ['body_back','body_front','leg_front','leg_back']:
            assert sample['slots']['ref_'+part+'_0'][1]>.999
        for part in ['arm_front','fore_front','hand_front','arm_back','hand_back']:
            alphas=[sample['slots'][f'guard_{part}_{view}'][1] for view in range(3)]
            assert abs(sum(alphas)-1)<1e-4 and sum(a>.001 for a in alphas)==1,(name,part,alphas)
        for side in ['front','back']:
            for bone,start,end,child in [('upper','shoulder','elbow','fore'),('thigh','hip','knee','shin'),('shin','knee','ankle','foot')]:
                length=np.linalg.norm(np.array(JOINTS[0][end+'_'+side])-JOINTS[0][start+'_'+side])*S
                a,b,c,d,x,y=sample['bones'][indices['ref_'+bone+'_'+side]]
                target=np.array(sample['bones'][indices['ref_'+child+'_'+side]][4:6])
                max_connection=max(max_connection,float(np.linalg.norm(np.array([x+a*length,y+c*length])-target)))
            foot=np.array(sample['bones'][indices['ref_foot_'+side]][4:6])
            anchor=np.array(poses[0]['bones'][indices['ref_foot_'+side]][4:6])
            max_floor_drift=max(max_floor_drift,float(np.linalg.norm(foot-anchor)))
    report[name]={'native_samples':len(poses),'duration':duration,'distinct_palm_positions':distinct,
                  'maximum_palm_speed':float(speed.max()),'ready_seam':float(np.linalg.norm(palm[0]-palm[-1]))}
assert max_connection<.03,max_connection
assert max_floor_drift<.002,max_floor_drift
out={'rig_sha256':hashlib.sha256((ROOT/'assets/animation/maid.spine-json').read_bytes()).hexdigest(),
     'profiles':report,'maximum_connected_joint_error':max_connection,'maximum_planted_foot_drift':max_floor_drift,
     'shared_ready_body':True,'one_view_per_arm_part':True,'rigid_palm_and_foreground_sleeve_halves':True,
     'not_verified':['Full combat scene and C# shield trigger/follow','GPU rendering and game FPS']}
(ROOT/'work/reference-guard-validation.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))
