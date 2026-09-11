# Richtet den Gaming-Assistenten nach einem frischen "git clone" komplett ein:
# Python-Umgebung + beide Modelle (LLM + Whisper). Ruft dafuer einfach die
# einzelnen Setup-Skripte nacheinander auf, statt deren Logik zu duplizieren -
# die einzelnen Skripte bleiben dadurch auch weiterhin fuer sich alleine
# nutzbar (z.B. um nur ein einzelnes Modell neu herunterzuladen).
#
# Die Server-Programme selbst (llama-server.exe, whisper-server.exe) muessen
# NICHT separat beschafft werden - die liegen bereits fertig im Repo (siehe
# vendor/). fetch_llama.ps1/build_whisper.ps1 bleiben nur als
# Fallback-/Reparatur-Skripte fuer den Ausnahmefall bestehen.
$ErrorActionPreference = 'Stop'
$scripts = Join-Path $PSScriptRoot 'scripts'

Write-Host "=== 1/3: Python-Umgebung ==="
& "$scripts\setup_venv.ps1"

Write-Host "`n=== 2/3: LLM-Modell (Gemma 4 E4B, ca. 5 GB) ==="
& "$scripts\download_llm.ps1"

Write-Host "`n=== 3/3: Whisper-Modell (ca. 0,5 GB) ==="
& "$scripts\fetch_models.ps1"

Write-Host "`nFertig eingerichtet. Start ueber Gaming-Assistent.vbs oder .venv\Scripts\python.exe -m gaming_assistant."
