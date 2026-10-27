extends SceneTree
func _initialize():
    call_deferred("_run")

func require(condition, message):
    if not condition:
        push_error(message)
        quit(1)
        assert(false, message)

func bone_position(skeleton, name):
    var b = skeleton.find_bone(name)
    return Vector2(b.get_world_x(), b.get_world_y())

func capture_pose(skeleton, definition, name, phase):
    var transforms = []
    var slot_states = {}
    for bone in definition.bones:
        var b = skeleton.find_bone(bone.name)
        transforms.append([b.get_a(),b.get_b(),b.get_c(),b.get_d(),b.get_world_x(),b.get_world_y()])
    for slot in definition.slots:
        var live = skeleton.find_slot(slot.name)
        var attachment = live.get_attachment()
        slot_states[slot.name] = [attachment.get_attachment_name() if attachment != null else "",live.get_color().a]
    return {"animation":name,"phase":phase,"bones":transforms,"slots":slot_states}

func _run():
    var project_root = OS.get_cmdline_user_args()[0]
    var folder = project_root.path_join("dist/DeepSeekMaid/animation")
    var definition = JSON.parse_string(FileAccess.get_file_as_string(folder.path_join("maid.spine-json")))
    var source = ClassDB.instantiate("SpineSkeletonFileResource")
    var atlas = ClassDB.instantiate("SpineAtlasResource")
    require(source.load_from_file(folder.path_join("maid.spine-json")) == OK, "Cannot load puppet JSON")
    require(atlas.load_from_atlas_file(folder.path_join("maid.atlas")) == OK, "Cannot load multipage atlas")
    var data = ClassDB.instantiate("SpineSkeletonDataResource")
    data.set_atlas_res(atlas)
    data.set_skeleton_file_res(source)
    data.set_default_mix(0.10)
    require(data.is_skeleton_data_loaded(), "Native Spine rejected puppet")
    var sprite = ClassDB.instantiate("SpineSprite")
    sprite.set_skeleton_data_res(data)
    sprite.set_update_mode(2)
    get_root().add_child(sprite)
    var state = sprite.get_animation_state()
    var skeleton = sprite.get_skeleton()
    var poses = []
    var loop_seams = {}
    var hand_reaches = {}
    var hurt_recoil = {}
    var reference_attack_metrics = {}
    for name in definition.animations:
        var track = state.set_animation(name, false, 0)
        track.set_mix_duration(0)
        var steps = ceili(track.get_animation_end() * (60.0 if name.ends_with("_loop") else 120.0))
        var initial = []
        var first_hand = Vector2.ZERO
        var reach = 0.0
        var recoil = 0.0
        var first_body_y = 0.0
        var first_front_ankle_y = 0.0
        for index in range(steps + 1):
            track.set_track_time(track.get_animation_end() * index / float(steps))
            sprite.update_skeleton(0.0)
            var transforms = []
            for bone in definition.bones:
                var b = skeleton.find_bone(bone.name)
                var point = Vector2(b.get_world_x(), b.get_world_y())
                require(is_finite(point.x) and is_finite(point.y), "Invalid bone pose: " + name)
                transforms.append([b.get_a(), b.get_b(), b.get_c(), b.get_d(), point.x, point.y])
                if index == 0: initial.append(point)
            var slot_states = {}
            for slot in definition.slots:
                var live = skeleton.find_slot(slot.name)
                var attachment = live.get_attachment()
                slot_states[slot.name] = [attachment.get_attachment_name() if attachment != null else "", live.get_color().a]
            var hand = bone_position(skeleton,"hand_front") - bone_position(skeleton,"chest")
            if index == 0:
                first_hand = hand
                first_body_y = bone_position(skeleton,"body").y
                first_front_ankle_y = bone_position(skeleton,"foot_front").y
            if name == "attack" and abs(index/float(steps)-.43) < .005:
                var palm = bone_position(skeleton,"hand_front")
                var shoulder = bone_position(skeleton,"arm_front")
                reference_attack_metrics = {
                    "feet_width":abs(bone_position(skeleton,"foot_back").x-bone_position(skeleton,"foot_front").x),
                    "body_drop":bone_position(skeleton,"body").y-first_body_y,
                    "palm_forward_of_shoulder":palm.x-shoulder.x,
                    "palm_height_delta_from_shoulder":abs(palm.y-shoulder.y),
                    "front_ankle_y_drift":abs(bone_position(skeleton,"foot_front").y-first_front_ankle_y)}
            reach = max(reach, hand.distance_to(first_hand))
            recoil = max(recoil, abs(bone_position(skeleton,"root").x))
            poses.append({"animation":name,"sample":index,"phase":index/float(steps),"bones":transforms,"slots":slot_states})
        if name.begins_with("attack"):
            require(reach > 65, "Attack is only a small arm wiggle: " + name)
            hand_reaches[name] = reach
        if name == "attack":
            require(reference_attack_metrics.feet_width > 210,"Reference attack needs a genuinely wide stance")
            require(reference_attack_metrics.body_drop > 60,"Reference attack did not crouch")
            require(reference_attack_metrics.palm_forward_of_shoulder > 95,"Reference palm did not extend")
            require(reference_attack_metrics.palm_height_delta_from_shoulder < 20,"Palm is not at shoulder height")
            require(reference_attack_metrics.front_ankle_y_drift < .01,"Front shoe left its ground anchor")
        if name.begins_with("hurt"):
            require(recoil <= 12.1, "Hurt recoil is too large: " + name)
            require(abs(skeleton.find_bone("body").get_rotation()) <= 3, "Hurt did not regain posture")
            require(skeleton.find_slot("head").get_attachment().get_attachment_name() == "head_angry", "Hurt did not become annoyed")
            hurt_recoil[name] = recoil
        if name.ends_with("_loop"):
            var maximum = 0.0
            for i in range(definition.bones.size()):
                maximum = max(maximum, initial[i].distance_to(bone_position(skeleton, definition.bones[i].name)))
            require(maximum < 0.02, "Loop position seam: " + name)
            loop_seams[name] = maximum
        if name == "death":
            require(skeleton.find_slot("prone").get_attachment().get_attachment_name() == "prone", "Missing prone death")
            require(skeleton.find_slot("prone").get_color().a > 0.99, "Prone pose is not opaque")
            for slot in definition.slots:
                if slot.name != "prone":require(skeleton.find_slot(slot.name).get_color().a < 0.01, "Upright layer remains after death")
        if name == "attack":
            for key_time in [.15,.375,.75]:
                track.set_track_time(key_time)
                sprite.update_skeleton(0)
                poses.append(capture_pose(skeleton,definition,name,key_time/track.get_animation_end()))
        if name == "guard":
            for key_phase in [.26,.46]:
                track.set_track_time(key_phase*track.get_animation_end())
                sprite.update_skeleton(0)
                poses.append(capture_pose(skeleton,definition,name,key_phase))
        if name == "cast":
            for key_phase in [.30,.54]:
                track.set_track_time(key_phase*track.get_animation_end())
                sprite.update_skeleton(0)
                poses.append(capture_pose(skeleton,definition,name,key_phase))
        print("Played ", name, ": ", snappedf(track.get_animation_end(),0.001), "s")
    var idle = state.set_animation("idle_loop",true,0)
    idle.set_mix_duration(0)
    var values = []
    var distinct = {}
    for i in range(361):
        idle.set_track_time(i/60.0)
        sprite.update_skeleton(0)
        var angle = skeleton.find_bone("hair_tip").get_rotation()
        values.append(angle)
        distinct[snappedf(angle,0.00001)] = true
    require(distinct.size() > 340, "Idle is not continuously interpolated")
    require(abs(values[0]-values[-1]) < 0.002, "Idle seam")
    state.set_animation("hurt",false,0)
    state.add_animation("idle_angry_loop",0,true,0)
    for i in range(100):sprite.update_skeleton(1.0/60)
    require(state.get_current(0).get_animation().get_name() == "idle_angry_loop", "Hurt did not queue angry idle")
    state.set_animation("death",false,0)
    for i in range(200):sprite.update_skeleton(1.0/60)
    require(skeleton.find_slot("prone").get_color().a > 0.99, "Death pose did not persist")
    state.set_animation("revive",false,0)
    state.add_animation("idle_loop",0,true,0)
    for i in range(120):sprite.update_skeleton(1.0/60)
    require(skeleton.find_slot("prone").get_attachment() == null, "Prone pose leaked after revive")
    require(skeleton.find_slot("ref_body_front_0").get_color().a > 0.99, "Revive did not restore the current ready figure")
    var max_jump = 0.0
    for name in ["attack","guard_cross","hurt","channel_overdrive","cast_dual","death","revive","idle_loop"]:
        var before = bone_position(skeleton,"head")
        state.set_animation(name,name.ends_with("_loop"),0)
        sprite.update_skeleton(0)
        max_jump = max(max_jump,before.distance_to(bone_position(skeleton,"head")))
        for i in range(9):sprite.update_skeleton(1.0/60)
    require(max_jump < 1, "Interrupted animation snapped")
    state.set_animation("idle_loop",true,0)
    sprite.set_update_mode(0)
    var playing = state.get_current(0)
    var before_time = playing.get_track_time()
    await create_timer(.12).timeout
    require(playing.get_track_time()-before_time > .08,"Native Process did not advance")
    paused = true
    var pause_time = playing.get_track_time()
    await create_timer(.06,true).timeout
    require(abs(playing.get_track_time()-pause_time) < .001,"Animation ignored pause")
    paused = false
    sprite.set_update_mode(2)
    var sequences = {
        "attack":[["idle_loop",.6],["attack",1.10],["idle_ready_loop",.4],["attack_sweep",.72],["idle_ready_loop",.4],["attack_double",.83],["idle_relax_loop",.65]],
        "reference_attack":[["idle_loop",.5],["attack",1.10],["idle_relax_loop",.5]],
        "reference_guard":[["idle_loop",.5],["guard",1.15],["idle_ready_loop",.5]],
        "guard_variants":[["idle_loop",.3],["guard_brace",1.25],["idle_ready_loop",.25],["guard_raise",1.15],["idle_look_loop",.25],["guard_cross",1.2],["idle_loop",.25],["guard_push",1.1],["idle_loop",.35]],
        "skills":[["idle_loop",.5],["cast",1.25],["idle_relax_loop",.3],["cast_dual",1.45],["idle_relax_loop",.3],["guard_cross",1.20],["idle_look_loop",.3],["channel_overdrive",1.90],["idle_relax_loop",.5]],
        "reference_cast":[["idle_loop",.5],["cast",1.25],["idle_relax_loop",.5]],
        "reference_channel":[["idle_loop",.5],["channel_overdrive",1.90],["idle_ready_loop",.5]],
        "spell_variants":[["cast_arc",1.35],["idle_loop",.2],["cast_release",1.15],["idle_loop",.2],["cast_point",1.20],["idle_loop",.2],["cast_circle",1.40],["idle_loop",.2],["channel",1.65],["idle_loop",.2],["channel_release",1.5],["idle_loop",.2],["channel_gather",1.75],["idle_loop",.2],["channel_pulse",1.6],["idle_loop",.4]],
        "spell_interruptions":[["idle_loop",.25],["cast_dual",.55],["hurt",.32],["idle_angry_loop",.35],["channel_overdrive",.7],["guard",1.15],["idle_loop",.3],["cast_circle",.65],["death",1.7]],
        "reactions":[["idle_loop",.6],["hurt",.32],["idle_angry_loop",1.1],["hurt_counter",.5],["idle_angry_loop",1.1],["death",2.1]],
        "life":[["greeting_wave",1.2],["idle_hand_loop",.7],["victory_wave_loop",2.4],["rest_sleep_loop",1.5],["revive",1.2],["idle_relax_loop",.5]],
        "idle":[["idle_loop",6.0]],
        "interruptions":[["idle_loop",.25],["attack",.64],["hurt",.32],["idle_angry_loop",.3],["attack",.24],["guard_cross",.4],["hurt",.32],["idle_angry_loop",.4]],
    }
    var showcases = {}
    for group in sequences:
        var frames = []
        var first = true
        var prior_clip = ""
        for item in sequences[group]:
            var playing_clip = state.set_animation(item[0],item[0].ends_with("_loop"),0)
            var forced_palm_interrupt = (prior_clip == "attack" or prior_clip.begins_with("guard") or prior_clip.begins_with("cast") or prior_clip.begins_with("channel")) and item[0] != prior_clip and not item[0].begins_with("idle_")
            forced_palm_interrupt = forced_palm_interrupt or item[0].begins_with("guard") or item[0].begins_with("cast") or item[0].begins_with("channel")
            playing_clip.set_mix_duration(0 if first or forced_palm_interrupt else .10)
            first = false
            prior_clip = item[0]
            for i in range(roundi(item[1]*60)):
                sprite.update_skeleton(1.0/60)
                frames.append(capture_pose(skeleton,definition,item[0],min(1.0,playing_clip.get_track_time()/playing_clip.get_animation_end())))
        showcases[group] = frames
    var showcase_file = FileAccess.open(project_root.path_join("work/spine-showcases.json"),FileAccess.WRITE)
    showcase_file.store_string(JSON.stringify(showcases));showcase_file.close()
    var mesh_file = FileAccess.open(project_root.path_join("work/spine-mesh-samples.json"),FileAccess.WRITE)
    mesh_file.store_string(JSON.stringify(poses));mesh_file.close()
    var report = {"native_engine":Engine.get_version_info().string,"spine_data_version":"4.2.43",
        "animation_system":"approved right-facing illustration / same-coordinate body and continuous arm meshes / native curve interpolation",
        "authored_bones":definition.bones.size(),"authored_animations":definition.animations.size(),"painted_slots":definition.slots.size(),
        "sampled_poses":poses.size(),"attack_hand_reach_source_pixels":hand_reaches,"hurt_recoil_source_pixels":hurt_recoil,
        "reference_attack_bone_units":reference_attack_metrics,
        "all_loop_position_seams_pixels":loop_seams,"idle_samples":361,"distinct_idle_poses":distinct.size(),
        "max_interrupted_switch_jump_pixels":max_jump,"prone_death_persists":true,"revive_restores_layers":true,
        "hurt_queues_angry_idle":true,"automatic_process_playback":true,"scene_pause_respected":true,
        "texture_atlas_loaded":true,"native_blended_preview_sequences":showcases.size(),"game_project_started":false,"deployed":false,
        "not_verified":["Full combat scene integration","GPU rendering and in-game FPS"]}
    var report_file = FileAccess.open(project_root.path_join("work/spine-validation.json"),FileAccess.WRITE)
    report_file.store_string(JSON.stringify(report,"  "));report_file.close()
    print("PASS: native Spine layered puppet: 50 clips, large arm motion, short recoil, annoyed recovery, prone death and revive.")
    sprite.free()
    quit()
