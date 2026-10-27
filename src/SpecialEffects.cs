using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Characters;
using MegaCrit.Sts2.Core.Models.Orbs;
using MegaCrit.Sts2.Core.Nodes.Vfx;

namespace DeepSeekMaid;

[HarmonyPatch]
internal static class SpecialEffectPatch
{
    private static readonly ConditionalWeakTable<Node2D, Replacement> Replacements = new();
    internal static IEnumerable<MethodBase> TargetMethods()
    {
        // Audited native effect factories used by this beta's Defect cards, plus the beam's child impact.
        // Each overload is deliberately included: creature overloads delegate to position overloads.
        foreach (Type type in new[] { typeof(NFireBurningVfx), typeof(NHyperbeamImpactVfx), typeof(NHyperbeamVfx),
            typeof(NLargeMagicMissileVfx), typeof(NScratchVfx), typeof(NSweepingBeamVfx), typeof(NSweepingBeamImpactVfx) })
            foreach (MethodInfo method in type.GetMethods(BindingFlags.Public | BindingFlags.Static | BindingFlags.DeclaredOnly)
                .Where(m => m.Name == "Create" && typeof(Node2D).IsAssignableFrom(m.ReturnType)))
                yield return method;
    }

    private static void Postfix(Node2D? __result, object[] __args, MethodBase __originalMethod)
    {
        if (!ModEntry.Options.Effects || __result == null || VfxScope.Current.Value is not string style) return;
        Replacement replacement = Replacements.GetValue(__result, node => new Replacement(node));
        replacement.Style = style;
        replacement.Arguments = __args;
        replacement.Kind = __originalMethod.DeclaringType!.Name;
        if (__result.IsNodeReady()) replacement.Draw();
    }

    private sealed class Replacement
    {
        private readonly Node2D _native;
        private bool _drawn;
        internal string Style = "data", Kind = "";
        internal object[] Arguments = Array.Empty<object>();
        internal Replacement(Node2D native)
        {
            _native = native;
            // Factories delegate to other overloads. Wait until the outer factory supplied its complete target list.
            native.Ready += Draw;
        }
        internal void Draw()
        {
            if (_drawn || !GodotObject.IsInstanceValid(_native) || !_native.IsInsideTree()) return;
            _drawn = true;
            try
            {
                var creatures = Arguments.OfType<Creature>().ToArray();
                var positions = Arguments.OfType<Vector2>().ToArray();
                Vector2 origin = creatures.FirstOrDefault()?.GetCreatureNode()?.VfxSpawnPosition
                    ?? (positions.Length > 0 ? positions[0] : _native.GlobalPosition);
                var targetPositions = Arguments.OfType<IEnumerable<Creature>>().SelectMany(list => list)
                    .Select(c => c.GetCreatureNode()).Where(n => n != null).Select(n => n!.VfxSpawnPosition).ToList();
                targetPositions.AddRange(Arguments.OfType<IEnumerable<Vector2>>().SelectMany(list => list));
                if (targetPositions.Count == 0 && creatures.Length > 1 && creatures[^1].GetCreatureNode() is { } node)
                    targetPositions.Add(node.VfxSpawnPosition);
                if (targetPositions.Count == 0 && positions.Length > 1) targetPositions.Add(positions[^1]);
                bool isBeam = Kind is "NHyperbeamVfx" or "NSweepingBeamVfx";
                bool isImpact = Kind.Contains("Impact", StringComparison.Ordinal) || Kind is "NScratchVfx" or "NFireBurningVfx";
                bool rendered = false;
                if (targetPositions.Count > 0 && !isImpact)
                {
                    if (creatures.FirstOrDefault()?.Player?.Character is Defect) origin += new Vector2(65, 25);
                    for (int i = 0; i < targetPositions.Count; ++i)
                    {
                        float delay = Kind == "NHyperbeamVfx" ? NHyperbeamVfx.hyperbeamAnticipationDuration
                            : Kind == "NSweepingBeamVfx" ? i * .55f / targetPositions.Count : 0;
                        rendered |= ThemeVfx.Stream(origin, targetPositions[i], Style, beam: isBeam, delay: delay);
                    }
                }
                else rendered = ThemeVfx.Pulse(targetPositions.LastOrDefault(origin), Style);
                // Preserve native waits/signals/cleanup. Fall back to its drawing if no replacement could spawn.
                if (rendered) _native.Modulate = new Color(1,1,1,0);
            }
            catch (Exception e) { GD.PushWarning($"[DeepSeekMaid] Native effect preserved after replacement error: {e.Message}"); }
        }
    }
}

[HarmonyPatch]
internal static class OrbEffectScopePatch
{
    internal static IEnumerable<MethodBase> TargetMethods()
    {
        var targets = new HashSet<MethodBase>();
        targets.Add(AccessTools.DeclaredMethod(typeof(OrbModel), nameof(OrbModel.TriggerPassive), new[] { typeof(PlayerChoiceContext), typeof(Creature) }));
        foreach (Type type in new[] { typeof(LightningOrb), typeof(FrostOrb), typeof(DarkOrb), typeof(PlasmaOrb), typeof(GlassOrb) })
        {
            targets.Add(AccessTools.Method(type, nameof(OrbModel.Evoke), new[] { typeof(PlayerChoiceContext) }));
            targets.Add(AccessTools.Method(type, nameof(OrbModel.Passive), new[] { typeof(PlayerChoiceContext), typeof(Creature) }));
        }
        return targets;
    }
    private static void Prefix(OrbModel __instance, out string? __state)
    {
        __state = VfxScope.Current.Value;
        VfxScope.Current.Value = __instance.IsMutable && __instance.Owner?.Character is Defect
            ? ThemeVfx.Style(__instance.Id.Entry) : null;
    }
    private static void Postfix(string? __state) => VfxScope.Current.Value = __state;
    private static Exception? Finalizer(Exception? __exception, string? __state)
    { VfxScope.Current.Value = __state; return __exception; }
}
