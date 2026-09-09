# CLAUDE.md

Gaming-Sprachassistent: freie gesprochene Sprache waehrend des Spielens wird per LLM in eine
feste Aktion klassifiziert und als Tastenkombination ausgeloest. Konzept siehe
`Gaming_assistent.md`. Nicht nur fuer Helldivers 2 gedacht — dessen Profil ist nur das erste von
mehreren geplanten Spielprofilen.

## Stand der Arbeit (fuer den Wiedereinstieg in einer neuen Session)

**Version 1.0 fertig und im echten Spiel bestaetigt (09.09.2026).** Push-to-Talk -> Whisper ->
LLM-Klassifikation -> Tastensequenz funktioniert Ende-zu-Ende gegen das laufende Helldivers 2:
richtig erkannte Tags loesen korrekt die passende Stratagem-Tastenfolge aus, nicht im Profil
enthaltene Kommandos loesen (wie vorgesehen) keine Aktion aus.

* **Modulstruktur** (Paket `gaming_assistant/`, ein einziger Prozess, als Vorlage aus
  `F:\Projekte\KI Diktier Tool` uebernommen, aber ohne WebSocket/Token-Auth/Server-Client-Split):
  `config.py` (globale JSON-Config), `profile.py` (YAML-Profil laden), `prompt.py`
  (System-Prompt + Whisper-initial_prompt aus dem Profil generieren), `parser.py`
  (Tag-Extraktion, verwirft bei Zweifel statt zu raten), `keypress.py` (Tastensequenz per
  pynput), `whisper_proc.py` + `stt.py` (whisper-server-Subprozess + Einzel-Transkription, kein
  rollierendes Fenster), `lmstudio.py` + `llm.py` (Modell laden ueber `lms`-CLI +
  Klassifikations-Request), `ptt.py` + `ptt_dialog.py` + `audio.py` (Push-to-Talk inkl.
  Tray-Dialog zum Aendern der PTT-Taste zur Laufzeit, Mikrofon-Aufnahme), `tray.py` + `icons.py`
  + `logbuf.py` (Tray-Icon mit Profil- und PTT-Auswahl-Menue, Log-Fenster), `training_log.py`
  (ungefiltertes JSONL-Live-Logging fuer spaeteres Fine-Tuning), `__main__.py` (verdrahtet
  alles). Start ueber `Gaming-Assistent.vbs` (lautlos, `.venv\Scripts\pythonw.exe -m
  gaming_assistant`) oder `python -m gaming_assistant` mit Konsole.
* **Design-Entscheidung `halte_taste`:** die `taste`-Listen im Profil sind IMMER eine
  Tipp-Sequenz (nacheinander druecken/loslassen), niemals eine gleichzeitig gehaltene
  Kombination. Optionales Profil-Feld `halte_taste` (bei Helldivers 2: `"ctrl"`) haelt waehrend
  der ganzen Sequenz eine Zusatztaste gedrueckt — noetig, weil Helldivers-2-Stratagem-Codes
  exakt so funktionieren.
* **`profiles/Helldivers2_Stratagems.yaml`** ist das erste, im echten Spiel bestaetigte Profil.
  Tasten sind als Pfeiltasten (`up`/`down`/`left`/`right`, nicht mehr WASD) hinterlegt, weil der
  Nutzer die Spielbelegung entsprechend umgestellt hat. Zwei Abtippfehler wurden im Zuge des
  Testens gefunden und korrigiert (`Panzerabwehrstellung`, `Automatische_Kanone`) — die
  `taste`-Werte gelten weiterhin als vorlaeufig aenderbar, nicht als endgueltig fixiert.
* **`vendor/whisper.cpp` und Whisper-Modell sind eigenstaendige Kopien**, keine Pfad-
  Abhaengigkeit zum Diktier-Tool-Repo (aus dessen fertigem Build kopiert: nur `whisper-
  server.exe` + noetige DLLs, nur die Q5-Deutsch-Modellvariante). `scripts/build_whisper.ps1`/
  `scripts/fetch_models.ps1` bleiben als Vorlage liegen, falls die Kopie mal neu erzeugt werden
  muss. `scripts/setup_venv.ps1` legt EIN venv an.
* **Bekannter, nicht als kritisch eingestufter Fund:** bei rein digitaler Stille (Testfall, kein
  echtes Mikrofon-Rauschen) halluziniert Whisper gelegentlich Text statt leer zu bleiben. Im
  echten Spielbetrieb bisher nicht als Problem aufgefallen.
* **Naechste moegliche Schritte (nicht angefangen):** weitere Spielprofile nach demselben YAML-
  Schema ergaenzen; die in Gaming_assistent.md skizzierte zweistufige Trainingsdaten-
  Aufbereitung (Extraktor-Durchlaeufe auf den `training_log.py`-Rohdaten) fuer kuenftiges
  Fine-Tuning; Whisper-`initial_prompt`-Wirksamkeit ist mitgebaut, aber ihr tatsaechlicher Nutzen
  noch nicht gezielt evaluiert.

* `Gaming_assistent.md` ist das massgebliche, vollstaendige Konzept — bei Widersprueche zwischen
  dieser Zusammenfassung hier und `Gaming_assistent.md` gilt **immer** `Gaming_assistent.md`.
  Alle Designentscheidungen stehen im Abschnitt "Bereits entschieden", das vollstaendige
  Testergebnis im Abschnitt "Testreihe (abgeschlossen)" — **keine offenen Konzeptfragen mehr**,
  siehe dort fuer die Begruendung.
* **Kernentscheidungen kurz:** ein Prozess statt Server/Client, Push-to-Talk, Whisper
  `large-v3-turbo-german-q5` fest auf Deutsch, LLM-Klassifikation statt Stringmatch
  (`google/gemma-4-e4b`, `temperature=0`, Denkmodus in diesem LM-Studio-Setup bereits aus),
  Tags im Format `&&TAG&&`, `&&NONE&&` bei Uneindeutigkeit, YAML-Profil pro Spiel mit
  `schlagwort`/`beispiel`/`taste`/`kontextlaenge`-Feldern (Details siehe „Aktionslisten-Format").
  Die vorherige Testreihe (vier Runden, zuletzt 105/107 auf der vollen 77-Tag-Helldivers-2-Liste)
  ist im Detail in `Gaming_assistent.md`, Abschnitt "Testreihe" dokumentiert.

## Uebertragbare Lektionen aus dem Vorgaengerprojekt

Volle Doku in `Diktiertool.md`:

* **LM Studio ignoriert `enable_thinking`.** Wirksam ist nur `/no_think` im Prompt
  (Qwen-Konvention, nicht bei allen Modellen) bzw. bei manchen Modellen der Schalter
  Inference -> Custom Fields -> "Enable Thinking" direkt in LM Studio. Bei diesem Projekt
  besonders wichtig, da Denk-Tokens vor der Tag-Ausgabe eine im Spiel spuerbare Verzoegerung
  verursachen wuerden. Fuer `google/gemma-4-e2b` und `google/gemma-4-e4b` bereits getestet und
  bestaetigt aus, siehe "Stand der Arbeit" oben.
* **`/load` von whisper-server beendet sich mit `exit(1)`** bei ungueltigem Modellpfad. Nie
  einen extern gelieferten Pfad durchreichen, nur Namen gegen einen eigenen Verzeichnis-Scan
  aufloesen.
* **pynput spielt eigene synthetische Anschlaege an den eigenen Listener zurueck.** Bei
  Tastendruck-Simulation (hier: Aktionstaste ausloesen) beachten, falls der Prozess auch
  eigene Eingaben beobachtet.
* **Kurzer klarer Fliesstext im Prompt schlaegt eine lange Regelliste.** Gemessen mehrfach im
  Diktier-Tool (Bereinigungs- und Uebersetzungs-Prompt). Gilt vermutlich auch fuer den
  Tag-Klassifikations-Prompt hier.
* **Marker/Tag-Parser robust bauen:** bei abgeschnittener Antwort (`finish_reason == "length"`)
  oder unbekanntem Marker verwerfen statt zu raten — hier gibt es kein sinnvolles Fallback
  ausser Nichtstun (siehe `Gaming_assistent.md`, Abschnitt Parser-Sicherheit).

Der Code wird deutsch kommentiert, Bezeichner gemischt deutsch/englisch, wie im
Diktier-Tool. Neue Kommentare auf Deutsch, ohne Umlaute im Quelltext (Ausnahme: Nutzertexte
und LLM-Prompts, dort sind Umlaute erwuenscht).
