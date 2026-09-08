# CLAUDE.md

Gaming-Sprachassistent: freie gesprochene Sprache waehrend des Spielens wird per LLM in eine
feste Aktion klassifiziert und als Tastenkombination ausgeloest. Konzept siehe
`Gaming_assistent.md`. Noch nichts implementiert.

## Stand der Arbeit (fuer den Wiedereinstieg in einer neuen Session)

Rein konzeptionelle Phase, kein Code vorhanden. Zuletzt bearbeitet: 08.09.2026. Zielspiel:
Helldivers 2 (siehe `Gaming_assistent.md`, Abschnitt "Grundidee").

* `Gaming_assistent.md` ist das konsolidierte, aktuelle Konzept (entstanden aus zwei
  urspruenglich getrennten Brainstorming-Dateien, die inzwischen geloescht sind). Enthaelt
  Architektur, Pipeline, Tag-Mechanismus, Aktionslisten-Format (YAML pro Spielprofil, manuelle
  Auswahl per Tray), Nero-Bezug und Trainingsdaten-Sammlung. Bereits entschiedene Punkte stehen
  im Abschnitt "Bereits entschieden" dort, u. a. Whisper-Modell `large-v3-turbo-german-q5`,
  kein Mehrsprachigkeits-Support (nur Deutsch), ein Prozess statt Server-Client.
* **Modellwechsel (07.09.2026): Gemma 4 E2B verworfen, jetzt Gemma 4 E4B.** Grund:
  Instruction-Following-Schwaechen von E2B bei verketteten/mehrfachen Kommandos in einer
  Aeusserung, laut Recherche (siehe `Gemma4.md`, mittlerweile in `Gaming_assistent.md`
  eingearbeitet). E4B gilt als robuster bei Mehrfachbefehlen, bei etwas hoeherer Latenz
  (unbelegte Richtwerte: E2B <15 ms, E4B 30-50 ms).
* **Getestet und bestaetigt (07.09.2026):** Fuer **beide** Modelle, `google/gemma-4-e2b` und
  `google/gemma-4-e4b`, ist der Denkmodus in diesem lokalen LM-Studio-Setup bereits aus,
  unabhaengig vom API-Parameter `chat_template_kwargs.enable_thinking` (true/false/weggelassen
  liefern identisch 0 Reasoning-Tokens). Getestet je gegen eine laufende und eine frisch ueber
  `lms load` geladene, unabhaengige Instanz — also kein Zufall einer bestimmten Instanz, sondern
  Eigenschaft des Basismodells in diesem LM-Studio-Setup. Damit ist auch die in
  Recherchematerial kursierende Behauptung widerlegt, der Denkmodus liesse sich ueber ein
  `<|think|>`-Token im System-Prompt steuern (siehe `Gaming_assistent.md`, Abschnitt "Latenz und
  Denkmodus"). Folge fuer dieses Projekt: beim Laden ueber `lms` mit eigenem Bezeichner (analog
  `diktier-<name>` im Diktier-Tool) ist keine zusaetzliche Denkmodus-Konfiguration noetig,
  solange niemand den GUI-Schalter Inference -> Custom Fields -> "Enable Thinking" fuer eines
  der beiden Modelle manuell umstellt.
* **Erster Klassifikationstest durchgefuehrt (08.09.2026): 24/25 (96 %).** Testaufbau: LLM-
  Klassifikation isoliert getestet, ohne Whisper (Text rein, Tag raus), gegen `google/gemma-4-e4b`
  (eigene `lms`-Instanz `gaming-test-gemma-e4b`), `temperature=0`, `max_tokens=40`. 8 echte
  Helldivers-2-Tags aus `Beispiele.txt` (vom Nutzer vorgegeben: Heilung, Fahrgestell,
  Teleport_Stadt, 500kg_Bombe, Verstärkung, Orbitallaser, Bombenteppich, Waffen), 25 Testfaelle
  in 5 Kategorien (Positiv, Mehrfachbefehle, Negativ, Negativ-Grenzfaelle, Indirekt) selbst
  entworfen. Testskript liegt nur im Scratchpad dieser Session, noch nicht ins Repo uebernommen.
  Ergebnis nach zwei Prompt-Iterationen:
  * Positiv, Mehrfachbefehle, Negativ, Negativ-Grenzfaelle: je 100 % (13/13, 3/3, 3/3, 2/2).
  * Indirekt (Absicht ohne Nennung der Aktion): 3/4 (75 %) — ein bewusst akzeptierter Fehlschlag,
    siehe naechster Punkt.
  * Mehrfachbefehle liefen von Anfang an fehlerfrei mit dem generischen Platzhalter-Ansatz
    (allgemeine Regel + ein Beispiel mit `&&AKTION_A&&`/`&&AKTION_B&&`) — die
    kombinationsspezifischen Beispiele aus `Gemma4.md` waren nicht noetig.
  * Verbesserung durch Prompt-Iteration: v1 (nur ein Satz fuer die `&&NONE&&`-Regel) lag bei
    22/25, mit zwei generischen `&&NONE&&`-Beispielen im Prompt bei 23/25, mit zusaetzlich
    wortgebundener Tag-Beschreibung fuer `Verstärkung` ("nur wenn im Befehl auch das Wort
    'Verstärkung' vorkommt") bei 24/25.
* **Bewusst akzeptierter Tradeoff bei `Verstärkung`:** die wortgebundene Beschreibung behebt
  Fehlklassifikationen bei sinnverwandten, aber falschen Begriffen ("Ruf die Artillerie" ->
  faelschlich Verstärkung), verhindert aber auch die Erkennung rein indirekter Umschreibungen
  ohne das Wort selbst ("Die sollen uns hier raushauen" -> NONE statt Verstärkung). Fuer diesen
  Tag akzeptiert, weil das Kommando in Helldivers 2 in der Praxis so gut wie immer woertlich
  "Verstärkung" genannt wird — keine allgemeine Regel fuer alle Tags, siehe
  `Gaming_assistent.md`, Abschnitt "Bereits entschieden".
* **Schlagwort-Toleranztest (08.09.2026): 12/12 (100 %).** Gezielt geprueft, ob eine
  schlagwortgebundene Tag-Beschreibung (nach dem `Verstärkung`-Muster) trotzdem verschiedene
  Schreib-/Sprechweisen des Schlagworts toleriert, statt exaktes Stringmatch zu erfordern.
  `&&500kg_Bombe&&` auf "nur wenn im Befehl eine Nennung der 500-Kilogramm-Bombe vorkommt (Zahl
  500 zusammen mit Kilo/Kilogramm/kg und Bombe, unabhaengig von genauer Schreibweise)" umgestellt,
  getestet gegen ausgeschriebene Zahl ("fuenfhundert"), fehlende Bindestriche, Zusammenschreibung
  ("500kilobombe") und einen simulierten Verhoerer/Tippfehler ("Bombär" statt "Bombe") — alle
  korrekt erkannt. Kontrollfaelle (andere Zahl "250-Kilo-Bombe", anderer Tag "Bombenteppich")
  korrekt nicht bzw. richtig zugeordnet. Bestaetigt: Schlagwort-Bindung schraenkt nur *welches*
  Konzept gemeint sein muss ein, nicht *wie* es geschrieben/gehoert wurde — der Vorteil
  gegenueber reinem Stringmatch/Regex bleibt erhalten (siehe `Gaming_assistent.md`, Abschnitt
  "Warum kein einfacher Stringmatch").
* **Vollstaendige Helldivers-2-Stratagem-Liste erfasst (08.09.2026), 77 Stratageme.** Quelle:
  acht vom Nutzer bereitgestellte Screenshots (liegen als PNG im Projektordner, z. B.
  `Waffen Stratagems Codes.png`), noch nicht ins Repo uebernommen/getrackt. Kategorien: Waffen
  (13), Orbitalkanonen (8), Hangar (9), Bruecke (7), Technikerstation (11), Robotik-Werkstatt
  (9), Kriegsanleihen (5), Missionsspezifisch (15). Nutzer hat bestaetigt: die Screenshots sind
  vollstaendig, keine abgeschnittenen Zeilen.
* **Zweiter Klassifikationstest: 13 echte Waffen-Stratageme, schlagwortbasiert, 21/25 (84 %)
  (08.09.2026).** Alle 13 Tags von Claude aus den offiziellen Stratagem-Namen abgeleitet (Tag,
  Schlagwort, Beispielsatz), dem Nutzer als Tabelle vorgelegt und bestaetigt — zwei Tags
  (`Kommando` fuer MLS-4X-Kommando, `Speer` fuer FAF-14-Speer) sind Alltagswoerter, laut Nutzer
  aber nicht aenderbar (echte Spielnamen). Ergebnis:
  * Positiv (13/13), Synonym "Wespenwerfer" fuer WASP (1/1), Mehrfachbefehle (2/2), normale
    Negativfaelle (4/4): je 100 %.
  * **Neuer Fehlertyp entdeckt:** `Kommando` 0/3, `Speer` 1/2 bei Saetzen, in denen das exakte
    Schlagwort in voellig anderer Bedeutung vorkommt ("Wer hat hier das Kommando?", "Der Speer
    der Wache..."). Anders als beim fruehreren `Verstärkung`/`Artillerie`-Fall (sinnverwandtes,
    aber anderes Wort) ist das hier dasselbe Wort in unpassendem Kontext — Schlagwort-Bindung
    ("nur wenn im Befehl das Wort X vorkommt") ist dagegen wirkungslos, weil das Wort ja
    tatsaechlich vorkommt.
  * **Vom Nutzer als vertretbar akzeptiert, mit wichtiger Begruendung:** Push-to-Talk begrenzt
    das Risiko strukturell — nur Audio, das der Nutzer bewusst durch Halten der PTT-Taste
    aufgenommen hat, erreicht ueberhaupt die Pipeline. Beilaeufiges Gespraech mit dem Schlagwort
    (Team-Chat etc.) kommt gar nicht erst bei Whisper/LLM an; riskant bleibt nur der seltene
    Fall, dass der Nutzer waehrend gehaltener PTT-Taste zufaellig einen sinnfremden Satz mit dem
    Schlagwort sagt. Im Konzept festgehalten (`Gaming_assistent.md`, Abschnitt "Pipeline").
  * Kein Nachbessern des Prompts fuer diesen Fehlertyp vorgenommen — bewusste Entscheidung, kein
    offener Punkt.
* **Restliche 64 Stratageme in `Helldivers2_Stratagems.yaml` uebersetzt (08.09.2026).** Von
  Claude aus den Namen abgeleitet (Tag/Schlagwort/Beispiel/Taste je Stratagem, Format nach
  `Gaming_assistent.md` Abschnitt "Aktionslisten-Format": `schlagwort`/`beispiel`/`taste`,
  `beschreibung` entfaellt hier da alle Tags schlagwortbasiert sind), dem Nutzer vorgelegt und
  mit zwei Korrekturen bestaetigt (`SEAF_Artillerie` Schlagwort vereinfacht auf "Artillerie" statt
  "SEAF-Artillerie" — kein zweiter Artillerie-Tag im Spiel; zwei EMS-Tags auf "EMP" umbenannt:
  `EMP_Moersergeschuetz`, `Orbital_EMP`). Datei enthaelt am Kopf eine Liste bekannter
  Namens-Konfliktcluster (u. a. dreifache "Guard Dog"-Familie) als Kommentar. **Achtung:** die
  `taste`-Werte (PC-Codes) hat Claude aus den Screenshots abgetippt, potenziell fehleranfaellig
  bei laengeren Codes — vor Code-Verwendung gegen die Original-Screenshots pruefen.
* **Dritter Klassifikationstest: vollstaendige 77-Tag-Liste, 105/107 (98,1 %) (08.09.2026).**
  Testaufbau: Prompt automatisch aus `Helldivers2_Stratagems.yaml` generiert (77 Tags, je
  wortgebundene Beschreibung + Few-Shot-Beispiel), `google/gemma-4-e4b` mit `context-length 8192`
  (noetig fuer den grossen Prompt, siehe naechster Punkt), `temperature=0`, `max_tokens=40`.
  System-Prompt: 9.814 Zeichen, 3.541 Prompt-Tokens.
  * **Alle 77 Positivfaelle (Paraphrasen, nicht identisch zu den Prompt-Beispielen): 100 %.**
  * **Alle 10 gezielt getesteten Namens-Konfliktcluster (20 Faelle): 100 %** — u. a. die drei
    "Guard Dog"-Varianten (Rover/plain/Hunde-Atem, deren Schlagwoerter sich als Substring
    ueberlappen), Moersergeschuetz vs. EMP-Moersergeschuetz, Kanone vs. Kanonengeschuetz,
    Rauchbeschuss (Adler vs. Orbital), Schildgenerator (Relais vs. Rucksack),
    Panzerabwehr (EAT/-minen/-stellung), Gatling (Orbitalsperrfeuer vs. -geschuetz).
  * Mehrfachbefehle (3/3) und allgemeine Negativfaelle (4/4): weiterhin 100 %.
  * Einzige Fehlschlaege: die zwei bereits bekannten, akzeptierten Risikofaelle (`Kommando`,
    `Speer` in sinnfremdem Kontext) — keine neuen Fehler, keine Regression durch den 10x
    groesseren Tag-Umfang.
  * **Latenz blieb bei 10x mehr Tags praktisch unveraendert** (~2,2 s Durchschnitt, 2,1–3,5 s
    Spanne) — kein messbarer Einbruch durch die Prompt-Groesse.
  * **Ergebnis der urspruenglichen Stresstest-Frage:** die flache Prompt-Struktur (alle Tags in
    einer Liste) haelt auch bei realistischem Umfang. Keine Kategorisierung/zweistufige
    Klassifikation noetig — dieser Punkt in `Gaming_assistent.md` ist damit erledigt.
* **Folgeentscheidung: Kontextlaenge muss pro Spielprofil passend gesetzt werden, nicht global.**
  Da der Prompt-Umfang stark je Profil variiert (Handvoll Tags bis 77 bei Helldivers 2), darf die
  Kontextlaenge beim `lms load` nicht auf einen einzigen knappen Wert fuers kleinste Profil
  gesetzt werden — sonst schneidet sie bei umfangreichen Profilen den Prompt ab. Naheliegend:
  Kontextlaenge automatisch aus der tatsaechlichen Prompt-Groesse des aktiven Profils ableiten
  (plus Marge fuer `max_tokens` und kuenftig ergaenzte Tags), statt sie von Hand zu raten — noch
  nicht implementiert, siehe `Gaming_assistent.md`, Abschnitt "Sampling-Parameter".
* **Naechster Schritt:** noch offen, siehe naechste Session-Runde.
* Repo ist initialisiert (`git init` direkt in diesem Ordner), vier Commits vorhanden. Neue,
  noch ungetrackte Dateien im Arbeitsverzeichnis: acht Stratagem-Screenshot-PNGs,
  `Helldivers2_Stratagems.yaml`.

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
