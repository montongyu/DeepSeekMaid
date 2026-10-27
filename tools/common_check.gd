extends SceneTree

func _initialize():
    call_deferred("_run")

func require(ok, message):
    if not ok:
        push_error(message)
        quit(1)
        assert(false,message)

func capture(skeleton, definition, name, phase):
    var matrices=[]
    var slots={}
    for item in definition.bones:
        var b=skeleton.find_bone(item.name)
        matrices.append([b.get_a(),b.get_b(),b.get_c(),b.get_d(),b.get_world_x(),b.get_world_y()])
    for item in definition.slots:
        var s=skeleton.find_slot(item.name)
        var attachment=s.get_attachment()
        slots[item.name]=[attachment.get_attachment_name() if attachment else "",s.get_color().a]
    return {"animation":name,"phase":phase,"bones":matrices,"slots":slots}

func distance_from_rest(pose, rest):
    var error=0.0
    for i in range(pose.bones.size()):
        for j in range(6):error=max(error,abs(pose.bones[i][j]-rest.bones[i][j]))
    return error

func _run():
    var root=OS.get_cmdline_user_args()[0]
    var folder=root.path_join("dist/DeepSeekMaid/animation")
    var definition=JSON.parse_string(FileAccess.get_file_as_string(folder.path_join("maid.spine-json")))
    var author=JSON.parse_string(FileAccess.get_file_as_string(root.path_join("assets/animation/common-state.json")))
    var source=ClassDB.instantiate("SpineSkeletonFileResource")
    var atlas=ClassDB.instantiate("SpineAtlasResource")
    require(source.load_from_file(folder.path_join("maid.spine-json"))==OK,"Cannot load shared-state rig")
    require(atlas.load_from_atlas_file(folder.path_join("maid.atlas"))==OK,"Cannot load shared-state atlas")
    var data=ClassDB.instantiate("SpineSkeletonDataResource")
    data.set_atlas_res(atlas);data.set_skeleton_file_res(source);data.set_default_mix(.08)
    require(data.is_skeleton_data_loaded(),"Native Spine rejected shared-state rig")
    var sprite=ClassDB.instantiate("SpineSprite")
    sprite.set_skeleton_data_res(data);sprite.set_update_mode(2)
    get_root().add_child(sprite)
    var state=sprite.get_animation_state()
    var skeleton=sprite.get_skeleton()
    sprite.update_skeleton(0)
    var setup=capture(skeleton,definition,"setup",0)
    var initial=state.set_animation("idle_loop",true,0);initial.set_mix_duration(0);initial.set_track_time(0)
    sprite.update_skeleton(0)
    var rest=capture(skeleton,definition,"idle_loop",0)
    var setup_error=distance_from_rest(setup,rest)
    require(setup_error<.002,"Setup frame is not the requested default pose")
    var poses=[];var seams={};var endpoints={};var hurt_recoil={};var reaches={}
    var head_index=-1;var hand_index=-1
    for i in range(definition.bones.size()):
        if definition.bones[i].name=="ref_head":head_index=i
        if definition.bones[i].name=="ref_hand_front":hand_index=i
    for name in definition.animations:
        var track=state.set_animation(name,false,0);track.set_mix_duration(0)
        var duration=track.get_animation_end()
        var steps=ceili(duration*(60 if name.ends_with("_loop") else 120))
        var maximum_reach=0.0;var maximum_recoil=0.0;var first={};var last={}
        for i in range(steps+1):
            track.set_track_time(duration*i/float(steps));sprite.update_skeleton(0)
            var pose=capture(skeleton,definition,name,i/float(steps))
            for matrix in pose.bones:
                for value in matrix:require(is_finite(value),"Nonfinite bone: "+name)
            var h=pose.bones[hand_index];var rh=rest.bones[hand_index]
            maximum_reach=max(maximum_reach,Vector2(h[4]-rh[4],h[5]-rh[5]).length())
            maximum_recoil=max(maximum_recoil,abs(pose.bones[head_index][4]-rest.bones[head_index][4]))
            poses.append(pose)
            if i==0:first=pose
            if i==steps:last=pose
        if name!="revive":require(distance_from_rest(first,rest)<.02,"Action does not begin at common rest: "+name)
        if name!="death":require(distance_from_rest(last,rest)<.02,"Action does not return to common rest: "+name)
        endpoints[name]={"start_error":distance_from_rest(first,rest),"end_error":distance_from_rest(last,rest)}
        if name.ends_with("_loop"):
            seams[name]=distance_from_rest(first,last)
            require(seams[name]<.02,"Loop seam: "+name)
        if name.begins_with("attack"):
            require(maximum_reach>55,"Attack has no substantial arm motion: "+name)
            reaches[name]=maximum_reach
        if name.begins_with("hurt"):
            require(maximum_recoil<12.1,"Hurt recoil is too large: "+name)
            require(last.slots.face[0]=="angry","Missing annoyed expression: "+name)
            hurt_recoil[name]=maximum_recoil
        if name=="death":
            require(last.slots.prone[1]>.999,"Prone view did not persist")
            for sn in last.slots:
                if sn!="prone":require(last.slots[sn][1]<.001,"Upright layer remains after death")
        for meta in author.meshes.values():
            if meta.check_animation!=name:continue
            track.set_track_time(meta.check_time);sprite.update_skeleton(0)
            poses.append(capture(skeleton,definition,name,meta.check_time/duration))
        print("Played ",name,": ",snappedf(duration,.001),"s, shared start/end checked")
    var idle=state.set_animation("idle_loop",true,0);idle.set_mix_duration(0)
    var unique={}
    for i in range(361):
        idle.set_track_time(i/60.0);sprite.update_skeleton(0)
        var b=skeleton.find_bone("ref_head")
        unique[snappedf(b.get_world_y(),.00001)]=true
    require(unique.size()>150,"Idle breathing is stepping or static")
    state.set_animation("hurt",false,0)
    state.add_animation("idle_angry_loop",0,false,0);state.add_animation("idle_loop",0,true,0)
    for i in range(100):sprite.update_skeleton(1.0/60)
    require(state.get_current(0).get_animation().get_name()=="idle_angry_loop","Hurt did not queue short annoyance")
    for i in range(200):sprite.update_skeleton(1.0/60)
    require(state.get_current(0).get_animation().get_name()=="idle_loop","Annoyance did not return to calm idle")
    sprite.set_update_mode(0)
    var before=state.get_current(0).get_track_time()
    await create_timer(.12).timeout
    require(state.get_current(0).get_track_time()-before>.08,"Render Process did not advance")
    paused=true;before=state.get_current(0).get_track_time()
    await create_timer(.06,true).timeout
    require(abs(state.get_current(0).get_track_time()-before)<.001,"Pause was ignored")
    paused=false;sprite.set_update_mode(2)
    var sequences={
        "reference_idle":[["idle_loop",6.0]],
        "reference_hurt":[["idle_loop",.4],["hurt",.58],["idle_angry_loop",3.0],["idle_loop",.6]],
        "common_actions":[["idle_loop",.3],["attack",1.1],["idle_loop",.2],["guard",1.15],["idle_loop",.2],["cast",1.25],["idle_loop",.2],["channel_overdrive",1.9],["idle_loop",.3]],
        "lifecycle":[["idle_loop",.35],["death",1.9],["revive",1.2],["idle_loop",.4]],
        "interruptions":[["idle_loop",.3],["cast_dual",.5],["hurt",.58],["idle_angry_loop",.6],["attack",.4],["guard",.5],["death",1.5],["revive",1.2],["idle_loop",.4]],
        "entry_victory":[["greeting",1.2],["greeting_wave",1.2],["greeting_bow",1.2],["victory_wave_loop",4.0],["idle_loop",.3]],
    }
    var showcases={}
    for group in sequences:
        var frames=[];var first=true
        for item in sequences[group]:
            var entry=state.set_animation(item[0],item[0].ends_with("_loop"),0)
            entry.set_mix_duration(0 if first else .08);first=false
            for i in range(roundi(item[1]*60)):
                sprite.update_skeleton(1.0/60)
                frames.append(capture(skeleton,definition,item[0],min(1.0,entry.get_track_time()/entry.get_animation_end())))
        showcases[group]=frames
    var f=FileAccess.open(root.path_join("work/spine-mesh-samples.json"),FileAccess.WRITE);f.store_string(JSON.stringify(poses));f.close()
    f=FileAccess.open(root.path_join("work/spine-showcases.json"),FileAccess.WRITE);f.store_string(JSON.stringify(showcases));f.close()
    var report={"native_engine":Engine.get_version_info().string,"spine_data_version":"4.2.43","authored_bones":definition.bones.size(),
        "painted_slots":definition.slots.size(),"authored_animations":definition.animations.size(),"sampled_poses":poses.size(),
        "default_setup_error":setup_error,"all_action_endpoints":endpoints,"all_loop_seams":seams,"distinct_idle_head_heights":unique.size(),
        "hurt_recoil_bone_units":hurt_recoil,"attack_hand_reach_bone_units":reaches,"hurt_returns_to_calm_idle":true,
        "native_blended_preview_sequences":showcases.size(),"automatic_process_playback":true,"scene_pause_respected":true,
        "game_project_started":false,"deployed":false,"not_verified":["Full combat scene and C# effect triggers","GPU rendering and in-game FPS"]}
    f=FileAccess.open(root.path_join("work/spine-validation.json"),FileAccess.WRITE);f.store_string(JSON.stringify(report,"  "));f.close()
    print("PASS: native Spine common default pose, all 50 action boundaries, short hit recovery, prone defeat and revive.")
    sprite.free();quit()
