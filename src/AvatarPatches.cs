using System;
using System.Runtime.CompilerServices;
using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Characters;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Runs;
using RunPortrait = MegaCrit.sts2.Core.Nodes.TopBar.NTopBarPortrait;

namespace DeepSeekMaid;

internal static class AvatarSkin
{
    private static readonly ConditionalWeakTable<RunPortrait, object> Watched = new();
    private static bool _reported;

    internal static void Replace(Control icon)
    {
        if (icon is not TextureRect image) return;
        image.Texture = Art.Icon;
        image.TextureFilter = CanvasItem.TextureFilterEnum.Linear;
        if (!_reported)
        {
            _reported = true;
            GD.Print("[DeepSeekMaid] Run avatar scene replaced with DeepSeek portrait (85x85).");
        }
    }

    internal static void Watch(RunPortrait portrait)
    {
        Watched.GetValue(portrait, node => {
            // AddChildSafely may defer attachment. Handle the scene when it actually enters the top bar.
            node.ChildEnteredTree += child => {
                if (child is Control icon && child.Name.ToString().StartsWith("DefectIcon", StringComparison.OrdinalIgnoreCase)) Replace(icon);
            };
            return new object();
        });
        foreach (Node child in portrait.GetChildren())
            if (child is Control icon && child.Name.ToString().StartsWith("DefectIcon", StringComparison.OrdinalIgnoreCase)) Replace(icon);
    }
}

// The run HUD instantiates CharacterModel.Icon (a scene), rather than requesting IconTexture.
[HarmonyPatch(typeof(CharacterModel), "get_Icon")]
internal static class CharacterIconScenePatch
{
    [HarmonyPriority(Priority.Last)]
    private static void Postfix(CharacterModel __instance, Control __result)
    {
        if (ModEntry.Options.Menus && __instance is Defect) AvatarSkin.Replace(__result);
    }
}

[HarmonyPatch(typeof(RunPortrait), nameof(RunPortrait.Initialize), typeof(Player))]
internal static class TopBarPortraitPatch
{
    [HarmonyPriority(Priority.Last)]
    private static void Postfix(RunPortrait __instance, Player player)
    {
        if (ModEntry.Options.Menus && player.Character is Defect) AvatarSkin.Watch(__instance);
    }
}

[HarmonyPatch(typeof(NTopBar), nameof(NTopBar.Initialize), typeof(IRunState))]
internal static class TopBarAvatarPatch
{
    [HarmonyPriority(Priority.Last)]
    private static void Postfix(NTopBar __instance, IRunState runState)
    {
        if (ModEntry.Options.Menus && LocalContext.GetMe(runState)?.Character is Defect) AvatarSkin.Watch(__instance.Portrait);
    }
}
