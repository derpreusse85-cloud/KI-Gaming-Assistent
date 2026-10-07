# Gaming-Sprachassistent

Frei gesprochene Sprache waehrend des Spielens wird per lokalem LLM einer festen Aktion
zugeordnet und als Tastenkombination ausgeloest — z. B. "Ruf die 500-Kilo-Bombe" loest in
Helldivers 2 automatisch den passenden Stratagem-Code aus. Kein Modding des Spiels noetig,
keine festen Kommandophrasen wie bei klassischen Voice-Command-Tools.

Das vollstaendige Konzept samt aller Design-Entscheidungen und der Testreihe steht in
`Gaming_assistent.md`; der aktuelle Entwicklungsstand in `CLAUDE.md`; die Versionshistorie in
`CHANGELOG.md`. Dieses README ist die kurze Gebrauchsanleitung fuer den taeglichen Betrieb.

> Kleiner Disclaimer: Ich bin kein Entwickler, sondern einfach nur ein Typ, der eine Idee hatte
> und schauen wollte, ob sie funktioniert. Da ich kaum Programmierkenntnisse habe, wurde der
> komplette Code mit KI geschrieben. Ich kann verstehen, wenn manchen das missfaellt, allerdings
> bitte ich darum, sachlich zu bleiben, da trotz KI-generierten Codes jede Menge Hirnschmalz
> reingeflossen ist.

Das Tool ist in erster Linie als Komfort-Werkzeug gedacht, nicht speziell fuer den kompetitiven
Bereich optimiert. Ob es sich trotzdem dafuer eignet, muss jeder fuer sich selbst entscheiden.

**Code und System-Prompt sind auf Gemma 4 ausgelegt** (Standard: **E4B**, optional das kleinere,
schnellere **E2B**, siehe unten), nicht auf ein LLM im Allgemeinen. Das betrifft u. a. das `--reasoning off`-Flag beim Start von `llama-server`
(schaltet den bei diesem Modell/Chat-Template automatisch aktiven Denkmodus ab, siehe
`CLAUDE.md`, Abschnitt "LM Studio abgeloest"), `temperature: 0.0` fuer deterministische
Klassifikation sowie der Aufbau und Wortlaut des System-Prompts selbst (`prompt.py`), der gegen
genau dieses Modell getestet wurde. Ein anderes Modell einzusetzen ist nicht als reiner
Config-Tausch gedacht (gemeint sind Modelle ausserhalb der Gemma-4-Familie) - es muesste erst gegen die eigene Testreihe (siehe
`Gaming_assistent.md`, Abschnitt "Testreihe") neu verifiziert werden, ob Denkmodus,
Instruction-Following bei Mehrfachbefehlen und Formattreue beim `&&TAG&&`-Marker weiterhin
zuverlaessig funktionieren.

**Zwei Modelle zur Wahl (E4B oder E2B).** E4B ist der Standard und die sicherere Wahl, besonders
bei Mehrfachbefehlen mit Wiederholungen und Wartezeiten sowie bei vielen aehnlich klingenden
Kommandos. E2B ist kleiner (ca. 3 statt 5 GB) und etwa 1,6-mal so schnell bei der
Klassifikation. In einer Testreihe (`tests/eskalationstest.py`, 175 Faelle ueber vier Profile,
nur Textklassifikation ohne Spracherkennung) erreichten beide am Ende dasselbe Ergebnis
(172/175 bis 173/175), E2B bei einem Teil der Faelle erst nach einer Verfeinerung des
System-Prompts. Im echten Betrieb haben der Wechsel im Tray und eine Handvoll Sprachbefehle mit E2B funktioniert,
ausgiebig getestet ist E2B im echten Spiel aber noch nicht. Umschalten geht
jederzeit im Tray-Menue unter **Sprachmodell** (siehe "Bedienung").

## Einrichtung (einmalig nach dem Klonen)

**Kein separates LLM-Programm noetig** — der Assistent startet ein eigenes llama.cpp
(`llama-server.exe`, Vulkan) und whisper.cpp (`whisper-server.exe`) als Hintergrundprozesse
automatisch mit. Beide liegen als fertige Binaries direkt im Repo (`vendor/`) - dafuer muss
nichts heruntergeladen oder kompiliert werden.

Was fehlt, sind nur die beiden grossen Modelldateien (zu gross fuers Repo) und die
Python-Umgebung - dafuer einmalig ausfuehren:

```powershell
.\setup.ps1
```

Das ruft nacheinander `setup_venv.ps1` (Python-venv + Abhaengigkeiten), `download_llm.ps1`
(Gemma-4-E4B-Modell, ca. 5 GB; das kleinere E2B optional zusaetzlich, siehe unten) und `fetch_models.ps1` (Whisper-Modell, ca. 0,5 GB) auf. Jedes
der drei Skripte laesst sich bei Bedarf auch einzeln erneut ausfuehren (z.B. um nur ein Modell
neu herunterzuladen).

**Optional: das kleinere Modell E2B** (ca. 3 GB) zusaetzlich herunterladen, um es im Tray-Menue
auswaehlen zu koennen:

```powershell
.\scripts\download_llm.ps1 -Modell E2B      # nur E2B
.\scripts\download_llm.ps1 -Modell Beide    # E4B und E2B
```

Ohne Parameter laedt das Skript wie bisher nur E4B. Die Download-Skripte sind
PowerShell-Skripte; erlaubt die Windows-Ausfuehrungsrichtlinie sie nicht, hilft z. B.
`powershell -ExecutionPolicy Bypass -File .\scripts\download_llm.ps1 -Modell E2B`.

**Nur im Ausnahmefall noetig** (Reparatur, falls `vendor/` beschaedigt ist, oder eine andere
Plattform/Architektur gebraucht wird): `scripts\fetch_llama.ps1` laedt `llama-server.exe` neu,
`scripts\build_whisper.ps1` kompiliert `whisper-server.exe` selbst (braucht dafuer Git, CMake,
VS Build Tools, Vulkan SDK).

Ein Mikrofon wird ausserdem gebraucht. Der Assistent nutzt immer das in Windows als
Standardaufnahmegeraet eingestellte Mikrofon (keine eigene Geraeteauswahl im Tool) - bei mehreren
angeschlossenen Mikrofonen also vorher unter Windows-Einstellungen -> System -> Sound ->
Eingabe festlegen, welches genutzt werden soll.

### Mindestanforderungen

* **Windows 10/11 (64-Bit)** — `pynput`/`pystray`/`whisper-server.exe`/`llama-server.exe` sind
  Windows-spezifisch, keine plattformuebergreifende Unterstuetzung vorgesehen.
* **Python 3** installiert (https://www.python.org/downloads/) — wird fuer `setup.ps1`/
  `setup_venv.ps1` gebraucht, um die eigene `.venv` anzulegen. Ist noch kein Python installiert,
  bricht `setup_venv.ps1` mit genau diesem Link und dem Hinweis ab, das Skript danach einfach
  erneut auszufuehren.
* **GPU mit Vulkan-Unterstuetzung**, mindestens **8 GB VRAM insgesamt**. Gemessen auf diesem
  Rechner (12.09.2026): Whisper-Modell ~0,92 GB, llama-server (Gemma 4 E4B, Q4_K_M, Kontext 8192,
  ein Slot) ~3,34 GB — zusammen ~4,26 GB fuers Tool allein (E2B nicht gemessen, braucht aber
  naturgemaess weniger), der Rest ist Platz fuers Spiel selbst
  (Helldivers 2 & Co. brauchen ebenfalls mehrere GB VRAM). Ohne GPU laeuft Whisper
  zwar auch auf der CPU, ist dann aber laut einer frueheren Messreihe fuer
  Push-to-Talk-Latenz zu langsam (z. B. `medium` 8,17 s statt <0,2 s je Aeusserung) — GPU ist
  hier praktisch Pflicht, nicht nur "nice to have".
* **16 GB RAM.**

### Empfohlene Anforderungen

* **Dedizierte GPU mit 16 GB VRAM** (getestet mit einer RX 7900 XTX, 24 GB) — mehr Reserve
  bedeutet, dass der llama.cpp-Prozess waehrend des Spielens seltener aus dem VRAM verdraengt
  wird (siehe `CLAUDE.md`, Abschnitt "Latenz gemessen" zu den Folgen einer Verdraengung).
* **32 GB RAM.**
* **SSD** fuer schnelleres Laden von Whisper-Modell und LLM.

## Starten

Doppelklick auf **`Gaming-Assistent.vbs`** — startet lautlos im Hintergrund, bedienbar ueber
das Icon im System-Tray.

**Fuer eine Desktop-Verknuepfung** (VBS-Dateien haben sonst ein generisches, wenig ansprechendes
Standard-Icon): Verknuepfung von `Gaming-Assistent.vbs` erstellen, dann per Rechtsklick ->
Eigenschaften -> "Anderes Symbol ..." die mitgelieferte `Gaming-Assistent.ico` auswaehlen (selbes
Gamepad-Motiv wie das Tray-Icon).

Alternativ mit sichtbarer Konsole (z. B. zum Mitlesen des Logs):

```powershell
.venv\Scripts\python.exe -m gaming_assistant
```

## Bedienung

Push-to-Talk-Taste halten, Befehl sprechen, loslassen. Erkennt das LLM eindeutig eines der im
aktiven Profil hinterlegten Kommandos, wird die zugehoerige Tastenfolge sofort ausgeloest.
Unbekannte oder mehrdeutige Aeusserungen loesen bewusst nichts aus (kein Rateversuch).

**Latenz** (gemessen mit der empfohlenen Hardware, siehe oben, 13.09.2026 gegen die aktuelle
llama-server-basierte Pipeline neu verifiziert): ein normaler Befehl braucht End-zu-Ende
(Spracherkennung + Klassifikation) **~0,24s** (Spracherkennung ~0,18s, Klassifikation ~0,065s
dank Prompt-Caching). Nur der allererste Befehl nach Programmstart oder einem Profilwechsel
dauert laenger (**~1,45s**, einmaliges Verarbeiten des langen System-Prompts) - danach bleibt es
durchgehend schnell. Mit dem kleineren Modell E2B ist die Klassifikation nochmal schneller
(in der Testreihe Median ~0,08s statt ~0,12s pro Anfrage, inkl. HTTP-Overhead, Cold-Start
~0,7s statt ~1,1-1,4s). **Alle diese Messungen wurden ohne nebenbei laufendes Spiel gemacht.** Bei laufendem
Spiel kann die Latenz je nach Leistungsbedarf der GPU des jeweiligen Spiels unterschiedlich
ausfallen, deshalb sind dort keine zuverlaessigen Testmessungen moeglich. Auf anderer Hardware
koennen die Werte ebenfalls abweichen - mit
`tests/latenz_messen.py` (siehe unten) laesst sich das auf dem eigenen Rechner nachmessen.

**Tray-Menue:**

* **Status/Log anzeigen** — Fenster mit den letzten Logzeilen, inkl. der Latenz je Befehl
  (`Latenz: STT ...s, LLM ...s, ...`).
* **Profil** — aktives Spielprofil wechseln (Liste aller YAML-Dateien in `profiles/`).
* **Sprachmodell** — zwischen den gefundenen Modellen wechseln (E4B/E2B, jede `.gguf`-Datei in
  einem Ordner `*-GGUF/` im Projektordner erscheint hier automatisch; die `mmproj`-Dateien
  zaehlen nicht). Beim Wechsel wird `llama-server` automatisch mit dem neuen Modell neu
  gestartet (dauert wenige Sekunden, das Tray-Icon zeigt solange "startet"); ein Befehl,
  der genau in dieser Zeit gesprochen wird, geht verloren. Schlaegt der Start fehl (Datei
  fehlt/defekt), bleibt das bisherige Modell aktiv. Waehrend einer laufenden Aufnahme
  ist der Wechsel gesperrt.
* **Push-to-talk festlegen ...** — neuen PTT-Ausloeser (Tastatur, Maustaste 4/5/Mitte oder ein
  Knopf an einem angeschlossenen Controller/HOTAS) durch einmaliges Druecken festlegen.
* **Trainingsdaten aufzeichnen** — an-/abschaltbarer Haken, siehe Abschnitt "Trainingsdaten"
  unten.
* **Debug-Log aktiv** — an-/abschaltbarer Haken, schaltet ausfuehrlichere Log-Ausgaben ein
  (u. a. jeder einzelne Tastendruck, Details zur Feuergruppen-Berechnung bei Elite Dangerous) -
  wirkt sofort, ohne Neustart, sichtbar unter "Status/Log anzeigen".
* **Beenden**

Die Einstellungen (aktives Profil, Sprachmodell, PTT-Taste, Trainingsdaten-Aufzeichnung) werden automatisch in
`config.json` gespeichert und beim naechsten Start wiederhergestellt.

## Ein neues Spielprofil anlegen

Eine YAML-Datei in `profiles/` (Dateiname ohne `.yaml` = Profilname im Tray-Menue). Beispiel
anhand eines einzelnen Tags:

```yaml
kontextlaenge: 4096          # Kontextlaenge fuers LLM, siehe unten

LANDEGESTELL:
  schlagwort: ["Landegestell", "Fahrgestell"]  # eines davon muss im Befehl woertlich vorkommen
  beispiel: "Fahrgestell einfahren"            # Few-Shot-Beispiel fuer das LLM
  taste: ["shift", "n"]                        # wird als Tipp-Sequenz ausgefuehrt (nacheinander, nicht gleichzeitig)

ORBITALSCHLAG:
  beschreibung: "nur wenn ein Orbitalschlag angefordert wird"  # frei formuliert statt Wortbindung
  beispiel: "Ruf den Orbitalschlag"
  taste: ["ctrl", "o"]

STRATAGEM_BEISPIEL:
  beschreibung: "nur wenn dieses Beispiel-Stratagem angefordert wird"
  beispiel: "Ruf das Beispiel-Stratagem"
  taste: ["ctrl_down", "down", "left", "ctrl_up"]  # Strg bleibt waehrend down+left gehalten
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
* **`taste`**: Liste einzelner Tasten, die **nacheinander** getippt werden. Sondertasten wie
  `ctrl`, `shift`, `alt`, `tab`, `up`/`down`/`left`/`right` sind moeglich, sonst einzelne Zeichen.
  Soll eine Taste ueber mehrere Schritte hinweg zusaetzlich GEHALTEN werden (z. B. Strg bei
  Helldivers-2-Stratagem-Codes), steht das direkt in der Liste: ein Eintrag `"<taste>_down"`
  drueckt und haelt sie, `"<taste>_up"` laesst sie wieder los — Vorbild ist AutoHotkeys eigene
  `{Ctrl down}`/`{Ctrl up}`-Schreibweise. Beispiel: `["ctrl_down", "down", "left", "ctrl_up"]`
  haelt Strg, waehrend `down`+`left` getippt werden. Lassen sich beliebig mischen und sogar
  mehrere Tasten gleichzeitig halten (`["ctrl_down", "shift_down", "x", "shift_up", "ctrl_up"]`).
* **`kontextlaenge`**: einmalig ermitteln (Prompt-Tokens des generierten System-Prompts plus
  Marge) und hier eintragen — wird beim Laden des Profils an den llama-server-Subprozess
  durchgereicht. Weicht sie vom bisher aktiven Profil ab, startet llama-server automatisch mit
  der neuen Kontextlaenge neu (kurze Pause beim Profilwechsel spuerbar, sonst kein Neustart noetig).
* **`initial_prompt_schlagwoerter`** (optional): kuratierte Liste einzelner Fremdwoerter/
  Akronyme/Eigennamen fuers Whisper-Vokabular. Bei echter Sprache ohne messbaren Latenz-Effekt
  (siehe `CLAUDE.md`), aber unschaedlich; kann auch ganz weggelassen werden.
* **`status_datei`** + **`feuergruppe_ziel`** (optional, bisher nur im Elite-Dangerous-Profil
  genutzt): fuer Spielaktionen, die nur ueber eine Zyklus-Taste ohne Direktwahl erreichbar sind
  (z. B. Elite Dangerous' Feuergruppen-Wechsel). Statt einer festen `taste`-Liste bekommt so ein
  Tag ein `feuergruppe_ziel` (Ziel-Index); die tatsaechliche Tastenfolge wird dann bei jedem
  Aufruf frisch aus dem echten Spielzustand berechnet, den das Spiel selbst laufend in eine Datei
  schreibt (`status_datei` zeigt auf diese Datei — bei Elite Dangerous die `Status.json` im
  eigenen "Saved Games"-Ordner, Pfad je nach Windows-Benutzername unterschiedlich, deshalb pro
  Profil einzutragen). **Einzige Ausnahme im gesamten Projekt, die auf eine Datei ausserhalb des
  Programmordners zugreift** — nur lesend, nie schreibend. Die dabei tatsaechlich gedrueckten
  Tasten (Vorgabe "n"/"b") lassen sich zusaetzlich per `feuergruppe_vorwaerts_taste`/
  `feuergruppe_rueckwaerts_taste` ueberschreiben, falls sie mit einer anderen Belegung
  kollidieren. **Wichtige Einschraenkung:** die Berechnung geht von genau 8 eingerichteten
  Feuergruppen aus - sind im Schiff weniger als 8 tatsaechlich eingerichtet, zykelt Elite
  Dangerous selbst nur durch die vorhandenen Gruppen, wodurch die berechnete Tastenfolge falsch
  wird (landet auf der falschen Gruppe). Im Schiff deshalb immer alle 8 Feuergruppen einrichten,
  auch wenn nicht alle genutzt werden. Details: `Gaming_assistent.md`, Abschnitt
  "Aktionslisten-Format".

Details und Hintergrund zu jedem Feld: `Gaming_assistent.md`, Abschnitt "Aktionslisten-Format".

### Komplexere Aktionen per AutoHotkey

`taste` deckt einfache Tastensequenzen ab, ist aber bewusst kein eigenes Skript-Format (keine
Schleifen, Bedingungen, Mausteuerung, Pausen pro Schritt). Wer mehr braucht, muss dafuer nichts an
diesem Tool aendern: [AutoHotkey](https://www.autohotkey.com/) ist eine kostenlose Windows-
Automatisierungssprache, die selbst Tastatureingaben ueberwacht (Hotkeys) — bindet man ein
AHK-Skript an eine sonst ungenutzte Taste (z. B. `f13`) und traegt genau diese Taste als `taste`
in einen Tag ein, loest dieses Tool das Skript per Sprachbefehl aus, als waere die Taste echt
gedrueckt worden. Keine Code-Integration noetig — dieses Tool und AHK laufen komplett unabhaengig
voneinander, nur ueber die simulierte Taste verbunden. Damit lassen sich die beiden Staerken
kombinieren: freie gesprochene Sprache (kann AHK nicht) mit beliebig komplexer Automatisierung
(baut dieses Tool bewusst nicht nach).

## Ein bestehendes Profil um Kommandos erweitern

Kommen z. B. bei Helldivers 2 neue Stratageme dazu, reicht es, einen weiteren Tag-Block im
selben Format wie die vorhandenen an die Profil-YAML anzuhaengen (siehe oben) - kein Code muss
angefasst werden. Zwei Dinge trotzdem im Blick behalten:

* **Namenskollisionen pruefen.** Ein neues Kommando mit aehnlichem Namen/Wortstamm wie ein
  bestehender Tag kann die Klassifikation durcheinanderbringen (siehe die dokumentierten
  Konfliktcluster am Anfang von `Helldivers2.yaml`). Am besten kurz mit ein paar
  Testformulierungen gegen den echten llama-server pruefen, bevor die Aenderung endgueltig ist:
  * `tests/profil_interaktiv_testen.py` — interaktives Werkzeug fuer **jedes** Profil (auch neu
    angelegte): Profil auswaehlen, beliebige Saetze eintippen, sofort sehen, welcher Tag/welche
    Taste dabei rauskaeme - reiner Trockentest, es wird nichts wirklich gedrueckt. Aufruf:
    `.venv\Scripts\python.exe tests\profil_interaktiv_testen.py [Profilname]`.
  * `tests/test_profil_klassifikation.py` — automatischer Regressionstest fuer **jedes** Profil:
    testet jeden Tag mit seinem eigenen `beispiel`-Feld (muss zu sich selbst klassifizieren),
    plus optionale handverlesene Zusatzfaelle je Profil. Aufruf ohne Argument testet alle
    Profile, mit Profilnamen als Argument nur die genannten:
    `.venv\Scripts\python.exe tests\test_profil_klassifikation.py [Profilname ...]`.
  * `tests/latenz_messen.py` — misst die Latenz (Spracherkennung + Klassifikation) auf der
    eigenen Hardware nach, da die in diesem README genannten Werte auf einem bestimmten
    Testrechner gemessen wurden und auf anderer Hardware abweichen koennen. Erzeugt sich sein
    Testaudio selbst per Windows-Sprachsynthese (keine Aufnahme noetig) und misst gegen das
    aktuell aktive Profil, am besten ohne nebenbei laufendes Spiel (siehe oben). Aufruf: `.venv\Scripts\python.exe tests\latenz_messen.py`.

  * `tests/eskalationstest.py` — Klassifikation mit stufenweise schwerer werdenden Aufgaben (von
    wenigen Grundtags ueber Namens-Konfliktcluster und Whisper-Verhoerer bis zu Mehrfachbefehlen mit
    Wiederholungen und Wartezeiten, dazu frische Faelle zur Kontrolle gegen Ueberanpassung des
    Prompts). Nimmt beliebig viele Modelldateien als Argument und zeigt das Ergebnis je Stufe -
    gedacht zum Vergleichen von Modellen und zum Pruefen von Prompt-Aenderungen:
    `.venv\Scripts\python.exe tests\eskalationstest.py [Modell.gguf ...]`.
  * `tests/modell_vergleich.py` — fuehrt dieselben Faelle wie der Regressionstest fuer mehrere
    Modelle nacheinander aus und vergleicht Trefferquote und Latenz:
    `.venv\Scripts\python.exe tests\modell_vergleich.py Modell1.gguf Modell2.gguf`.

  Alle fuenf brauchen einen laufenden llama-server (wird vom jeweiligen Skript selbst gestartet),
  aber kein Mikrofon.
* **`kontextlaenge` im Auge behalten.** Jeder zusaetzliche Tag macht den generierten
  System-Prompt etwas laenger. Bei einzelnen neuen Kommandos passt das meist locker in die
  vorhandene Marge, bei vielen auf einmal ggf. neu messen und `kontextlaenge` anpassen - sonst
  wird der Prompt beim Laden abgeschnitten.

Die YAML wird nicht waehrend des laufenden Betriebs neu eingelesen - nach dem Speichern das
Programm neu starten oder im Tray-Menue das Profil einmal neu auswaehlen, damit der
System-Prompt neu gebaut wird (und `llama-server` bei geaenderter `kontextlaenge` automatisch
neu startet).

## Trainingsdaten

Jeder Sprachbefehl wird ungefiltert nach `training_data/raw/<Datum>.jsonl` protokolliert (Rohtext
+ erkannte Tags) — Grundlage fuer eine spaetere Fine-Tuning-Aufbereitung, siehe
`Gaming_assistent.md`, Abschnitt "Trainingsdaten-Sammlung". Ueber den Haken **"Trainingsdaten
aufzeichnen"** im Tray-Menue laesst sich das jederzeit komplett abschalten (Standard: an) - dann
wird gar nichts mehr mitgeschrieben.

## Lizenz und Drittanbieter-Komponenten

Der eigene Code dieses Projekts steht unter der **GPL-3.0** (siehe `LICENSE`).
Copyright (C) 2026 DerPreusse.

Im Repo mitgelieferte Drittanbieter-Binaries stehen unter ihrer jeweils eigenen Lizenz, davon
unberuehrt (MIT ist mit GPL-3.0 vereinbar, es handelt sich um separate Werke):

* **`vendor/llama.cpp/`** — vorgefertigte Binaries aus dem offiziellen
  [llama.cpp](https://github.com/ggml-org/llama.cpp)-Release (MIT-Lizenz).
* **`vendor/whisper.cpp/`** — vorgefertigte Binaries aus dem offiziellen
  [whisper.cpp](https://github.com/ggml-org/whisper.cpp)-Projekt (MIT-Lizenz).

Nicht im Repo enthalten, aber per Skript nachgeladen: das **Gemma-4-E4B**-Modell
(`gemma-4-E4B-it-GGUF/`, Quelle `unsloth/gemma-4-E4B-it-GGUF` auf Hugging Face) sowie das optionale
**Gemma-4-E2B**-Modell (`gemma-4-E2B-it-GGUF/`, Quelle `unsloth/gemma-4-E2B-it-GGUF`) stehen unter der
**Apache-2.0**-Lizenz, das Whisper-Modell (`models/`) unter der Lizenz des jeweiligen
whisper.cpp-Modell-Downloads.
