# Safe per-user uninstall. By default workspace and presets are preserved.
param([switch]$DeleteUserData)
$ErrorActionPreference = 'Stop'
$dest=Join-Path $env:LOCALAPPDATA 'KiKiModels\LayoutOptimizer'
$ext=Join-Path $env:APPDATA 'Adobe\CEP\extensions\com.kikimodels.layoutoptimizer'
# Never remove an extension that now belongs to another installation.
$cfg=Join-Path $ext 'config.js'
if (Test-Path -LiteralPath $cfg) {
    $raw=Get-Content -LiteralPath $cfg -Raw -Encoding UTF8
    $match=[regex]::Match($raw,'window\.KIKI_PROJECT_ROOT\s*=\s*("(?:\\.|[^"\\])*")\s*;')
    if ($match.Success) {
        $configured=ConvertFrom-Json -InputObject $match.Groups[1].Value
        if ([string]::Equals($configured, $dest, [StringComparison]::OrdinalIgnoreCase)) {
            Remove-Item -LiteralPath $ext -Recurse -Force
            Write-Host 'KiKi CEP extension removed'
        } else { Write-Warning 'CEP extension points elsewhere and was left untouched.' }
    } else { Write-Warning 'CEP configuration was not recognized; extension left untouched.' }
}
foreach ($name in @('runtime','cep','illustrator','assets','installers','docs')) {
    $target=Join-Path $dest $name
    if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force }
}
foreach ($name in @('LICENSE','VERSION','README.md','README_RU.md','README_EN.md','CHANGELOG.md','SHA256SUMS.json','SHA256SUMS.txt')) {
    $file=Join-Path $dest $name
    if (Test-Path -LiteralPath $file) { Remove-Item -LiteralPath $file -Force }
}
if ($DeleteUserData) {
    foreach ($name in @('workspace','presets')) {
        $target=Join-Path $dest $name
        if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force }
    }
    Write-Warning 'User workspace and presets deleted by explicit request.'
} else { Write-Host "Workspace and presets preserved under $dest" }
Write-Host 'CEP developer-mode registry settings have NOT been changed.'
