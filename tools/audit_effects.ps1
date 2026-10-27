$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Add-Type -Path (Join-Path $root '.tools\decompiler\lib\netstandard2.0\ICSharpCode.Decompiler.dll')
$settings = [ICSharpCode.Decompiler.DecompilerSettings]::new()
$settings.ThrowOnAssemblyResolveErrors = $false
$decompiler = [ICSharpCode.Decompiler.CSharp.CSharpDecompiler]::new('C:\game\steamapps\common\Slay the Spire 2\data_sts2_windows_x86_64\sts2.dll', $settings)
$index = Get-Content -Raw -LiteralPath (Join-Path $root 'assets\cards\index.json') | ConvertFrom-Json -AsHashtable
$wanted = @{}
foreach ($name in $index.Keys) { $wanted[$name.Replace('_','')] = $name }
$rows = [System.Collections.Generic.List[object]]::new()
foreach ($type in $decompiler.TypeSystem.MainModule.TypeDefinitions) {
    if ($type.Namespace -ne 'MegaCrit.Sts2.Core.Models.Cards' -or !$wanted.ContainsKey($type.Name.ToLowerInvariant())) { continue }
    $text = $decompiler.DecompileTypeAsString([ICSharpCode.Decompiler.TypeSystem.FullTypeName]::new($type.FullName))
    $factories = [regex]::Matches($text, '(N\w+Vfx)\.Create\(') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
    $rows.Add(@{ card=$wanted[$type.Name.ToLowerInvariant()]; type=$type.FullName; factories=@($factories) })
}
$json = $rows | ConvertTo-Json -Depth 5
[IO.File]::WriteAllText((Join-Path $root 'work\vfx-audit.json'), $json)
Write-Output "Audited $($rows.Count) card models. Native VFX factories:"
$rows.factories | Sort-Object -Unique
