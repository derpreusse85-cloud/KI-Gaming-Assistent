# Gaming-Sprachassistent — Konzept

Status: Konzeptphase, nichts implementiert. Fasst mehrere Brainstorming-Sessions zusammen.

## Grundidee

Ein Tool, das gesprochene, freie Sprache (keine festen Kommandophrasen) während des Spielens
in Tastatureingaben übersetzt — z. B. "Fahrgestell ausfahren" oder "Landegestell raus" löst
automatisch die passende Tastenkombination im Spiel aus (z. B. Shift+D). Kein Modding des
Spiels selbst nötig.

Abgrenzung zu bestehenden Lösungen (z. B. VoiceAttack-Profile für Helldivers 2): Diese arbeiten
mit festen, vorprogrammierten Sprachphrasen. Der eigene Ansatz nutzt ein LLM zur freien
Absichtserkennung — nicht an exakten Wortlaut gebunden.

**Zielspiel: Helldivers 2.** Die Beispiel-Tags im Testaufbau (`Verstärkung`, `Orbitallaser`,
`Bombenteppich`, `500kg_Bombe`, ...) sind keine Platzhalter, sondern echte Kommandos aus diesem
Spiel — u. a. `&&Verstärkung&&` für das Rufen von Verstärkung (Respawn eines gefallenen
Mitspielers per Tastenkombination).

## Architektur: alles in einem Prozess

Anders als das Diktier-Tool **keine Server-Client-Aufteilung**. Dort macht die Trennung Sinn,
weil Mikrofon-PC und die GPU mit Whisper/LLM auf verschiedenen Rechnern sitzen können
(WebSocket dazwischen). Der Game Assistant läuft dagegen komplett auf dem Spiele-PC:
Mikrofonaufnahme, Whisper-Transkription, LLM-Klassifikation und das Auslösen der
Tastenkombination in einem einzigen Prozess, ohne Netzwerk-Hop dazwischen. Das spart Latenz
(kein WebSocket-Roundtrip) und Komplexität (kein Token/Auth-Handling, kein
Verbindungsmanagement).

## Pipeline

```
Sprache (PTT) → Whisper (STT) → kleines LLM (Intent-Erkennung) → Parser → Tastendruck-Simulation
```

Baut auf der bereits vorhandenen Diktier-Tool-Architektur auf: Push-to-Talk, Audio-Capture und
Whisper-STT lassen sich als Code-Vorlage direkt wiederverwenden (siehe Abschnitt
"Wiederverwendbare Bausteine" — als Vorlage in den einen Prozess übernommen, nicht als
eigenständige Server-/Client-Module weiterbetrieben).

**Push-to-Talk begrenzt das Fehlauslöse-Risiko strukturell, nicht nur der Prompt.** Whisper und
das LLM bekommen ausschließlich Audio zu Gesicht, das der Nutzer durch bewusstes Halten der
PTT-Taste aufgenommen hat — beiläufiges Gespräch (z. B. "Wer hat hier eigentlich das Kommando?"
im Team-Chat) erreicht die Pipeline gar nicht erst. Bei schlagwortgebundenen Tags (siehe
„Aktionslisten-Format") bleiben dadurch nur die Fälle riskant, in denen der Nutzer die
PTT-Taste haelt und dabei zufaellig einen sinnfremden Satz mit dem Schlagwort sagt — spürbar
seltener als beiläufige Erwähnung im laufenden Spielgespräch.

## Warum kein einfacher Stringmatch

Feste Befehlsphrasen liessen sich per Fuzzy-Match/Levenshtein direkt gegen den Whisper-Rohtext
matchen — schnell, aber unflexibel. Da freie Formulierung gewünscht ist ("Fahrgestell" vs.
"Landegestell" vs. andere Umschreibungen), braucht es stattdessen ein LLM als Klassifikator.

## Unterschied zur Diktier-Pipeline

Wichtig: das ist eine andere Aufgabe als das Bereinigen/Übersetzen im Diktier-Tool.

* **Kein Umformulieren, sondern Klassifikation** in eine geschlossene Menge bekannter Aktionen.
  Das ist für ein kleines lokales Modell (4B) deutlich einfacher und zuverlässiger als freies
  Umschreiben — genau das Umformulierungsproblem, an dem wir uns beim Bereinigungs-Prompt
  (Qwen3.5-4B, dann Gemma 4 E2B) abgearbeitet haben, entfällt hier weitgehend.
* **Kein rollierendes Fenster nötig.** Kommandos sind kurz, eine einzelne Transkription nach
  Loslassen reicht — kein 700-ms-Zwischenergebnis-Takt wie im Standardmodus.
* **Zustandslose Einzel-Session pro Aufruf.** Jeder Klassifikationsaufruf läuft ohne
  Chat-Historie, um Speicher und Tokens zu sparen. Da kein Vorkontext existiert, wird das Modell
  rein über prägnante Beispiele im System-Prompt gesteuert (Few-Shot statt Konversation) — es
  fungiert dadurch wie eine schnelle Zuordnungsfunktion, nicht wie ein Chatbot.
* **Das LLM soll nie die Taste selbst nennen.** Es antwortet nur mit einer festen Aktions-ID
  aus einer im Prompt vorgegebenen Liste (oder einem "kein Befehl"-Marker). Das Mapping von
  Aktions-ID auf Tastenkombination passiert deterministisch im Code, nicht im Modell — sonst
  besteht Hallucination-Risiko bei der Taste selbst.

## LLM-Ausgabeformat

Statt Fließtext gibt das LLM ausschließlich Tags aus, die eine feste Aktion referenzieren, z. B.
`&&LANDEGESTELL&&`.

Beispiel-Prompt-Grundgerüst:

```
Du ordnest gesprochene Anweisungen genau einem der folgenden Tags zu:
&&LANDEGESTELL&& — Fahrgestell/Landegestell aus- oder einfahren
&&ORBITALSCHLAG&& — Orbitalschlag/Orbital Strike anfordern
...
Antworte ausschließlich mit dem/den passenden Tag(s). Trifft keines zu,
antworte mit &&NONE&&.
```

Wichtige Prompt-Anforderungen:

* Explizite Regel für den Fall "kein Tag trifft zu" (`&&NONE&&`) — sonst besteht die Gefahr,
  dass das LLM bei Unsicherheit ein Tag rät statt nichts auszugeben. **Entschieden:** Passt die
  Äußerung nicht eindeutig auf einen Tag aus der Aktionsliste, wird immer `&&NONE&&` ausgegeben
  — kein Rateversuch auf den "naheliegendsten" Tag. Konsistent mit der Parser-Sicherheit (siehe
  unten), die im Zweifel ebenfalls nichts tut statt zu raten.
* **Alle erlaubten Marker explizit im Prompt aufzählen** (`&&LANDEGESTELL&&`, `&&SCHILDE&&`,
  `&&NONE&&`, ...), statt das Modell den Markertext frei formulieren zu lassen. Sonst tippt es
  irgendwann `&&Fahrwerk&&` statt `&&Landegestell&&`, und der Parser findet keinen Treffer.
* Parser muss den/die Tag(s) robust per Regex extrahieren, nicht auf exakte
  Gesamt-Antwort-Gleichheit prüfen (falls das LLM trotz Anweisung zusätzlichen Text ausgibt).
* Wie beim Bereinigungs-Prompt gilt: kurzer klarer Fließtext mit konkreten Beispielen schlägt
  eine lange Regelliste (siehe `Diktiertool.md`, Abschnitt Fallstricke).
* **Ein Beispiel pro Tag reicht in der Regel**, solange die tatsächlich gesprochenen Kommandos
  strukturell nah an den Prompt-Beispielen bleiben. Das hält den Prompt kurz und minimiert die
  Prefill-Latenz — mehr Beispiele pro Tag bringen hier voraussichtlich abnehmenden Ertrag
  (ähnlich der Beobachtung beim Bereinigungs-Prompt in `Diktiertool.md`).

## Mehrere Befehle in einer Äußerung

Möglich, z. B. "Landegestell ausfahren und um Landeerlaubnis bitten" →
`&&LANDEGESTELL&& &&LANDEERLAUBNIS&&`.

* Prompt gibt Tags in Nennreihenfolge aus.
* Parser verarbeitet eine Liste von Tags statt eines einzelnen Treffers, führt sie in der
  ausgegebenen Reihenfolge aus.
* **Bevorzugter Ansatz: allgemeine Regel statt kombinationsspezifischer Beispiele.** Eine
  Aufzählung "1–2 Beispiele pro tatsächlich vorkommender Kombination" skaliert nicht — bei N
  Tags wächst die Zahl möglicher Kombinationen kombinatorisch. Stattdessen eine Regel in Prosa
  (z. B. "Nennt die Äußerung mehrere Aktionen, gib alle passenden Tags durch Leerzeichen
  getrennt in der genannten Reihenfolge aus.") plus **ein einziges generisches Beispiel mit
  Platzhalter-Tags** (`&&AKTION_A&&`/`&&AKTION_B&&`, nicht die echten Spiel-Tags), das nur das
  *Format* der Mehrfachausgabe demonstriert. Verlässt sich auf die Instruction-Following-Fähigkeit
  von Gemma 4 E4B (genau der Grund für den Wechsel von E2B, siehe „Modellwahl für die
  Intent-Erkennung"), statt Kombinationen auswendiglernen zu lassen.
* **Fallback nicht nötig gewesen:** gezielte Beispiele mit echten Tags für konkrete Kombinationen
  (ursprünglich vorgeschlagene Methode aus `Gemma4.md`) waren als Rückfalloption vorgesehen,
  falls der generische Ansatz nicht robust genug generalisiert. Bestätigt in allen drei
  Testrunden (08.–09.09.2026, zuletzt 3/3 bei der vollständigen 77-Tag-Liste, siehe
  „Testreihe"): der generische Platzhalter-Ansatz reichte durchgehend aus, der Fallback blieb
  ungenutzt.
* **`max_tokens` für Mehrfachbefehle hochsetzen** (von ~10 für einen Einzel-Tag auf ~30–40),
  damit das Modell die Tag-Kette nicht mitten in der Ausgabe abschneidet.
* Ob eine Reihenfolge tatsächlich relevant ist oder ob bestimmte Kombinationen im jeweiligen
  Spiel überhaupt gleichzeitig ausführbar sind, liegt in der Verantwortung des Nutzers — das
  Tool soll unterstützen, nicht die spielerische Einschätzung ersetzen. Keine Sonderlogik für
  Konflikterkennung oder Reihenfolge-Unabhängigkeit vorgesehen.

## Sampling-Parameter

Für eine Klassifikation mit Tastendruck-Konsequenz ist Determinismus wichtiger als Varianz —
anders als bei freier Textgenerierung (z. B. dem Bereinigungs-Prompt im Diktier-Tool), wo etwas
Spielraum in der Formulierung unproblematisch ist.

* **`temperature = 0.0`** (Greedy Decoding): Das Modell wählt bei jedem Token immer den
  wahrscheinlichsten Nachfolger. Dieselbe Äußerung liefert dadurch reproduzierbar denselben Tag
  statt gelegentlicher Ausreißer. Nebeneffekt: die Inferenz-Engine spart sich den
  Zufalls-Sampling-Schritt, was zusätzlich etwas Latenz spart.
* **`top_p` auf Standardwert (1.0) belassen**, nicht manuell verändern — bei `temperature = 0.0`
  ist Nucleus Sampling ohnehin wirkungslos (es wird immer nur der wahrscheinlichste Token
  gewählt), ein abweichender Wert würde also nichts bewirken, aber unnötig vom Standard
  abweichen.
* **`max_tokens` hart begrenzen** (siehe oben, ~30–40 bei Mehrfachbefehlen): dient nicht nur der
  Tag-Ketten-Vollständigkeit, sondern auch als Absicherung — falls das Modell doch einmal in eine
  ungewöhnlich lange Ausgabe geraet, bricht die Anfrage hier hart ab, statt das Spiel spürbar zu
  blockieren. Ergänzt die Abschneide-Erkennung über `finish_reason` in der Parser-Sicherheit
  (siehe unten).
* **`max_tokens` und Kontextlänge bewusst minimal halten**, nicht nur wegen Latenz, sondern auch
  um den VRAM-Bedarf zu minimieren — das Modell teilt sich die GPU mit dem laufenden Spiel
  (analog zur Kontextlängen-Reduktion im Diktier-Tool, dort 1,04 GB VRAM gespart bei
  unveränderter Geschwindigkeit, siehe `Diktiertool.md`).
* **"Minimal" heißt: minimal für das jeweilige Profil, nicht ein einzelner globaler Wert.**
  Da der System-Prompt komplett pro Spielprofil generiert wird (siehe „Aktionslisten-Format"),
  variiert sein Umfang stark mit der Tag-Zahl — vom Kommando-Klassifikator mit einer Handvoll
  Tags bis zum Extremfall Helldivers 2 mit 77 Tags (gemessen 3.541 Prompt-Tokens, System-Prompt
  9.814 Zeichen — eine gemessene Zahl aus der LM-Studio-Antwort, keine Schätzung; siehe
  „Testreihe"). Die Kontextlänge beim `lms load` muss deshalb **pro Profil** passend gesetzt werden,
  nicht auf einen einzigen knappen Wert fürs kleinste Profil — sonst schneidet sie bei
  umfangreichen Profilen den Prompt ab.
* **Kontextlänge als explizites Feld im Profil, nicht automatisch zur Laufzeit berechnet.**
  Analog zu `llm_context_length`, das im Diktier-Tool schon je Profil überschreibbar ist (siehe
  `Diktiertool.md`, Abschnitt Betriebsmodi). Einmalig beim Erstellen/Testen eines Profils
  ermittelt (gemessene Prompt-Tokens plus Marge für `max_tokens` und künftig ergänzte Tags) und
  als `kontextlaenge`-Feld im Profil hinterlegt — einfacher als eine Tokenizer-Anfrage zur
  Laufzeit, und konsistent mit dem bestehenden Diktier-Tool-Muster. Für das Helldivers-2-Profil:
  `kontextlaenge: 8192` (siehe `Helldivers2_Stratagems.yaml`).

## Parser-Sicherheit (übertragbar aus `server/llm.py`)

Der Marker-Parser braucht denselben Abschneide-/Plausibilitätsschutz wie `LLMCleaner`:

* Antwort bei `finish_reason == "length"` abgeschnitten → verwerfen, kein Tastendruck
  (statt zu raten).
* Marker nicht exakt in der bekannten Liste → verwerfen, kein Tastendruck.
* Kein "Rohtext behalten" wie beim Diktat — hier gibt es kein sinnvolles Fallback ausser
  Nichtstun.

## Latenz und Denkmodus

`disable_reasoning`/das LM-Studio-„Enable Thinking"-Problem (siehe `Diktiertool.md`) gilt hier
verschärft: ein Modell, das erst hunderte Tokens nachdenkt, bevor es `&&LANDEGESTELL&&`
ausspuckt, macht aus einem Sprachbefehl eine im Spiel spürbare Verzögerung — stärker relevant
als beim Diktieren, wo eine LLM-Nachbearbeitung erst nach dem Loslassen der Taste läuft und ein
paar hundert ms weniger auffallen.

**Geprüft und verworfen: Denkmodus über ein `<|think|>`-Token im System-Prompt steuern.** Diese
Behauptung taucht in Recherchematerial auf, ist aber dieselbe, die für Gemma 4 in
`Diktiertool.md` bereits widerlegt wurde — die Chat-Vorlage erzeugt das Token selbst aus der
Variable `enable_thinking`, ein Prompt-Trick greift nicht. Eigener Test (07.09.2026, gegen
`google/gemma-4-e2b` **und** `google/gemma-4-e4b`, je gegen eine laufende und eine frisch
geladene Instanz): `chat_template_kwargs.enable_thinking` (weggelassen/`true`/`false`) liefert in
allen Fällen identisch 0 Reasoning-Tokens. Der Denkmodus ist für beide Modelle in diesem
LM-Studio-Setup bereits über den GUI-Schalter deaktiviert — weder Prompt noch API-Parameter
spielen eine Rolle, solange niemand den Schalter manuell umstellt.

## Modellwahl für die Intent-Erkennung

* **Gemma 4 E2B verworfen** (2,3 Mrd. effektive Parameter): Recherche ergab
  Instruction-Following-Schwächen bei verketteten/mehrfachen Kommandos in einer Äußerung. Da
  genau das ein vorgesehener Anwendungsfall ist (siehe „Mehrere Befehle in einer Äußerung"),
  ist E2B als Standardmodell ungeeignet.
* **Aktuelle Wahl: Gemma 4 E4B** (4,5 Mrd. effektive Parameter) — laut Recherche der
  „Stabilitäts-Sieger" bei Mehrfachbefehlen, mit genug paralleler Aufmerksamkeit, um mehrere
  Absichten in einem Satz sauber zu erfassen, ohne dass die Tags im Q4-Quant durcheinandergeraten.
  Preis ist etwas höhere Latenz gegenüber E2B (Recherche nennt ca. 30–50 ms gegen <15 ms —
  **unbelegte Zahlen, nicht selbst nachgemessen**).
* **Denkmodus kein Hindernis für E4B:** eigener Test (07.09.2026) bestätigt 0 Reasoning-Tokens
  in diesem LM-Studio-Setup, siehe „Latenz und Denkmodus" oben — der Wechsel von E2B auf E4B
  ändert daran nichts.
* Kernfrage bleibt die Instruction-Following-Fähigkeit des Modells — strikte Formattreue und
  zuverlässige Negativ-Erkennung sind hier kritischer als bei freier Textgenerierung, da eine
  Fehlklassifikation eine ungewollte Spielaktion auslöst. **Erster Test (08.09.2026): 24/25
  (96 %)** auf einem kleinen, informellen Testset — siehe „Bereits entschieden" und „Testreihe"
  für Details und Einschränkungen.

## Aktionslisten-Format

Die Zuordnung Tag ↔ Beschreibung ↔ Taste wird in **YAML-Dateien, eine pro Spielprofil**,
gepflegt:

```yaml
# profiles/star_citizen.yaml
kontextlaenge: 4096  # Top-Level-Feld, einmalig ermittelt (siehe "Sampling-Parameter")
LANDEGESTELL:
  schlagwort: ["Landegestell", "Fahrgestell"]
  beispiel: "Fahrgestell einfahren"
  taste: ["shift", "n"]
ORBITALSCHLAG:
  schlagwort: ["Orbitalschlag"]
  beispiel: "Ruf den Orbitalschlag"
  taste: ["ctrl", "o"]
```

* **YAML statt JSON/TOML**, weil Kommentare möglich sind und sich die Datei gut von Hand
  editieren lässt.
* **`schlagwort`** ist immer eine Liste (auch bei nur einem Wort) und die Grundlage für die im
  Prompt aufgezählten Tags — daraus wird standardmäßig die wortgebundene Beschreibung generiert
  (`&&TAG&& — nur wenn im Befehl eines der Wörter "..." vorkommt`), siehe „Bereits entschieden"
  zur Schlagwort-Bindung als Prompt-Strategie für dieses Spiel. Mehrere gleichwertige Wörter
  (Synonyme, Abkürzungen, englische Alternativbegriffe) lassen sich einfach als weitere
  Listeneinträge ergänzen — umgesetzt und gegen Konfliktcluster getestet im Helldivers-2-Profil,
  siehe `CLAUDE.md`. Optional überschreibbar über ein zusätzliches
  `beschreibung`-Feld, falls ein Tag statt Schlagwort-Bindung eine freiere, inhaltliche
  Beschreibung braucht (Einzelfall, siehe `Verstärkung`-Tradeoff). **`schlagwort`** ist
  zusätzlich die Quelle für die automatisch zusammengesetzte Whisper-`initial_prompt`-Liste
  (siehe „Wiederverwendbare Bausteine"). **`beispiel`** liefert die Formulierung fürs
  Few-Shot-Beispiel im Prompt (`"{beispiel}" -> &&TAG&&`) — laut Testergebnis (siehe
  „Testreihe") reicht dafür in der Regel ein Beispiel pro Tag. **`taste`** wird dem Modell nie
  gezeigt und nur im Code für die Tastendruck-Simulation verwendet — passt zum Prinzip "Modell
  nennt nie die Taste selbst"
  (siehe oben).
* **Der komplette System-Prompt wird pro Spielprofil generiert, nicht geteilt.** Tag-Liste,
  Beschreibungen und Few-Shot-Beispiele stammen ausschließlich aus dem aktuell ausgewählten
  Profil — es gibt keinen spielübergreifenden Basis-Prompt, in den Profile nur Tags einspeisen.
  Grund: die im Klassifikationstest (siehe „Testreihe") gefundenen, tag-spezifischen
  Formulierungsanpassungen (z. B. die wortgebundene Beschreibung bei `Verstärkung`) sind
  spielspezifisches Feintuning, das sich nicht sinnvoll auf ein anderes Spiel übertragen lässt.
* **Taste als Liste** (`["shift", "n"]`), nicht als zusammengesetzter String (`"shift+n"`) —
  eindeutig beim Parsen, kein Trennzeichen-Problem bei Sondertasten.
* **Ein Profil pro Spiel**, nicht eine globale Liste, um Tastenkombinations-Kollisionen
  zwischen verschiedenen Spielen zu vermeiden.
* **Manuelle Profilauswahl über das Tray-Menü**, analog zu `profiles` und dem Menü „Modus" im
  Diktier-Tool (siehe `Diktiertool.md`). Es gibt bewusst **keine automatische Spielerkennung**
  (kein Fenstertitel-/Prozessname-Scan) — der Nutzer wählt das passende Profil vor dem Spielen
  selbst aus.

## Wiederverwendbare Bausteine aus dem Diktier-Tool

Werden als Code-Vorlage in den einen Prozess übernommen, nicht als eigenständige
Server-/Client-Module weiterbetrieben — WebSocket, Token-Auth und alles, was nur der
Verteilung auf zwei Rechner dient, entfällt:

* `server/stt.py` — Whisper-Transkription (ohne rollierendes Fenster, einmalig nach Loslassen).
  Der dort bereits vorhandene `initial_prompt`-Mechanismus (getestet in `test_prompt.py`, im
  Diktier-Tool für einen anderen Zweck genutzt) eignet sich hier, um Whisper die Eigennamen des
  aktiven Spielprofils vorab bekannt zu machen — verbessert die Erkennung ungewöhnlicher
  Begriffe (z. B. Stratagem-Namen) schon auf STT-Ebene, vor der LLM-Klassifikation. Die Liste
  wird automatisch aus den Schlagwörtern des Profils zusammengesetzt (siehe
  „Aktionslisten-Format"), nicht separat gepflegt.
* `server/llm.py` — Grundgerüst für die LM-Studio-Anfrage (Payload, Timeout,
  Abschneide-Erkennung), Klassifikations-Logik statt Bereinigungs-Logik
* `server/lmstudio.py` — Modell-Laden/-Verwaltung über `lms`
* `client/typer.py` — `pynput.keyboard.Controller`, `press`/`release` funktioniert genauso mit
  Tastenkombinationen (Shift+D) wie mit einzelnen Zeichen beim Tippen
* PTT-Erkennung aus `client/ptt.py` (Taste halten = Aufnahme an), da Push-to-talk auch hier das
  Auslöser-Modell bleibt

## Verbindung zu Nero

Das Gaming-Tool dient als kleineres, klar abgegrenztes Testfeld für ein Architekturprinzip, das
später bei Nero für eine Spiel-/Werkzeug-Integration gebraucht würde: Sprache → Absicht
erkennen → Aktion auslösen.

Wichtiger Unterschied zu Nero: Beim Gaming-Tool ist die LLM-Ausgabe ausschließlich der Tag. Bei
Nero soll das Modell zusätzlich zu einer natürlichen Textantwort einen Tag einbetten (näher an
Function Calling/Tool Use als an reiner Klassifikation) — das ist eine komplexere Aufgabe, die
separat getestet werden müsste, sobald sie bei Nero ansteht. Nero hat dabei den Vorteil, ohnehin
ein stärkeres, robusteres LLM zu nutzen (aktuell Qwen3.5 9B) statt eines auf Geschwindigkeit
optimierten Kleinmodells wie beim Gaming-Tool — das sollte Instruction-Following und
Robustheit bei Randfällen begünstigen.

Nero verfügt bereits über eine konzeptionelle Sammlung eigener Tags (OKF-Link-Kategorien) —
strukturell verwandt mit dem hier verwendeten Tag-Mechanismus.

Der beim Gaming-Tool gesammelte und aufbereitete Trainingsdatensatz (Text + korrekter Tag,
siehe Abschnitt "Trainingsdaten-Sammlung" unten) soll perspektivisch nicht nur zum Fine-Tuning
des Gaming-Tool-eigenen Live-Modells dienen, sondern auch als Trainingsmaterial für Nero selbst
wiederverwendet werden können — dieselbe Grundfähigkeit (Text einer Absicht/einem Tag
zuordnen) wird an beiden Stellen gebraucht.

## Trainingsdaten-Sammlung für künftiges Fine-Tuning

Ziel: Aus echter Nutzung heraus einen Datensatz aufbauen, um das Live-Modell (kleines,
schnelles Modell) durch Fine-Tuning zu verbessern — im Grunde eine Wissens-Destillation von
einem stärkeren Offline-Modell auf das schnelle Live-Modell.

**Live-Betrieb (während des Spielens):** Rohdaten werden ungefiltert mitgeloggt — Whisper-
Rohtext + vom LLM erkannte(r) Tag(s). Kein Echtzeit-Feedback-Mechanismus nötig, kein Eingriff
in den Spielfluss.

**Offline-Aufbereitung (zeitlich entkoppelt, z. B. einmalig nach Tagen/Wochen Sammelzeit):**
Zweistufiger Extraktor-Durchlauf über die gesammelten Rohdaten, analog zum Extraktor-Prinzip
aus dem Nero-Projekt:

1. **Durchlauf 1 — Plausibilitätsprüfung:** Für jeden geloggten Fall wird geprüft, ob Rohtext
   und ursprünglich erkannter Tag plausibel zusammenpassen (Ja/Nein). Als "richtig" bestätigte
   Fälle werden gespeichert (`training_data/correct/`).
2. **Durchlauf 2 — Korrektur:** Nur die in Durchlauf 1 als "falsch" aussortierten Fälle werden
   erneut vorgelegt, diesmal mit dem Auftrag, den korrekt gewesenen Tag zu bestimmen. Ergebnis
   wird separat gespeichert (`training_data/corrected/`), inkl. ursprünglich falschem und
   korrigiertem Tag.

Vorteil der Zweiteilung: Durchlauf 1 ist eine einfache, für alle Fälle schnell zu lösende
Aufgabe; Durchlauf 2 (komplexere Aufgabe) läuft nur auf der kleineren Teilmenge der tatsächlich
fehlerhaften Fälle. Da der gesamte Extraktor-Durchlauf offline und zeitlich entkoppelt vom
Spielbetrieb läuft, kann dafür ein größeres, langsameres, aber robusteres Modell verwendet
werden (z. B. Qwen3.5 9B aus dem Nero-Setup), ohne dass dies den Spielbetrieb beeinträchtigt —
dieselbe GPU-Konkurrenz-Problematik wie beim Diktier-Tool-Gaming-Modus tritt hier gar nicht
erst auf.

Offene Grenze des Ansatzes: Der Extraktor kann nur korrigieren, wenn sich aus dem Kontext
eindeutig ableiten lässt, was gemeint war. Bei echter Mehrdeutigkeit bleibt vermutlich
weiterhin eine manuelle Sichtung durch den Nutzer nötig.

### Nebengedanke: Weiterverwendung der Trainingsdaten für Nero

> Kein Bestandteil des Gaming-Tools selbst — nur als Idee festgehalten, wie die hier
> gesammelten Daten später einem anderen Projekt (Nero) nützen könnten.

Die zweistufig aufbereiteten Trainingsdaten (`correct/` + `corrected/`) bestehen aus
Text→Tag-Zuordnungen mit Kontext. Dieses Format könnte auch als Trainingsmaterial für Neros
eigene Absichtserkennung dienen — dort allerdings mit anderen, für Nero relevanten Tags statt
Gaming-Kommandos wie Landegestell/Orbitalschlag. Der Wert läge weniger in den konkreten
Inhalten als im bewährten Sammel- und Aufbereitungsprozess selbst.

Einschränkung: Nero soll zusätzlich zum Tag eine natürliche sprachliche Antwort liefern (anders
als das Gaming-Tool, das ausschließlich den Tag ausgibt). Der reine Text→Tag-Datensatz reicht
dafür nicht aus. Lösungsidee: ein weiterer, nachgelagerter LLM-Durchlauf auf dem bereits
bereinigten Datensatz, der pro Eintrag um den feststehenden, verifizierten Tag herum eine
passende sprachliche Antwort ergänzt. Dabei müsste der Antwort-Generierungs-Prompt Kontext
über Neros Charakter/Sprechweise mitbekommen, damit die erzeugten Antworten zu Neros eigenem
Sprachstil passen und nicht neutral/systemhaft klingen.

## Bereits entschieden

* **Eigenständiges Projekt, eigenes Repo** statt Betriebsprofil im Diktier-Tool oder Branch
  dort. Als Referenz liegt eine Kopie der Diktier-Tool-`CLAUDE.md` als `Diktiertool.md` bei,
  dazu diese Konzeptdatei; das Repo bekommt eine eigene, schlanke `CLAUDE.md` mit nur den
  übertragbaren Lektionen.
* **Ein Prozess statt Server-Client** (siehe oben) — läuft komplett lokal auf dem Spiele-PC.
* **Kein Mehrsprachigkeits-Support** — Kommandos werden ausschließlich auf Deutsch gesprochen,
  Whisper wird fest auf Deutsch statt auf automatische Spracherkennung eingestellt.
* **Whisper-Modell: `large-v3-turbo-german-q5`** — dasselbe Modell, das im Diktier-Tool für den
  Gaming-Modus vorgesehen ist (547 MB, gemessen zeichengleich zur vollen Fassung, 3,5 % lockere
  Wortfehlerrate, siehe `Diktiertool.md`). Passt hier besonders, weil Kommandos kurz sind und
  kein LLM den Whisper-Text nachbessert.
* **Bei mehrdeutigen Tags: Präzision vor Vollständigkeit, notfalls über Wortbindung.** Erster
  Klassifikationstest (08.09.2026, siehe „Testreihe") zeigte, dass Gemma 4 E4B bei
  `&&Verstärkung&&` sinnverwandte, aber falsche Begriffe ("Ruf die Artillerie") fälschlich
  demselben Tag zuordnete. Behoben durch eine an das wörtliche Vorkommen des Begriffs gebundene
  Tag-Beschreibung ("nur wenn im Befehl auch das Wort 'Verstärkung' vorkommt") — Kehrseite: eine
  rein umschriebene, indirekte Formulierung ohne das Wort selbst ("Die sollen uns hier
  raushauen") wird dadurch nicht mehr erkannt. Für `Verstärkung` bewusst akzeptiert, weil das
  Zielspiel Helldivers 2 (siehe „Grundidee") für dieses Kommando ohnehin keinen echten
  Interpretationsspielraum hat — Spieler sagen in der Praxis das Wort "Verstärkung" so gut wie
  immer direkt. Kein allgemeines Prinzip für alle Tags, sondern eine Einzelfallentscheidung, die
  sich bei anderen mehrdeutigen Tags wiederholen könnte.

## Testreihe (abgeschlossen)

Keine offenen Konzeptfragen mehr — alle Punkte, die vor Implementierungsbeginn geklärt werden
sollten, sind durch die Testreihe beantwortet.

* **Testreihe durchgeführt (08.–09.09.2026, Details in `CLAUDE.md`):** vom 8-Tag-Testset (24/25)
  über 13 echte Waffen-Stratageme (21/25) bis zur vollständigen 77-Tag-Helldivers-2-Liste
  (105/107, 98,1 %) — siehe `Helldivers2_Stratagems.yaml` für das vollständige Profil.
  **Damit ist die ursprüngliche Stresstest-Frage beantwortet:** die flache Prompt-Struktur
  (alle Tags in einer Liste) bricht auch bei realistischem Umfang nicht ein — 100 % auf allen
  77 Positivfällen und allen 10 gezielt getesteten Namens-Konfliktclustern (u. a. die
  Guard-Dog-Familie mit drei sich überlappenden Schlagwörtern), Latenz blieb bei 10x mehr Tags
  praktisch unverändert (~2,2 s Durchschnitt). Keine Kategorisierung/zweistufige Klassifikation
  nötig. Bleibt bewusst akzeptiert: die zwei bekannten Risikofälle bei Schlagwörtern, die auch
  Alltagswörter sind (`Kommando`, `Speer`), siehe „Bewusst akzeptierter Tradeoff" und die
  PTT-Einordnung unter „Pipeline".

Was jetzt noch offen ist, ist keine Konzeptfrage mehr, sondern reine Umsetzung: Code schreiben
(siehe „Wiederverwendbare Bausteine"), Whisper-`initial_prompt`-Integration bauen (noch nicht
getestet, nur als Idee festgehalten), und die übrigen Spielprofile (aktuell nur Helldivers 2
existiert) nach Bedarf ergänzen.

## Status

**Umgesetzt, Version 1.0 (09.09.2026), im echten Spiel gegen Helldivers 2 bestätigt** — nicht
mehr rein konzeptionell. Aktueller Stand, Modulstruktur und alle seither gewonnenen Erkenntnisse
(Latenzmessung, Design-Entscheidung `halte_taste` usw.) stehen in `CLAUDE.md`, Abschnitt "Stand
der Arbeit" — diese Konzeptdatei hier bleibt für das grundsätzliche Design und die
Testreihen-Begründung maßgeblich, wird aber nicht mehr laufend nachgeführt.

**In Planung (11.09.2026, noch nicht begonnen): eigenständiger Betrieb ohne LM Studio.**
Hintergrund ist eine mögliche Veröffentlichung auf GitHub — ähnliche Sprache-zu-Tastenanschlag-
Tools existieren zwar bereits, nutzen aber alle feste Kommandophrasen statt freier Phrasierung
per LLM, was das Alleinstellungsmerkmal dieses Projekts wäre. Eine Pflicht-Abhängigkeit zu einer
separat zu installierenden LM-Studio-Instanz wäre dafür aber eine hohe Einstiegshürde. Geplant:
Git LFS einrichten, das Gemma-4-E4B-Modell (Apache-2.0-lizenziert, verifiziert 11.09.2026) direkt
ins Repo übernehmen, und `llm.py`/`lmstudio.py` durch eine direkte llama.cpp-Anbindung ersetzen
statt der LM-Studio-API. Details und offene Architekturfragen: `CLAUDE.md`, Abschnitt "Geplant:
LM Studio ablösen".
