# Klont und baut whisper.cpp mit Vulkan-Backend - eigener Build fuer dieses Projekt,
# bewusst keine Abhaengigkeit zum Diktier-Tool-Repo (siehe CLAUDE.md).
# Voraussetzungen: Git, CMake, VS Build Tools (Desktopentwicklung mit C++), Vulkan SDK.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$src  = Join-Path $root 'vendor\whisper.cpp'

if (-not $env:VULKAN_SDK) { throw "VULKAN_SDK ist nicht gesetzt - Vulkan SDK installieren und Shell neu starten." }
# glslc wird zum Kompilieren der Vulkan-Shader gebraucht
$env:PATH = "$env:VULKAN_SDK\Bin;$env:PATH"

if (-not (Test-Path $src)) {
    git clone --depth 1 https://github.com/ggml-org/whisper.cpp $src
} else {
    Write-Host "vendor\whisper.cpp existiert bereits - ueberspringe clone."
}

cmake -S $src -B "$src\build" -DGGML_VULKAN=ON -DCMAKE_BUILD_TYPE=Release
if ($LASTEXITCODE -ne 0) { throw "cmake configure fehlgeschlagen" }

cmake --build "$src\build" --config Release -j
if ($LASTEXITCODE -ne 0) { throw "cmake build fehlgeschlagen" }

Write-Host "`nGebaute Binaries:"
Get-ChildItem -Path "$src\build" -Recurse -Filter 'whisper-*.exe' | ForEach-Object { $_.FullName }
