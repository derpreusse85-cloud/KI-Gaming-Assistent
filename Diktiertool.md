# CLAUDE.md

Lokales Push-to-talk-Diktat: Taste halten, sprechen, loslassen. Der Text erscheint live
im aktiven Fenster und wird beim Loslassen durch eine LLM-bereinigte Fassung ersetzt.
Alles im eigenen LAN, keine Cloud.

Der Code ist deutsch kommentiert, Bezeichner sind gemischt deutsch/englisch. Neue
Kommentare bitte auf Deutsch, ohne Umlaute im Quelltext (Ausnahme: Nutzertexte und
LLM-Prompts, dort sind Umlaute erwuenscht).

## Aufbau

```
Client (beliebiger PC)                  Server (Haupt-PC, RX 7900 XTX)
 pynput  Push-to-talk                    whisper.cpp (Vulkan) als Subprozess
 sounddevice  Mikrofon    ── WebSocket ─▶ rollierendes Fenster
 pynput  Live-Tippen      ◀── (Token) ── LM Studio, Gemma 4 E2B
```

* `server/` — WebSocket, whisper.cpp-Steuerung, LLM-Nachbearbeitung, Tray
* `client/` — PTT, Audio, Tippen, Tray. Haengt nur an `client/` und `common/`
* `common/` — Config, Ring-Log mit Tk-Fenster, gezeichnete Tray-Icons
* `tests/` — Regressionssuiten, siehe unten
* `eval/` — Werkzeug fuer ASR-Vergleiche (Aufnahme, Wortfehlerrate), `eval/LIESMICH.md`
* Zwei getrennte venvs (`.venv-server`, `.venv-client`), damit ein reiner Client-PC
  keine Server-Pakete braucht. Python **3.12** (3.14 hat keine Wheels fuer sounddevice/pystray)

## Befehle

```powershell
scripts\build_whisper.ps1            # whisper.cpp mit -DGGML_VULKAN=ON bauen
scripts\fetch_models.ps1             # sechs Modelle laden, siehe Kopf des Skripts
scripts\setup_venvs.ps1              # beide venvs anlegen
scripts\package_client.ps1           # Quellcode-Paket, ~28 KB, braucht Python
scripts\package_client.ps1 -Portable # alles dabei, ~34 MB, braucht nichts
tests\run_all.ps1 [-Full]            # Regression; LM Studio muss laufen

.venv-server\Scripts\python.exe -m server   # mit Konsole
.venv-client\Scripts\python.exe -m client
Diktier-Server.vbs / Diktier-Client.vbs     # lautlos, ueber Tray bedienbar
```

## Kernmechanismen

**Rollierendes Fenster statt Streaming.** whisper.cpp kann nicht inkrementell
transkribieren, `whisper-server` verarbeitet immer eine vollstaendige Datei. Der Server
transkribiert deshalb alle 700 ms das aktive Fenster neu und schreibt alte Segmente
anhand der `verbose_json`-Timestamps fest (`server/stt.py`). Dadurch bleibt die Latenz
konstant, egal wie lang diktiert wird.

**Ein Codepfad fuer Tippen und Ersetzen.** Der Server schickt in jedem Zwischenergebnis
den *vollstaendigen* Session-Text. Der Client vergleicht ihn mit dem selbst Getippten,
loescht die Differenz per Backspace und tippt den Rest (`client/typer.py`). Whisper-
Revisionen und die finale LLM-Ersetzung laufen so ueber denselben Mechanismus. Es werden
nie mehr Zeichen geloescht, als der Client selbst getippt hat.

**Betriebsmodi** (`profiles` in der Config, Tray-Menue „Modus"): `standard` mit
Live-Vorschau und LLM, `gaming` ohne beides — statt ~15 Inferenzen je Diktat laeuft dann
genau eine, rund 91 % weniger GPU-Arbeit. `uebersetzen` ist wie `gaming` gebaut, schickt
den Whisper-Text aber durch Gemma 4 E2B und tippt Englisch. Der Client waehlt, der Server
wendet an; der Profilname geht in der `start`-Nachricht mit. Ein Profil darf `llm_model`,
`llm_prompt`, `llm_no_think`, `llm_context_length`, `partial_interval_ms` und `language`
ueberschreiben.

**`standard` und `uebersetzen` nutzen seit 24.08.2026 dasselbe Sprachmodell**
(`google/gemma-4-e2b`), nur mit unterschiedlichem `llm_prompt`. Da der `lms`-Bezeichner
allein aus dem Modellnamen gebildet wird (`server/lmstudio.py`), bleibt beim Wechseln
zwischen den beiden dieselbe LM-Studio-Instanz geladen — kein Nachladen noetig, anders
als beim Wechsel von/zu `gaming`.

**`gaming` erkennt die Sprache selbst** (`language: "auto"` statt des globalen `"de"`),
damit der Modus ohne LLM-Nachbearbeitung auch mit englischem Diktat funktioniert. Das
Whisper-Modell ist serverweit, nicht je Profil (siehe Offene Punkte) — ein Umschalten
zwischen `large-v3-turbo-german-q5` und `large-v3-turbo-q5` je nach Sprache waere im
Gaming-Modus also staendiges Tray-Gefummel, zumal sich Deutsch und Englisch im Spiel auch
**innerhalb derselben Session** abwechseln koennen (Team-Ansagen auf Englisch, alles
andere Deutsch). Deshalb ist fuer diesen Modus **`large-v3-turbo-q5`** (die nicht
deutsch nachtrainierte, mehrsprachige Fassung) der bessere Kompromiss als Vorgabe — die
deutsche Fassung ist auf Deutsch optimiert und dafuer bei Englisch im Nachteil.

**Der Server laedt die LLM-Modelle selbst** ueber die `lms`-CLI, mit eigenem Bezeichner
(`diktier-<name>`), fester Kontextlaenge und `--gpu max` (`server/lmstudio.py`). Das haelt
die Einstellungen von anderen Verwendungen derselben Modelle in LM Studio fern. Abschaltbar
ueber `llm.manage_loading`; fehlt die CLI, wird geloggt und LM Studios eigenes Nachladen
greift wie zuvor.

Beim Moduswechsel wird das nicht mehr gebrauchte Sprachmodell **sofort entladen**
(`llm.unload_other_models`), statt auf die TTL zu warten — gemessen 5,7 GB weniger im
Uebersetzungsmodus, Preis sind 4,4 s Nachladen beim Zurueckwechseln. Angefasst werden nur
Instanzen mit unserem Praefix. Bei mehreren Clients in verschiedenen Modi gehoert das
abgeschaltet, sonst raeumen sie sich gegenseitig das Modell weg.

**Modellwechsel zur Laufzeit** ueber `/load` von whisper-server, Tray-Menue
„Whisper-Modell". Das Modell ist serverseitig — wer umschaltet, aendert es fuer alle.

**Erweiterter Log** (Tray-Haekchen, `client.verbose_log`, standardmaessig aus): schreibt
Whisper-Rohtext und LLM-Ergebnis im Klartext ins Log. Nur damit laesst sich unterscheiden,
ob Whisper danebenlag oder das LLM daraus etwas Falsches gemacht hat — im
Uebersetzungsmodus ist der deutsche Zwischentext sonst nirgends sichtbar. Der Client
entscheidet, der Server protokolliert; das Flag geht in der `start`-Nachricht mit.

## Fallstricke — hier bitte nichts „vereinfachen"

Jeder Punkt hat Zeit gekostet und ist im Code kommentiert.

**Mikrofon-Audio ueber AnyDesk (oder aehnliche Remote-Tools) treibt Whisper bei kurzen
Diktaten zuverlaessig in Halluzinationen.** Beobachtet am 23.08.2026: "I am happy"
(~1 s) lieferte ueber das lokale PC-Mikrofon 8 von 8 Mal sauber "I am happy.", ueber
Laptop-Mikro → AnyDesk → PC dagegen 2 von 2 Mal "Thank you." — bei niedrigem
`no_speech_prob` und normalem `avg_logprob`, Whisper war sich seiner falschen Antwort
also sicher. Ursache vermutlich Kompression/Rauschunterdrueckung in AnyDesks
Audio-Weiterleitung, die bei so kurzem Audio genug Signal kostet, um das Modell in eine
gelernte Standardphrase abrutschen zu lassen. Bei laengeren Diktaten faellt es nicht auf,
weil genug sauberes Signal uebrig bleibt. Betrifft den Transportweg, nicht den Code -
kein Fix hier moeglich; beim Testen ueber Remote-Tools also mit Vorsicht genau lesen.
Zum Nachstellen: Tray-Haekchen „Debug-Log" am Server zeigt pro Segment
`no_speech_prob`, `avg_logprob` und die erkannte Sprache (`server/stt.py`, `log.debug`
in `_transcribe_once`).

**LM Studio ignoriert `enable_thinking`.** Nachgemessen: Qwen3 denkt trotzdem, fuellt
`reasoning_content` und laesst `content` leer. Wirksam ist `/no_think` im Prompt.
`server/llm.py` schickt beides und strippt `<think>` in jedem Fall.

**`/load` beendet whisper-server mit `exit(1)`,** wenn die Datei existiert, aber kein
gueltiges Modell ist (offenes TODO im Quelltext). Deshalb wird **nie ein vom Client
gelieferter Pfad** durchgereicht — nur Namen, aufgeloest gegen den eigenen
Verzeichnis-Scan (`server/whisper_proc.py`).

**whisper-server schneidet Segmente mitten durch Woerter.** Seine Vorgabe fuer `max_len`
ist 0, was er intern zu **60 Zeichen** macht, und geschnitten wird an der *Token*-Grenze.
Aus „Pull Request" wurden so zwei Segmente „Pull Re" und „quest", die `server/stt.py`
mit Leerzeichen wieder zusammensetzte — im Standardmodus buegelt das LLM es aus, im
Gaming-Modus landet es so im Fenster. Deshalb geht `split_on_word` in jeder Anfrage mit
(`server/stt.py`). Erkennungsmerkmal im `verbose_json`: das Folgesegment beginnt dann
*ohne* fuehrendes Leerzeichen. Gemessen 8,8 % → 4,4 % Wortfehlerrate.

**pynput spielt eigene synthetische Anschlaege an den eigenen Listener zurueck**
(8 von 8 gemessen). Ohne Gegenmassnahme markiert sich jedes Diktat selbst als
„Nutzer hat getippt" und die Endersetzung entfaellt. Ein exakter Zaehler traegt nicht,
weil Grossbuchstaben und Umlaute zusaetzliche Shift-Events erzeugen — daher das
Zeitfenster im `EchoGuard` (`client/typer.py`).

**Der dirty-Schutz greift nur, wenn tatsaechlich geloescht wird.** Er soll verhindern,
dass Backspaces fremden Text treffen. Im Gaming-Modus steht noch kein Text im Fenster,
das Einfuegen ist rein additiv — dort waere die Sperre schaedlich, weil beim Spielen
staendig Bewegungstasten gedrueckt werden.

**Tk-Objekte aus einem Nebenthread muessen dort auch aufgeraeumt werden.** Sonst sammelt
sie der Garbage Collector des Hauptthreads ein und Tcl beendet den Prozess mit
`Tcl_AsyncDelete: async handler deleted by the wrong thread`. Logfenster und PTT-Dialog
kapseln ihre Tk-Objekte deshalb in einer eigenen Funktion und rufen danach `gc.collect()`
im Fensterthread (`common/logbuf.py`, `client/ptt_dialog.py`). Keine `tk.StringVar` —
deren `__del__` hat dieselbe Ursache.

**PyInstaller ist keine Option.** Die damit gebaute .exe lief hier einwandfrei und wurde
auf einem anderen PC von Windows Defender kommentarlos geloescht; der Bootloader kommt in
viel Schadsoftware vor. Das portable Paket legt statt dessen die signierte
Embeddable-Distribution von python.org bei. Dabei zu beachten: sie laeuft **isoliert**
(`sys.path` steht nur in `python\python312._pth`, dort muss `..` stehen) und bringt
**kein Tkinter** mit — das wird aus der normalen Installation nachgereicht, inklusive
`zlib1.dll`, an der `tcl86t.dll` haengt.

**Gemmas Denkmodus haengt an einem Schalter in LM Studio,** nicht am Code: Inference →
Custom Fields → „Enable Thinking". Er muss **aus** stehen, sonst wird der
Uebersetzungsmodus rund dreimal so langsam — bei zeichengleichem Ergebnis, nachgemessen.
In beide Richtungen geprueft: `chat_template_kwargs` wird von LM Studio verworfen, und
`lms` hat keinen Unterbefehl fuer Custom Fields. Die Modellkarte behauptet, man steuere es
ueber `<|think|>` im System-Prompt — das trifft nicht zu, die Chat-Vorlage erzeugt das
Token selbst aus der Variablen `enable_thinking` (Vorgabewert `false`).

**`/no_think` ist eine Qwen-Konvention.** Modelle, die sie nicht kennen, duerfen sie nicht
bekommen — sie waere nur Rauschen im Prompt. Dafuer gibt es `llm_no_think` je Profil.

**Qwen3.5 unterstuetzt laut eigener Modellkarte kein `/no_think`/`/nothink` mehr** (anders
als Qwen3) — abschaltbar nur ueber `chat_template_kwargs.enable_thinking: false`, und das
haengt vom konkreten Quant ab: `lmstudio-community/qwen3.5-4b` ignoriert den Parameter
komplett (5900+ Reasoning-Tokens fuer einen Satz, Antwort bricht bei `max_tokens=4096` ab,
`llm.py` behaelt dann den Rohtext). Der **Unsloth-Build `unsloth/qwen3.5-4b` respektiert
ihn zuverlaessig** (0 Reasoning-Tokens, nachgemessen). Deshalb steht `llm.model` seit
23.08.2026 auf `unsloth/qwen3.5-4b`, nicht auf den kuerzeren Bezeichner `qwen3.5-4b` (der
loest sich ueber `lms` sonst auf den falschen Anbieter auf).

**Vision-Encoder und Sprachmodell sind bei multimodalen GGUFs getrennte Dateien**
(`Qwen3.5-4B-Q4_K_S.gguf` + `mmproj-*.gguf`, bei `unsloth/qwen3.5-4b` 1,3 GB). llama.cpp
laedt den `mmproj`-Teil nachweislich nur bei tatsaechlicher Bildeingabe (nachgemessen:
`lms ps` zeigt nach dem Laden und nach einer reinen Text-Anfrage konstant 3,92 GB, die
GPU-Speicherbelegung aendert sich durch die Text-Anfrage um unter 4 MB). Da unser Server
nie Bilder schickt, kostet der Vision-Teil hier ohnehin kein VRAM — es gibt nichts
abzuschalten.

**Qwen3.5-4B formuliert staerker um als Qwen3 8B es tat,** trotz Anweisung „Ändere den
Inhalt und die Reihenfolge sonst nicht": Tempus/Modus wurden veraendert („wollte" →
„möchte", „kannst" → „könntest"), Anglizismen uebersetzt statt bereinigt („done" →
„erledigt"), und Selbstkorrekturen des Sprechers („äh ich meine") wurden ohne Beispiel im
Prompt so gut wie nie erkannt (`Abendkasse äh ich meine Abgabefrist` wurde zu Unsinn
verschmolzen statt ersetzt). Der Prompt bekam deshalb zwei konkrete Beispiele fuer
Selbstkorrekturen (eines davon elliptisch, ohne wiederholte Praeposition) sowie ein
explizites Verbot von Synonymen/Tempus-/Modus-Wechsel/Anglizismen-Uebersetzung. Damit
funktionieren Selbstkorrekturen zuverlaessig, wenn die beiden Woerter thematisch
zusammenpassen (Wochentage, Projektbegriffe). Bleibt unzuverlaessig: korrigiert der
Sprecher zu einem semantisch voellig unverwandten Wort (`Abendkasse` → `Abgabefrist`),
deutet das Modell „ich meine" gelegentlich weiter als Aufzaehlung statt als Korrektur —
wirkt wie eine Grenze der 4B-Groesse, nicht (nur) ein Prompt-Problem. Weitere
Beispielsaetze im Prompt brachten dagegen abnehmenden Ertrag.

**Trotzdem war Qwen3.5-4B als Standardmodell nicht zufriedenstellend** (24.08.2026) —
das Umformulieren blieb im Alltag spuerbar. Gegentest mit `google/gemma-4-e2b` und
demselben Bereinigungs-Prompt (statt des Uebersetzungs-Prompts) gegen dieselben
Testfaelle: Gemma ist bei einem realistischen Diktatsatz deutlich schneller (0,46 s /
60 Tokens gegen 4,1 s bei Qwen3.5-4B), haelt Tempus/Modus zuverlaessiger und uebersetzt
keine Anglizismen. Der Abendkasse/Abgabefrist-Randfall besteht bei Gemma **genauso** —
das ist also keine Qwen3.5-Eigenheit, sondern zeigt sich bei kleinen lokalen Modellen
allgemein. Gemma brauchte dafuer zusaetzlich die Satzzeichen-Anweisung (siehe naechster
Absatz) — ohne sie blieben Satzanfaenge klein und Saetze ohne Schlusspunkt, auch beim
Bereinigen, nicht nur beim Uebersetzen. Seit 24.08.2026 ist `llm.model` deshalb
`google/gemma-4-e2b`, mit dem in `common/config.py` hinterlegten erweiterten Prompt.

**Gemma braucht beim Uebersetzen die ausdrueckliche Ansage, Satzzeichen zu setzen.**
Im Feld fielen sie weg. Der Uebersetzungs-Prompt verlangt deshalb
ausdruecklich „vollstaendige englische Saetze mit Satzzeichen" — gemessen 5/5 gegen 0/5 ohne.
Dabei zaehlte die Formulierung, nicht die zusaetzliche Regel: dieselbe Anweisung an den alten
Prompt *angehaengt* brachte nur 1/5. Wie schon bei Qwen3 schlaegt kurzer, klarer Fliesstext
die Regelsammlung.

Die urspruengliche Erklaerung dafuer war falsch und ist nachtraeglich widerlegt: Ich hatte
angenommen, Whisper liefere bei kurzen Diktaten keine Satzzeichen und Gemma spiegele nur die
Vorlage. Nachgemessen liefert Whisper sie sehr wohl — **7 von 7 Ausschnitten, auch zwei
Sekunden kurze, enden mit einem Satzzeichen und beginnen gross.** Genau darum kommt der
Gaming-Modus ohne LLM aus. Warum Gemma sie trotzdem verlor, ist offen; dafuer gibt es jetzt
den erweiterten Log.

**`_sounddevice_data` liegt als eigenstaendiges Paket neben `sounddevice`,** nicht darin.

**PowerShell 5.1 schreibt bei `-Encoding UTF8` eine BOM,** an der `json.load` scheitert.
`common/config.py` liest deshalb mit `utf-8-sig`; das Paketskript schreibt `config.json`
ueber `File::WriteAllText` ohne BOM.

**`config.ROOT`** wird aus `sys.frozen` abgeleitet und ist im portablen Paket der Ordner
neben dem Starter. Fuer Pfade immer `config.ROOT` nehmen, nie `sys.executable` — im
portablen Paket liegt der Interpreter im Unterordner `python\`.

## Messwerte (RX 7900 XTX)

Nicht erneut messen, ausser es aendert sich etwas Grundlegendes.

| | |
|---|---|
| Whisper-Inferenz, 11 s Audio | base 0,07 s · small 0,09 s · **medium 0,18 s** · large-v3-turbo 0,14 s |
| Inferenzdauer vs. Fensterlaenge | konstant — Whisper paddet intern auf 30 s |
| Modellwechsel ueber `/load` | 0,2–1,0 s |
| Qwen3 8B (Standardmodell bis 23.08.2026, unsloth/qwen3.5-4b bis 24.08.2026) | ~75 Tok/s bei vollem GPU-Offload; faellt auf ~5 Tok/s, wenn LM Studio Layer in den RAM auslagert |
| Gemma 4 E2B (Standardmodell seit 24.08.2026, 8192 Kontext, GPU max) | ~2,9 GB VRAM allein (nachgemessen per GPU-Adapter-Zaehler, Delta vor/nach `lms load`), Laden 3,0 s. Uebersetzt in 0,16 s je Satz; beim Bereinigen 0,46 s / 60 Tokens fuer einen realistischen Diktatsatz |
| Kontextlaenge 15524 → 8192 | 1,04 GB VRAM gespart bei unveraenderter Geschwindigkeit |
| **VRAM des Tools** | Gaming **1,95 GB** · Standard und Uebersetzen (gleiches Modell seit 24.08.2026) **~4,9 GB**. Grundlast des Systems ohne das Tool: 2,4 GB. Die fruehere Standard-Messung mit Qwen3 8B lag bei 7,68 GB |
| Modell laden ueber `lms` | Qwen3 8B (fruehres Modell) 3,2 s · Gemma 4 E2B 3,0 s |
| Deutscher Text | 3,73 Zeichen je Token |
| pynput | 3,63 ms/Zeichen tippen, 2,59 ms/Zeichen loeschen (bei 3/2 ms Config-Verzoegerung) |
| Nachlauf nach Loslassen | Standard 1,6 s (kurzes Diktat) · Gaming 0,4 s |
| Upstream im Betrieb | ~260 kbit/s (unkomprimiertes PCM), Downstream <10 kbit/s |
| whisper.cpp auf CPU (8 Threads) | base **0,70 s** · small 2,52 s · medium 8,17 s, je 11 s Audio. Ohne GPU traegt der Gaming-Modus mit base oder small |
| `audio_ctx` senken | nur 17–30 % Ersparnis, unter 375 kippt die Erkennung |
| **Wortfehlerrate deutsch**, acht eigene Saetze (`eval/`) | base 16,7 % · small 7,3 % · medium 5,3 % · large-v3-turbo 4,4 % · **large-v3-turbo-german 3,5 %**. Streng (mit Satzzeichen und Grossschreibung): 29,6 / 19,4 / 13,9 / 15,6 / **10,3 %** |
| Satzzeichen und Grossschreibung | **8/8 bei allen Modellen** — auch `base`. Das traegt den Gaming-Modus |
| Deutsche Turbo-Fassung gegen das Original | gleiche Groesse (1.549 MB), gleiche Inferenzzeit (0,20 s), kein Satz schlechter |
| **q5-Quantisierung** der deutschen Fassung | **547 statt 1.549 MB bei zeichengleicher Ausgabe in 8 von 8 Faellen.** Inferenz unveraendert 0,20 s, Laden 0,52 s statt 1,54 s |

## Tests

`tests\run_all.ps1` fuehrt die Regression aus. Die Suiten pruefen echtes Verhalten gegen
laufende Dienste, es gibt keine Mocks fuer whisper.cpp oder LM Studio.

* `test_client.py`, `test_capture.py` — Client-Logik ohne Server, schnell
* `test_tk_stress.py` — Absturz-Regression fuer die Tk-Threads
* `test_server.py` — Token-Abweisung, rollierendes Fenster, LLM-Kette
* `test_prompt.py` — Initial Prompt, Abschneide-Schutz
* `test_modell.py` — Modellwechsel samt Abwehr von Pfadangaben
* `test_profile.py` + `e2e_server.py`/`e2e_client.py` — Betriebsmodi, volle Kette
* `bench_*.py` — Messungen, kein Bestanden/Nicht-bestanden

Drei Eigenheiten: `test_server.py` behauptet etwas ueber Whisper-Ausgaben, die von Lauf
zu Lauf schwanken — die Pruefung „keine drastischen Textrueckspruenge" schlaegt
gelegentlich zu Unrecht an, ein zweiter Lauf klaert das. Tests, die `config.json`
aendern, sichern sie vorher und stellen sie im `finally` wieder her.

Und: **laeuft der Diktier-Server nebenher, haengen sich die Suiten stillschweigend an
dessen whisper-server.** Der eigene Start scheitert am belegten Port 8910, die
Bereitschaftspruefung findet die fremde Instanz und meldet „bereit" — gemessen wird dann
gegen deren Modell statt gegen das aus der Config. Fuer einen belastbaren Lauf den
Diktier-Server vorher beenden. `eval/vergleich.py` umgeht das mit einem eigenen freien
Port.

## Bildraten-Einbruch beim Spielen — Stand

Im Feld beobachtet (Diablo 4): **Mit deaktiviertem Raytracing ist das Ruckeln im
Gaming-Modus praktisch verschwunden.** Mit RT fehlt der GPU schlicht die Reserve fuer
die eine Inferenz.

Uebrig bleibt ein kurzer Einbruch **beim ersten Satz nach einer Pause**. Ursache ist
nicht, dass whisper-server das Modell entlaedt — das tut er nie —, sondern dass der
Treiber unter Speicherdruck eines Vollbildspiels die Speicherbereiche inaktiver
Hintergrundprozesse auslagert. Nach der Pause muss das Modell ueber PCIe zurueck.

Daraus folgt: fuer diesen Resteffekt zaehlt die **Modellgroesse**, nicht die Rechenzeit.
`base` ist mit 141 MB rund zehnmal weniger zurueckzuholen als `medium` mit 1463 MB.
Lokal nicht reproduzierbar — die Verdraengung tritt nur unter echtem Speicherdruck auf,
ein Leerlauftest von 20 s zeigte keinerlei Unterschied.

**Damit ist das Thema erledigt.** Der verbliebene Ruckler ist im Alltag vertretbar.

Und seit dem Modellvergleich gibt es dagegen einen Hebel ohne Gegenleistung:
**`large-v3-turbo-german-q5` ist mit 547 MB ein Drittel so gross wie die volle Fassung
und lieferte auf allen acht Testaufnahmen zeichengleichen Text** — es gibt also nichts
abzuwaegen, anders als frueher bei `base` oder `small`.

**Im Feld bestaetigt (18.08.2026, Diablo 4, q5 aktiv): das Nachladen war kaum noch zu
merken.** Damit ist der Resteffekt praktisch erledigt, ohne dass ein Warmhalter noetig
waere. Zu beachten: das Whisper-Modell ist global, nicht je Profil einstellbar; fuer
„q5 nur beim Spielen" muss man im Tray umschalten, bis `stt_model` je Profil nachgeruestet
ist (siehe Offene Punkte).

Ein Warmhalter (alle 30–60 s eine winzige
Inferenz ueber Stille, damit nichts ausgelagert wird) waere der naechste Hebel — bewusst
nicht gebaut, er wuerde dauerhaft kleine GPU-Blips einfuehren, um ein Problem zu loesen,
das keines mehr ist.

## Nemotron 3.5 ASR — geprueft und verworfen

Im August 2026 als Whisper-Ersatz bewertet. **Ergebnis: laeuft, wird aber nicht
uebernommen.** Ausschlaggebend war das Feintuning — es liefe ueber das
NeMo-Toolkit, das auf Linux und CUDA ausgerichtet ist. Auf dieser Hardware waere
der Weg praktisch verschlossen, waehrend Whisper eine ausgetretene
Werkzeugkette hat und whisper.cpp konvertierte Modelle direkt liest.

Die technische Machbarkeit steht damit trotzdem fest, das muss niemand erneut
herausfinden:

| | |
|---|---|
| PyTorch mit ROCm auf **Windows** | 2.9.1+rocm7.2.1, reine pip-Wheels von `repo.radeon.com`, **kein System-SDK** |
| RX 7900 XTX | wird erkannt, Rechenprobe auf der GPU laeuft |
| Nemotron 0.6B | laedt in ~9,5 s, 11 s Audio in **0,29 s**, 2,59 GB VRAM |

Drei Fallstricke, alle in `eval/nemotron.py` kommentiert:

* Die **transformers-Pipeline verlangt ffmpeg**, wenn man ihr einen Dateinamen
  gibt. Uebergibt man Samples als Array, entfaellt das — und es entspricht dem
  Betrieb, wo der Server ohnehin rohes PCM haelt.
* Die **Pipeline reicht die Sprache nicht durch.** `generate_kwargs={"language":
  "de"}` wird ignoriert, das Modell faellt auf automatische Erkennung zurueck.
  Die Sprachwahl steckt in den `prompt_ids`, die der **Processor** aus
  `language=` erzeugt — deshalb Processor und Modell direkt statt Pipeline.
* `generate()` liefert ein `NemotronAsrStreamingGenerateOutput`, nicht die
  Token-IDs. Dekodiert wird `.sequences`.

Die Modellklasse heisst `Nemotron3_5AsrForRNNT`.

Geblieben ist `eval/` mit dem Aufnahme- und Vergleichswerkzeug — siehe
`eval/LIESMICH.md`. Damit ist die Frage beantwortet, welches Whisper-Modell fuer
deutsches Diktat taugt: **`large-v3-turbo-german`**, siehe unten.

## Gemma-4 mit nativer Audio-Eingabe — verworfen ohne Test

Am 22.08.2026 als moeglicher Ersatz fuer die Zweistufigkeit im
`uebersetzen`-Modus erwogen: `llama.cpp` unterstuetzt seit PR #21421 einen
Audio-Encoder fuer Gemma-4-E2B/E4B, was Whisper+LLM auf einen einzigen
Aufruf (Audio rein, Uebersetzung raus) haette verkuerzen koennen. Entscheidung:
**verworfen, bevor gebaut wurde** — `large-v3-turbo-german-q5` liefert mit der
bestehenden Pipeline bereits eine schlanke, gemessene Loesung (547 MB, 3,5 %
lockere Wortfehlerrate, siehe oben), der Aufwand fuer einen unerprobten
zweiten Pfad (eigener `llama.cpp`-Build, ungeklaerter SIGABRT-Bug #24084,
ungeprüfte GGUF-Dateinamen) stand in keinem Verhaeltnis zum Nutzen. Der
urspruengliche Pruefplan lag als `plan-gemma4-audio-llamacpp.md` vor und wurde
entfernt.

## Whisper-Modellvergleich, acht eigene Saetze

**Vorgabe ist `large-v3-turbo-german`** (`cstr/whisper-large-v3-turbo-german-ggml`,
aus `primeline/whisper-large-v3-turbo-german` konvertiert). Gegen das Original: 3,5
statt 4,4 % locker, 10,3 statt 15,6 % streng, bei gleicher Dateigroesse und gleicher
Inferenzzeit. Kein Satz faellt schlechter aus.

Der Vorsprung liegt aber **nicht** im Verstehen — beide Modelle erkennen alle acht
Saetze inhaltlich richtig. Er liegt in der Schreibweise: `Kubernetes-Cluster` statt
`Kubernetes Cluster`, `um drei Uhr` statt `um 3 Uhr`. Das zaehlt im Gaming-Modus, wo
kein LLM nachbessert; im Standardmodus buegelt Qwen3 beides ohnehin aus. Die
Herstellerangabe von 5 % gegen 14 % liess sich hier weder bestaetigen noch widerlegen:
sie beschreibt Fehlerkennungen, und die hatte auf diesem Material keines der beiden
Modelle. Dafuer braeuchte es schwierigeres Material — Nebengeraeusche, schnelles
Sprechen, Dialekt.

Eine Abweichung faellt auf, taugt aber nicht zur Entscheidung: die deutsche Fassung
**behaelt „Ähm"**, das Original wirft es weg. Im Betrieb ist das gleichgueltig — im
Gaming-Modus stoert ein Fuellwort nicht, im Standardmodus raeumt Qwen3 es ohnehin weg.
Nur die Messung rechnet es an, weil die Referenz das Fuellwort enthaelt: wer es
wegwirft, bekommt dafuer Fehler angeschrieben (Satz 3, 15 % beim Original). Beim
Deuten der Zahlen also ausklammern.

`large-v3-turbo` hat auf dem Testmaterial ebenfalls **kein Wort falsch verstanden**; seine
restlichen 4,4 % sind das von Whisper gefilterte „ähm, also" und die Wortstellung bei
Uhrzeiten („vierzehn Uhr dreissig" gegen „14.30 Uhr"). `medium` liegt dicht dahinter und
ist streng gezaehlt sogar besser, weil `turbo` bei Bindestrichen schwankt
(`Kubernetes Cluster`, `Pull-Request`). `small` ist brauchbar, `base` faellt durch
(„Kubernetes-Cluster" → „Kuba nett, ist klasterlaeuftset").

Zwei Dinge, ohne die die Messung nichts wert ist — beide haben zusammen rund
14 Prozentpunkte vorgetaeuscht:

* **Zahlwoerter umrechnen.** Whisper schreibt „17." und „24 GB", die vorgelesene Referenz
  steht in Worten da. `eval/wer.py` rechnet das fuer die lockere Zaehlung um; die strenge
  laesst es stehen, sie misst ja, was im Fenster landet.
* **Die Referenz muss das Gesprochene abbilden,** nicht die Vorlage. Ein verlesenes Wort
  („vierundzwanzig" statt „vierhundertzwanzig") sieht in der Auswertung aus wie ein
  Modellfehler, den alle vier Modelle gleichzeitig machen — das ist das Erkennungszeichen.

## Offene Punkte

* **Zwei Entscheidungen zum deutschen Modell sind bewusst vertagt,** bis es sich im
  Alltag bewaehrt hat — acht Testsaetze sind eine schmale Grundlage, und beide Schritte
  waeren schwer rueckgaengig zu machen, wenn sich die Quantisierung bei schwierigerem
  Audio doch raecht:

  * **q5 als Vorgabe** statt der vollen Fassung. Gemessen zeichengleich, ein Drittel so
    gross, schneller geladen. Vorgabe bleibt vorerst `large-v3-turbo-german`.
  * **`stt_model` je Profil**, damit der Gaming-Modus q5 nimmt und der Standardmodus die
    volle Fassung. Die Profillogik ueberschreibt heute schon `llm_model` und
    `partial_interval_ms`; ein Modellwechsel beim Sessionstart ginge ueber dasselbe
    `/load`, das der Tray-Umschalter nutzt. Bis dahin schaltet man von Hand.

  Beim Sammeln von Praxiserfahrung hilft der erweiterte Log (Tray-Haekchen): nur damit
  ist im Nachhinein zu sehen, ob Whisper danebenlag oder das LLM.

* Warum Gemma im Uebersetzungsmodus die Satzzeichen verlor, ist weiterhin offen. Der
  Prompt faengt es ab, die Ursache kennt niemand. Der erweiterte Log wuerde es beim
  naechsten Auftreten zeigen
* Internetbetrieb ist zurueckgestellt. Vorarbeit dafuer waere Opus statt rohem PCM
  (Faktor 10 weniger Upstream) und das Verhalten bei vollem Sendepuffer: derzeit staut
  der Client bis 60 s Audio und verwirft danach, statt zu bremsen
* Beim VPN: FritzBox kann nur IPSec/IKEv1, Windows-Bordmittel nur IKEv2 — keine
  Schnittmenge. Bliebe WireGuard im Userspace (Go-Hilfsprogramm) oder ein IKEv2-Endpunkt
  ausserhalb der FritzBox, dann ginge es mit `Add-VpnConnection` ohne Adminrechte
