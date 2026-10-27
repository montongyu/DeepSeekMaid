extends SceneTree

func _initialize():
    call_deferred("_run")

func _run():
    print("Isolated project: ", ProjectSettings.get_setting("application/config/name"))
    print("SpineSprite present: ", ClassDB.class_exists("SpineSprite"))
    if not ClassDB.class_exists("SpineSprite"):
        quit(1)
        return
    var project_root = OS.get_cmdline_user_args()[0]
    var folder = project_root.path_join("dist/DeepSeekMaid/animation")
    var rig_data = JSON.parse_string(FileAccess.get_file_as_string(folder.path_join("maid.spine-json")))
    var clips = rig_data.animations.keys()
    var source = ClassDB.instantiate("SpineSkeletonFileResource")
    var atlas = ClassDB.instantiate("SpineAtlasResource")
    if source.load_from_file(folder.path_join("maid.spine-json")) != OK or atlas.load_from_atlas_file(folder.path_join("maid.atlas")) != OK:
        push_error("Cannot load authored rig or external PNG atlas")
        quit(1)
        return
    var data = ClassDB.instantiate("SpineSkeletonDataResource")
    data.set_atlas_res(atlas)
    data.set_skeleton_file_res(source)
    data.set_default_mix(0.10)
    if not data.is_skeleton_data_loaded():
        push_error("Native Spine parser rejected data")
        quit(1)
        return
    var sprite = ClassDB.instantiate("SpineSprite")
    sprite.set_skeleton_data_res(data)
    sprite.set_update_mode(2)
    get_root().add_child(sprite)
    print("Sprite inside tree: ",sprite.is_inside_tree(),"; visible: ",sprite.is_visible_in_tree())
    var state = sprite.get_animation_state()
    var skeleton = sprite.get_skeleton()
    var bone = skeleton.find_bone("hair_tip")
    print("Loaded mesh and PNG atlas; hair bone initial rotation: ", bone.get_rotation())
    for name in clips:
        var entry = state.set_animation(name, false, 0)
        for frame in range(60):
            sprite.update_skeleton(1.0/60.0)
            if not is_finite(bone.get_rotation()):
                push_error("Non-finite pose in " + name)
                quit(1)
                return
        print("Parsed and played: ",name,"; duration=",entry.get_animation_end())
    var idle = state.set_animation("idle_loop", true, 0)
    idle.set_mix_duration(0.0)
    var samples = []
    var distinct = {}
    var max_step = 0.0
    for frame in range(289):
        idle.set_track_time(frame / 60.0)
        sprite.update_skeleton(0.0)
        var angle = bone.get_rotation()
        if samples.size() > 0:
            max_step = max(max_step, abs(angle - samples[-1]))
        samples.append(angle)
        distinct[snappedf(angle, 0.00001)] = true
    var seam = abs(samples[0] - samples[-1])
    var velocity_seam = abs((samples[1]-samples[0])-(samples[-1]-samples[-2]))
    print("Idle metrics: unique=",distinct.size()," max_step=",max_step," seam=",seam," velocity_seam=",velocity_seam)
    if distinct.size() < 280 or max_step > 0.09 or seam > 0.002 or velocity_seam > 0.003:
        push_error("Idle interpolation/loop seam regression")
        quit(1)
        return
    print("Idle at 60Hz: ",distinct.size()," distinct poses / 289 samples; max angular step=",max_step,"; seam=",seam)
    var loop_seams = {}
    for name in clips:
        if not name.ends_with("_loop"):
            continue
        var looping = state.set_animation(name,false,0)
        looping.set_mix_duration(0.0)
        sprite.update_skeleton(0.0)
        var first = []
        for definition in rig_data.bones:
            var current_bone = skeleton.find_bone(definition.name)
            first.append(Vector2(current_bone.get_world_x(),current_bone.get_world_y()))
        looping.set_track_time(looping.get_animation_end())
        sprite.update_skeleton(0.0)
        var maximum_seam = 0.0
        for index in range(rig_data.bones.size()):
            var current_bone = skeleton.find_bone(rig_data.bones[index].name)
            maximum_seam = max(maximum_seam,first[index].distance_to(Vector2(current_bone.get_world_x(),current_bone.get_world_y())))
        loop_seams[name] = maximum_seam
        if maximum_seam > 0.02:
            push_error("Loop seam in " + name + ": " + str(maximum_seam))
            quit(1)
            return
    state.set_animation("attack", false, 0)
    state.add_animation("idle_loop",0.0,true,0)
    for frame in range(120):
        sprite.update_skeleton(1.0/60.0)
    var queued = state.get_current(0).get_animation().get_name()
    if queued != "idle_loop":
        push_error("Action did not blend back to idle")
        quit(1)
        return
    var head = skeleton.find_bone("head")
    var max_switch_jump = 0.0
    for name in ["attack","hurt","cast","guard","channel","death","idle_loop"]:
        var before = Vector2(head.get_world_x(),head.get_world_y())
        state.set_animation(name,name == "idle_loop",0)
        sprite.update_skeleton(0.0)
        var after = Vector2(head.get_world_x(),head.get_world_y())
        print("Switch ",name," immediate head delta=",before.distance_to(after))
        max_switch_jump = max(max_switch_jump,before.distance_to(after))
        for frame in range(9):
            sprite.update_skeleton(1.0/60.0)
    # Under one source pixel is under 0.6 screen pixels at the default height.
    if max_switch_jump > 1.0:
        push_error("Interrupted action snapped instead of blending")
        quit(1)
        return
    var head_transform = sprite.get_global_bone_transform("head")
    if head_transform.origin.y > 0:
        push_error("Skeleton rendered upside down")
        quit(1)
        return
    var mesh_samples = []
    for name in clips:
        var track = state.set_animation(name,false,0)
        track.set_mix_duration(0.0)
        var steps = ceili(track.get_animation_end() * (60.0 if name.ends_with("_loop") else 120.0))
        for index in range(steps + 1):
            track.set_track_time(track.get_animation_end()*index/float(steps))
            sprite.update_skeleton(0.0)
            var transforms = []
            for definition in rig_data.bones:
                var sample_bone = skeleton.find_bone(definition.name)
                transforms.append([sample_bone.get_a(),sample_bone.get_b(),sample_bone.get_c(),sample_bone.get_d(),sample_bone.get_world_x(),sample_bone.get_world_y()])
            mesh_samples.append({"animation":name,"sample":index,"phase":index/float(steps),"bones":transforms})
    var mesh_file = FileAccess.open(project_root.path_join("work/spine-mesh-samples.json"),FileAccess.WRITE)
    mesh_file.store_string(JSON.stringify(mesh_samples))
    mesh_file.close()
    state.set_animation("idle_loop",true,0)
    sprite.set_update_mode(0)
    var render_track = state.get_current(0)
    var initial_time = render_track.get_track_time()
    await create_timer(0.12).timeout
    var elapsed = render_track.get_track_time() - initial_time
    if elapsed < 0.08:
        push_error("Native Process mode failed to advance without manual updates")
        quit(1)
        return
    paused = true
    var pause_time = render_track.get_track_time()
    await create_timer(0.06,true).timeout
    var pause_drift = abs(render_track.get_track_time() - pause_time)
    paused = false
    if pause_drift > 0.001:
        push_error("Animation ignored the scene pause")
        quit(1)
        return
    var report = {
        "native_engine":Engine.get_version_info().string,
        "spine_data_version":"4.2.43",
        "authored_bones":rig_data.bones.size(),"authored_animations":clips.size(),"weighted_vertices":rig_data.skins[0].attachments.character.maid.uvs.size()/2,
        "sample_rate":60,"idle_samples":289,"distinct_idle_poses":distinct.size(),
        "max_idle_angular_step_degrees":max_step,"loop_seam_degrees":seam,
        "loop_velocity_seam_degrees_per_sample":velocity_seam,
        "max_interrupted_switch_jump_pixels":max_switch_jump,
        "action_queue_returns_to_idle":true,"texture_atlas_loaded":true,
        "automatic_process_playback":true,"scene_pause_respected":true,
        "all_loop_position_seams_pixels":loop_seams,
        "game_project_started":false,"deployed":false,
        "not_verified":["Full combat scene integration","GPU rendering and subjective visual quality","In-game frame rate"]
    }
    var file = FileAccess.open(project_root.path_join("work/spine-validation.json"),FileAccess.WRITE)
    file.store_string(JSON.stringify(report,"  "))
    file.close()
    print("Interrupted animation mix: maximum immediate head jump=",max_switch_jump," pixels; action queue returns to idle.")
    print("PASS: native Spine loads all clips, interpolates at 60Hz, closes the idle loop and mixes interrupted actions.")
    sprite.free()
    quit()
