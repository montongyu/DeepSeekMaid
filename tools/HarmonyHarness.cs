using System;
using System.IO;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.Loader;
using HarmonyLib;

internal static class HarmonyHarness
{
    public static int Main(string[] args)
    {
        AssemblyLoadContext.Default.Resolving += (context, name) => {
            string candidate = Path.Combine(args[1], name.Name + ".dll");
            return File.Exists(candidate) ? context.LoadFromAssemblyPath(candidate) : null;
        };
        return Run(args[0]);
    }
    [MethodImpl(MethodImplOptions.NoInlining)]
    private static int Run(string mod)
    {
        const string id = "local.deepseekmaid.isolated-verification";
        var harmony = new Harmony(id);
        try
        {
            Assembly assembly = AssemblyLoadContext.Default.LoadFromAssemblyPath(mod);
            Type patch = assembly.GetType("DeepSeekMaid.CardDisplayPatch", true)!;
            var methods = harmony.CreateClassProcessor(patch).Patch();
            if (methods.Count != 3) throw new Exception("Expected three card UI postfixes.");
            Console.WriteLine("PASS: all three display postfixes actually apply under .NET " + Environment.Version);
            harmony.UnpatchAll(id);
            foreach (string name in new[] { "CharacterIconScenePatch", "TopBarPortraitPatch", "TopBarAvatarPatch" })
            {
                var avatar = harmony.CreateClassProcessor(assembly.GetType("DeepSeekMaid." + name, true)!).Patch();
                if (avatar.Count != 1) throw new Exception("Avatar target missing: " + name);
            }
            Console.WriteLine("PASS: icon-scene, run-portrait initialization and top-bar initialization patches all apply.");
            harmony.UnpatchAll(id);
            harmony.PatchAll(assembly);
            Console.WriteLine("PASS: all mod patches apply in this isolated .NET 9 process; no game executable or Godot nodes were started.");
            return 0;
        }
        catch (Exception e) { Console.Error.WriteLine(e); return 1; }
        finally { harmony.UnpatchAll(id); }
    }
}
