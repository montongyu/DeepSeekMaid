param([string]$GameDir = 'C:\game\steamapps\common\Slay the Spire 2')
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$data = Join-Path $GameDir 'data_sts2_windows_x86_64'
$stage = Join-Path $root 'dist\DeepSeekMaid'
$work = Join-Path $root 'work'
New-Item -ItemType Directory -Path $stage,$work -Force | Out-Null
if (!(Test-Path -LiteralPath (Join-Path $data 'sts2.dll'))) { throw 'Cannot find game assemblies.' }
$release = Get-Content -Raw -LiteralPath (Join-Path $GameDir 'release_info.json') | ConvertFrom-Json
if ($release.version -ne 'v0.111.0') { throw "Game is $($release.version); re-inspect and update the mod before building for a different beta." }
$compiler = Join-Path $root '.tools\roslyn\tasks\netcore\bincore\csc.dll'
$hostExe = 'C:\Program Files\dotnet\dotnet.exe'
if (!(Test-Path -LiteralPath $compiler)) { throw 'Run tools/bootstrap.ps1 to fetch the pinned compiler, or use dotnet build DeepSeekMaid.csproj with a .NET 9 SDK.' }
$response = [System.Collections.Generic.List[string]]::new()
foreach ($argument in @('/target:library','/langversion:13','/nullable:enable','/nostdlib+','/optimize+','/deterministic+','/warn:4','/warnaserror+')) { $response.Add($argument) }
$response.Add('/out:"' + (Join-Path $stage 'DeepSeekMaid.dll') + '"')
foreach ($file in Get-ChildItem -LiteralPath $data -Filter '*.dll') {
    if ($file.Name -match '^(System\.|Microsoft\.CSharp|netstandard|mscorlib|GodotSharp|sts2|0Harmony)') {
        try { [System.Reflection.AssemblyName]::GetAssemblyName($file.FullName) | Out-Null; $response.Add('/reference:"' + $file.FullName + '"') } catch [System.BadImageFormatException] { }
    }
}
$response.Add('/resource:"' + (Join-Path $root 'assets\cards\index.json') + '",DeepSeekMaid.cards.index')
$response.Add('/resource:"' + (Join-Path $root 'assets\effects\elemental-orbs.png') + '",DeepSeekMaid.elements.png')
$response.Add('/resource:"' + (Join-Path $root 'assets\ui\character-select.png') + '",DeepSeekMaid.selection.png')
$response.Add('/resource:"' + (Join-Path $root 'assets\ui\selection-background.png') + '",DeepSeekMaid.selection-background.png')
$cardIndex = Get-Content -Raw -LiteralPath (Join-Path $root 'assets\cards\index.json') | ConvertFrom-Json -AsHashtable
$cardFiles = [System.Collections.Generic.HashSet[string]]::new()
foreach ($entry in $cardIndex.Values) {
    [void]$cardFiles.Add($entry.sheet_file)
    if ($entry.ContainsKey('file')) { [void]$cardFiles.Add($entry.file) }
}
foreach ($name in ($cardFiles | Sort-Object)) {
    $file = Join-Path $root ('assets\cards\' + $name)
    $response.Add('/resource:"' + $file + '",DeepSeekMaid.' + $name)
}
foreach ($file in Get-ChildItem -LiteralPath (Join-Path $root 'src') -Filter '*.cs') { $response.Add('"' + $file.FullName + '"') }
$rsp = Join-Path $work 'compile.rsp'
[System.IO.File]::WriteAllLines($rsp, $response, [System.Text.UTF8Encoding]::new($false))
& $hostExe $compiler /noconfig ('@' + $rsp)
if ($LASTEXITCODE -ne 0) { throw 'C# compilation failed.' }
$animationStage = Join-Path $stage 'animation'
New-Item -ItemType Directory -Path $animationStage -Force | Out-Null
foreach ($name in @('maid.spine-json','maid.atlas')) {
    Copy-Item -LiteralPath (Join-Path $root ('assets\animation\' + $name)) -Destination $animationStage -Force
}
$payload = Get-Content -Raw -LiteralPath (Join-Path $root 'assets\animation\payload.json') | ConvertFrom-Json
foreach ($name in $payload.textures) {
    Copy-Item -LiteralPath (Join-Path $root ('assets\sprites\' + $name)) -Destination $animationStage -Force
}
$expectedAnimationStage = [System.IO.Path]::GetFullPath((Join-Path $root 'dist\DeepSeekMaid\animation'))
if ([System.IO.Path]::GetFullPath($animationStage) -ne $expectedAnimationStage) { throw 'Unexpected staged animation directory.' }
foreach ($file in Get-ChildItem -LiteralPath $animationStage -File -Filter '*.png') {
    if ($file.Name -notin $payload.textures) { Remove-Item -LiteralPath $file.FullName }
}
$legacyTexture = Join-Path $animationStage 'deepseek-poses-v0.3.png'
if (Test-Path -LiteralPath $legacyTexture) { Remove-Item -LiteralPath $legacyTexture }
foreach ($name in @('puppet-parts-v0.7.png','puppet-skirt-v0.7.png','puppet-tail-v0.7.png','puppet-angry-v0.7.png','puppet-prone-v0.7.png')) {
    $legacyTexture = Join-Path $animationStage $name
    if (Test-Path -LiteralPath $legacyTexture) { Remove-Item -LiteralPath $legacyTexture }
}
foreach ($name in @('DeepSeekMaid.json','DeepSeekMaid.cfg','README.md','CREDITS.md')) {
    if (Test-Path -LiteralPath (Join-Path $root $name)) { Copy-Item -LiteralPath (Join-Path $root $name) -Destination $stage -Force }
}
Write-Output "Compiled to $stage. No game files were written and the game was not launched."
