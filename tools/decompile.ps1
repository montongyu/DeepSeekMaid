param(
    [Parameter(Mandatory=$true)][string[]]$Types,
    [string]$GameDir = 'C:\game\steamapps\common\Slay the Spire 2'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$library = Join-Path $root '.tools\decompiler\lib\netstandard2.0\ICSharpCode.Decompiler.dll'
Add-Type -Path $library
$settings = [ICSharpCode.Decompiler.DecompilerSettings]::new()
$settings.ThrowOnAssemblyResolveErrors = $false
$assembly = Join-Path $GameDir 'data_sts2_windows_x86_64\sts2.dll'
$decompiler = [ICSharpCode.Decompiler.CSharp.CSharpDecompiler]::new($assembly, $settings)
$target = Join-Path $root 'work\decompiled'
New-Item -ItemType Directory -Path $target -Force | Out-Null
foreach ($name in $Types) {
    $fullName = [ICSharpCode.Decompiler.TypeSystem.FullTypeName]::new($name)
    $source = $decompiler.DecompileTypeAsString($fullName)
    $path = Join-Path $target ($name + '.cs')
    [System.IO.File]::WriteAllText($path, $source)
    Write-Output $path
}
