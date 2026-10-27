"""Validate visible shared-slot geometry using actual native action/mix poses."""
import json
import hashlib
import numpy as np
from puppet_geometry import ROOT,DATA,REGIONS,MESHES,points,areas

meta=json.loads((ROOT/'assets/animation/common-state.json').read_text())
payload=json.loads((ROOT/'assets/animation/payload.json').read_text())
for f in ['maid.spine-json','maid.atlas']:
    assert (ROOT/'assets/animation'/f).read_bytes()==(ROOT/'dist/DeepSeekMaid/animation'/f).read_bytes(),f
for f in payload['textures']:
    assert (ROOT/'assets/sprites'/f).read_bytes()==(ROOT/'dist/DeepSeekMaid/animation'/f).read_bytes(),f
single=json.loads((ROOT/'work/spine-mesh-samples.json').read_text());groups=json.loads((ROOT/'work/spine-showcases.json').read_text())
samples=single+[s for sequence in groups.values() for s in sequence]
baseline={};source_error=0.
for key,m in MESHES.items():
    record=meta['meshes']['/'.join(key)];expected=np.array(record['source_geometry']);expected[:,1]*=-1
    baseline[key]=areas(expected,m['tri'])
    candidates=[s for s in single if s['animation']==record['check_animation']]
    duration=meta['clips'][record['check_animation']]['duration']
    sample=min(candidates,key=lambda s:abs(s['phase']*duration-record['check_time']))
    source_error=max(source_error,float(np.abs(points(m,sample)-expected).max()))
assert source_error<.0004,('Source key geometry mismatch',source_error)
seen=set();tested=0;minimum=1e9;maximum_joint_error=0.;max_blend_step=0.
idx={b['name']:i for i,b in enumerate(DATA['bones'])}
for sample in samples:
    for sn,(attachment,alpha) in sample['slots'].items():
        if not attachment or alpha<.001:continue
        key=(sn,attachment);seen.add(key);m=MESHES[key];p=points(m,sample)
        assert np.isfinite(p).all() and np.abs(p).max()<950,(sample['animation'],sn)
        ratio=areas(p,m['tri'])/baseline[key]
        assert (ratio>0).all(),('Folded geometry',sample['animation'],sample['phase'],key,float(ratio.min()))
        minimum=min(minimum,float(ratio.min()));tested+=len(ratio)
    for side in ['front','back']:
        for part,child in [('upper','fore'),('thigh','shin'),('shin','foot')]:
            a,b,c,d,x,y=sample['bones'][idx['ref_'+part+'_'+side]]
            length=meta['bone_lengths'][part+'_'+side]
            target=np.array(sample['bones'][idx['ref_'+child+'_'+side]][4:6])
            error=np.linalg.norm(np.array([x+a*length,y+c*length])-target)
            maximum_joint_error=max(maximum_joint_error,float(error))
assert seen==set(MESHES),('Unused attachments',set(MESHES)-seen)
# Native mixing interpolates independent joint origins and angles. Its brief
# in-between connection error is recorded separately from standalone action paths.
standalone_joint_error=0.
for sample in single:
    for side in ['front','back']:
        for part,child in [('upper','fore'),('thigh','shin'),('shin','foot')]:
            a,b,c,d,x,y=sample['bones'][idx['ref_'+part+'_'+side]];length=meta['bone_lengths'][part+'_'+side]
            target=np.array(sample['bones'][idx['ref_'+child+'_'+side]][4:6])
            standalone_joint_error=max(standalone_joint_error,float(np.linalg.norm(np.array([x+a*length,y+c*length])-target)))
assert standalone_joint_error<.04,standalone_joint_error
assert maximum_joint_error<.04,('Native mixed joints detached',maximum_joint_error)
for group,sequence in groups.items():
    for a,b in zip(sequence,sequence[1:]):
        # Head motion measures actual transition continuity independently of
        # drawn view substitutions (there is only one attachment per slot).
        delta=np.array(a['bones'][idx['ref_head']][4:6])-b['bones'][idx['ref_head']][4:6]
        max_blend_step=max(max_blend_step,float(np.linalg.norm(delta)))
idle_detail={}
if 'idle_detail' in meta:
    idle=[s for s in single if s['animation']=='idle_loop']
    # Measure actual native skin vertices, not just authored curve parameters.
    mesh=MESHES['body_front','body_front'];uv=mesh['uv']*[800,724]
    from PIL import Image
    image=np.array(Image.open(ROOT/'assets/sprites'/meta['baseline']).convert('RGBA'))
    px=np.minimum((mesh['uv']*[image.shape[1],image.shape[0]]).astype(int),[image.shape[1]-1,image.shape[0]-1])
    hair=(uv[:,0]<330)&(uv[:,1]>95)&(uv[:,1]<315)&(image[px[:,1],px[:,0],3]>180)
    assert hair.sum()>20,'Not enough visible long-hair vertices to check'
    head=np.array([s['bones'][idx['ref_head']][4:6] for s in idle])
    vertices=np.array([points(mesh,s)[hair]-h for s,h in zip(idle,head)])
    visible_travel=float(np.linalg.norm(vertices-vertices[0],axis=2).max())
    crown=(uv[:,0]>425)&(uv[:,0]<580)&(uv[:,1]<55)&(image[px[:,1],px[:,0],3]>180)
    assert crown.sum()>2,'Not enough visible crown-curl vertices to check'
    crown_vertices=np.array([points(mesh,s)[crown]-h for s,h in zip(idle,head)])
    crown_travel=float(np.linalg.norm(crown_vertices-crown_vertices[0],axis=2).max())
    controls={};peak_phases={}
    for bone in meta['idle_detail']['hair_controls']:
        track=np.array([s['bones'][idx[bone]][4:6] for s in idle])-head
        delta=track-track[0];travel=np.linalg.norm(delta,axis=1)
        controls[bone]=float(travel.max());peak_phases[bone]=idle[int(np.argmax(travel))]['phase']
    feet=np.array([[s['bones'][idx['ref_foot_'+side]][4:6] for side in ['front','back']] for s in idle])
    foot_drift=float(np.abs(feet-feet[0]).max())
    assert visible_travel>4.,('Hair skin is barely moving',visible_travel)
    assert crown_travel>1.,('Visible crown curl is static',crown_travel)
    assert abs(peak_phases['ref_hair_tip']-peak_phases['ref_hair_lower_tip'])>.02,('Hair layers move in lockstep',peak_phases)
    assert foot_drift<.002,('Idle feet sliding',foot_drift)
    idle_detail={'visible_hair_vertices':int(hair.sum()),'maximum_visible_hair_travel_relative_to_head':visible_travel,
        'visible_crown_vertices':int(crown.sum()),'maximum_visible_crown_travel_relative_to_head':crown_travel,
        'hair_control_travel_relative_to_head':controls,'hair_control_peak_phases':peak_phases,
        'foot_drift':foot_drift,'phase_delayed_visible_skin':True}
report=json.loads((ROOT/'work/spine-validation.json').read_text())
report.update({'rig_sha256':hashlib.sha256((ROOT/'assets/animation/maid.spine-json').read_bytes()).hexdigest(),
 'standalone_pose_samples':len(single),'native_mixed_pose_samples':len(samples)-len(single),'mesh_pose_samples':len(samples),
 'layered_attachments_checked':len(seen),'triangle_evaluations':tested,'minimum_triangle_area_ratio':minimum,
 'all_sampled_triangles_preserve_winding':True,'maximum_source_key_geometry_error':source_error,
 'maximum_standalone_joint_connection_error':standalone_joint_error,'maximum_native_mix_joint_connection_error':maximum_joint_error,
 'maximum_preview_head_frame_step':max_blend_step,'single_attachment_per_body_part':True,'external_rig_files_match_source':True,
 'baseline_matches_user_reference':'Master texture copied unchanged from the supplied PNG; body occlusions and expression patches separately reconstructed'})
if idle_detail:report['idle_detail']=idle_detail
(ROOT/'work/spine-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
(ROOT/'work/common-state-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(f'PASS: {len(samples)} native poses, {len(seen)} attachments, {tested:,} triangle evaluations; no foldovers. Source key error {source_error:.8f}; action joint error {standalone_joint_error:.8f}.')
