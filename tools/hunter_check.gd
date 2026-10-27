extends SceneTree

func _initialize():
    call_deferred("_run")

func _run():
    var pack = "C:/game/steamapps/workshop/content/2868840/3787753911/LieRenTVmod.pck"
    if not ProjectSettings.load_resource_pack(pack,false):
        push_error("Cannot mount installed hunter mod read-only")
        quit(1)
        return
    var source = load("res://.godot/imported/silent.skel-6e16eb58aa55af660d5a669d7ed3f2fe.spskel")
    var atlas = load("res://.godot/imported/silent.atlas-37058586efd562ee4ef348a9b0ee2e44.spatlas")
    if source == null or atlas == null:
        quit(1)
        return
    var data = ClassDB.instantiate("SpineSkeletonDataResource")
    data.set_atlas_res(atlas)
    data.set_skeleton_file_res(source)
    if not data.is_skeleton_data_loaded():
        quit(1)
        return
    var animations = []
    for animation in data.get_animations():
        animations.append({"name":animation.get_name(),"duration":animation.get_duration()})
    var bones = []
    for bone in data.get_bones():
        bones.append(bone.get_bone_name())
    print("Hunter animations: ",animations)
    print("Hunter bone count: ",bones.size())
    var relevant = []
    for slot in data.get_slots():
        var slot_name = slot.get_name()
        if "臂" in slot_name or "手" in slot_name or "身体" in slot_name:
            relevant.append({"slot":slot_name,"bone":slot.get_bone_data().get_bone_name()})
    print("Hunter hand and torso bindings: ",relevant)
    var sprite = ClassDB.instantiate("SpineSprite")
    sprite.set_skeleton_data_res(data)
    sprite.set_update_mode(2)
    get_root().add_child(sprite)
    var state = sprite.get_animation_state()
    var skeleton = sprite.get_skeleton()
    var metrics = {}
    var height = max(1.0,abs(data.get_height()))
    for clip in ["attack","cast","hurt","idle_loop","relaxed_loop","shiv"]:
        var track = state.set_animation(clip,false,0)
        track.set_mix_duration(0)
        var measured = {}
        for bone_name in ["bone18","bone19","bone20","bone21","bone22","bone23","bone31","bone32","bone90"]:
            var moving = skeleton.find_bone(bone_name)
            var positions = []
            var rotations = []
            for frame in range(121):
                track.set_track_time(track.get_animation_end()*frame/120.0)
                sprite.update_skeleton(0.0)
                var anchor = skeleton.find_bone("root")
                positions.append(Vector2(moving.get_world_x()-anchor.get_world_x(),moving.get_world_y()-anchor.get_world_y()))
                rotations.append(moving.get_rotation())
            var reach = 0.0
            var peak = 0
            var max_speed = 0.0
            var speed_phase = 0
            for index in range(121):
                var distance = positions[index].distance_to(positions[0])
                if distance>reach:
                    reach=distance
                    peak=index
                if index>0:
                    var speed=positions[index].distance_to(positions[index-1])
                    if speed>max_speed:
                        max_speed=speed
                        speed_phase=index
            measured[bone_name]={"reach_in_character_heights":reach/height,"max_reach_phase":peak/120.0,"max_speed_phase":speed_phase/120.0,"rotation_range_degrees":rotations.max()-rotations.min()}
        metrics[clip]={"duration":track.get_animation_end(),"bones":measured}
    var report={"workshop_id":"3787753911","manifest":"LieRenTVmod","spine_version":data.get_version(),"bone_count":bones.size(),"height":height,"animations":animations,"hand_bindings":relevant,"motion_metrics":metrics,"source_modified":false,"assets_copied":false}
    var output=FileAccess.open(OS.get_cmdline_user_args()[0].path_join("work/hunter-motion-inspection.json"),FileAccess.WRITE)
    output.store_string(JSON.stringify(report,"  "))
    output.close()
    sprite.free()
    print("PASS: hunter inspection measured timing and hand motion read-only; no source assets were copied.")
    quit()
