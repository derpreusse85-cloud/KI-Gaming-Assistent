# Legt EIN venv an und installiert die Abhaengigkeiten (kein Server/Client-Split
# mehr wie beim Diktier-Tool). Bewusst NICHT an eine feste Python-Version gebunden
# ("py -3" statt z.B. "py -3.12") - nimmt automatisch die jeweils neueste auf dem
# Rechner installierte Python-3-Version. Frueher war 3.12 fest vorgegeben, weil
# sounddevice/pystray damals noch keine Python-3.14-Wheels hatten - inzwischen
# (getestet 12.09.2026) haben alle Abhaengigkeiten aus requirements.txt Wheels fuer
# 3.14, die Einschraenkung war also nicht mehr noetig und haette bei einem
# kuenftigen Python-Upgrade des Nutzers nur unnoetig im Weg gestanden.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $root '.venv'
$py   = Join-Path $venv 'Scripts\python.exe'

if (-not (Test-Path $py)) {
    Write-Host "Erzeuge .venv mit der neuesten installierten Python-3-Version ..."
    py -3 -m venv $venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "Python 3 wurde nicht gefunden (py.exe nicht im PATH)." -ForegroundColor Yellow
        Write-Host "Bitte zuerst Python 3 installieren: https://www.python.org/downloads/"
        Write-Host "Danach dieses Skript einfach noch einmal ausfuehren."
        throw "Python 3 nicht gefunden - siehe Hinweis oben."
    }
}

& $py -m pip install --upgrade pip --quiet
& $py -m pip install -r (Join-Path $root 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw "pip install fehlgeschlagen" }

Write-Host "`n--- Import-Test ---"
& $py -c "import sounddevice, numpy, pynput, pystray, PIL, requests, yaml; print('ok')"
