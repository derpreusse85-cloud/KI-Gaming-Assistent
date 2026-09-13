# Changelog

Alle nennenswerten Aenderungen dieses Projekts werden hier zusammengefasst. Ausfuehrlichere
Hintergruende und Design-Entscheidungen stehen in `CLAUDE.md`; das vollstaendige Konzept in
`Gaming_assistent.md`.

## [1.3] - 2026-09-13

### Hinzugefuegt

- Drittes Spielprofil: **Elite Dangerous** (`profiles/EliteDangerous.yaml`, 13 Kommandos:
  Energieverteilung, Fahrgestell, FSD, Ladeluke, Stop, Boost, Heatsink, Schildzellenbank, ECM,
  Duempel). Anders als die Helldivers-Profile mit freier `beschreibung` statt Wortbindung, da nur
  wenige, klar unterscheidbare Kommandos. Gegen den echten llama-server getestet (31/31 korrekt,
  inkl. freier Paraphrasen und Mehrfachbefehlen). Drei Kommandos haben im Spiel standardmaessig
  keine Taste und muessen von jedem Nutzer selbst belegt werden.
- Trainingsdaten-Aufzeichnung ueber einen neuen Tray-Menuepunkt ein-/ausschaltbar (Standard: an,
  kein Verhaltenswechsel fuer bestehende Nutzer).
- `LICENSE` (GPL-3.0) sowie Hinweise zu Drittanbieter-Lizenzen (vendor/-Binaries MIT, Gemma-4-
  Gewichte Apache-2.0) in der README.

### Geaendert

- Profil-Dateien umbenannt: `Helldivers1_Stratagems.yaml` -> `Helldivers1.yaml`,
  `Helldivers2_Stratagems.yaml` -> `Helldivers2.yaml`.
- Programm faellt beim Start automatisch auf ein tatsaechlich vorhandenes Profil zurueck, falls
  der konfigurierte Profilname zu keiner Datei mehr passt (z.B. nach einer Umbenennung) - der
  Profile-Ordner bleibt die einzige Quelle der Wahrheit, kein hart hinterlegter Dateiname mehr
  noetig.
- VRAM-Messwerte in der README aktualisiert (~4,26 GB gesamt, per Windows-GPU-Performance-Counter
  neu gemessen).
- README ergaenzt um einen Hinweis, dass Code und System-Prompt aktuell fest auf Gemma 4 E4B
  ausgelegt sind, sowie um eine Anleitung zum Erweitern bestehender Profile um neue Kommandos.

## [1.2] - 2026-09-11

### Hinzugefuegt

- Zweites Spielprofil: **Helldivers 1** (55 Stratageme, Codes aus einer Wiki-Quelle abgetippt).
  Noch nicht im echten Spiel getestet, da der Nutzer Helldivers 1 nicht besitzt - `taste`-Werte
  koennen vor produktivem Einsatz noch Korrekturen brauchen.

## [1.1] - 2026-09-11

### Geaendert

- **LM Studio als Pflichtabhaengigkeit entfernt.** llama.cpp laeuft jetzt als eigener, selbst
  verwalteter `llama-server`-Subprozess (analog zum bestehenden `whisper-server`-Muster), startet
  bei einem Profilwechsel mit anderer Kontextlaenge automatisch neu. Latenz dabei leicht
  verbessert (~0,1s Wiederholung, ~1,5s Cold-Start statt vorher ~0,14s/~2,5s), VRAM-Bedarf
  spuerbar gesunken (~3,3 GB statt ~6,33 GB bei gleicher Kontextlaenge).
- Ersteinrichtung deutlich vereinfacht: `llama-server.exe`/`whisper-server.exe` liegen fertig im
  Repo (kein Download/Kompilieren mehr noetig), ein einziges `setup.ps1` im Hauptordner richtet
  Python-Umgebung und beide Modell-Downloads in einem Aufruf ein.
- Tray-Icon von Mikrofon auf Gamepad umgestellt.

## [1.0] - 2026-09-09

### Hinzugefuegt

- Erste funktionierende Version: Push-to-Talk -> Whisper (STT) -> LLM-Klassifikation (Gemma 4
  E4B ueber LM Studio) -> Tastensequenz, End-zu-Ende gegen das laufende Helldivers 2 bestaetigt.
  Erstes Spielprofil: **Helldivers 2** (77 Stratageme).
