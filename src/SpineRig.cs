using System;
using System.IO;
using Godot;

namespace DeepSeekMaid;

internal static class SpineRig
{
    private static Resource _data = null!;
    internal static Texture2D WaterTexture { get; private set; } = null!;
    internal static Texture2D ShieldTexture { get; private set; } = null!;

    internal static void Preload()
    {
        string directory = Path.Combine(Path.GetDirectoryName(typeof(ModEntry).Assembly.Location)!, "animation");
        foreach (string name in new[] { "maid.spine-json", "maid.atlas", "offer-master-v0.8.5.png", "offer-body-v0.8.5.png", "offer-blink-v0.8.5.png", "offer-angry-v0.8.5.png", "offer-prone-v0.8.5.png", "reference-palm-0-v0.8.2.png", "reference-palm-1-v0.8.2.png", "reference-palm-2-v0.8.2.png", "reference-guard-0-v0.8.3.png", "reference-guard-1-v0.8.3.png", "reference-spell-0-v0.8.4.png", "reference-water-v0.8.2.png", "reference-shield-v0.8.3.png" })
            if (!File.Exists(Path.Combine(directory,name))) throw new FileNotFoundException("Missing animation file",name);
        using var waterImage = Image.LoadFromFile(Path.Combine(directory,"reference-water-v0.8.2.png"));
        if (waterImage == null || waterImage.IsEmpty()) throw new InvalidDataException("Cannot load the painted palm water effect.");
        WaterTexture = ImageTexture.CreateFromImage(waterImage);
        using var shieldImage = Image.LoadFromFile(Path.Combine(directory,"reference-shield-v0.8.3.png"));
        if (shieldImage == null || shieldImage.IsEmpty()) throw new InvalidDataException("Cannot load the painted defense shield.");
        ShieldTexture = ImageTexture.CreateFromImage(shieldImage);
        // The installed beta already provides these native classes. No bundled
        // runtime, imported hunter assets, game resource override or PCK is needed.
        var skeleton = NewResource("SpineSkeletonFileResource");
        var atlas = NewResource("SpineAtlasResource");
        _data = NewResource("SpineSkeletonDataResource");
        using Variant skelResult = skeleton.Call("load_from_file", Path.Combine(directory, "maid.spine-json"));
        using Variant atlasResult = atlas.Call("load_from_atlas_file", Path.Combine(directory, "maid.atlas"));
        if (skelResult.AsInt32() != (int)Error.Ok || atlasResult.AsInt32() != (int)Error.Ok)
            throw new InvalidDataException("Cannot load the native Spine rig or atlas.");
        _data.Set("atlas_res", atlas);
        _data.Set("skeleton_file_res", skeleton);
        _data.Set("default_mix", .08f);
        using Variant loaded = _data.Call("is_skeleton_data_loaded");
        if (!loaded.AsBool()) throw new InvalidDataException("Spine 4.2 rejected the DeepSeek animation data.");
        GD.Print("[DeepSeekMaid] Native Spine figure ready: shared palm-up rest pose, 50 connected actions, short hit reaction and temporary annoyance, matching prone defeat.");
    }

    private static Resource NewResource(string name)
    {
        if (!ClassDB.ClassExists(name)) throw new NotSupportedException("Missing native class: " + name);
        using Variant instance = ClassDB.Instantiate(name);
        return (Resource)instance.AsGodotObject();
    }

    internal static Node2D Create(float height, string animation = "idle_loop")
    {
        using Variant instance = ClassDB.Instantiate("SpineSprite");
        var sprite = (Node2D)instance.AsGodotObject();
        sprite.Name = "DeepSeekMaidSpine";
        sprite.TextureFilter = CanvasItem.TextureFilterEnum.Linear;
        sprite.Scale = Vector2.One * (height / 443f);
        sprite.Position = new Vector2(0, height * .01f);
        sprite.Set("skeleton_data_res", _data);
        // Native Process mode follows render delta instead of a low fixed frame rate.
        sprite.Set("update_mode", 0);
        // The sprite is scene-owned. Disposing a MegaSprite binding would free
        // the node itself, rather than merely release a transient wrapper.
        using Variant state = sprite.Call("get_animation_state");
        using Variant entry = state.AsGodotObject().Call("set_animation", animation, true, 0);
        return sprite;
    }
}
