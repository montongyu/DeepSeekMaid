using System;

namespace DeepSeekMaid;

// Cosmetic, per-instance sequencing. It never consumes the game's RNG stream.
internal sealed class AnimationSelector
{
    private static readonly string[] Families = { "attack", "cast", "guard", "channel", "hurt" };
    private static readonly string[] Attacks = { "attack", "attack_jab", "attack_cross", "attack_sweep", "attack_uppercut", "attack_double", "attack_triple", "attack_ranged", "attack_palm", "attack_overhead" };
    private static readonly string[] Casts = { "cast", "cast_arc", "cast_release", "cast_dual", "cast_point", "cast_circle" };
    private static readonly string[] Guards = { "guard", "guard_brace", "guard_raise", "guard_cross", "guard_push" };
    private static readonly string[] Powers = { "channel", "channel_release", "channel_gather", "channel_pulse", "channel_overdrive" };
    private static readonly string[] Hits = { "hurt", "hurt_recover", "hurt_recoil", "hurt_stagger", "hurt_counter" };
    private static readonly string[] Greetings = { "greeting", "greeting_wave", "greeting_bow" };
    private static readonly string[] Victories = { "victory_loop", "victory_wave_loop", "victory_pose_loop" };
    private static int _entries, _victories;
    private int _attacks, _casts, _guards, _powers, _hits;

    internal string Attack(string nativeName)
    {
        if (nativeName.Equals("StrikeDefect", StringComparison.OrdinalIgnoreCase)) return "attack";
        int variation = _attacks++ % Attacks.Length;
        if (nativeName.Contains("beam", StringComparison.OrdinalIgnoreCase)
            || nativeName.Contains("cannon", StringComparison.OrdinalIgnoreCase)) return variation % 2 == 0 ? "attack_ranged" : "attack_palm";
        if (nativeName.Contains("meteor", StringComparison.OrdinalIgnoreCase)) return "attack_overhead";
        if (nativeName.Contains("barrage", StringComparison.OrdinalIgnoreCase)) return variation % 2 == 0 ? "attack_double" : "attack_triple";
        if (nativeName.Contains("claw", StringComparison.OrdinalIgnoreCase)
            || nativeName.Contains("sweep", StringComparison.OrdinalIgnoreCase)) return variation % 2 == 0 ? "attack_sweep" : "attack_uppercut";
        return Attacks[variation];
    }

    internal string Skill(bool gainsBlock, bool power)
    {
        if (power) return Powers[_powers++ % Powers.Length];
        if (gainsBlock) return Guards[_guards++ % Guards.Length];
        return Casts[_casts++ % Casts.Length];
    }

    internal string Hurt() => Hits[_hits++ % Hits.Length];
    internal static string Greeting() => Greetings[_entries++ % Greetings.Length];
    internal static string Victory() => Victories[_victories++ % Victories.Length];
    internal static string Rest(bool sleepy) => sleepy ? "rest_sleep_loop" : "meditate_loop";

    internal static string Family(string name)
    {
        foreach (string family in Families)
            if (name.Equals(family, StringComparison.Ordinal) || name.StartsWith(family + "_", StringComparison.Ordinal)) return family;
        return name;
    }

    internal static string IdleAfter(string animation)
    {
        if (Family(animation) == "hurt") return "idle_angry_loop";
        return animation switch {
            "attack_ranged" or "cast" or "channel_pulse" => "idle_breathe_loop",
            "attack_palm" or "attack_jab" or "cast_dual" => "idle_hand_loop",
            "attack_sweep" or "cast_circle" => "idle_tail_loop",
            "cast_arc" or "channel_gather" => "idle_hair_loop",
            "cast_point" or "guard_raise" or "greeting_wave" => "idle_look_loop",
            "greeting" or "revive" => "idle_loop",
            _ => Family(animation) is "attack" or "guard" ? "idle_ready_loop" : "idle_relax_loop"
        };
    }
}
