# Laedt eine feste llama.cpp-Server-Version (Windows/Vulkan) nach vendor\llama.cpp\ -
# eigenstaendige Kopie, analog zu vendor\whisper.cpp (siehe CLAUDE.md, "eigenstaendige
# Kopien"). Bewusst eine gepinnte Build-Nummer statt "latest": llama.cpp veroeffentlicht
# mehrmals woechentlich neue Builds, "latest" waere nicht reproduzierbar und koennte
# unbemerkt Verhalten/Flags aendern.
$ErrorActionPreference = 'Stop'
$root   = Split-Path -Parent $PSScriptRoot
$outDir = Join-Path $root 'vendor\llama.cpp'
$build  = 'b10909'   # bei Bedarf aktualisieren: https://github.com/ggml-org/llama.cpp/releases
$asset  = "llama-$build-bin-win-vulkan-x64.zip"
$url    = "https://github.com/ggml-org/llama.cpp/releases/download/$build/$asset"

New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$zielExe = Join-Path $outDir 'llama-server.exe'

if (Test-Path $zielExe) {
    Write-Host "llama-server.exe existiert bereits in $outDir - uebersprungen."
} else {
    $tmpZip = Join-Path $env:TEMP $asset
    Write-Host "Lade $asset ..."
    curl.exe -L --fail --progress-bar -o $tmpZip $url
    if ($LASTEXITCODE -ne 0) { Remove-Item $tmpZip -ErrorAction SilentlyContinue; throw "Download fehlgeschlagen" }

    Write-Host "Entpacke nach $outDir ..."
    Expand-Archive -Path $tmpZip -DestinationPath $outDir -Force
    Remove-Item $tmpZip

    if (-not (Test-Path $zielExe)) {
        throw "llama-server.exe nach dem Entpacken nicht gefunden - Archivstruktur pruefen."
    }
}

Write-Host "`nInhalt von $outDir :"
Get-ChildItem $outDir -Filter '*.exe' | ForEach-Object { "{0,-30} {1,8:N0} KB" -f $_.Name, ($_.Length / 1KB) }
