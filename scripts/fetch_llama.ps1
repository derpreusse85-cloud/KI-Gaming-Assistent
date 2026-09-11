# Fallback-/Reparatur-Skript: laedt eine feste llama.cpp-Server-Version (Windows/Vulkan)
# nach vendor\llama.cpp\. Fuer den Normalfall NICHT noetig - llama-server.exe liegt
# bereits fertig im Repo (klein genug fuers normale Git, siehe CLAUDE.md). Nur noetig,
# falls vendor\llama.cpp\ fehlt/beschaedigt ist oder auf eine neuere Build-Nummer
# aktualisiert werden soll.
# Bewusst eine gepinnte Build-Nummer statt "latest": llama.cpp veroeffentlicht
# mehrmals woechentlich neue Builds, "latest" waere nicht reproduzierbar und koennte
# unbemerkt Verhalten/Flags aendern.
$ErrorActionPreference = 'Stop'
$root   = Split-Path -Parent $PSScriptRoot
$outDir = Join-Path $root 'vendor\llama.cpp'
$build  = 'b10909'   # bei Bedarf aktualisieren: https://github.com/ggml-org/llama.cpp/releases
$asset  = "llama-$build-bin-win-vulkan-x64.zip"
$url    = "https://github.com/ggml-org/llama.cpp/releases/download/$build/$asset"

# Von den vielen im Release-Zip enthaltenen Werkzeugen (llama-cli, llama-bench,
# llama-quantize, diverse *-cli-Tools fuer Bild/Video, ...) braucht dieses Projekt
# ausschliesslich llama-server.exe - der Rest wird nach dem Entpacken wieder
# geloescht, um das Repo schlank zu halten.
$ueberfluessigeExe = @(
    'ggml-rpc-server.exe', 'llama-batched-bench.exe', 'llama-bench.exe', 'llama-cli.exe',
    'llama-completion.exe', 'llama-fit-params.exe', 'llama-gemma3-cli.exe',
    'llama-gguf-split.exe', 'llama-imatrix.exe', 'llama-llava-cli.exe',
    'llama-minicpmv-cli.exe', 'llama-mtmd-cli.exe', 'llama-mtmd-debug.exe',
    'llama-perplexity.exe', 'llama-quantize.exe', 'llama-qwen2vl-cli.exe',
    'llama-results.exe', 'llama-tokenize.exe', 'llama-tts.exe', 'llama.exe'
)

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

    Write-Host "Entferne nicht benoetigte Zusatzwerkzeuge ..."
    foreach ($datei in $ueberfluessigeExe) {
        # Zugehoerige *-impl.dll traegt denselben Namensstamm wie die Exe.
        $stamm = [System.IO.Path]::GetFileNameWithoutExtension($datei)
        Remove-Item (Join-Path $outDir $datei) -ErrorAction SilentlyContinue
        Remove-Item (Join-Path $outDir "$stamm-impl.dll") -ErrorAction SilentlyContinue
    }
}

Write-Host "`nInhalt von $outDir :"
Get-ChildItem $outDir -Filter '*.exe' | ForEach-Object { "{0,-30} {1,8:N0} KB" -f $_.Name, ($_.Length / 1KB) }
