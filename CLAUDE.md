# CLAUDE.md

Gaming-Sprachassistent: freie gesprochene Sprache waehrend des Spielens wird per LLM in eine
feste Aktion klassifiziert und als Tastenkombination ausgeloest. Konzept siehe
`Gaming_assistent.md`. Nicht nur fuer Helldivers 2 gedacht — dessen Profil ist nur das erste von
mehreren geplanten Spielprofilen.

**Hinweis:** `Diktiertool.md` (Kopie der `CLAUDE.md` des unabhaengigen Diktier-Tool-Projekts) und
`Gemma4.md` (rohe Recherche-Notizen) liegen nur lokal vor, nicht im Git-Repo (seit 12.09.2026,
siehe `.gitignore`). Die daraus fuer dieses Projekt relevanten Erkenntnisse stehen bereits
zusammengefasst an ihrer jeweiligen Stelle in diesem Dokument sowie in `Gaming_assistent.md` -
keine direkten Dateiverweise mehr darauf (12.09.2026 auch dort bereinigt).

## Stand der Arbeit (fuer den Wiedereinstieg in einer neuen Session)

**Version 1.0 fertig und im echten Spiel bestaetigt (09.09.2026), seither auf v1.4 (13.09.2026,
Git-Tags vorhanden).** Push-to-Talk -> Whisper -> LLM-Klassifikation -> Tastensequenz
funktioniert Ende-zu-Ende gegen das laufende Helldivers 2: richtig erkannte Tags loesen korrekt
die passende Stratagem-Tastenfolge aus, nicht im Profil enthaltene Kommandos loesen (wie
vorgesehen) keine Aktion aus. v1.1: LM Studio abgeloest (siehe eigener Abschnitt weiter unten).
v1.2: zweites Spielprofil (Helldivers 1) ergaenzt. v1.3: drittes Spielprofil (Elite Dangerous)
ergaenzt, Trainingsdaten-Aufzeichnung per Tray abschaltbar, GitHub-Veroeffentlichung vorbereitet
(siehe eigener Abschnitt "Veroeffentlichung vorbereitet" weiter unten). v1.4: Feuergruppen-
Direktwahl fuer Elite Dangerous per `Status.json`-Auslesen (neues Modul `ed_status.py`), zwei
weitere Elite-Dangerous-Kommandos (`Aufhaengungen`, `Moduswechsel`), Debug-Log per Tray-Haken
umschaltbar inkl. Log-Datei (siehe "Stand der Arbeit" unten fuer Details).

* **Modulstruktur** (Paket `gaming_assistant/`, ein einziger Prozess, als Vorlage aus
  `F:\Projekte\KI Diktier Tool` uebernommen, aber ohne WebSocket/Token-Auth/Server-Client-Split):
  `config.py` (globale JSON-Config), `profile.py` (YAML-Profil laden), `prompt.py`
  (System-Prompt + Whisper-initial_prompt aus dem Profil generieren), `parser.py`
  (Tag-Extraktion, verwirft bei Zweifel statt zu raten), `keypress.py` (Tastensequenz per
  pynput), `whisper_proc.py` + `stt.py` (whisper-server-Subprozess + Einzel-Transkription, kein
  rollierendes Fenster), `llama_proc.py` + `llm.py` (llama-server-Subprozess, startet bei
  Kontextlaengen-Aenderung automatisch neu, + Klassifikations-Request), `ptt.py` +
  `ptt_dialog.py` + `audio.py` (Push-to-Talk inkl.
  Tray-Dialog zum Aendern der PTT-Taste zur Laufzeit, Mikrofon-Aufnahme), `tray.py` + `icons.py`
  + `logbuf.py` (Tray-Icon mit Profil- und PTT-Auswahl-Menue, Log-Fenster), `training_log.py`
  (ungefiltertes JSONL-Live-Logging fuer spaeteres Fine-Tuning), `ed_status.py` (liest die von
  Elite Dangerous selbst geschriebene `Status.json`, nur fuer die Feuergruppen-Tags dieses einen
  Profils gebraucht, siehe unten), `__main__.py` (verdrahtet alles). Start ueber
  `Gaming-Assistent.vbs` (lautlos, `.venv\Scripts\pythonw.exe -m gaming_assistant`) oder
  `python -m gaming_assistant` mit Konsole.
* **Design-Entscheidung `halte_taste`:** die `taste`-Listen im Profil sind IMMER eine
  Tipp-Sequenz (nacheinander druecken/loslassen), niemals eine gleichzeitig gehaltene
  Kombination. Optionales Profil-Feld `halte_taste` (bei Helldivers 2: `"ctrl"`) haelt waehrend
  der ganzen Sequenz eine Zusatztaste gedrueckt — noetig, weil Helldivers-2-Stratagem-Codes
  exakt so funktionieren.
* **`profiles/Helldivers2.yaml`** (bis 13.09.2026 `Helldivers2_Stratagems.yaml`, umbenannt) ist
  das erste, im echten Spiel bestaetigte Profil.
  Tasten sind als Pfeiltasten (`up`/`down`/`left`/`right`, nicht mehr WASD) hinterlegt, weil der
  Nutzer die Spielbelegung entsprechend umgestellt hat. Zwei Abtippfehler wurden im Zuge des
  Testens gefunden und korrigiert (`Panzerabwehrstellung`, `Automatische_Kanone`) — die
  `taste`-Werte gelten weiterhin als vorlaeufig aenderbar, nicht als endgueltig fixiert.
* **`profiles/Helldivers1.yaml`** (bis 13.09.2026 `Helldivers1_Stratagems.yaml`, umbenannt) ist
  das zweite Profil (12.09.2026), 55 Stratageme.
  Codes aus einer Wiki-Quelle abgetippt (die urspruenglich verlinkte Fandom-Seite war per
  Cloudflare blockiert, `helldivers.wiki.gg` ging stattdessen), **NICHT im echten Spiel
  getestet** - Nutzer besitzt Helldivers 1 nicht, steht so auch im Dateikopf. `taste`-Werte
  koennen also falsch sein, vor produktivem Einsatz noch verifizieren. `schlagwort` traegt hier
  durchgaengig zwei Woerter (englischer Original-Codename + deutsche Uebersetzung), Klassifikation
  gegen das echte llama-server-Setup stichprobenartig getestet (inkl. zweier anfangs gefundener,
  dann behobener Namenskonflikte: Maschinengewehr-Familie MG-94/MGX-42, Tiefflieger-Angriff-
  Familie).
* **`profiles/EliteDangerous.yaml`** ist das dritte Profil (13.09.2026), 23 Kommandos
  (Energieverteilung Waffen/Schilde/Antrieb, Fahrgestell, FSD, Ladeluke, Stop, Boost, Heatsink,
  Aufhaengungen/Hardpoints, Moduswechsel Kampf/Analyse, Schildzellenbank, ECM, Dueppel/Chaff, plus
  acht Feuergruppen-Tags siehe unten). Anders als die Helldivers-Profile durchgaengig freie
  `beschreibung` statt Wortbindung (klar unterscheidbare Kommandos, keine grosse Konfliktgefahr
  wie bei 55-77 Stratagemen). Gegen den echten llama-server getestet: 31/31 (erste 13 Tags) +
  26/26 (nach Ergaenzung der acht Feuergruppen-Tags, inkl. Regressionstest der ersten 13 sowie
  Mehrfachbefehl mit gemischtem Tag) + 20/20 (nach Ergaenzung von `Aufhaengungen`/`Moduswechsel`,
  voller Regressionstest ueber alle 23 Tags) + 27/27 (nach Ergaenzung engl. Begriffe in Klammern,
  siehe naechster Punkt) korrekt. **Drei Kommandos (`Schildzellenbank`, `ECM`,
  `Dueppel`) haben im Spiel standardmaessig keine Taste** - `taste: []` mit erklaerendem
  Kommentar, muss von jedem Nutzer selbst im Spiel belegt werden, kein vorlaeufiger/fehlender
  Wert wie bei den anderen Profilen. `kontextlaenge: 4096` ist ein grober Startwert, nicht einzeln
  nachgemessen (bei 23 Tags/3.350 Zeichen System-Prompt aber weiterhin mit Marge). Die acht
  Feuergruppen-Tags sind mittlerweile **im echten Spiel bestaetigt**
  (siehe naechster Absatz); die uebrigen 13 Kommandos noch nicht - Nutzer besitzt Elite Dangerous
  aber selbst und kann das im Gegensatz zu Helldivers 1 grundsaetzlich noch verifizieren.
  **Erkanntes Muster (13.09.2026, Nutzerbeobachtung): englische Begriffe in Klammern in der
  `beschreibung` verbessern die Erkennung englischer Paraphrasen, ohne die deutsche Erkennung zu
  gefaehrden.** Aufgefallen beim `Aufhaengungen`-Tag: die Beschreibung nennt "(Hardpoints/Waffen)",
  und "Fahr die Hardpoints aus" (kein deutsches Wort daraus) wurde trotzdem korrekt erkannt.
  Systematisch auf die uebrigen Tags uebertragen und mit gezielten englischen Paraphrasen plus
  vollem Regressionstest verifiziert (27/27): `WaffenMAX`/`SchildeMAX`/`AntriebMAX` -> "(WEP-Pips)"/
  "(SYS-Pips)"/"(ENG-Pips)" (Community-Kurzform fuer die drei Energiekanaele), `Fahrgestell` ->
  "(Landing Gear)", `Ladeluke` -> "(Cargo Hatch)", `Stop` -> "(Vollstopp/All Stop)",
  `Schildzellenbank` -> "(Shield Cell Bank)", `Moduswechsel` -> "(Combat Mode)"/"(Analysis Mode)".
  Anders als bei der Wortbindung (`schlagwort`) bei Helldivers 2 ist das hier reiner Zusatz zur
  freien `beschreibung`, kein Ersatz - erweitert nur, was das Modell als plausible Umschreibung
  akzeptiert. `Dueppel` ("(Chaff)") und `Frameshiftdrive` ("(FSD)") hatten dieses Muster schon
  vorher unabhaengig davon.
* **Feuergruppen-Direktwahl umgesetzt (13.09.2026)** - eine urspruenglich in derselben Session
  verworfene Idee (Direktwahl per intern mitgefuehrtem Zaehler, siehe vorheriger Absatz in
  fruehreren CLAUDE.md-Versionen der Git-Historie: Risiko eines unbemerkten Abdriftens vom echten
  Spielzustand, da kein Rueckmelde-Kanal existiert). **Doch ein Rueckmelde-Kanal existiert**:
  Elite Dangerous schreibt selbst laufend eine `Status.json` mit dem echten Ist-Zustand, u.a.
  `"FireGroup"` (0-indiziert). Neues Modul `gaming_assistant/ed_status.py::feuergruppen_tasten()`
  liest diese Datei bei JEDEM Tastendruck frisch (kein Caching), berechnet die Differenz zum
  Ziel-Index modulo 8 in beide Richtungen und waehlt den kuerzeren Weg - liefert `None`, wenn das
  Feld fehlt (Spiel laeuft nicht/kein Schiff aktiv) oder die Datei nicht lesbar ist (mit 2-3
  kurzen Wiederholungsversuchen bei `JSONDecodeError`, da die Datei laufend komplett neu
  geschrieben wird); `__main__.py::verarbeiten()` loest dann bewusst KEINEN Tastendruck aus statt
  zu raten - Grundprinzip bleibt gewahrt. Acht neue Tags `FeuergruppeA`..`FeuergruppeH`
  (`feuergruppe_ziel: 0..7`), `taste: []` (Sequenz wird zur Laufzeit berechnet statt fest in der
  YAML zu stehen). Neues profilweites YAML-Feld `status_datei` (Pfad zur `Status.json`) - **bei
  jedem Nutzer potenziell anders** (anderer Windows-Benutzername, verschobener Speicherort), daher
  NICHT im Code hart hinterlegt, sondern in der YAML mit Platzhalter
  `<DeinBenutzername>` und erklaerendem Kommentar (waehrend der Umsetzung/des Testens stand dort
  kurzzeitig der echte lokale Pfad des Nutzers, vor dem Commit durch den Platzhalter ersetzt).
  Vorwaerts-Taste "N" ist Spiel-Standardbelegung, Rueckwaerts-Taste "B" hat keine
  Standardbelegung und muss vom Nutzer selbst in den Elite-Dangerous-Optionen eingestellt werden
  (kollisionsfrei getestet). Beide Tasten sind seit 13.09.2026 zusaetzlich per Profil
  ueberschreibbar (`feuergruppe_vorwaerts_taste`/`feuergruppe_rueckwaerts_taste`, Vorgabe "n"/"b"
  aus `ed_status.py::TASTE_VORWAERTS_STANDARD`/`TASTE_RUECKWAERTS_STANDARD`) - Nutzerwunsch, falls
  die Tasten bei jemandem doch kollidieren. Maximal 8 Feuergruppen (A-H) angenommen, ohne die
  tatsaechlich vom
  Nutzer konfigurierte Anzahl zu kennen - liegt laut Nutzeraussage in dessen eigener
  Verantwortung, eine sinnvoll belegte Gruppe zu nennen. Isoliert gegen die echte, laufende
  `Status.json` verifiziert (`FireGroup:0` als Ausgangspunkt, alle acht Ziel-Berechnungen
  stimmten) UND **im echten Spiel per Sprachbefehl bestaetigt** (A->C->H->A durchgespielt,
  jeweils korrekte Zielgruppe erreicht). Dieses eine Feature ist die einzige Ausnahme im ganzen
  Projekt, die auf eine Datei ausserhalb des Projektordners zugreift (nur lesend).
  **Nebenbefund beim Live-Test:** ein zunaechst wie ein Bug wirkendes Verhalten (Elite Dangerous
  oeffnete beim Sprachbefehl scheinbar zufaellig das Pause-Menue) lag NICHT am Gaming-Assistant-
  Code, sondern daran, dass parallel das unabhaengige Diktiertool-Projekt lief und zufaellig
  dieselbe Push-to-Talk-Taste konfiguriert hatte - beide Tools loesten dadurch gleichzeitig aus.
  Nach Aenderung der Diktiertool-PTT-Taste verschwand das Verhalten. Fuer die Fehlersuche wurde
  dabei zusaetzliches Debug-Tooling eingebaut, das unabhaengig vom eigentlichen Bug nuetzlich
  bleibt: `ed_status.py` loggt jetzt auf Debug-Ebene aktuelle/Ziel-Feuergruppe und berechnete
  Sequenz, `keypress.py` loggt jeden einzelnen Tastendruck/-loslassen einzeln, Log-Zeitstempel
  haben jetzt Millisekunden (`logbuf.py`), ein neuer Tray-Haken **"Debug-Log aktiv"** schaltet den
  Log-Level zur Laufzeit ohne Neustart um (`logbuf.set_level()`), und das Log wird zusaetzlich zum
  Ringpuffer/Tray-Fenster fortlaufend nach `logs/gaming_assistant.log` geschrieben (pro
  Programmstart neu, nicht endlos wachsend) - praktisch, wenn man waehrend des Spielens nicht
  staendig zum Log-Fenster wechseln will/kann.
* **Kommentar-Konvention fuer Profil-YAMLs (12.09.2026, Nutzerwunsch):** so minimal wie moeglich.
  Kein Kopfkommentar mit Formaterklaerung (steht zentral in `Gaming_assistent.md`, Abschnitt
  "Aktionslisten-Format"), keine Datums-/Aenderungshistorie in der Datei selbst (gehoert in die
  Git-Historie). Pro-Tag-Kommentare nur, wo sie eine sonst nicht ersichtliche Mehrdeutigkeit
  zwischen zwei Tags erklaeren. Gilt fuer beide bestehenden Profile und alle kuenftigen.
* **Tray-Icon von Mikrofon auf Gamepad umgestellt** (`gaming_assistant/icons.py`, 12.09.2026,
  Nutzerwunsch) - passender zum Gaming-Thema. Programmatisch aus PIL-Formen gezeichnet (kein
  Bild geladen): kastenfoermiger Sockel, D-Pad-Kreuz links, zwei Aktionsknoepfe rechts.
* **Trainingsdaten-Aufzeichnung per Tray abschaltbar** (13.09.2026, Nutzerwunsch, Hinblick auf
  Veroeffentlichung: nicht jeder GitHub-Nutzer soll gezwungen sein, seine gesprochenen Befehle
  mitschreiben zu lassen). Neuer Config-Wert `cfg["training_log"]["aktiv"]` (Default `true`, kein
  Verhaltenswechsel fuer Bestandsnutzer), checkbarer Menuepunkt in `tray.py`, Pruefung in
  `__main__.py::verarbeiten()` vor dem `training_log.eintrag_anhaengen()`-Aufruf.
* **Profilnamen sind nicht mehr im Code hart hinterlegt** (13.09.2026, Nutzerfrage nach dem
  Umbenennen der beiden Helldivers-Profile). `__main__.py` faellt beim Start automatisch auf das
  erste per `profile.liste_profile()` gefundene Profil zurueck, falls der in `config.json`
  gespeicherte Name zu keiner Datei mehr passt (Warnung statt Absturz) - `config.py`s
  `DEFAULTS["profil"]["aktiv"]` bleibt nur noch ein Vorschlag fuer den Erststart, keine harte
  Abhaengigkeit mehr. Grund fuer die Umbenennung selbst: `Helldivers1_Stratagems.yaml` ->
  `Helldivers1.yaml`, `Helldivers2_Stratagems.yaml` -> `Helldivers2.yaml` (kuerzer, konsistent
  mit `EliteDangerous.yaml`).
* **`schlagwort` ist jetzt optional** (11.09.2026, Nutzergespraech): ein Tag braucht mindestens
  eines von `schlagwort`/`beschreibung`, `profile.py::laden()` bricht sonst mit klarer
  Fehlermeldung ab. Hintergrund: `schlagwort` und `beschreibung` haben unabhaengige Aufgaben -
  `beschreibung` (falls gesetzt) bestimmt die Klassifikations-Beschreibung im System-Prompt,
  `schlagwort` (falls gesetzt) speist unabhaengig davon nur die `initial_prompt`-Vokabelliste;
  ein Tag mit `beschreibung` kann trotzdem ein `schlagwort` haben, nur um ein einzelnes Fremdwort
  daraus im initial_prompt bekannt zu machen. Fuer Helldivers 2 mit seinen vielen aehnlichen
  Stratagem-Namen wird durchgaengig die wortgebundene Standardbeschreibung (ueber `schlagwort`,
  ohne eigenes `beschreibung`) gebraucht; ein Spiel mit wenigen, eindeutigen Kommandos koennte
  stattdessen durchgaengig `beschreibung` ohne `schlagwort` nutzen - beide Modi laufen ueber
  denselben `prompt.py`-Code, keine Sonderbehandlung noetig.
* **`schlagwort` unterstuetzt jetzt mehrere gleichwertige Woerter pro Tag** (11.09.2026,
  `profile.py::TagEintrag.schlagwort` ist jetzt immer eine Liste, `prompt.py` passt die
  Tag-Beschreibung entsprechend an: "eines der Woerter X oder Y"). In der YAML durchgaengig als
  Liste in eckigen Klammern geschrieben, auch bei nur einem Wort (`["MG-43"]`), fuer eine
  einheitliche, leicht erweiterbare Schreibweise (Motivation: spaetere GitHub-Nutzer sollen
  eigene Schlagwoerter leicht ergaenzen koennen). Mehrere zusaetzliche Schlagwoerter ergaenzt und
  jeweils einzeln gegen LM Studio auf Kollisionen mit den bestehenden Konfliktclustern getestet:
  `EAT` + "Panzerabwehrkanone" (bewusst NICHT das blosse "Panzerabwehr" - das kollidierte im Test
  mit `Panzerabwehrstellung`), `Automatische_Kanone` + "Autocannon", `Kanonengeschuetz` +
  "Autocannon-Geschuetz" (unterscheidet sich im Test sauber von `Automatische_Kanone`s
  "Autocannon"), `Luftdetonations_Raketenwerfer` + "Airburst", `Minenfeld` + "AP-Minenfeld",
  `Panzerabwehrminen` + "AT-Minen", `Moersergeschuetz` + "Moerser",
  `EMP_Moersergeschuetz` + "EMP-Moerser", `Hellbombe` + "Hellbomb"/"Hoellenbombe". Ausserdem bei
  den sechs Hangar-Adler-Tags (`Adler_Tieffliegerangriff`, `_Luftschlag`, `_Streubombe`,
  `_Napalmluftschlag`, `_Rauchbeschuss`, `_Raketenpods`) das Wort "Adler" versuchsweise entfernt
  und behalten, weil auch der Risikofall Rauchbeschuss/Orbital-Rauchbeschuss (Cluster B) im Test
  weiterhin korrekt unterschieden wurde; `Orbital_Schienenkanone` verlor ebenso das "Orbital"-
  Praefix (einzigartiges Wort im Profil, keine Kollision mit `Railgun`). `Adler_Nachladen`
  (Missionsspezifisch, nicht Hangar) bewusst unveraendert gelassen - "nachladen" allein waere zu
  generisch. **Arbeitsweise, die sich bewaehrt hat:** jede Aenderung einzeln mit einem kleinen
  Testskript (`lmstudio.sicherstellen_geladen` + `llm.klassifizieren` + `parser.tags_extrahieren`
  gegen mehrere Formulierungen inkl. der bekannten Konfliktcluster) gegen das echte LM Studio
  verifiziert, bevor sie in die YAML uebernommen wurde - dabei genau ein Fall gefunden und korrigiert
  (`Panzerabwehr` -> `Panzerabwehrkanone`). Abschliessender Regressionstest ueber 32 Faelle
  (alle Aenderungen plus Referenzfaelle wie Guard-Dog-Familie, NONE-Erkennung): 32/32 korrekt.
* **`vendor/whisper.cpp` und Whisper-Modell sind eigenstaendige Kopien**, keine Pfad-
  Abhaengigkeit zum Diktier-Tool-Repo (aus dessen fertigem Build kopiert: nur `whisper-
  server.exe` + noetige DLLs, nur die Q5-Deutsch-Modellvariante). Analog dazu ist
  `vendor/llama.cpp/` eine eigenstaendige Kopie des offiziellen llama.cpp-Vulkan-Windows-
  Release-Zips (gepinnter Build `b10909`), auf `llama-server.exe` + noetige DLLs verschlankt
  (die vielen mitgelieferten Zusatzwerkzeuge wie `llama-cli.exe`/`llama-bench.exe`/etc. werden
  nicht gebraucht). **Beide Server-Binaries liegen seit 12.09.2026 direkt im Repo** (siehe
  "Server-Binaries eingebettet" weiter unten) statt separat heruntergeladen werden zu muessen -
  `scripts/build_whisper.ps1`/`scripts/fetch_llama.ps1` bleiben nur noch als
  Fallback-/Reparatur-Skripte fuer den Ausnahmefall bestehen. `setup.ps1` buendelt die
  Ersteinrichtung (venv + beide Modell-Downloads) in einem Aufruf.
* **Bekannter, nicht als kritisch eingestufter Fund:** bei rein digitaler Stille (Testfall, kein
  echtes Mikrofon-Rauschen) halluziniert Whisper gelegentlich Text statt leer zu bleiben. Im
  echten Spielbetrieb bisher nicht als Problem aufgefallen.
* **Latenz gemessen und dokumentiert (10.09.2026, nach der LM-Studio-Abloesung am 12.09.2026 mit
  llama-server neu verifiziert), siehe `__main__.py::verarbeiten()`** (schreibt pro Befehl eine
  Log-Zeile `Latenz: STT ...s, LLM ...s, ...`): realer End-zu-Ende-Durchlauf mit echter Sprache
  (per Windows-TTS synthetisiert, nicht mit Stille/Rauschen getestet - dazu gleich mehr) liegt bei
  **~0,33-0,35s pro Befehl** (STT ~0,2s, LLM ~0,14s dank Prompt-Caching fuer den identischen
  System-Prompt). Mit llama-server (`cache_prompt: true` in `llm.py`) **eher noch etwas besser**:
  per Testskript gemessene Wiederholungs-Latenz **~0,09-0,11s**, siehe "LM Studio abgeloest"
  unten. **Nur der allererste Aufruf nach Programmstart oder Tray-Profilwechsel kostet laenger**
  (vorher ~2,5s mit LM Studio, jetzt gemessen ~1,5s mit llama-server - einmaliges Prefill des
  System-Prompts, je nach Profil mehrere Tausend Tokens). **Bewusst NICHT gebaut:** weder ein
  einmaliger Warmup-Aufruf beim Profil-Laden noch ein wiederkehrender Warmhalter-Ping waehrend des
  Spielens - Grund: der llama-server-Prozess (Modell + Prompt-Cache) kann durch VRAM-Druck des
  Spiels jederzeit verdraengt werden (dasselbe Phaenomen wie beim Whisper-Modell, aus der
  Diktier-Tool-Messreihe bekannt), ein einmaliger Warmup schuetzt also nur den
  Start-Fall, nicht spaetere Verdraengungen mitten im Spiel: ein wiederkehrender Ping wuerde davor
  zuverlaessiger schuetzen, aber dauerhafte GPU-Last waehrend des Spielens verursachen. Nutzer hat
  sich explizit gegen beide Varianten entschieden - die seltene Verzoegerung nach Start/Verdraengung
  wird bewusst in Kauf genommen. Diese Begruendung ist backend-unabhaengig und gilt nach der
  LM-Studio-Abloesung unveraendert weiter.
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
* **Naechste moegliche Schritte:** offene Punkte am Elite-Dangerous-Profil (drei fehlende Tasten
  fuer `Schildzellenbank`/`ECM`/`Dueppel` selbst im Spiel belegen und eintragen, `kontextlaenge`
  einmal real nachmessen statt Schaetzwert, Test der uebrigen 15 Kommandos im echten Spiel - die
  acht Feuergruppen-Tags sind bereits live bestaetigt, siehe oben); abwarten, ob sich ueber den
  Reddit-Post Interesse und/oder Wuensche fuer
  weitere Spielprofile ergeben (siehe "Veroeffentlichung vorbereitet" oben), dann ggf. Repo auf
  oeffentlich stellen; eine zweistufige Trainingsdaten-Aufbereitung (Extraktor-Durchlaeufe auf den
  `training_log.py`-Rohdaten - Durchlauf 1 prueft Plausibilitaet Rohtext/erkannter Tag,
  Durchlauf 2 korrigiert nur die aussortierten Faelle) fuer kuenftiges Fine-Tuning.
* **Ueberlegung (12.09.2026, noch nicht umgesetzt): LoRA-Adapter statt volles Fine-Tuning pro
  Profil.** Da das Tool profilbasiert ist (unterschiedliche Tag-Listen je Spiel), wuerde ein
  vollstaendig fine-getuntes Modell pro Profil bedeuten, dass fuer jedes Spiel eine eigene,
  mehrere GB grosse Modellkopie vorgehalten werden muesste - und ein Profilwechsel muesste dann
  das komplette Modell neu laden statt nur (wie aktuell) die Kontextlaenge anzupassen. Deshalb
  angedachter Ansatz: LoRA- bzw. QLoRA-Adapter (kleine Zusatzgewichts-Datei, wenige MB statt
  mehrere GB, wird zur Laufzeit auf das gemeinsame Basismodell geladen, ohne dieses selbst zu
  veraendern - QLoRA betrifft nur die Trainingsphase selbst, das Ergebnis ist derselbe
  Adapter-Dateityp). llama-server unterstuetzt das Laden eines Adapters ueber `--lora`. Pro
  Spielprofil koennte ein eigener, winziger Adapter trainiert und direkt neben der jeweiligen
  Profil-YAML abgelegt werden; beim Profilwechsel wuerde der Server (analog zum bereits
  bestehenden Neustart bei geaenderter Kontextlaenge) mit dem passenden Adapter neu gestartet -
  vertretbarer Umweg, falls sich dynamisches Nachladen eines noch nicht beim Start geladenen
  Adapters ohne Neustart als nicht zuverlaessig herausstellt. Zweck waere dabei primaer nicht,
  dem Modell Tag-Namen eines bestimmten Spiels beizubringen (das leistet schon der
  System-Prompt), sondern die allgemeine Faehigkeit zu verbessern, Text anhand einer im Prompt
  mitgegebenen Tag-Liste zuverlaessig zu klassifizieren - trainiert auf ueber alle Profile
  hinweg gesammelten Daten, nicht auf ein einzelnes Spiel beschraenkt.

* `Gaming_assistent.md` ist das massgebliche, vollstaendige Konzept — bei Widersprueche zwischen
  dieser Zusammenfassung hier und `Gaming_assistent.md` gilt **immer** `Gaming_assistent.md`.
  Alle Designentscheidungen stehen im Abschnitt "Bereits entschieden", das vollstaendige
  Testergebnis im Abschnitt "Testreihe (abgeschlossen)" — **keine offenen Konzeptfragen mehr**,
  siehe dort fuer die Begruendung.
* **Kernentscheidungen kurz:** ein Prozess statt Server/Client, Push-to-Talk, Whisper
  `large-v3-turbo-german-q5` fest auf Deutsch, LLM-Klassifikation statt Stringmatch
  (Gemma 4 E4B, `temperature=0`, Denkmodus per `--reasoning off` an llama-server explizit aus -
  frueher LM-Studio-GUI-Schalter, siehe "LM Studio abgeloest" unten),
  Tags im Format `&&TAG&&`, `&&NONE&&` bei Uneindeutigkeit, YAML-Profil pro Spiel mit
  `schlagwort`/`beispiel`/`taste`/`kontextlaenge`-Feldern (Details siehe „Aktionslisten-Format").
  Die vorherige Testreihe (vier Runden, zuletzt 105/107 auf der vollen 77-Tag-Helldivers-2-Liste)
  ist im Detail in `Gaming_assistent.md`, Abschnitt "Testreihe" dokumentiert.

## LM Studio abgeloest (12.09.2026)

Ueberlegung vom 11.09.2026, weil eine Veroeffentlichung auf GitHub ernsthaft in Betracht gezogen
wurde. Eine Pflicht-Abhaengigkeit zu einer separat zu installierenden LM-Studio-Instanz waere fuer
ein Open-Source-Tool eine hohe Einstiegshuerde. **Ziel erreicht:** der Assistent kommt jetzt
komplett ohne LM Studio aus.

**Architekturentscheidung: eigener Subprozess statt Python-Bindings.** Die beiden Kandidaten aus
der urspruenglichen Planung waren `llama-cpp-python` (Python-Bindings) oder ein eigener
Subprozess (Vorlage: `whisper_proc.py`/`whisper-server.exe`, dasselbe Muster). Entschieden fuer
den Subprozess: `llama-server.exe` (offizieller vorgefertigter Windows/Vulkan-Build von
`github.com/ggml-org/llama.cpp`) bringt von Haus aus dieselbe OpenAI-kompatible
`/v1/chat/completions`-API mit, die vorher LM Studio lieferte, sodass `llm.py` kaum geaendert
werden musste; kein Kompilieren noetig; keine Unsicherheit wegen fehlender vorgefertigter Wheels
fuer das hier verwendete Python 3.14 auf Windows; passt zum bereits etablierten Whisper-Muster
(gleicher Vulkan-Backend, gleiche Prozess-Isolation).

**Neue Module:** `gaming_assistant/llama_proc.py` (`LlamaServer`-Klasse, ersetzt `lmstudio.py`)
startet/ueberwacht `llama-server.exe` genau wie `whisper_proc.py` das fuer Whisper tut - mit
einer Besonderheit: die Kontextlaenge (`-c`) ist nur beim Start setzbar, nicht zur Laufzeit
aenderbar. Deshalb gibt es `LlamaServer.sicherstellen(kontextlaenge)`, das bei jedem
Profilwechsel aufgerufen wird und nur dann neu startet, wenn sich die Kontextlaenge tatsaechlich
geaendert hat (getestet: kein Neustart bei gleicher Kontextlaenge, sauberer Neustart bei anderer).
`gaming_assistant/llm.py` blieb strukturell fast unveraendert - nur die Ziel-URL (jetzt
`http://127.0.0.1:<port>/v1/chat/completions` statt LM Studios `api_base`) und ein neuer
`"cache_prompt": true`-Payload-Parameter kamen dazu (siehe naechster Punkt).

**Wichtiger Fund beim Testen, nicht im urspruenglichen Plan vorhergesehen: Denkmodus muss aktiv
per `--reasoning off` an `llama-server` abgeschaltet werden.** Der in diesem llama.cpp-Build
verwendete Gemma-4-Chat-Template-Standard aktiviert den Denkmodus automatisch, sobald eine
System-Message vorhanden ist (bei diesem Projekt immer der Fall) - ohne das Flag verbrauchte das
Modell seine kompletten `max_tokens` fuers Nachdenken (`reasoning_content` im Response-JSON), die
eigentliche Tag-Antwort blieb leer, `finish_reason` war `"length"`. Mit `--reasoning off` in
`llama_proc.py::LlamaServer.start()` verhaelt sich das Modell wie zuvor unter LM Studio (kein
unaufgefordertes Denken). Ebenfalls beim manuellen Testen entdeckt: `llama-server` startet ohne
explizites `-np 1` standardmaessig mit mehreren parallelen Slots (hier beobachtet: 4), was den
VRAM-Bedarf des KV-Cache vervierfacht, obwohl immer nur ein Push-to-Talk-Nutzer gleichzeitig
spricht - `-np 1` ist deshalb ebenfalls fest in `llama_proc.py` gesetzt.

**Latenz nach der Umstellung neu gemessen (12.09.2026, Testskript gegen die echte Helldivers-2-
Kontextlaenge 8192):** Wiederholungs-Latenz (Prompt-Cache greift) **~0,09-0,11s** (vorher LM
Studio: ~0,14s), Cold-Start-Latenz (erster Aufruf direkt nach Programmstart) **~1,5s** (vorher LM
Studio: ~2,5s) - beides eine spuerbare Verbesserung, kein Regressions-Risiko. `finish_reason`-Werte
(`"stop"`/`"length"`) stimmen mit der OpenAI-Konvention ueberein, auf die sich `parser.py`
verlaesst - per Test bestaetigt. **Erneut nachgemessen (13.09.2026, Nutzervermutung "duerfte
nochmal besser geworden sein" bestaetigt sich):** mit TTS-synthetisierter echter Sprache ("Ruf
das MG 43", Windows-TTS wie gewohnt) STT ~0,18s (Minimum ueber 5 Durchlaeufe), LLM-Wiederholung
**~0,065s** (Minimum ueber 10 Durchlaeufe - nochmal spuerbar schneller als die vorherige
~0,09-0,11s-Messung), Cold-Start ~1,45s. End-zu-Ende (STT + LLM-Wiederholung) **~0,24s** statt
vorher ~0,3s. In README.md, Abschnitt "Bedienung" mit diesen aktuellen Werten uebernommen (vorher
gar nicht in der README gestanden, nur hier in CLAUDE.md - dabei aufgefallen).

**VRAM-Bedarf neu gemessen (12.09.2026, per Windows-GPU-Performance-Counter, "Dedicated Usage"
pro Prozess statt Vorher/Nachher-Differenz):** llama-server (Gemma 4 E4B, Q4_K_M, Kontext 8192,
ein Slot) ~3,34 GB, whisper-server (large-v3-turbo-german-q5) ~0,92 GB, zusammen **~4,26 GB** -
beide Werte etwas hoeher als die vorherige Messreihe (llama-server ~3,3 GB, Whisper ~0,57 GB,
zusammen ~3,9 GB), aber weiterhin deutlich unter der fruehesten LM-Studio-Messung von ~6,33 GB
(Nutzer erinnert sich an eine noch frühere Messung von knapp 8 GB) bei gleicher Kontextlaenge.
**Wahrscheinlichste Erklaerung fuer den grossen Ruecksprung nach der LM-Studio-Abloesung:**
LM Studios interne llama.cpp-basierte Engine lief vermutlich mit mehreren parallelen Slots ohne
Moeglichkeit, das ueber die GUI auf 1 zu begrenzen - genau der Effekt, der beim eigenen
`llama-server`-Setup per curl-Test gefunden und durch das feste `-np 1`-Flag behoben wurde (siehe
oben, "VRAM-Bedarf des KV-Cache vervierfacht"): mehr Slots bedeuten einen mehrfachen KV-Cache
bei gleicher Kontextlaenge. Nebenfaktoren, die einen kleineren Teil der Luecke erklaeren koennten:
LM Studio laedt bei multimodalen GGUF-Modellen oft automatisch die `mmproj`-Datei mit (~0,95 GB)
auch wenn nur Text gebraucht wird, plus moeglicher Verwaltungs-Overhead durch LM Studios eigenes
Modell-Loading/-Caching. Nicht abschliessend verifiziert (LM Studio wurde bereits abgeloest, ein
Nachtest waere nur noch von akademischem Interesse) - siehe Session vom 12.09.2026.

**Verwendete llama.cpp-Version:** gepinnter Release-Tag `b10909` (`llama-b10909-bin-win-vulkan-x64.zip`),
per `scripts/fetch_llama.ps1` nach `vendor/llama.cpp/` geladen - bewusst gepinnt statt "latest",
da llama.cpp mehrmals woechentlich neue Builds veroeffentlicht (Reproduzierbarkeit,
keine unbemerkten Breaking Changes).

**Config-Migration:** `cfg["llm"]` hat ein neues Schema (`llama_bin`, `model` als Dateipfad statt
LM-Studio-Katalogname, `n_gpu_layers`, `llama_host`/`llama_port` statt `api_base`,
`manage_loading`/`gpu_offload`/`ttl_s`/`unload_other_models` entfallen komplett). Eine bereits
vorhandene `config.json` mit dem alten Schema wuerde durch `_deep_merge` sonst den alten
`"model": "google/gemma-4-e4b"`-Wert ueber den neuen Datei-Pfad-Default legen (Schluesselname-
Kollision, gleicher Name "model", andere Bedeutung) - beim Umstieg einmalig den `llm`-Block aus
der lokalen `config.json` entfernt, damit er sauber aus den neuen `DEFAULTS` befuellt wird. Kein
automatischer Config-Migrator gebaut (Projekt war zu diesem Zeitpunkt noch nicht veroeffentlicht,
Einzelfall).

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

* **Entscheidung revidiert (12.09.2026): kein Git LFS, Modell bleibt ausserhalb des Repos.**
  Git LFS war eingerichtet und getestet (`git lfs track`), aber verworfen: die Hauptdatei
  `gemma-4-E4B-it-Q4_K_M.gguf` liegt bei ~4,97 GiB, knapp unter GitHubs 5-GiB-Limit pro
  LFS-Datei, und zusammen mit der `mmproj`-Datei (~0,95 GB) weit ueber dem kostenlosen
  LFS-Kontingent (1 GB Speicher/Bandbreite pro Monat) — fuer ein oeffentliches Repo ohne
  bezahlten Datenpaket-Zusatz nicht praktikabel. Stattdessen: der Ordner
  `gemma-4-E4B-it-GGUF/` bleibt im Repo (mit eigener `README.md` als Download-Anleitung), die
  `*.gguf`-Dateien selbst sind ueber `.gitignore` ausgeschlossen. Nutzer laden die Modelldatei
  manuell herunter (Quelle: `unsloth/gemma-4-E4B-it-GGUF` auf Hugging Face, siehe
  `gemma-4-E4B-it-GGUF/README.md` und Haupt-`README.md`) und kopieren sie selbst in den Ordner —
  gleiches Prinzip wie schon bei Whisper (`vendor/whisper.cpp` + Modell, siehe oben), nur ohne
  Git-Versionierung der Gewichte.
* **Lizenzfrage bereits geklaert (11.09.2026, per Websuche verifiziert):** Gemma 4 (die hier
  genutzte Version) laeuft seit April 2026 unter **Apache 2.0** — keine Redistributions-
  Einschraenkungen fuer die Modellgewichte. Nur Gemma 1-3 liefen noch unter den restriktiveren,
  selbst geschriebenen "Gemma Terms of Use"; fuer dieses Projekt nicht relevant.
* **Server-Binaries eingebettet (12.09.2026), Ersteinrichtung auf ein Skript gebuendelt.**
  Nachtraeglich aufgefallen: die eigentlichen Server-Programme (`llama-server.exe`,
  `whisper-server.exe`) sind winzig im Vergleich zu den Modellgewichten - nach dem Verschlanken
  auf nur die tatsaechlich gebrauchten Dateien (Rest siehe "Modulstruktur" oben) ~81 MB
  (llama.cpp) bzw. ~54 MB (whisper.cpp), jede einzelne Datei weit unter GitHubs 100-MB-Grenze
  fuer normale (nicht-LFS-)Dateien. Anders als bei den Modellgewichten (mehrere GB, siehe oben)
  gibt es hier also **kein** Kontingent-Problem. Deshalb: `.gitignore` von einem pauschalen
  `vendor/`-Ausschluss auf eine gezielte Regel umgestellt (verschachtelte `!`-Ausnahmen fuer
  `vendor/whisper.cpp/build/bin/Release/`, damit ein evtl. von `build_whisper.ps1` geklonter
  Quellcode/Build-Zwischenstand weiterhin ignoriert bleibt, aber die fertigen Binaries darin
  nicht; `vendor/llama.cpp/` braucht keine eigene Regel, da dort nie Quellcode anfaellt) - beide
  Binary-Sets sind jetzt direkt im Repo committet. `fetch_llama.ps1`/`build_whisper.ps1` sind
  dadurch fuer den Normalfall ueberfluessig geworden, bleiben aber als Fallback-/
  Reparatur-Skripte bestehen (z.B. falls `vendor/` beschaedigt ist oder eine andere
  Plattform/Architektur gebraucht wird) - `fetch_llama.ps1` entfernt dabei automatisch dieselben
  ueberfluessigen Zusatzwerkzeuge, die einmalig manuell aus `vendor/llama.cpp/` geloescht wurden.
  Uebrig bleiben fuer eine Ersteinrichtung nur noch die Python-Umgebung und die beiden grossen
  Modell-Downloads (LLM ~5 GB, Whisper ~0,5 GB) - dafuer neu `setup.ps1`, das
  `setup_venv.ps1`/`download_llm.ps1`/`fetch_models.ps1` nacheinander aufruft (keine
  Logik-Duplizierung, die drei Skripte bleiben einzeln nutzbar).

## Veroeffentlichung vorbereitet (13.09.2026)

**Status: GitHub-Repo existiert und ist vollstaendig gepusht (Stand v1.4), aber bewusst noch
privat.** Repo `derpreusse85-cloud/KI-Gaming-Assistent` (leer angelegt, kein README/.gitignore/
Lizenz beim Erstellen, um Konflikte mit den bereits lokal fertigen Dateien zu vermeiden). Lokaler
Branch `main` per `git push -u origin main` hochgeladen (inzwischen mehrfach per einfachem
`git push` aktualisiert, zuletzt bis Commit `56c8a86`), dazu alle fuenf Versions-Tags v1.0-v1.4
(`git push origin --tags` bzw. einzeln `git push origin v1.4`) und passende GitHub-Releases zu
allen fuenf Tags (Notizen aus `CHANGELOG.md`, per `gh release create` angelegt - `gh` blieb ueber
die Session hinweg angemeldet, spaetere Releases liefen direkt aus der KI-Sitzung, nicht mehr nur
vom Nutzer selbst). Authentifizierung: Personal Access Token (classic, Scope
`public_repo`, 90 Tage, laeuft ~12.12.2026 ab) fuer `git push` ueber den Windows Git Credential
Manager gespeichert; `gh`-CLI (per `winget install --id GitHub.cli` installiert) separat per
Browser-Login authentifiziert - beide Anmeldungen sind unabhaengig voneinander und wurden vom
Nutzer selbst in seinem eigenen Terminal durchgefuehrt, nicht durch die KI-Sitzung (Sicherheits-
prinzip: Zugangsdaten nie im Chat teilen). Repo-Sichtbarkeit aktuell **privat** - Nutzer hat einen
Reddit-Post zum Sammeln neuer Spielideen erstellt (wartet noch auf Mod-Freigabe) und will das
Repo erst oeffentlich stellen, wenn sich echtes Nutzerinteresse zeigt. **Nutzer-Hintergrund:**
dies ist seine allererste GitHub-Veroeffentlichung ueberhaupt - GitHub-Konzepte (Tokens, `gh`,
Fork/Pull-Request-Modell, Releases vs. Tags, Packages/Contributors-Widgets) wurden in der Session
jeweils von Grund auf erklaert, nicht vorausgesetzt.

**`LICENSE` (GPL-3.0):** offizieller Volltext von `gnu.org/licenses/gpl-3.0.txt`, mit eigener
Copyright-Zeile ("Gaming-Sprachassistent / Copyright (C) 2026 DerPreusse") vorangestellt. **Fund
und Korrektur (13.09.2026):** der urspruenglich komplett uebernommene Text enthielt am Ende noch
den offiziellen GPL-Anhang "How to Apply These Terms to Your New Programs" mit woertlichen
Platzhaltern (`<year>`, `<name of author>`) - das ist normaler Bestandteil des offiziellen
GPL-Texts (Anleitung fuer Entwickler, kein Fehler), haette hier aber wie eine nicht ausgefuellte
Lizenz gewirkt. Datei auf den reinen Lizenztext bis "END OF TERMS AND CONDITIONS" gekuerzt, der
Anhang entfernt.

**`CHANGELOG.md`** neu (Keep-a-Changelog-Stil, v1.0-v1.3), Inhalte aus den vorhandenen
Git-Tag-Nachrichten und diesem Dokument destilliert, in der README verlinkt.

**README-Ergaenzungen fuer die Veroeffentlichung:** Hinweis dass Code/System-Prompt fest auf
Gemma 4 E4B ausgelegt sind (kein reiner Config-Tausch bei anderem Modell moeglich, siehe
"Modellwahl" oben); Abschnitt zum Erweitern bestehender Profile um neue Kommandos
(Namenskollisionen pruefen, `kontextlaenge` im Blick behalten); Abschnitt "Lizenz und
Drittanbieter-Komponenten" (eigener Code GPL-3.0, `vendor/`-Binaries MIT, Gemma-Gewichte
Apache-2.0); persoenlicher Disclaimer des Autors (Nicht-Entwickler, kompletter Code KI-generiert,
Bitte um Sachlichkeit) als Zitat-Block direkt nach der Einleitung, wortwoertlich vom Nutzer
vorgegeben.

**`.gitignore`:** `Elite Dangerous (erster entwurf).txt` (roher Arbeitsentwurf, analog zu
`Beispiele.txt`) ergaenzt - beide sind persoenliches Referenzmaterial, nicht Teil des Repos.
Ausserdem (13.09.2026) `profiles/EliteDangerous_Lokal.yaml` ausgeschlossen: persoenliche Kopie
von `EliteDangerous.yaml` mit dem echten `status_datei`-Pfad des Nutzers statt des im oeffentlichen
Profil hinterlegten Platzhalters `<DeinBenutzername>` - noetig, damit das Feuergruppen-Feature
(siehe "Stand der Arbeit" oben) trotz Platzhalter im Repo lokal weiter funktioniert. Nutzers
lokale `config.json` (selbst nicht versioniert) hat `profil.aktiv` aktuell auf
`"EliteDangerous_Lokal"` gesetzt - **Hinweis fuer eine kuenftige Session:** das war eigenmaechtig
von der KI gesetzt worden, Nutzer haette lieber selbst im Tray-Menue ausgewaehlt (Feedback dazu
liegt auch im Auto-Memory-System) - falls das nochmal auffaellt, nicht erneut automatisch aendern.

## Uebertragbare Lektionen aus dem Vorgaengerprojekt

Kurzfassungen der fuer dieses Projekt relevanten Erkenntnisse aus dem Diktier-Tool:

* **(LM-Studio-spezifisch, vor der Abloesung relevant) LM Studio ignoriert `enable_thinking`.**
  Wirksam war nur `/no_think` im Prompt (Qwen-Konvention, nicht bei allen Modellen) bzw. bei
  manchen Modellen der Schalter Inference -> Custom Fields -> "Enable Thinking" direkt in LM
  Studio. Bei diesem Projekt besonders wichtig, da Denk-Tokens vor der Tag-Ausgabe eine im Spiel
  spuerbare Verzoegerung verursachen wuerden. Nach der Abloesung (siehe "LM Studio abgeloest")
  gilt die analoge Lektion fuer llama-server: dort ist es der explizite `--reasoning off`-
  Kommandozeilen-Flag statt eines GUI-Schalters.
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
