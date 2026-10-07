# Laedt eine Gemma-4-Modelldatei nach gemma-4-<Modell>-it-GGUF\ - liegt nicht im Repo
# (zu gross fuers kostenlose GitHub-Kontingent, siehe CLAUDE.md, Abschnitt "Geplant:
# LM Studio abloesen"), deshalb dieser Download statt Git LFS.
#
# Aufruf:
#   .\scripts\download_llm.ps1                 -> E4B (Standard, ca. 5 GB)
#   .\scripts\download_llm.ps1 -Modell E2B     -> kleineres Modell (ca. 3 GB)
#   .\scripts\download_llm.ps1 -Modell Beide   -> beide Modelle
# Das Modell laesst sich danach im Tray-Menue unter "Sprachmodell" umschalten.
param(
    [ValidateSet('E4B', 'E2B', 'Beide')]
    [string]$Modell = 'E4B'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

function Lade-Modell([string]$name, [string]$groesse) {
    $outDir = Join-Path $root "gemma-4-$name-it-GGUF"
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null

    $quelle = "https://huggingface.co/unsloth/gemma-4-$name-it-GGUF/resolve/main"
    $datei  = "gemma-4-$name-it-Q4_K_M.gguf"
    $dest   = Join-Path $outDir $datei

    if (Test-Path $dest) {
        $gb = [math]::Round((Get-Item $dest).Length / 1GB, 2)
        Write-Host "$datei existiert bereits ($gb GB) - uebersprungen."
    } else {
        Write-Host "Lade $datei (ca. $groesse) ..."
        curl.exe -L --fail --progress-bar -o $dest "$quelle/$datei"
        if ($LASTEXITCODE -ne 0) { Remove-Item $dest -ErrorAction SilentlyContinue; throw "Download fehlgeschlagen" }
    }

    $gb = [math]::Round((Get-Item $dest).Length / 1GB, 2)
    Write-Host "`n$datei bereit ($gb GB) in $outDir"
}

if ($Modell -in 'E4B', 'Beide') { Lade-Modell 'E4B' '5 GB' }
if ($Modell -in 'E2B', 'Beide') { Lade-Modell 'E2B' '3 GB' }
