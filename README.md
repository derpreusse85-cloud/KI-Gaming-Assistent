# Gaming-Sprachassistent

Frei gesprochene Sprache waehrend des Spielens wird per lokalem LLM einer festen Aktion
zugeordnet und als Tastenkombination ausgeloest — z. B. "Ruf die 500-Kilo-Bombe" loest in
Helldivers 2 automatisch den passenden Stratagem-Code aus. Kein Modding des Spiels noetig,
keine festen Kommandophrasen wie bei klassischen Voice-Command-Tools.

Das vollstaendige Konzept samt aller Design-Entscheidungen und der Testreihe steht in
`Gaming_assistent.md`; der aktuelle Entwicklungsstand in `CLAUDE.md`. Dieses README ist die
kurze Gebrauchsanleitung fuer den taeglichen Betrieb.

## Voraussetzungen

* **LM Studio muss laufen**, mit `google/gemma-4-e4b` in der Modellliste (muss nicht manuell
  geladen sein — das Tool laedt es beim Start selbst mit den passenden Parametern).
* Ein Mikrofon.
* **Modelldatei herunterladen** (nicht im Repo enthalten, zu gross fuer GitHub):
  `.\scripts\download_llm.ps1` laedt `gemma-4-E4B-it-Q4_K_M.gguf` automatisch in den Ordner
  `gemma-4-E4B-it-GGUF/` — Details siehe `gemma-4-E4B-it-GGUF/README.md`.

Whisper (eigener `vendor/whisper.cpp`-Build + Modell) und das Python-venv sind auf diesem
Rechner bereits eingerichtet. Falls das Projekt mal auf einen neuen Rechner umzieht: siehe
`scripts/setup_venv.ps1`, `scripts/build_whisper.ps1` und `scripts/fetch_models.ps1`.

### Mindestanforderungen

* **Windows 10/11 (64-Bit)** — `pynput`/`pystray`/`whisper-server.exe` sind Windows-spezifisch,
  keine plattformuebergreifende Unterstuetzung vorgesehen.
* **GPU mit Vulkan-Unterstuetzung**, mindestens **12 GB VRAM insgesamt**. Gemessen auf diesem
  Rechner (`lms ps`): Whisper-Modell ~0,57 GB, Gemma 4 E4B bei Kontext 8192 ~6,33 GB — zusammen
  ~6,9 GB fuers Tool allein, der Rest ist Platz fuers Spiel selbst (Helldivers 2 & Co. brauchen
  ebenfalls mehrere GB VRAM). Ohne GPU laeuft Whisper
  zwar auch auf der CPU, ist dann aber laut Diktier-Tool-Messung (`Diktiertool.md`) fuer
  Push-to-Talk-Latenz zu langsam (z. B. `medium` 8,17 s statt <0,2 s je Aeusserung) — GPU ist
  hier praktisch Pflicht, nicht nur "nice to have".
* **16 GB RAM.**
* Ein LM-Studio-Konto/-Installation mit heruntergeladenem `google/gemma-4-e4b`.

### Empfohlene Anforderungen

* **Dedizierte GPU mit 16 GB+ VRAM** (getestet mit einer RX 7900 XTX, 24 GB) — mehr Reserve
  bedeutet, dass LM Studio waehrend des Spielens seltener aus dem VRAM verdraengt wird (siehe
  `CLAUDE.md`, Abschnitt "Latenz gemessen" zu den Folgen einer Verdraengung).
* **32 GB RAM.**
* **SSD** fuer schnelleres Laden von Whisper-Modell und LLM.

## Starten

Doppelklick auf **`Gaming-Assistent.vbs`** — startet lautlos im Hintergrund, bedienbar ueber
das Icon im System-Tray.

Alternativ mit sichtbarer Konsole (z. B. zum Mitlesen des Logs):

```powershell
.venv\Scripts\python.exe -m gaming_assistant
```

## Bedienung

Push-to-Talk-Taste halten, Befehl sprechen, loslassen. Erkennt das LLM eindeutig eines der im
aktiven Profil hinterlegten Kommandos, wird die zugehoerige Tastenfolge sofort ausgeloest.
Unbekannte oder mehrdeutige Aeusserungen loesen bewusst nichts aus (kein Rateversuch).

**Tray-Menue:**

* **Status/Log anzeigen** — Fenster mit den letzten Logzeilen, inkl. der Latenz je Befehl
  (`Latenz: STT ...s, LLM ...s, ...`).
* **Profil** — aktives Spielprofil wechseln (Liste aller YAML-Dateien in `profiles/`).
* **Push-to-talk festlegen ...** — neue PTT-Taste (Tastatur oder Maustaste 4/5/Mitte) durch
  einmaliges Druecken festlegen.
* **Beenden**

Die Einstellungen (aktives Profil, PTT-Taste) werden automatisch in `config.json` gespeichert
und beim naechsten Start wiederhergestellt.

## Ein neues Spielprofil anlegen

Eine YAML-Datei in `profiles/` (Dateiname ohne `.yaml` = Profilname im Tray-Menue). Beispiel
anhand eines einzelnen Tags:

```yaml
kontextlaenge: 4096          # Kontextlaenge fuers LLM, siehe unten
halte_taste: "ctrl"          # optional: Taste, die waehrend jeder Tasten-Sequenz gehalten wird

LANDEGESTELL:
  schlagwort: ["Landegestell", "Fahrgestell"]  # eines davon muss im Befehl woertlich vorkommen
  beispiel: "Fahrgestell einfahren"            # Few-Shot-Beispiel fuer das LLM
  taste: ["shift", "n"]                        # wird als Tipp-Sequenz ausgefuehrt (nacheinander, nicht gleichzeitig)

ORBITALSCHLAG:
  beschreibung: "nur wenn ein Orbitalschlag angefordert wird"  # frei formuliert statt Wortbindung
  beispiel: "Ruf den Orbitalschlag"
  taste: ["ctrl", "o"]
```

* **`schlagwort`** und **`beschreibung`** haben zwei unabhaengige Aufgaben — ein Tag braucht
  mindestens eines von beiden, oft reicht eines allein:
  * **`schlagwort`**: eine Liste in eckigen Klammern, auch bei nur einem Wort (`["EAT"]`). Ohne
    eigene `beschreibung` bindet es den Tag an das woertliche Vorkommen **eines** dieser Woerter
    im Befehl (Praezision vor Vollstaendigkeit) — praktisch fuer Spiele mit vielen aehnlich
    klingenden Kommandos wie Helldivers 2. Eigene Woerter lassen sich einfach mit Komma innerhalb
    der Klammern ergaenzen. Unabhaengig davon speist `schlagwort` auch das Whisper-Vokabular
    (`initial_prompt`) — kann also selbst bei einem Tag mit eigener `beschreibung` sinnvoll sein,
    einfach um ein einzelnes Fremdwort daraus dort bekannt zu machen.
  * **`beschreibung`** (optional): ersetzt die wortgebundene Standardbeschreibung durch freien
    Text. Sinnvoll bei Spielen mit wenigen, eindeutigen Kommandos, die keine strikte Wortbindung
    brauchen (siehe `ORBITALSCHLAG` oben) — dann kann `schlagwort` komplett entfallen.
* **`taste`**: Liste einzelner Tasten, die **nacheinander** getippt werden (kein gleichzeitig
  gehaltener Hotkey). Sondertasten wie `ctrl`, `shift`, `alt`, `tab`, `up`/`down`/`left`/`right`
  sind moeglich, sonst einzelne Zeichen.
* **`halte_taste`** (optional, Profil- oder Tag-Ebene): eine Taste, die waehrend der ganzen
  `taste`-Sequenz zusaetzlich gehalten wird — bei Helldivers 2 z. B. Strg, weil das Spiel
  Stratagem-Codes so entgegennimmt.
* **`kontextlaenge`**: einmalig ermitteln (Prompt-Tokens des generierten System-Prompts plus
  Marge) und hier eintragen — wird beim Laden des Profils an LM Studio durchgereicht.
* **`initial_prompt_schlagwoerter`** (optional): kuratierte Liste einzelner Fremdwoerter/
  Akronyme/Eigennamen fuers Whisper-Vokabular. Bei echter Sprache ohne messbaren Latenz-Effekt
  (siehe `CLAUDE.md`), aber unschaedlich; kann auch ganz weggelassen werden.

Details und Hintergrund zu jedem Feld: `Gaming_assistent.md`, Abschnitt "Aktionslisten-Format".

## Trainingsdaten

Jeder Sprachbefehl wird ungefiltert nach `training_data/raw/<Datum>.jsonl` protokolliert (Rohtext
+ erkannte Tags) — Grundlage fuer eine spaetere Fine-Tuning-Aufbereitung, siehe
`Gaming_assistent.md`, Abschnitt "Trainingsdaten-Sammlung".
