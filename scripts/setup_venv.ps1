# Legt EIN venv an und installiert die Abhaengigkeiten (kein Server/Client-Split
# mehr wie beim Diktier-Tool). Python 3.12, aus denselben Gruenden wie dort:
# 3.14 hat noch keine Wheels fuer sounddevice/pystray.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $root '.venv'
$py   = Join-Path $venv 'Scripts\python.exe'

if (-not (Test-Path $py)) {
    Write-Host "Erzeuge .venv mit Python 3.12 ..."
    py -3.12 -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw "venv-Erstellung fehlgeschlagen" }
}

& $py -m pip install --upgrade pip --quiet
& $py -m pip install -r (Join-Path $root 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw "pip install fehlgeschlagen" }

Write-Host "`n--- Import-Test ---"
& $py -c "import sounddevice, numpy, pynput, pystray, PIL, requests, yaml; print('ok')"
