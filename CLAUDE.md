# CLAUDE.md

Gaming-Sprachassistent: freie gesprochene Sprache waehrend des Spielens wird per LLM in eine
feste Aktion klassifiziert und als Tastenkombination ausgeloest. Konzept siehe
`Gaming_assistent.md`. Noch nichts implementiert.

## Stand der Arbeit (fuer den Wiedereinstieg in einer neuen Session)

**Konzeptphase abgeschlossen, Implementierung noch nicht begonnen.** Zuletzt bearbeitet:
09.09.2026. Zielspiel: Helldivers 2 (siehe `Gaming_assistent.md`, Abschnitt "Grundidee").
Repo ist initialisiert (`git init` direkt in diesem Ordner), acht Commits vorhanden, Working
Tree sauber (`git status` zeigt nur den nicht relevanten `.claude/`-Ordner als untracked).

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
* **Testreihe (siehe `Gaming_assistent.md`, Abschnitt "Testreihe"):** vier Testrunden vom
  8-Tag-Set bis zur vollstaendigen 77-Tag-Helldivers-2-Liste, zuletzt 105/107 (98,1 %) inkl.
  zehn gezielter Namens-Konfliktcluster (z. B. dreifache "Guard Dog"-Familie) — alle korrekt
  aufgeloest. Latenz blieb bei 10x mehr Tags praktisch unveraendert. Zwei bewusst akzeptierte
  Restrisiken bei Alltagswort-Schlagwoertern (`Kommando`, `Speer`), abgefedert durch
  Push-to-Talk (siehe „Pipeline"). Die Testskripte selbst liegen nur im Scratchpad der
  jeweiligen Session, nicht im Repo — bei Bedarf muessten sie neu geschrieben werden (Vorlage:
  Prompt aus einem YAML-Profil generieren, gegen `http://localhost:1234/v1/chat/completions`
  mit `temperature=0` testen, Tags per Regex `&&([^&]+?)&&` parsen).
* **`Helldivers2_Stratagems.yaml`** ist das fertige, getestete erste Spielprofil (77 Tags,
  `kontextlaenge: 8192`). **Achtung:** die `taste`-Werte (Tastenkombinationen) hat Claude aus
  acht Nutzer-Screenshots abgetippt, potenziell fehleranfaellig bei laengeren Codes — vor
  Code-Verwendung gegen die Original-Screenshots pruefen (liegen als PNG im Projektordner).
* **Naechster Schritt (noch nicht begonnen): Implementierung.** Sinnvoller Einstieg laut
  Konzept, Abschnitt "Wiederverwendbare Bausteine": `server/stt.py`, `server/llm.py`,
  `server/lmstudio.py`, `client/typer.py` und `client/ptt.py` aus dem Diktier-Tool
  (Pfad dort unbekannt, Nutzer fragen oder danach suchen) als Vorlage in einen einzigen Prozess
  uebernehmen, WebSocket/Token-Auth weglassen. Whisper-`initial_prompt`-Integration (Eigennamen
  aus dem Profil-Schlagwort) ist bisher nur eine Idee, nicht getestet.

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
