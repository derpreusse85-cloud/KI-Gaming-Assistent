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
* **Latenz gemessen und dokumentiert (10.09.2026), siehe `__main__.py::verarbeiten()`** (schreibt
  pro Befehl eine Log-Zeile `Latenz: STT ...s, LLM ...s, ...`): realer End-zu-Ende-Durchlauf mit
  echter Sprache (per Windows-TTS synthetisiert, nicht mit Stille/Rauschen getestet - dazu gleich
  mehr) liegt bei **~0,33-0,35s pro Befehl** (STT ~0,2s, LLM ~0,14s dank LM-Studio-Prompt-Caching
  fuer den identischen System-Prompt). **Nur der allererste Aufruf nach Programmstart oder
  Tray-Profilwechsel kostet ~2,5s** (einmaliges Prefill des 3.541-Token-System-Prompts).
  **Bewusst NICHT gebaut:** weder ein einmaliger Warmup-Aufruf beim Profil-Laden noch ein
  wiederkehrender Warmhalter-Ping waehrend des Spielens - Grund: LM Studio (Modell + Prompt-
  Cache) kann durch VRAM-Druck des Spiels jederzeit verdraengt werden (dasselbe Phaenomen wie
  beim Whisper-Modell, siehe `Diktiertool.md`, Abschnitt "Bildraten-Einbruch"), ein einmaliger
  Warmup schuetzt also nur den Start-Fall, nicht spaetere Verdraengungen mitten im Spiel: ein
  wiederkehrender Ping wuerde davor zuverlaessiger schuetzen, aber dauerhafte GPU-Last waehrend
  des Spielens verursachen. Nutzer hat sich explizit gegen beide Varianten entschieden - die
  seltene ~2,5s-Verzoegerung nach Start/Verdraengung wird bewusst in Kauf genommen.
* **`initial_prompt`-Laenge hat bei echter Sprache keinen messbaren Effekt auf die Latenz**
  (getestet: 0/143/700 Zeichen -> alle ~0,19-0,2s STT-Zeit). Die kuratierte Kurzliste
  (`initial_prompt_schlagwoerter` im Profil, nur Fremdwoerter/Akronyme statt aller 77
  Schlagwoerter) wurde trotzdem eingebaut und bleibt drin (schadet nicht, evtl. fokussierter),
  ist aber kein Latenz-Gewinn - **eine fruehere Messung, die genau das nahelegte, war ein
  Test-Artefakt:** mit digitaler Stille/synthetischem Rauschen als Testaudio halluziniert
  Whisper und loest teure Wiederholungsdurchlaeufe (`temperature_inc`) aus, was die Zeitmessung
  verfaelscht hatte. **Lektion: Whisper-Latenz nur mit echter (oder zumindest TTS-synthetisierter)
  Sprache messen, nie mit Stille oder Rauschen** - Windows-TTS (`System.Speech.Synthesis`,
  Stimme "Microsoft Hedda Desktop", 16kHz-Mono-WAV) hat sich dafuer als schneller Ersatz fuer
  eine echte Aufnahme bewaehrt.
* **Naechste moegliche Schritte (nicht angefangen):** weitere Spielprofile nach demselben YAML-
  Schema ergaenzen; die in Gaming_assistent.md skizzierte zweistufige Trainingsdaten-
  Aufbereitung (Extraktor-Durchlaeufe auf den `training_log.py`-Rohdaten) fuer kuenftiges
  Fine-Tuning.

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

## Geplant: LM Studio abloesen (noch nicht begonnen)

Ueberlegung vom 11.09.2026, weil eine Veroeffentlichung auf GitHub ernsthaft in Betracht gezogen
wird. Eine Pflicht-Abhaengigkeit zu einer separat zu installierenden LM-Studio-Instanz waere fuer
ein Open-Source-Tool eine hohe Einstiegshuerde.

**Ziel:** der Assistent soll komplett ohne LM Studio auskommen.

**Konkurrenz-Recherche (11.09.2026, per Websuche), Korrektur einer fruehen Annahme:** die
urspruengliche Annahme "kein Tool nutzt ein LLM statt fester Kommandophrasen" haelt so **nicht**
stand — **Wingman AI** (wingman-ai.com, Kern Open Source) macht das bereits: freie Formulierung,
LLM interpretiert Intent, loest Tastendruck/Aktion aus, laeuft optional komplett lokal (LM
Studio/Ollama). Der tatsaechliche Unterschied liegt woanders: Wingman AI ist als
**Companion-Plattform** aufgebaut (Charaktere mit eigener Persoenlichkeit, Sprachsynthese-
Antworten inkl. geklonter Stimmen, Chat-Historie, Rollenspiel-Fokus, Skill-Oekosystem fuer
Spotify/Websuche/Bildgenerierung usw. — Tastendruck ist nur eine von vielen Faehigkeiten).
**Dieses Projekt bleibt bewusst ein reiner Befehls-zu-Tastendruck-Uebersetzer ohne Persoenlichkeit,
Konversation oder Sprachausgabe** — das ist die tatsaechlich belastbare Abgrenzung, nicht "LLM
statt fester Phrasen" allein. Zwei andere geprueften Kandidaten sind keine echte Konkurrenz:
VoiceMacro LLM nutzt ein LLM nur zur Makro-*Erstellung*, nicht zur Laufzeit-Spracherkennung;
ottomate ist lokal + kommerziell, nutzt aber eher klassische lokale Spracherkennungsmodelle statt
erkennbar ein generatives LLM zur Intent-Klassifikation. Passende Formulierung fuer einen
kuenftigen README/Pitch: *"Wingman AI ist eine Companion-Plattform mit Charakteren und
Rollenspiel-Fokus, bei der Tastendruck-Steuerung eine von vielen Faehigkeiten ist. Dieses Tool
ist bewusst schlank: ein reiner Sprache-zu-Tastendruck-Uebersetzer ohne Konversation oder
Persoenlichkeit."* (Nebenbefund: Wingman AIs "Wingmen"-Konzept aehnelt eher dem separaten
Nero-Projekt des Nutzers als diesem Gaming-Tool — fuer Nero selbst nicht in diesem Repo
dokumentiert, siehe ggf. dortiges Projekt-Gedaechtnis.)

* **Git LFS einrichten**, das Gemma-4-E4B-Modell direkt ins Repo uebernehmen — analog dazu, wie
  `vendor/whisper.cpp` + Whisper-Modell bereits als eigenstaendige Kopie im Projekt liegen (siehe
  oben, "keine Pfad-Abhaengigkeit zum Diktier-Tool-Repo"). Konsequente Fortsetzung desselben
  Prinzips (keine Fremdabhaengigkeiten) auf die LLM-Komponente.
* **`gaming_assistant/lmstudio.py` und `llm.py` ersetzen**: statt der LM-Studio-OpenAI-API soll
  llama.cpp das LLM direkt ansteuern. Architekturentscheidung noch offen: Python-Bindings
  (`llama-cpp-python`) vs. eigener Subprozess (Vorlage: `gaming_assistant/whisper_proc.py`, das
  bereits denselben Subprozess-Ansatz fuer whisper.cpp nutzt).
* **Lizenzfrage bereits geklaert (11.09.2026, per Websuche verifiziert):** Gemma 4 (die hier
  genutzte Version, `google/gemma-4-e4b`) laeuft seit April 2026 unter **Apache 2.0** — keine
  Redistributions-Einschraenkungen, unproblematisch fuers Einbetten der Modellgewichte per Git
  LFS in ein oeffentliches Repo. Nur Gemma 1-3 liefen noch unter den restriktiveren, selbst
  geschriebenen "Gemma Terms of Use"; fuer dieses Projekt nicht relevant. Kein offener Punkt mehr.

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
