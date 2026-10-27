using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Threading;
using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Hooks;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.CardPools;
using MegaCrit.Sts2.Core.Models.Characters;
using MegaCrit.Sts2.Core.Nodes.Combat;
using MegaCrit.Sts2.Core.Nodes.Cards;
using MegaCrit.Sts2.Core.Nodes.Orbs;
using MegaCrit.Sts2.Core.Nodes.RestSite;
using MegaCrit.Sts2.Core.Nodes.Screens.CharacterSelect;
using MegaCrit.Sts2.Core.Nodes.Screens.Shops;

namespace DeepSeekMaid;

[HarmonyPatch(typeof(CardModel), "get_Portrait")]
internal static class CardPortraitPatch
{
    private static bool Prefix(CardModel __instance, ref Texture2D __result)
    {
        if (!ModEntry.Options.Cards || !Art.TryPortrait(__instance, out Texture2D texture)) return true;
        __result = texture;
        return false;
    }
}

[HarmonyPatch]
internal static class CardDisplayPatch
{
    private static bool _reported;
    internal static IEnumerable<MethodBase> TargetMethods()
    {
        yield return AccessTools.DeclaredMethod(typeof(NCard), "UpdatePortrait", Type.EmptyTypes);
        yield return AccessTools.DeclaredMethod(typeof(NCard), "Reload", Type.EmptyTypes);
        yield return AccessTools.DeclaredMethod(typeof(NCard), nameof(NCard.UpdateVisuals), new[] { typeof(PileType), typeof(CardPreviewMode) });
    }

    [HarmonyPriority(Priority.Last)]
    private static void Postfix(NCard __instance)
    {
        if (!ModEntry.Options.Cards || !__instance.IsNodeReady() || !Art.TryPortrait(__instance.Model, out Texture2D texture)) return;
        TextureRect? portrait = __instance.GetNodeOrNull<TextureRect>("%Portrait");
        if (portrait == null) return;
        if (portrait.Texture != texture) portrait.Texture = texture;
        if (!_reported)
        {
            _reported = true;
            GD.Print($"[DeepSeekMaid] Card UI portrait applied: {__instance.Model!.Id.Entry}; {texture.GetWidth()}x{texture.GetHeight()}.");
        }
    }
}

[HarmonyPatch(typeof(NCreature), nameof(NCreature._Ready))]
internal static class CreatureReadyPatch
{
    private static void Postfix(NCreature __instance) => MaidActor.Get(__instance);
}

[HarmonyPatch(typeof(NCreature), nameof(NCreature.SetAnimationTrigger), typeof(string))]
internal static class AnimationPatch
{
    private static void Postfix(NCreature __instance, string trigger) => MaidActor.Get(__instance)?.Trigger(trigger);
}

[HarmonyPatch(typeof(NCreature), nameof(NCreature.StartReviveAnim))]
internal static class RevivePatch
{
    private static void Postfix(NCreature __instance) => MaidActor.Get(__instance)?.Trigger("Revive");
}

[HarmonyPatch(typeof(NCreature), "OnCombatEnded")]
internal static class VictoryPatch
{
    private static void Postfix(NCreature __instance)
    {
        if (__instance.Entity.IsAlive) MaidActor.Get(__instance)?.Trigger("Victory");
    }
}

[HarmonyPatch(typeof(Hook), nameof(Hook.BeforeCardPlayed), typeof(ICombatState), typeof(CardPlay))]
internal static class CardPlayedPatch
{
    private static void Prefix(CardPlay cardPlay)
    {
        if (cardPlay.Player.Character is not Defect) return;
        MaidActor.Get(cardPlay.Player.Creature.GetCreatureNode())?.Card(cardPlay);
        ThemeVfx.Card(cardPlay);
    }
}

// The context is captured by the original async method's continuations and restored immediately in its caller.
// No returned Task, game wait, damage, target, RNG or command result is replaced.
internal static class VfxScope
{
    internal static readonly AsyncLocal<string?> Current = new();
    internal static string? Enter(CardModel card) => card.Owner?.Character is Defect ? ThemeVfx.Style(card.Id.Entry) : null;
}

[HarmonyPatch(typeof(CardModel), nameof(CardModel.OnPlayWrapper), typeof(PlayerChoiceContext), typeof(Creature), typeof(bool), typeof(ResourceInfo), typeof(bool))]
internal static class CardScopePatch
{
    private static void Prefix(CardModel __instance, out string? __state)
    { __state = VfxScope.Current.Value; VfxScope.Current.Value = VfxScope.Enter(__instance); }
    private static void Postfix(string? __state) => VfxScope.Current.Value = __state;
    private static Exception? Finalizer(Exception? __exception, string? __state)
    { VfxScope.Current.Value = __state; return __exception; }
}

[HarmonyPatch(typeof(VfxCmd), nameof(VfxCmd.PlayVfx), typeof(Vector2), typeof(string), typeof(Control))]
internal static class HitVfxPatch
{
    private static bool Prefix(Vector2 position, string path, Control? vfxContainer)
    {
        if (!ModEntry.Options.Effects || VfxScope.Current.Value is not string style) return true;
        // These are the common native hit/heal/block effects. UI, card movement and text remain native.
        string p = path.ToLowerInvariant();
        if (!new[] { "attack_", "impact", "scratch", "slash", "vfx_block", "cross_heal", "rock_shatter", "vfx_chain" }.Any(p.Contains)) return true;
        return !ThemeVfx.Pulse(position, style, p.Contains("block"), vfxContainer);
    }
}

[HarmonyPatch(typeof(CharacterModel), "get_IconTexture")]
internal static class CharacterIconPatch
{
    private static bool Prefix(CharacterModel __instance, ref Texture2D __result)
    {
        if (!ModEntry.Options.Menus || __instance is not Defect) return true;
        __result = Art.Icon; return false;
    }
}

[HarmonyPatch(typeof(CharacterModel), "get_IconOutlineTexture")]
internal static class CharacterOutlinePatch
{
    private static bool Prefix(CharacterModel __instance, ref Texture2D __result)
    {
        if (!ModEntry.Options.Menus || __instance is not Defect) return true;
        __result = Art.Icon; return false;
    }
}

[HarmonyPatch]
internal static class SelectButtonPatch
{
    internal static IEnumerable<MethodBase> TargetMethods()
    {
        foreach (string name in new[] { "Init", "LockForAnimation", "DebugUnlock", "UnlockIfPossible", "_Process" })
            yield return AccessTools.DeclaredMethod(typeof(NCharacterSelectButton), name);
    }
    private static void Postfix(NCharacterSelectButton __instance)
    {
        if (!ModEntry.Options.Menus || __instance.Character is not Defect) return;
        var icon = __instance.GetNodeOrNull<TextureRect>("%Icon");
        if (icon != null) icon.Texture = Art.SelectIcon;
        var add = __instance.GetNodeOrNull<TextureRect>("%IconAdd");
        if (add != null) add.Texture = Art.SelectIcon;
    }
}

[HarmonyPatch]
internal static class SelectBackgroundPatch
{
    internal static IEnumerable<MethodBase> TargetMethods()
    {
        yield return AccessTools.DeclaredMethod(typeof(NCharacterSelectScreen), nameof(NCharacterSelectScreen.SelectCharacter), new[] { typeof(NCharacterSelectButton), typeof(CharacterModel) });
        yield return AccessTools.DeclaredMethod(typeof(NCharacterSelectScreen), "OnLocalCharacterChangedForRandom", new[] { typeof(CharacterModel) });
    }

    private static void Postfix(NCharacterSelectScreen __instance, CharacterModel characterModel)
    {
        if (!ModEntry.Options.Menus || characterModel is not Defect) return;
        Node? bg = __instance.GetNodeOrNull("AnimatedBg")?.GetChildren().FirstOrDefault(n => n.Name.ToString().Equals("DEFECT_bg", StringComparison.OrdinalIgnoreCase));
        if (bg == null) return;
        foreach (Node node in Descendants(bg))
            if (node is CanvasItem canvas && (node.GetClass() == "SpineSprite" ||
                (ModEntry.Options.SelectionBackground && (node.GetClass() == "CPUParticles2D" || node.GetClass() == "GPUParticles2D")))) canvas.Visible = false;
        if (ModEntry.Options.SelectionBackground && bg.GetNodeOrNull("DeepSeekSelectionBackdrop") == null)
            AddBackdrop(bg);
        if (bg.GetNodeOrNull("DeepSeekMaidSelection") != null) return;
        var sprite = Art.Selection(920);
        // The native background is a 2560x1200 canvas anchored around the viewport center.
        sprite.Position = new Vector2(1230, 535);
        bg.AddChild(sprite);
        Tween idle = sprite.CreateTween().SetLoops();
        idle.TweenProperty(sprite, "position:y", 529f, 1.6).SetTrans(Tween.TransitionType.Sine).SetEase(Tween.EaseType.InOut);
        idle.TweenProperty(sprite, "position:y", 535f, 1.6).SetTrans(Tween.TransitionType.Sine).SetEase(Tween.EaseType.InOut);
    }

    private static void AddBackdrop(Node parent)
    {
        var backdrop = new TextureRect {
            Name = "DeepSeekSelectionBackdrop", Texture = Art.SelectBackground, MouseFilter = Control.MouseFilterEnum.Ignore,
            ExpandMode = TextureRect.ExpandModeEnum.IgnoreSize, StretchMode = TextureRect.StretchModeEnum.KeepAspectCovered,
            TextureFilter = CanvasItem.TextureFilterEnum.LinearWithMipmaps
        };
        parent.AddChild(backdrop);
        backdrop.SetAnchorsAndOffsetsPreset(Control.LayoutPreset.FullRect);
        parent.MoveChild(backdrop, 0);
        // Protect native character descriptions and stats from a bright environment painting.
        var gradient = new Gradient {
            Offsets = new[] { 0f, .28f, .55f, 1f },
            Colors = new[] { new Color(.015f,.035f,.08f,.78f), new Color(.015f,.035f,.08f,.5f), new Color(0,0,0,.04f), Colors.Transparent }
        };
        var shade = new TextureRect {
            Name = "DeepSeekTextShade", Texture = new GradientTexture1D { Gradient = gradient, Width = 512 },
            MouseFilter = Control.MouseFilterEnum.Ignore, ExpandMode = TextureRect.ExpandModeEnum.IgnoreSize,
            StretchMode = TextureRect.StretchModeEnum.Scale
        };
        parent.AddChild(shade);
        shade.SetAnchorsAndOffsetsPreset(Control.LayoutPreset.FullRect);
        parent.MoveChild(shade, 1);
    }
    internal static IEnumerable<Node> Descendants(Node parent)
    {
        foreach (Node child in parent.GetChildren())
        { yield return child; foreach (Node sub in Descendants(child)) yield return sub; }
    }
}

[HarmonyPatch(typeof(NMerchantCharacter), nameof(NMerchantCharacter._Ready))]
internal static class MerchantPatch
{
    private static void Postfix(NMerchantCharacter __instance)
    {
        if (!ModEntry.Options.Character || !__instance.Name.ToString().Contains("Defect", StringComparison.OrdinalIgnoreCase)) return;
        foreach (Node child in __instance.GetChildren())
            if (child.GetClass() == "SpineSprite" && child is CanvasItem canvas) canvas.Visible = false;
        __instance.AddChild(SpineRig.Create(300, "idle_look_loop"));
    }
}

[HarmonyPatch(typeof(NRestSiteCharacter), nameof(NRestSiteCharacter._Ready))]
internal static class RestSitePatch
{
    private static int _rests;
    private static void Postfix(NRestSiteCharacter __instance)
    {
        if (!ModEntry.Options.Character || __instance.Player.Character is not Defect) return;
        foreach (Node child in __instance.GetChildren())
            if (child.GetClass() == "SpineSprite" && child is CanvasItem canvas) canvas.Visible = false;
        var sprite = SpineRig.Create(560, AnimationSelector.Rest(_rests++ % 2 != 0));
        sprite.Position = new Vector2(0, -35);
        __instance.AddChild(sprite);
    }
}

[HarmonyPatch(typeof(NOrb), nameof(NOrb.UpdateVisuals), typeof(bool))]
internal static class OrbPatch
{
    private static void Postfix(NOrb __instance, bool isEvoking)
    {
        if (!ModEntry.Options.Orbs || !__instance.IsNodeReady() || __instance.Model is not { IsMutable: true } model
            || model.Owner?.Character is not Defect) return;
        var native = (Node2D?)AccessTools.Field(typeof(NOrb), "_sprite").GetValue(__instance);
        if (native == null || !GodotObject.IsInstanceValid(native)) return;
        if (native.GetNodeOrNull("DeepSeekOrbCartoon") is Node2D existing)
        { existing.Scale = Vector2.One * (isEvoking ? 1.13f : 1f); return; }
        Node2D? spine = native.GetNodeOrNull<Node2D>("SpineSkeleton");
        if (spine != null) spine.Visible = false;
        Node2D cartoon = ThemeVfx.Orb(ThemeVfx.Style(model.Id.Entry));
        native.AddChild(cartoon);
        Tween idle = cartoon.CreateTween().SetLoops();
        idle.TweenProperty(cartoon, "position:y", -2f, 1.1).SetTrans(Tween.TransitionType.Sine).SetEase(Tween.EaseType.InOut);
        idle.TweenProperty(cartoon, "position:y", 1f, 1.1).SetTrans(Tween.TransitionType.Sine).SetEase(Tween.EaseType.InOut);
    }
}

public static class Compatibility
{
    // Pure metadata checks: safe to run outside Godot. Does not install patches or start the game.
    public static string[] CheckBindings()
    {
        var missing = new List<string>();
        foreach (Type type in typeof(ModEntry).Assembly.GetTypes().Where(t => t.Name.EndsWith("Patch", StringComparison.Ordinal)))
        {
            var target = type.GetMethod("TargetMethods", BindingFlags.Static | BindingFlags.NonPublic | BindingFlags.Public);
            if (target != null)
            {
                foreach (MethodBase? method in (IEnumerable<MethodBase>)target.Invoke(null, null)!)
                    if (method == null) missing.Add(type.Name + ": missing target");
                continue;
            }
            var patch = type.GetCustomAttributes<HarmonyPatch>().FirstOrDefault(a => a.info.declaringType != null);
            if (patch == null) continue;
            MethodInfo? found = AccessTools.Method(patch.info.declaringType, patch.info.methodName, patch.info.argumentTypes);
            if (found == null) missing.Add(type.Name + ": " + patch.info.methodName);
        }
        if (AccessTools.Field(typeof(NOrb), "_sprite") == null) missing.Add("NOrb._sprite");
        return missing.ToArray();
    }
}
