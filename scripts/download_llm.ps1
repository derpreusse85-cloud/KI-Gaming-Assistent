# Laedt die Gemma-4-E4B-Modelldatei nach gemma-4-E4B-it-GGUF\ - liegt nicht im Repo
# (zu gross fuers kostenlose GitHub-Kontingent, siehe CLAUDE.md, Abschnitt "Geplant:
# LM Studio abloesen"), deshalb dieser Download statt Git LFS.
$ErrorActionPreference = 'Stop'
$root   = Split-Path -Parent $PSScriptRoot
$outDir = Join-Path $root 'gemma-4-E4B-it-GGUF'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$quelle = 'https://huggingface.co/unsloth/gemma-4-E4B-it-GGUF/resolve/main'
$datei  = 'gemma-4-E4B-it-Q4_K_M.gguf'
$dest   = Join-Path $outDir $datei

if (Test-Path $dest) {
    $gb = [math]::Round((Get-Item $dest).Length / 1GB, 2)
    Write-Host "$datei existiert bereits ($gb GB) - uebersprungen."
} else {
    Write-Host "Lade $datei (ca. 5 GB) ..."
    curl.exe -L --fail --progress-bar -o $dest "$quelle/$datei"
    if ($LASTEXITCODE -ne 0) { Remove-Item $dest -ErrorAction SilentlyContinue; throw "Download fehlgeschlagen" }
}

$gb = [math]::Round((Get-Item $dest).Length / 1GB, 2)
Write-Host "`n$datei bereit ($gb GB) in $outDir"
