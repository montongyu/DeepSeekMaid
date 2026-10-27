using System;
using System.Collections.Generic;
using Godot;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Nodes.Rooms;

namespace DeepSeekMaid;

internal static class ThemeVfx
{
    private static int _active;
    private static readonly Dictionary<string, string> Styles = new(StringComparer.Ordinal);
    private static readonly Dictionary<(int, int, string, bool), ulong> RecentImpacts = new();
    private static readonly Vector2[] Circle = CirclePoints(40), Hexagon = CirclePoints(6);
    private static readonly string[][] Keywords = {
        new[] { "frost", "ice", "cold", "chill", "glacier", "hail", "coolant", "coolheaded" },
        new[] { "dark", "shadow", "null", "consume" }, new[] { "plasma", "fusion", "meteor", "ignition", "energy" },
        new[] { "glass", "refract", "shatter" }, new[] { "lightning", "zap", "thunder", "storm", "tesla", "voltaic" }
    };
    private static readonly string[] StyleNames = { "frost", "dark", "plasma", "glass", "lightning" };

    internal static string Style(string id)
    {
        if (Styles.TryGetValue(id, out string? found)) return found;
        string normalized = id.ToLowerInvariant();
        for (int i = 0; i < Keywords.Length; ++i)
            foreach (string keyword in Keywords[i])
                if (normalized.Contains(keyword, StringComparison.Ordinal)) return Styles[id] = StyleNames[i];
        return Styles[id] = "data";
    }
    internal static Color ColorFor(string style) => style switch {
        "frost" => new Color("c0efff"), "dark" => new Color("ad8aef"), "plasma" => new Color("ffd17c"),
        "glass" => new Color("99eadb"), "lightning" => new Color("80d8ff"), _ => new Color("67bfff")
    };
    internal static Node2D Orb(string style)
    {
        var root = new Node2D { Name = "DeepSeekOrbCartoon" };
        root.AddChild(Glyph(style, 78));
        return root;
    }
    internal static Node2D? HandPulse(Node2D owner, double delay, bool reference = false)
    {
        if (!ModEntry.Options.Effects || ModEntry.Options.Intensity <= 0) return null;
        if (reference) return ReferencePalmWater(owner,delay);
        var root = new Node2D { Name = "DeepSeekPalmRipple", ZIndex = 14, Visible = false };
        owner.AddChild(root);
        // A translucent water ribbon gives the ring volume; the center stays
        // open so the palm and the forward gesture remain readable.
        const int ribbonSegments = 24;
        for (int i = 0; i < ribbonSegments; ++i)
        {
            float a = i * Mathf.Tau / ribbonSegments, b = (i + 1) * Mathf.Tau / ribbonSegments;
            Vector2 pa = Vector2.FromAngle(a) * new Vector2(18,46) * (1.06f + .055f * Mathf.Sin(a * 5));
            Vector2 pb = Vector2.FromAngle(b) * new Vector2(18,46) * (1.06f + .055f * Mathf.Sin(b * 5));
            float ia = .73f + .08f * Mathf.Sin(a * 3), ib = .73f + .08f * Mathf.Sin(b * 3);
            root.AddChild(new Polygon2D {
                Polygon = new[] { pa, pb, pb * ib, pa * ia },
                Color = i % 3 == 0 ? new Color("53d8ff",.75f) : new Color("237fde",.7f)
            });
        }
        for (int ring = 0; ring < 3; ++ring)
        {
            var contour = new Vector2[64];
            float radius = ring == 0 ? 1f : ring == 1 ? .82f : 1.13f;
            for (int i = 0; i < contour.Length; ++i)
            {
                float a = i * Mathf.Tau / contour.Length;
                float ripple = 1f + .06f * Mathf.Sin(a * 5 + ring) + .025f * Mathf.Sin(a * 9 - ring);
                contour[i] = Vector2.FromAngle(a) * new Vector2(18,46) * radius * ripple;
            }
            if (ring == 0) root.AddChild(Line(contour,new Color("43bfff",.3f),10f,true));
            root.AddChild(Line(contour, ring == 0 ? new Color("8fe9ff") : ring == 1 ? new Color("e5fbff") : new Color("37b4fa",.8f), ring == 0 ? 4f : 2f, true));
        }
        // Small splashes are deterministic artwork, not gameplay RNG or particles.
        for (int i = 0; i < 9; ++i)
        {
            float a = i * Mathf.Tau / 9 + .13f;
            Vector2 edge = Vector2.FromAngle(a) * new Vector2(23,54);
            var drop = new Node2D { Position = edge };
            var outline = new Vector2[12];
            for (int j = 0; j < outline.Length; ++j) outline[j] = Vector2.FromAngle(j * Mathf.Tau / outline.Length) * new Vector2(1.8f,3f);
            drop.AddChild(Line(outline,new Color("baf4ff"),1.5f,true));
            root.AddChild(drop);
        }
        Tween animation = root.CreateTween();
        animation.TweenInterval(delay);
        animation.TweenCallback(Callable.From(() => {
            if (!GodotObject.IsInstanceValid(owner) || !root.IsInsideTree()) return;
            using Variant skeleton = owner.Call("get_skeleton");
            using Variant bone = skeleton.AsGodotObject().Call("find_bone", "ref_hand_front");
            using Variant x = bone.AsGodotObject().Call("get_world_x");
            using Variant y = bone.AsGodotObject().Call("get_world_y");
            root.Position = new Vector2(x.AsSingle() + 22,y.AsSingle());
            root.Scale = Vector2.One * .4f;
            root.Modulate = new Color(1,1,1,Math.Min(1f,ModEntry.Options.Intensity * 1.5f));
            root.Visible = true;
        }));
        animation.TweenProperty(root,"scale",Vector2.One * 1.25f,.32).SetTrans(Tween.TransitionType.Quad).SetEase(Tween.EaseType.Out);
        animation.Parallel().TweenProperty(root,"modulate:a",0f,.22).SetDelay(.10);
        animation.TweenCallback(Callable.From(root.QueueFree));
        return root;
    }
    internal static Node2D? SpellWeave(Node2D owner, double duration, bool power, bool centered)
    {
        if (!ModEntry.Options.Effects || ModEntry.Options.Intensity <= 0) return null;
        var root = new Node2D { Name = "DeepSeekHandSpell", ZIndex = 14, Visible = false };
        owner.AddChild(root);
        Color color = power ? new Color("b69bff") : new Color("6de3ff");
        var halo = Ring(24,new Color(color,.24f),5f);
        var first = Ring(24,new Color(color,.9f),1.6f);
        var second = Ring(24,new Color("e8faff",.8f),1.2f);
        var core = Ring(8,new Color(color,.8f),2.2f);
        root.AddChild(halo); root.AddChild(first); root.AddChild(second); root.AddChild(core);
        var motes = new Node2D[8];
        for (int i=0;i<motes.Length;++i)
        {
            var mote = new Node2D();
            mote.AddChild(Line(new[] { new Vector2(0,-3),new Vector2(2,0),new Vector2(0,3),new Vector2(-2,0) },
                i%3==0 ? new Color("ffe3a6") : new Color(color,.85f),1.1f,true));
            root.AddChild(mote); motes[i]=mote;
        }
        Tween animation = root.CreateTween();
        animation.TweenMethod(Callable.From<float>(phase => {
            if (!GodotObject.IsInstanceValid(owner) || !root.IsInsideTree()) return;
            root.Visible = phase>=.12f && phase<.88f;
            if (!root.Visible) return;
            using Variant skeleton = owner.Call("get_skeleton");
            Vector2 front = SpellPalm(skeleton.AsGodotObject(),"ref_hand_front");
            Vector2 rear = SpellPalm(skeleton.AsGodotObject(),"ref_hand_back");
            float release = centered ? 0 : SpellRamp(.40f,.60f,phase);
            root.Position = ((front+rear)*.5f + new Vector2(0,-5)).Lerp(front+new Vector2(18,-14),release);
            float charge = SpellRamp(.12f,.46f,phase);
            float radius = (12+charge*(power ? 21 : 15))*(1+(power ? .08f : .035f)*MathF.Sin(phase*Mathf.Tau*3));
            float size = radius/24;
            halo.Scale = Vector2.One*size;
            first.Scale = new Vector2(1.12f,.48f)*size; first.Rotation = phase*Mathf.Tau*1.3f;
            second.Scale = new Vector2(.62f,1.08f)*size; second.Rotation = -phase*Mathf.Tau*1.1f;
            core.Scale = Vector2.One*(.6f+charge*.75f);
            for (int i=0;i<motes.Length;++i)
            {
                float angle = i*Mathf.Tau/motes.Length+phase*Mathf.Tau*(power ? 1.4f : 1.1f);
                motes[i].Position = Vector2.FromAngle(angle)*new Vector2(radius*1.25f,radius*.78f);
                motes[i].Rotation = angle;
            }
            float alpha = SpellRamp(.12f,.22f,phase)*(1-SpellRamp(.70f,.88f,phase));
            root.Modulate = new Color(1,1,1,alpha*Math.Min(1f,ModEntry.Options.Intensity*1.4f));
        }),0f,1f,duration);
        animation.TweenCallback(Callable.From(root.QueueFree));
        return root;
    }

    private static float SpellRamp(float start, float end, float value)
    {
        float t = Math.Clamp((value-start)/(end-start),0f,1f);
        return t*t*(3-2*t);
    }

    private static Vector2 SpellPalm(GodotObject skeleton, string name)
    {
        using Variant bone = skeleton.Call("find_bone",name);
        using Variant x = bone.AsGodotObject().Call("get_world_x");
        using Variant y = bone.AsGodotObject().Call("get_world_y");
        return new Vector2(x.AsSingle(),y.AsSingle());
    }

    internal static Node2D? DefenseShield(Node2D owner, double duration)
    {
        if (!ModEntry.Options.Effects || ModEntry.Options.Intensity <= 0) return null;
        var root = new Node2D { Name = "DeepSeekDefenseWater", ZIndex = 14, Visible = false };
        owner.AddChild(root);
        root.AddChild(new Sprite2D {
            Texture = SpineRig.ShieldTexture,
            Scale = Vector2.One * (290f / SpineRig.ShieldTexture.GetHeight()),
            TextureFilter = CanvasItem.TextureFilterEnum.Linear
        });
        Tween animation = root.CreateTween();
        animation.TweenInterval(duration * .17);
        animation.TweenCallback(Callable.From(() => {
            if (!GodotObject.IsInstanceValid(owner) || !root.IsInsideTree()) return;
            PlaceDefenseShield(owner,root);
            root.Scale = new Vector2(.30f,.55f);
            root.Modulate = new Color(1,1,1,Math.Min(1f,ModEntry.Options.Intensity*1.4f));
            root.Visible = true;
            // The palm draws back to brace; keep the shield against it at
            // render-update cadence instead of leaving the effect behind.
            Tween follow = root.CreateTween();
            follow.TweenMethod(Callable.From<float>(_ => PlaceDefenseShield(owner,root)),0f,1f,duration*.64);
        }));
        animation.TweenProperty(root,"scale",Vector2.One,duration*.15).SetTrans(Tween.TransitionType.Cubic).SetEase(Tween.EaseType.Out);
        animation.TweenInterval(duration*.14);
        animation.TweenProperty(root,"scale",new Vector2(.90f,1.035f),duration*.045).SetTrans(Tween.TransitionType.Quad).SetEase(Tween.EaseType.Out);
        animation.TweenProperty(root,"scale",Vector2.One,duration*.075).SetTrans(Tween.TransitionType.Sine).SetEase(Tween.EaseType.Out);
        animation.TweenProperty(root,"scale",new Vector2(1.13f,1.05f),duration*.23).SetTrans(Tween.TransitionType.Sine).SetEase(Tween.EaseType.Out);
        animation.Parallel().TweenProperty(root,"modulate:a",0f,duration*.23);
        animation.TweenCallback(Callable.From(root.QueueFree));
        return root;
    }

    private static void PlaceDefenseShield(Node2D owner, Node2D effect)
    {
        if (!GodotObject.IsInstanceValid(owner) || !effect.IsInsideTree()) return;
        using Variant skeleton = owner.Call("get_skeleton");
        using Variant bone = skeleton.AsGodotObject().Call("find_bone","ref_hand_front");
        using Variant x = bone.AsGodotObject().Call("get_world_x");
        using Variant y = bone.AsGodotObject().Call("get_world_y");
        effect.Position = new Vector2(x.AsSingle()+58,y.AsSingle()+60);
    }

    private static Node2D ReferencePalmWater(Node2D owner, double delay)
    {
        var root = new Node2D { Name = "DeepSeekPaintedPalmWater", ZIndex = 14, Visible = false };
        owner.AddChild(root);
        root.AddChild(new Sprite2D {
            Texture = SpineRig.WaterTexture,
            Scale = Vector2.One * (190f / SpineRig.WaterTexture.GetHeight()),
            TextureFilter = CanvasItem.TextureFilterEnum.Linear
        });
        Tween animation = root.CreateTween();
        animation.TweenInterval(delay);
        animation.TweenCallback(Callable.From(() => {
            if (!GodotObject.IsInstanceValid(owner) || !root.IsInsideTree()) return;
            using Variant skeleton = owner.Call("get_skeleton");
            using Variant bone = skeleton.AsGodotObject().Call("find_bone","ref_hand_front");
            using Variant x = bone.AsGodotObject().Call("get_world_x");
            using Variant y = bone.AsGodotObject().Call("get_world_y");
            root.Position = new Vector2(x.AsSingle()+10,y.AsSingle()+4);
            root.Scale = new Vector2(.52f,.75f);
            root.Modulate = new Color(1,1,1,Math.Min(1f,ModEntry.Options.Intensity*1.5f));
            root.Visible = true;
        }));
        animation.TweenProperty(root,"scale",Vector2.One,.14).SetTrans(Tween.TransitionType.Cubic).SetEase(Tween.EaseType.Out);
        animation.TweenProperty(root,"scale",new Vector2(1.18f,1.10f),.24).SetTrans(Tween.TransitionType.Sine).SetEase(Tween.EaseType.Out);
        animation.Parallel().TweenProperty(root,"modulate:a",0f,.24);
        animation.TweenCallback(Callable.From(root.QueueFree));
        return root;
    }
    internal static Node2D? Anger(Node2D owner)
    {
        if (!ModEntry.Options.Effects || ModEntry.Options.Intensity <= 0) return null;
        var root = new Node2D { Name = "DeepSeekAnnoyed", ZIndex = 15,
            Modulate = new Color(1,1,1,Math.Min(1f,ModEntry.Options.Intensity*1.4f)) };
        owner.AddChild(root);
        var head = new Node2D { Modulate = new Color(1,1,1,0) };
        root.AddChild(head);
        var mark = new Node2D(); head.AddChild(mark);
        for (int i=0;i<4;++i)
        {
            float angle = i*Mathf.Pi/2;
            Vector2[] corners = { new Vector2(3,-2).Rotated(angle),new Vector2(3,-9).Rotated(angle),new Vector2(10,-9).Rotated(angle) };
            mark.AddChild(Line(corners,new Color("fff2d9"),5));
            mark.AddChild(Line(corners,new Color("ff6753"),2.5f));
        }
        Tween animation = root.CreateTween().SetParallel();
        animation.TweenProperty(head,"modulate:a",1f,.08).SetDelay(.14);
        animation.TweenProperty(mark,"scale",Vector2.One,.14).From(Vector2.One*.45f).SetDelay(.14)
            .SetTrans(Tween.TransitionType.Cubic).SetEase(Tween.EaseType.Out);
        for (int i=0;i<2;++i)
        {
            var steam = new Node2D { Position = new Vector2(i==0 ? -32 : 16,0) };
            head.AddChild(steam);
            steam.AddChild(Line(new[] { new Vector2(0,5),new Vector2(-3,-1),new Vector2(2,-7),new Vector2(-1,-13),new Vector2(3,-19) },new Color("fff3e3"),1.6f));
            animation.TweenProperty(steam,"position:y",-9f,.55).SetDelay(.20+i*.05);
            animation.TweenProperty(steam,"modulate:a",0f,.28).SetDelay(.65+i*.05);
        }
        var impact = new Node2D(); root.AddChild(impact);
        for (int i=0;i<4;++i)
        {
            Vector2 direction=Vector2.FromAngle(-1.1f+i*.7f);
            impact.AddChild(Line(new[] { direction*8,direction*20 },i%2==0 ? new Color("abf0ff") : new Color("67c9ff"),1.8f));
        }
        animation.TweenProperty(impact,"scale",Vector2.One*1.35f,.18).From(Vector2.One*.5f);
        animation.TweenProperty(impact,"modulate:a",0f,.15).SetDelay(.04);
        animation.TweenMethod(Callable.From<float>(_ => {
            if (!GodotObject.IsInstanceValid(owner) || !root.IsInsideTree()) return;
            using Variant skeleton=owner.Call("get_skeleton");
            head.Position=SpellPalm(skeleton.AsGodotObject(),"ref_head")+new Vector2(43,-53);
            impact.Position=SpellPalm(skeleton.AsGodotObject(),"ref_torso")+new Vector2(45,-28);
        }),0f,1f,1.20);
        animation.TweenProperty(head,"modulate:a",0f,.22).SetDelay(.95);
        animation.Chain().TweenCallback(Callable.From(root.QueueFree));
        return root;
    }
    private static Sprite2D Glyph(string style, float size) => new() {
        Name = "ElementalSprite", Texture = Art.Element(style), Scale = Vector2.One * (size / 128f),
        TextureFilter = CanvasItem.TextureFilterEnum.Linear
    };
    private static Vector2[] CirclePoints(int count)
    {
        var points = new Vector2[count];
        for (int i = 0; i < count; ++i) points[i] = Vector2.FromAngle(i * Mathf.Tau / count);
        return points;
    }
    private static Line2D Line(Vector2[] points, Color color, float width, bool closed = false) => new() {
        Points = points, Width = width, DefaultColor = color, Closed = closed, Antialiased = true,
        BeginCapMode = Line2D.LineCapMode.Round, EndCapMode = Line2D.LineCapMode.Round
    };
    private static Line2D Ring(float radius, Color color, float width = 1.5f, bool hex = false)
    {
        Vector2[] unit = hex ? Hexagon : Circle;
        var points = new Vector2[unit.Length];
        for (int i = 0; i < unit.Length; ++i) points[i] = unit[i] * radius;
        return Line(points, color, width, true);
    }
    private static Node2D? Root(Vector2 position, Control? container)
    {
        if (!ModEntry.Options.Effects || ModEntry.Options.Intensity <= 0 || _active >= ModEntry.Options.MaxEffects) return null;
        container ??= NCombatRoom.Instance?.CombatVfxContainer;
        if (container == null || !GodotObject.IsInstanceValid(container) || !container.IsInsideTree()) return null;
        var root = new Node2D { Name = "DeepSeekSpell", ZIndex = 4,
            Modulate = new Color(1, 1, 1, Math.Min(.85f, ModEntry.Options.Intensity)) };
        container.AddChild(root);
        root.GlobalPosition = position;
        ++_active;
        root.TreeExiting += () => --_active;
        return root;
    }
    internal static bool Pulse(Vector2 position, string style, bool guard = false, Control? container = null)
    {
        ulong now = Time.GetTicksMsec();
        var key = ((int)MathF.Round(position.X / 20), (int)MathF.Round(position.Y / 20), style, guard);
        if (RecentImpacts.TryGetValue(key, out ulong last) && now - last < (guard ? 130ul : 70ul)) return true;
        Node2D? root = Root(position, container);
        if (root == null) return false;
        if (RecentImpacts.Count > 128) RecentImpacts.Clear();
        RecentImpacts[key] = now;
        Color color = ColorFor(style);
        float radius = guard ? 61 : 29;
        var ring = Ring(radius, new Color(color, guard ? .7f : .5f), guard ? 2 : 1.5f, style == "glass");
        root.AddChild(ring);
        Tween animation = root.CreateTween().SetParallel();
        animation.TweenProperty(ring, "scale", Vector2.One * 1.25f, .32).From(Vector2.One * .45f)
            .SetTrans(Tween.TransitionType.Cubic).SetEase(Tween.EaseType.Out);
        if (guard || style is "frost" or "dark")
        {
            var inner = Ring(radius * .79f, new Color(color, .25f), 1, style == "glass");
            root.AddChild(inner);
            animation.TweenProperty(inner, "rotation", .35f, .38).From(-.2f);
        }
        if (guard)
        {
            Sprite2D badge = Glyph(style, 39);
            root.AddChild(badge);
            animation.TweenProperty(badge, "scale", badge.Scale, .16).From(badge.Scale * .6f)
                .SetTrans(Tween.TransitionType.Back).SetEase(Tween.EaseType.Out);
        }
        int count = ModEntry.Options.Particles;
        for (int i = 0; i < count; ++i)
        {
            Vector2 direction = Vector2.FromAngle(i * Mathf.Tau / Math.Max(1, count) - .3f);
            var sparkle = Glyph("sparkle", i % 2 == 0 ? 12 : 8);
            sparkle.Modulate = new Color(color, .8f);
            sparkle.Position = direction * (guard ? radius * .8f : 8);
            sparkle.Rotation = i * .7f;
            root.AddChild(sparkle);
            animation.TweenProperty(sparkle, "position", direction * (radius + 18 + i % 3 * 5), .32)
                .SetTrans(Tween.TransitionType.Cubic).SetEase(Tween.EaseType.Out);
        }
        AddElementMark(root, style, color, radius);
        animation.TweenProperty(root, "modulate:a", 0f, .24).SetDelay(guard ? .16 : .08);
        animation.Chain().TweenCallback(Callable.From(root.QueueFree));
        return true;
    }
    private static void AddElementMark(Node2D root, string style, Color color, float radius)
    {
        if (style == "lightning")
            root.AddChild(Line(new[] { new Vector2(-14,-23), new Vector2(1,-4), new Vector2(-3,1), new Vector2(13,23) }, color, 2));
        else if (style == "frost")
            for (int i = 0; i < 3; ++i) {
                Vector2 end = Vector2.FromAngle(i * Mathf.Pi / 3) * radius * .6f;
                root.AddChild(Line(new[] { -end, end }, new Color(color, .65f), 1.3f));
            }
        else if (style == "plasma") root.AddChild(Ring(radius * .5f, new Color(color, .7f), 3));
        else if (style == "glass") root.AddChild(Line(new[] {
            new Vector2(0,-17), new Vector2(12,0), new Vector2(0,17), new Vector2(-12,0) }, color, 1.6f, true));
    }
    internal static bool Stream(Vector2 source, Vector2 destination, string style, Control? container = null, bool beam = false, float delay = 0)
    {
        Node2D? root = Root(source, container);
        if (root == null) return false;
        Vector2 end = root.ToLocal(destination);
        Vector2 normal = end.LengthSquared() < 1 ? Vector2.Up : end.Orthogonal().Normalized();
        Vector2 control = end * .5f + normal * (beam ? 0 : Math.Min(42, end.Length() * .07f));
        var points = new Vector2[17];
        for (int i = 0; i < points.Length; ++i) {
            float t = i / (points.Length - 1f);
            points[i] = 2 * (1 - t) * t * control + t * t * end;
        }
        Color color = ColorFor(style);
        root.AddChild(Line(points, new Color(color, beam ? .15f : .08f), beam ? 13 : 5));
        root.AddChild(Line(points, new Color(color, beam ? .8f : .32f), beam ? 2.3f : 1.1f));
        var orb = Glyph(style, beam ? 25 : 33);
        root.AddChild(orb);
        float duration = beam ? .28f : .3f;
        Tween animation = root.CreateTween().SetParallel();
        root.Modulate = new Color(1,1,1,0);
        animation.TweenProperty(root, "modulate:a", Math.Min(.8f, ModEntry.Options.Intensity), .06).SetDelay(delay);
        animation.TweenMethod(Callable.From<float>(t => {
            orb.Position = 2 * (1 - t) * t * control + t * t * end;
            orb.Rotation = MathF.Sin(t * Mathf.Pi) * .12f;
        }), 0f, 1f, duration).SetDelay(delay).SetTrans(Tween.TransitionType.Sine).SetEase(Tween.EaseType.InOut);
        animation.TweenProperty(root, "modulate:a", 0f, .16).SetDelay(delay + duration);
        animation.Chain().TweenCallback(Callable.From(root.QueueFree));
        return true;
    }
    internal static void Card(CardPlay play)
    {
        // Native hit/beam factories own impacts. Do not create a duplicate projectile for every card.
        var node = play.Player.Creature.GetCreatureNode();
        if (node == null || play.Card.Type == CardType.Attack || play.Card.GainsBlock) return;
        string style = Style(play.Card.Id.Entry);
        Node2D? root = Root(node.VfxSpawnPosition + new Vector2(50, 24), null);
        if (root == null) return;
        var rune = Ring(18, new Color(ColorFor(style), .55f), 1.2f, style == "glass");
        root.AddChild(rune);
        Tween animation = root.CreateTween().SetParallel();
        animation.TweenProperty(rune, "scale", Vector2.One * .55f, .24).From(Vector2.One * 1.2f);
        animation.TweenProperty(rune, "rotation", .8f, .24);
        animation.TweenProperty(root, "modulate:a", 0f, .18).SetDelay(.12);
        animation.Chain().TweenCallback(Callable.From(root.QueueFree));
    }
}
