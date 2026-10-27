$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$target = Join-Path $root '.tools'
New-Item -ItemType Directory -Path $target -Force | Out-Null
$packages = @(
    @{ Name='roslyn'; Id='microsoft.net.compilers.toolset'; Version='4.14.0' },
    @{ Name='decompiler'; Id='icsharpcode.decompiler'; Version='9.1.0.7988' }
)
foreach ($package in $packages) {
    $zip = Join-Path $target ($package.Name + '.zip')
    $url = 'https://api.nuget.org/v3-flatcontainer/{0}/{1}/{0}.{1}.nupkg' -f $package.Id,$package.Version
    Invoke-WebRequest -Uri $url -OutFile $zip -TimeoutSec 120
    Expand-Archive -LiteralPath $zip -DestinationPath (Join-Path $target $package.Name) -Force
}
Write-Output 'Project-local tools ready. No global tools or game files were changed.'
