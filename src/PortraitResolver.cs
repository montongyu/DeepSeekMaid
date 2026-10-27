using System;
using System.Collections.Generic;
using System.Linq;
using MegaCrit.Sts2.Core.Models;

namespace DeepSeekMaid;

internal static class PortraitResolver
{
    // Card pools can be wrapped or reassigned by content mods. Resolve native card identity independently.
    internal static string Normalize(string value) => new(value.Where(char.IsLetterOrDigit).Select(char.ToLowerInvariant).ToArray());

    internal static string? Resolve(Type cardType, string entry, ISet<string> known)
    {
        if (cardType.Assembly != typeof(CardModel).Assembly || cardType.Namespace != "MegaCrit.Sts2.Core.Models.Cards") return null;
        string typeKey = Normalize(cardType.Name);
        if (!known.Contains(typeKey)) return null;
        string entryKey = Normalize(entry);
        return entryKey == typeKey ? entryKey : typeKey;
    }
}
