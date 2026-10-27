using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Text.Json;
using Godot;

namespace DeepSeekMaid;

internal static class Art
{
    private static readonly Dictionary<string, Texture2D> Portraits = new(StringComparer.Ordinal);
    private static readonly HashSet<string> PortraitKeys = new(StringComparer.Ordinal);
    private static readonly Texture2D[] Elements = new Texture2D[6];
    internal static Texture2D Icon { get; private set; } = null!;
    internal static Texture2D SelectIcon { get; private set; } = null!;
    internal static Texture2D SelectPortrait { get; private set; } = null!;
    internal static Texture2D SelectBackground { get; private set; } = null!;
    internal static int CardCount => Portraits.Count;

    private static byte[] Read(string name)
    {
        using Stream stream = typeof(Art).Assembly.GetManifestResourceStream("DeepSeekMaid." + name)
            ?? throw new FileNotFoundException("Missing embedded asset", name);
        using var buffer = new MemoryStream();
        stream.CopyTo(buffer);
        return buffer.ToArray();
    }

    private static Image LoadImage(string name)
    {
        var image = new Image();
        if (image.LoadPngFromBuffer(Read(name)) != Error.Ok)
            throw new InvalidDataException("Cannot decode " + name);
        return image;
    }

    internal static void Preload()
    {
        using var select = LoadImage("selection.png");
        select.GenerateMipmaps();
        SelectPortrait = ImageTexture.CreateFromImage(select);
        using var backdrop = LoadImage("selection-background.png");
        backdrop.GenerateMipmaps();
        SelectBackground = ImageTexture.CreateFromImage(backdrop);
        int sw = select.GetWidth(), sh = select.GetHeight();
        using var face = select.GetRegion(new Rect2I(sw * 18 / 100, sh * 3 / 100, sw * 58 / 100, sw * 58 / 100));
        face.Resize(85, 85, Image.Interpolation.Lanczos);
        Icon = ImageTexture.CreateFromImage(face);
        using var full = select.GetRegion(new Rect2I(sw * 15 / 100, 0, sw * 70 / 100, sh * 70 / 100));
        full.Resize(132, 195, Image.Interpolation.Lanczos);
        SelectIcon = ImageTexture.CreateFromImage(full);
        using var elemental = LoadImage("elements.png");
        for (int slot = 0; slot < Elements.Length; ++slot)
        {
            int x0 = slot % 3 * elemental.GetWidth() / 3, x1 = (slot % 3 + 1) * elemental.GetWidth() / 3;
            int y0 = slot / 3 * elemental.GetHeight() / 2, y1 = (slot / 3 + 1) * elemental.GetHeight() / 2;
            using var cell = elemental.GetRegion(new Rect2I(x0, y0, x1 - x0, y1 - y0));
            cell.Resize(128, 128, Image.Interpolation.Lanczos);
            Elements[slot] = ImageTexture.CreateFromImage(cell);
        }
        using var index = JsonDocument.Parse(Read("cards.index"));
        var sheets = new Dictionary<int, Image>();
        try
        {
            foreach (JsonProperty entry in index.RootElement.EnumerateObject())
            {
                int sheet = entry.Value.GetProperty("sheet").GetInt32();
                int slot = entry.Value.GetProperty("slot").GetInt32();
                if (!sheets.TryGetValue(sheet, out Image? image))
                    sheets[sheet] = image = LoadImage(entry.Value.TryGetProperty("sheet_file", out JsonElement atlasFile)
                        ? atlasFile.GetString()! : $"cards-{sheet:00}.png");
                // Integer boundaries cover the whole image even when dimensions aren't divisible by the grid.
                int x0 = (slot % 5) * image.GetWidth() / 5;
                int x1 = (slot % 5 + 1) * image.GetWidth() / 5;
                int y0 = (slot / 5) * image.GetHeight() / 4;
                int y1 = (slot / 5 + 1) * image.GetHeight() / 4;
                using var cell = entry.Value.TryGetProperty("file", out JsonElement replacement)
                    ? LoadImage(replacement.GetString()!)
                    : image.GetRegion(new Rect2I(x0, y0, x1 - x0, y1 - y0));
                cell.Resize(250, 190, Image.Interpolation.Lanczos);
                string key = PortraitResolver.Normalize(entry.Name);
                Portraits.Add(key, ImageTexture.CreateFromImage(cell));
                PortraitKeys.Add(key);
            }
        }
        finally { foreach (Image image in sheets.Values) image.Dispose(); }
    }

    internal static bool TryPortrait(string id, out Texture2D texture) => Portraits.TryGetValue(PortraitResolver.Normalize(id), out texture!);

    internal static bool TryPortrait(MegaCrit.Sts2.Core.Models.CardModel? card, out Texture2D texture)
    {
        texture = null!;
        if (card == null) return false;
        string? key = PortraitResolver.Resolve(card.GetType(), card.Id.Entry, PortraitKeys);
        return key != null && Portraits.TryGetValue(key, out texture!);
    }

    internal static Texture2D Element(string style) => Elements[style switch {
        "frost" => 1, "dark" => 2, "plasma" => 3, "glass" => 4, "sparkle" => 5, _ => 0
    }];

    internal static Sprite2D Selection(float height) => new() {
        Name = "DeepSeekMaidSelection", Texture = SelectPortrait,
        TextureFilter = CanvasItem.TextureFilterEnum.LinearWithMipmaps,
        Scale = Vector2.One * (height / SelectPortrait.GetHeight())
    };

}
