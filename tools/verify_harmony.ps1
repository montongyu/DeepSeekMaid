# Apply the display postfixes only in a disposable .NET 9 host, without creating Godot nodes or starting the game.
param([string]$GameDir = 'C:\game\steamapps\common\Slay the Spire 2')
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$work = Join-Path $root 'work'
$data = Join-Path $GameDir 'data_sts2_windows_x86_64'
$response = [System.Collections.Generic.List[string]]::new()
foreach ($line in Get-Content -LiteralPath (Join-Path $work 'compile.rsp')) {
    if ($line.StartsWith('/reference:') -or $line.StartsWith('/langversion:') -or $line.StartsWith('/nullable:') -or $line -eq '/nostdlib+') { $response.Add($line) }
}
$exe = Join-Path $work 'HarmonyHarness.dll'
$response.Add('/target:exe')
$response.Add('/out:"' + $exe + '"')
$response.Add('"' + (Join-Path $root 'tools\HarmonyHarness.cs') + '"')
$rsp = Join-Path $work 'harmony-harness.rsp'
[IO.File]::WriteAllLines($rsp,$response,[Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText((Join-Path $work 'HarmonyHarness.runtimeconfig.json'), '{"runtimeOptions":{"tfm":"net9.0","framework":{"name":"Microsoft.NETCore.App","version":"9.0.7"}}}')
$hostExe = 'C:\Program Files\dotnet\dotnet.exe'
& $hostExe (Join-Path $root '.tools\roslyn\tasks\netcore\bincore\csc.dll') /noconfig ('@' + $rsp)
if ($LASTEXITCODE -ne 0) { throw 'Cannot compile isolated Harmony test host.' }
& $hostExe $exe (Join-Path $root 'dist\DeepSeekMaid\DeepSeekMaid.dll') $data
if ($LASTEXITCODE -ne 0) { throw 'Card-display Harmony application check failed.' }
