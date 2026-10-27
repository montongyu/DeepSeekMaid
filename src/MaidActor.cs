using System;
using System.Runtime.CompilerServices;
using Godot;
using MegaCrit.Sts2.Core.Bindings.MegaSpine;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Models.Characters;
using MegaCrit.Sts2.Core.Nodes.Combat;

namespace DeepSeekMaid;

internal sealed class MaidActor
{
    private static readonly ConditionalWeakTable<NCreature, MaidActor> Actors = new();
    private readonly Node2D _sprite;
    private readonly MegaAnimationState _state;
    private readonly AnimationSelector _choices = new();
    private Node2D? _anger;
    private Node2D? _handEffect;
    private bool _dead, _victory, _guard;

    private MaidActor(NCreature owner)
    {
        _sprite = SpineRig.Create(ModEntry.Options.SpriteHeight);
        owner.Visuals.AddChild(_sprite);
        var binding = new MegaSprite(_sprite);
        _state = binding.GetAnimationState();
        // Keep the original skeleton and waits for game logic, hitboxes and events.
        // Only the visible character is driven by the independent cosmetic rig.
        owner.Visuals.Body.Visible = false;
        owner.TreeExiting += Stop;
        if (owner.Entity.IsDead) Trigger("Dead");
        else _state.SetAnimation("idle_loop",true);
    }

    internal static MaidActor? Get(NCreature? creature)
    {
        if (!ModEntry.Options.Character || creature == null || !GodotObject.IsInstanceValid(creature)
            || !creature.IsNodeReady() || creature.Entity.Player?.Character is not Defect) return null;
        return Actors.GetValue(creature, n => new MaidActor(n));
    }

    private void Stop()
    {
        ClearHandEffect();
        ClearAnger();
        // Dispose transient Spine wrappers on the scene thread, as the beta does.
        _state.Dispose();
    }

    internal void Card(CardPlay play)
    {
        _guard = play.Card.GainsBlock;
        string animation = play.Card.Type == CardType.Attack ? _choices.Attack(play.Card.GetType().Name)
            : _choices.Skill(_guard, play.Card.Type == CardType.Power);
        if (!_dead && !_victory) Action(animation, true);
    }

    internal void Trigger(string trigger)
    {
        if (!GodotObject.IsInstanceValid(_sprite) || !_sprite.IsInsideTree()) return;
        if (trigger == "Revive")
        {
            ClearHandEffect();
            _dead = _victory = false;
            ClearAnger();
            Play("revive");
            _state.AddAnimation("idle_relax_loop", 0, true);
            return;
        }
        if (_dead || _victory) return;
        // The native Spine queue owns action completion; idle notifications must
        // not cut short an attack or rewind the ongoing idle phase.
        if (trigger == "Idle") return;
        if (trigger is "Relaxed" or "Victory")
        {
            ClearHandEffect();
            _victory = true;
            ClearAnger();
            Play(AnimationSelector.Victory(),true);
            return;
        }
        switch (trigger)
        {
            case "Greet": Action(AnimationSelector.Greeting(),true); break;
            case "Attack": Action("attack"); break;
            case "Cast": Action(_guard ? "guard" : "cast"); break;
            case "PowerUp": Action("channel"); break;
            case "Hit":
                Action(_choices.Hurt(), true);
                ClearAnger();
                _anger = ThemeVfx.Anger(_sprite);
                break;
            case "Dead": _dead = true; ClearAnger(); ClearHandEffect(); Play("death"); break;
        }
    }

    private void ClearAnger()
    {
        if (_anger != null && GodotObject.IsInstanceValid(_anger)) _anger.QueueFree();
        _anger = null;
    }

    private void ClearHandEffect()
    {
        if (_handEffect != null && GodotObject.IsInstanceValid(_handEffect)) _handEffect.QueueFree();
        _handEffect = null;
    }

    private void Play(string name, bool loop = false)
    {
        // One shared set of attachment slots permits an ordinary short native
        // mix, including interrupted actions, without two fading characters.
        _state.SetAnimation(name,loop);
    }

    private void Action(string name, bool force = false)
    {
        // Card and native hooks can report the same action. A new card may restart
        // it, while the duplicate native event leaves interpolation uninterrupted.
        string? current = _state.GetCurrentAnimationName();
        if (!force && current != null && AnimationSelector.Family(current) == AnimationSelector.Family(name)) return;
        ClearHandEffect();
        bool hurt = AnimationSelector.Family(name) == "hurt";
        if (!hurt) ClearAnger();
        Play(name);
        _state.AddAnimation(AnimationSelector.IdleAfter(name),0,!hurt);
        if (hurt) _state.AddAnimation("idle_loop",0,true);
        if (name is "attack" or "attack_palm" or "attack_ranged" or "attack_jab" or "attack_cross")
            _handEffect = ThemeVfx.HandPulse(_sprite, name == "attack_jab" ? .28 : name == "attack" ? .34 : .36, name == "attack");
        else if (AnimationSelector.Family(name) == "guard")
            _handEffect = ThemeVfx.DefenseShield(_sprite,name == "guard_brace" ? 1.25 : name == "guard_cross" ? 1.20 : name == "guard_push" ? 1.10 : 1.15);
        else if (AnimationSelector.Family(name) is "cast" or "channel")
        {
            using MegaTrackEntry? entry = _state.GetCurrent(0);
            _handEffect = ThemeVfx.SpellWeave(_sprite,entry?.GetAnimationEnd() ?? 1.25f,
                AnimationSelector.Family(name) == "channel",name is "cast_circle" or "channel" or "channel_gather" or "channel_pulse");
        }
    }
}

