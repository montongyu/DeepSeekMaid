using System;
using System.IO;
using System.Reflection;
using System.Text.Json;
using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.Modding;
using MegaCrit.Sts2.Core.Models;

namespace DeepSeekMaid;

[ModInitializer(nameof(Initialize))]
public static class ModEntry
{
    public const string TestedVersion = "v0.111.0";
    private static bool _initialized;
    internal static Settings Options { get; private set; } = new();

    public static void Initialize()
    {
        if (_initialized) return;
        _initialized = true;
        try
        {
            Options = Settings.Load();
            string data = Path.GetDirectoryName(typeof(CardModel).Assembly.Location)!;
            string release = Path.Combine(data, "..", "release_info.json");
            using var doc = JsonDocument.Parse(File.ReadAllText(release));
            string actual = doc.RootElement.GetProperty("version").GetString() ?? "unknown";
            if (Options.StrictVersion && actual != TestedVersion)
            {
                GD.PushWarning($"[DeepSeekMaid] Disabled: built for {TestedVersion}, found {actual}. Rebuild for this beta first.");
                return;
            }
            string[] missing = Compatibility.CheckBindings();
            if (missing.Length != 0)
                throw new MissingMethodException(string.Join("; ", missing));
            // Load and validate every embedded asset before installing any patches.
            Art.Preload();
            if (Options.Character) SpineRig.Preload();
            var harmony = new Harmony("local.deepseekmaid.cosmetics");
            try { harmony.PatchAll(typeof(ModEntry).Assembly); }
            catch { harmony.UnpatchAll(harmony.Id); throw; }
            GD.Print($"[DeepSeekMaid] Ready on {actual}: {Art.CardCount} portraits, native Spine mesh animation. Cosmetic only.");
        }
        catch (Exception e)
        {
            GD.PushError($"[DeepSeekMaid] Initialization skipped: {e}");
        }
    }
}

internal sealed class Settings
{
    internal bool Character = true, Cards = true, Effects = true, Orbs = true, Menus = true, StrictVersion = true, SelectionBackground = true;
    internal float SpriteHeight = 300f, Intensity = .65f;
    internal int MaxEffects = 24, Particles = 6;

    internal static Settings Load()
    {
        var result = new Settings();
        var cfg = new ConfigFile();
        string path = Path.Combine(Path.GetDirectoryName(typeof(ModEntry).Assembly.Location)!, "DeepSeekMaid.cfg");
        if (cfg.Load(path) != Error.Ok) return result;
        result.Character = cfg.GetValue("visuals", "character", true).AsBool();
        result.Cards = cfg.GetValue("visuals", "cards", true).AsBool();
        result.Effects = cfg.GetValue("visuals", "effects", true).AsBool();
        result.Orbs = cfg.GetValue("visuals", "orbs", true).AsBool();
        result.Menus = cfg.GetValue("visuals", "menus", true).AsBool();
        result.SelectionBackground = cfg.GetValue("visuals", "selection_background", true).AsBool();
        result.StrictVersion = cfg.GetValue("compatibility", "strict_version", true).AsBool();
        result.SpriteHeight = Mathf.Clamp((float)cfg.GetValue("visuals", "sprite_height", 300f).AsDouble(), 160f, 380f);
        result.Intensity = Mathf.Clamp((float)cfg.GetValue("visuals", "effect_intensity", .65f).AsDouble(), 0f, 1.5f);
        result.MaxEffects = Mathf.Clamp(cfg.GetValue("visuals", "max_effects", 24).AsInt32(), 8, 48);
        result.Particles = Mathf.Clamp(cfg.GetValue("visuals", "particles_per_impact", 6).AsInt32(), 0, 12);
        return result;
    }
}
