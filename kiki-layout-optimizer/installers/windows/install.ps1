# Transparent per-user Windows installer. Does not download code or enable CEP developer mode silently.
param(
    [string]$Source = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path,
    [switch]$SkipCopy,
    [switch]$EnableUnsignedDev
)
$ErrorActionPreference = 'Stop'
$dest = Join-Path $env:LOCALAPPDATA 'KiKiModels\LayoutOptimizer'
$sourceRoot = if ($SkipCopy) { $dest } else { (Resolve-Path -LiteralPath $Source).Path }
$manifest = Join-Path $sourceRoot 'SHA256SUMS.txt'
if (-not (Test-Path -LiteralPath $manifest -PathType Leaf)) { throw 'Missing SHA256SUMS.txt — use a verified portable release.' }
$checked = 0
foreach ($line in [System.IO.File]::ReadAllLines($manifest)) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    if ($line -notmatch '^([0-9a-fA-F]{64})  (.+)$') { throw "Malformed SHA-256 entry: $line" }
    $expectedHash = $Matches[1].ToLowerInvariant()
    $relative = $Matches[2]
    if ($relative -match '(^/|^[a-zA-Z]:|(^|/|\\)\.\.($|/|\\))') { throw "Unsafe manifest path: $relative" }
    $file = Join-Path $sourceRoot ($relative -replace '/', '\')
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Missing package file: $relative" }
    $got = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($got -ne $expectedHash) { throw "Integrity check failed: $relative" }
    $checked++
}
if ($checked -lt 8) { throw 'Unexpectedly short package manifest' }
if (-not (Test-Path -LiteralPath (Join-Path $sourceRoot 'runtime\kiki-worker.exe'))) {
    throw 'Windows executable missing. Download Windows portable, not the source archive.'
}
Write-Host "Package integrity: verified $checked files"
if (-not $SkipCopy) {
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    foreach ($item in @('runtime','cep','illustrator','assets','installers','docs')) {
        $from=Join-Path $sourceRoot $item
        if (Test-Path $from) {
            $to=Join-Path $dest $item
            New-Item -ItemType Directory -Force -Path $to | Out-Null
            Copy-Item -Path (Join-Path $from '*') -Destination $to -Recurse -Force
        }
    }
    foreach ($name in @('LICENSE','VERSION','README.md','README_RU.md','README_EN.md','CHANGELOG.md','SHA256SUMS.json','SHA256SUMS.txt')) {
        $file=Join-Path $sourceRoot $name
        if (Test-Path -LiteralPath $file) { Copy-Item -LiteralPath $file -Destination $dest -Force }
    }
}
$ext = Join-Path $env:APPDATA 'Adobe\CEP\extensions\com.kikimodels.layoutoptimizer'
New-Item -ItemType Directory -Force -Path $ext | Out-Null
Copy-Item -Path (Join-Path $dest 'cep\com.kikimodels.layoutoptimizer\*') -Destination $ext -Recurse -Force
$escaped = ConvertTo-Json -InputObject $dest -Compress
Set-Content -LiteralPath (Join-Path $ext 'config.js') -Value ("window.KIKI_PROJECT_ROOT = " + $escaped + ";") -Encoding UTF8
if ($EnableUnsignedDev) {
    foreach ($n in @(11,12)) {
        $key="HKCU:\Software\Adobe\CSXS.$n"
        New-Item -Path $key -Force | Out-Null
        New-ItemProperty -Path $key -Name PlayerDebugMode -Value '1' -PropertyType String -Force | Out-Null
    }
    Write-Warning 'Unsigned Adobe CEP developer mode enabled for current user (CSXS.11/12).'
}
Write-Host "KiKi installed: $dest"
Write-Host 'Restart Illustrator. Developer mode remains opt-in.'
