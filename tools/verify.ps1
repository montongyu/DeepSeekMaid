param([string]$GameDir = 'C:\game\steamapps\common\Slay the Spire 2')
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$data = Join-Path $GameDir 'data_sts2_windows_x86_64'
$resolve = [System.Func[System.Runtime.Loader.AssemblyLoadContext,System.Reflection.AssemblyName,System.Reflection.Assembly]] {
    param($context, $name)
    $candidate = Join-Path $data ($name.Name + '.dll')
    if (Test-Path -LiteralPath $candidate) { return $context.LoadFromAssemblyPath($candidate) }
    return $null
}.GetNewClosure()
[System.Runtime.Loader.AssemblyLoadContext]::Default.add_Resolving($resolve)
try {
    $assembly = [System.Runtime.Loader.AssemblyLoadContext]::Default.LoadFromAssemblyPath((Join-Path $root 'dist\DeepSeekMaid\DeepSeekMaid.dll'))
    $compatibility = $assembly.GetType('DeepSeekMaid.Compatibility', $true)
    $missing = $compatibility.GetMethod('CheckBindings').Invoke($null, @())
    if ($missing.Length -gt 0) { throw ('Missing beta patch targets: ' + ($missing -join ', ')) }
    $resources = $assembly.GetManifestResourceNames()
    if ($resources.Length -ne 11) { throw "Expected 11 embedded resources, found $($resources.Length)." }
    foreach ($resource in $resources) {
        $stream = $assembly.GetManifestResourceStream($resource)
        try {
            if ($stream.Length -lt 100) { throw "Empty resource: $resource" }
            $file = if ($resource -eq 'DeepSeekMaid.cards.index') { Join-Path $root 'assets\cards\index.json' }
                elseif ($resource -eq 'DeepSeekMaid.elements.png') { Join-Path $root 'assets\effects\elemental-orbs.png' }
                elseif ($resource -eq 'DeepSeekMaid.selection.png') { Join-Path $root 'assets\ui\character-select.png' }
                elseif ($resource -eq 'DeepSeekMaid.selection-background.png') { Join-Path $root 'assets\ui\selection-background.png' }
                else { Join-Path $root ('assets\cards\' + $resource.Substring('DeepSeekMaid.'.Length)) }
            $sha = [System.Security.Cryptography.SHA256]::Create()
            try { $embeddedHash = [Convert]::ToHexString($sha.ComputeHash($stream)) } finally { $sha.Dispose() }
            if ($embeddedHash -ne (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash) { throw "Stale embedded resource: $resource" }
        } finally { $stream.Dispose() }
    }
    Write-Output 'PASS: all Harmony targets and reflected fields resolve against the installed beta assemblies.'
    $index = Get-Content -Raw -LiteralPath (Join-Path $root 'assets\cards\index.json') | ConvertFrom-Json -AsHashtable
    $known = [System.Collections.Generic.HashSet[string]]::new()
    foreach ($key in $index.Keys) { [void]$known.Add(($key -replace '[^a-zA-Z0-9]', '').ToLowerInvariant()) }
    $resolver = $assembly.GetType('DeepSeekMaid.PortraitResolver', $true).GetMethod('Resolve', [Reflection.BindingFlags]'NonPublic,Static')
    $game = [System.Runtime.Loader.AssemblyLoadContext]::Default.LoadFromAssemblyPath((Join-Path $data 'sts2.dll'))
    $pool = $game.GetType('MegaCrit.Sts2.Core.Models.CardPools.DefectCardPool', $true)
    $generate = $pool.GetMethod('GenerateAllCards', [Reflection.BindingFlags]'NonPublic,Instance')
    $il = $generate.GetMethodBody().GetILAsByteArray()
    $types = [System.Collections.Generic.HashSet[Type]]::new()
    for ($i = 0; $i -le $il.Length - 5; ++$i) {
        if ($il[$i] -ne 0x28) { continue }
        try {
            $called = $generate.Module.ResolveMethod([BitConverter]::ToInt32($il,$i+1))
            if ($called.IsGenericMethod -and $called.Name -eq 'Card' -and $called.DeclaringType.FullName -eq 'MegaCrit.Sts2.Core.Models.ModelDb') {
                [void]$types.Add($called.GetGenericArguments()[0])
            }
        } catch { }
    }
    if ($types.Count -ne 91) { throw "Expected 91 active Defect card types, found $($types.Count)" }
    foreach ($type in $types) {
        foreach ($id in @($type.Name.ToUpperInvariant(), ('EXTERNAL_POOL:' + $type.Name))) {
            $actual = $resolver.Invoke($null, @($type, $id, $known))
            if ($actual -ne $type.Name.ToLowerInvariant()) { throw "Portrait lookup failed for $($type.Name) / $id" }
        }
    }
    $foreign = $game.GetType('MegaCrit.Sts2.Core.Models.Cards.StrikeIronclad', $true)
    if ($null -ne $resolver.Invoke($null, @($foreign, 'STRIKE_DEFECT', $known))) { throw 'Defect art leaked onto an unrelated card type.' }
    Write-Output 'PASS: 91 active Defect card types resolve with native and prefixed IDs; unrelated cards are excluded.'
    $rig = Get-Content -Raw -LiteralPath (Join-Path $root 'assets\animation\maid.spine-json') | ConvertFrom-Json -AsHashtable
    $selector = $assembly.GetType('DeepSeekMaid.AnimationSelector', $true)
    $selection = [Activator]::CreateInstance($selector,$true)
    $flags = [Reflection.BindingFlags]'NonPublic,Instance'
    $attack = $selector.GetMethod('Attack',$flags)
    $skill = $selector.GetMethod('Skill',$flags)
    $hurt = $selector.GetMethod('Hurt',$flags)
    $chosen = [System.Collections.Generic.HashSet[string]]::new()
    foreach ($i in 1..10) {
        if ($attack.Invoke($selection,@('StrikeDefect')) -ne 'attack') { throw 'Basic Strike must use the approved wide-stance palm attack.' }
    }
    foreach ($i in 1..10) { [void]$chosen.Add($attack.Invoke($selection,@('BallLightning'))) }
    if ($chosen.Count -ne 10) { throw 'Generic attacks did not choose ten distinct attack motions.' }
    foreach ($nativeName in @('Hyperbeam','FlakCannon','Barrage','Claw')) { [void]$chosen.Add($attack.Invoke($selection,@($nativeName))) }
    foreach ($i in 1..6) { [void]$chosen.Add($skill.Invoke($selection,@($false,$false))) }
    foreach ($i in 1..5) {
        [void]$chosen.Add($skill.Invoke($selection,@($true,$false)))
        [void]$chosen.Add($skill.Invoke($selection,@($false,$true)))
        [void]$chosen.Add($hurt.Invoke($selection,@()))
    }
    $staticFlags = [Reflection.BindingFlags]'NonPublic,Static'
    $family = $selector.GetMethod('Family',$staticFlags)
    $returnIdle = $selector.GetMethod('IdleAfter',$staticFlags)
    $selectedActions = @($chosen)
    foreach ($clip in $selectedActions) {
        if (!$rig.animations.ContainsKey($clip)) { throw "Animation selection references a missing clip: $clip" }
        $idleName = $returnIdle.Invoke($null,@($clip))
        if (!$rig.animations.ContainsKey($idleName) -or !$idleName.EndsWith('_loop')) { throw "Missing return idle for $clip" }
        [void]$chosen.Add($idleName)
        if ($clip.StartsWith('hurt') -and $idleName -ne 'idle_angry_loop') { throw 'Hurt must return to annoyed idle.' }
    }
    foreach ($method in @('Greeting','Victory')) {
        foreach ($i in 1..3) {
            $clip = $selector.GetMethod($method,$staticFlags).Invoke($null,@())
            [void]$chosen.Add($clip)
            if ($method -eq 'Greeting') { [void]$chosen.Add($returnIdle.Invoke($null,@($clip))) }
        }
    }
    foreach ($sleepy in @($false,$true)) { [void]$chosen.Add($selector.GetMethod('Rest',$staticFlags).Invoke($null,@($sleepy))) }
    foreach ($clip in @('death','revive')) { [void]$chosen.Add($clip) }
    if ($chosen.Count -ne 50) { throw "Only $($chosen.Count) of 50 animations are reachable from cosmetic routes." }
    foreach ($clip in $chosen) { if (!$rig.animations.ContainsKey($clip)) { throw "Route references missing animation: $clip" } }
    foreach ($clip in @('attack','attack_sweep','attack_double','attack_ranged')) {
        if ($family.Invoke($null,@($clip)) -ne 'attack') { throw 'A duplicate native Attack would cancel an attack variant.' }
    }
    Write-Output 'PASS: all 50 animations are reachable; ten attack variants, guards, powers and hurt routes resolve; hurt returns to annoyed idle.'
    Write-Output 'PASS: all eleven embedded payloads match source SHA-256; no Godot objects were instantiated in this metadata check.'
} finally {
    [System.Runtime.Loader.AssemblyLoadContext]::Default.remove_Resolving($resolve)
}
