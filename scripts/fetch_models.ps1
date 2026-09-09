# Laedt das Whisper-Modell nach models\ - eigenstaendig fuer dieses Projekt,
# bewusst keine Abhaengigkeit zum Diktier-Tool-Repo (siehe CLAUDE.md).
#
# Nur EIN Modell noetig: laut Konzept (Gaming_assistent.md, "Bereits entschieden")
# ist large-v3-turbo-german-q5 fest vorgegeben, kein Modellwechsel zur Laufzeit.
# Das Modell liegt in einem anderen HuggingFace-Repo als das ggml-Original und
# heisst dort ggml-model-q5_0.bin - deshalb die Umbenennung beim Download.
$ErrorActionPreference = 'Stop'
$root   = Split-Path -Parent $PSScriptRoot
$outDir = Join-Path $root 'models'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$de   = 'https://huggingface.co/cstr/whisper-large-v3-turbo-german-ggml/resolve/main'
$dest = Join-Path $outDir 'ggml-large-v3-turbo-german-q5.bin'

if (Test-Path $dest) {
    $mb = [math]::Round((Get-Item $dest).Length / 1MB, 1)
    Write-Host "ggml-large-v3-turbo-german-q5.bin existiert bereits ($mb MB) - uebersprungen."
} else {
    Write-Host "Lade ggml-large-v3-turbo-german-q5.bin ..."
    curl.exe -L --fail --progress-bar -o $dest "$de/ggml-model-q5_0.bin"
    if ($LASTEXITCODE -ne 0) { Remove-Item $dest -ErrorAction SilentlyContinue; throw "Download fehlgeschlagen" }
}

Write-Host "`nModelle in models\:"
Get-ChildItem $outDir -Filter '*.bin' | ForEach-Object { "{0,-34} {1,8:N0} MB" -f $_.Name, ($_.Length / 1MB) }
