"""Actual native spell motion: body consistency, planted feet and joined arms."""
import hashlib
import json
import numpy as np
from puppet_geometry import ROOT,DATA
from reference_spell import PROFILES,PARTS
from reference_palm import JOINTS,S

samples=json.loads((ROOT/'work/spine-mesh-samples.json').read_text())
idx={b['name']:i for i,b in enumerate(DATA['bones'])}
report={};connection=0.;drift=0.;minimum_forearm=1e9
for name,(duration,gesture) in PROFILES.items():
    poses=sorted((s for s in samples if s['animation']==name),key=lambda s:s['phase'])
    palm=np.array([s['bones'][idx['ref_hand_front']][4:6] for s in poses])
    times=np.array([s['phase']*duration for s in poses]);dt=np.diff(times)
    speed=np.linalg.norm(np.diff(palm,axis=0),axis=1)[dt>1e-5]/dt[dt>1e-5]
    distinct=len(np.unique(np.round(palm,5),axis=0))
    assert distinct>70,(name,distinct)
    assert speed.max()<1800,(name,float(speed.max()))
    assert np.linalg.norm(palm[0]-palm[-1])<.002,(name,'ready seam')
    for s in poses:
        assert s['slots']['torso'][1]<.001
        for part in ['body_back','body_front','leg_back','leg_front']:assert s['slots'][f'ref_{part}_0'][1]>.999
        for part in PARTS:
            alphas=[s['slots'][f'spell_{part}_{view}'][1] for view in range(3)]
            assert abs(sum(alphas)-1)<1e-4 and sum(a>.001 for a in alphas)==1,(name,part,alphas)
        for side in ['front','back']:
            fore=np.array(s['bones'][idx['ref_fore_'+side]][4:6]);wrist=np.array(s['bones'][idx['ref_hand_'+side]][4:6])
            source_length=np.linalg.norm(np.array(JOINTS[0]['wrist_'+side])-JOINTS[0]['elbow_'+side])*S
            b=s['bones'][idx['ref_fore_'+side]]
            minimum_forearm=min(minimum_forearm,float(np.linalg.norm([b[0],b[2]])*source_length))
            for bone,start,end,child in [('upper','shoulder','elbow','fore'),('thigh','hip','knee','shin'),('shin','knee','ankle','foot')]:
                length=np.linalg.norm(np.array(JOINTS[0][end+'_'+side])-JOINTS[0][start+'_'+side])*S
                a,b,c,d,x,y=s['bones'][idx['ref_'+bone+'_'+side]]
                target=np.array(s['bones'][idx['ref_'+child+'_'+side]][4:6])
                connection=max(connection,float(np.linalg.norm(np.array([x+a*length,y+c*length])-target)))
            foot=np.array(s['bones'][idx['ref_foot_'+side]][4:6]);anchor=np.array(poses[0]['bones'][idx['ref_foot_'+side]][4:6])
            drift=max(drift,float(np.linalg.norm(foot-anchor)))
    report[name]={'duration':duration,'gesture':gesture,'native_samples':len(poses),'distinct_palm_positions':distinct,'maximum_palm_speed':float(speed.max())}
assert connection<.03,connection
assert drift<.002,drift
assert minimum_forearm>9,minimum_forearm
out={'rig_sha256':hashlib.sha256((ROOT/'assets/animation/maid.spine-json').read_bytes()).hexdigest(),
     'profiles':report,'maximum_connected_joint_error':connection,'maximum_planted_foot_drift':drift,
     'minimum_forearm_length_bone_units':minimum_forearm,'one_view_per_part':True,'shared_ready_body':True,
     'not_verified':['Full combat scene and C# hand weave trigger','GPU rendering and game FPS']}
(ROOT/'work/reference-spell-validation.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))
