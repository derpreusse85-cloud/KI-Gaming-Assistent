# CLAUDE.md

Gaming-Sprachassistent: freie gesprochene Sprache waehrend des Spielens wird per LLM in eine
feste Aktion klassifiziert und als Tastenkombination ausgeloest. Konzept siehe
`Gaming_assistent.md`. Noch nichts implementiert.

## Stand der Arbeit (fuer den Wiedereinstieg in einer neuen Session)

Rein konzeptionelle Phase, kein Code vorhanden. Zuletzt bearbeitet: 07.09.2026.

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
* **Naechster offener Punkt** (siehe `Gaming_assistent.md`, Abschnitt "Offene Punkte"): Testen
  der Grundzuverlaessigkeit der Tag-Klassifikation mit Gemma 4 E4B anhand von Beispielkommandos,
  inklusive Mehrfachbefehlen und Negativ-Faellen (`&&NONE&&`). Geplanter Testaufbau (noch nicht
  umgesetzt): LLM-Klassifikation isoliert testen, ohne Whisper (Text rein, Tag raus), Testfaelle
  in drei Kategorien (klare Positivfaelle je Tag mit mehreren Formulierungen, Mehrfachbefehle in
  einer Aeusserung, Negativfaelle inkl. Grenzfaelle), Metrik: Tag-Trefferquote + gesondert die
  Treffsicherheit bei `&&NONE&&` + Latenz. Anzahl der Test-Tags fuer den ersten Durchlauf noch
  nicht festgelegt.
* Repo ist initialisiert (`git init` direkt in diesem Ordner), ein Commit vorhanden.

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
