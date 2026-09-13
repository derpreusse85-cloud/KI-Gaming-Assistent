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

**Code und System-Prompt sind aktuell fest auf Gemma 4 E4B ausgelegt**, nicht auf ein LLM
im Allgemeinen. Das betrifft u. a. das `--reasoning off`-Flag beim Start von `llama-server`
(schaltet den bei diesem Modell/Chat-Template automatisch aktiven Denkmodus ab, siehe
`CLAUDE.md`, Abschnitt "LM Studio abgeloest"), `temperature: 0.0` fuer deterministische
Klassifikation sowie der Aufbau und Wortlaut des System-Prompts selbst (`prompt.py`), der gegen
genau dieses Modell getestet wurde. Ein anderes Modell einzusetzen ist nicht als reiner
Config-Tausch gedacht - es muesste erst gegen die eigene Testreihe (siehe
`Gaming_assistent.md`, Abschnitt "Testreihe") neu verifiziert werden, ob Denkmodus,
Instruction-Following bei Mehrfachbefehlen und Formattreue beim `&&TAG&&`-Marker weiterhin
zuverlaessig funktionieren.

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
(Gemma-4-E4B-Modell, ca. 5 GB) und `fetch_models.ps1` (Whisper-Modell, ca. 0,5 GB) auf. Jedes
der drei Skripte laesst sich bei Bedarf auch einzeln erneut ausfuehren (z.B. um nur ein Modell
neu herunterzuladen).

**Nur im Ausnahmefall noetig** (Reparatur, falls `vendor/` beschaedigt ist, oder eine andere
Plattform/Architektur gebraucht wird): `scripts\fetch_llama.ps1` laedt `llama-server.exe` neu,
`scripts\build_whisper.ps1` kompiliert `whisper-server.exe` selbst (braucht dafuer Git, CMake,
VS Build Tools, Vulkan SDK).

Ein Mikrofon wird ausserdem gebraucht.

### Mindestanforderungen

* **Windows 10/11 (64-Bit)** — `pynput`/`pystray`/`whisper-server.exe`/`llama-server.exe` sind
  Windows-spezifisch, keine plattformuebergreifende Unterstuetzung vorgesehen.
* **GPU mit Vulkan-Unterstuetzung**, mindestens **8 GB VRAM insgesamt**. Gemessen auf diesem
  Rechner (12.09.2026): Whisper-Modell ~0,92 GB, llama-server (Gemma 4 E4B, Q4_K_M, Kontext 8192,
  ein Slot) ~3,34 GB — zusammen ~4,26 GB fuers Tool allein, der Rest ist Platz fuers Spiel selbst
  (Helldivers 2 & Co. brauchen ebenfalls mehrere GB VRAM). Ohne GPU laeuft Whisper
  zwar auch auf der CPU, ist dann aber laut einer frueheren Messreihe fuer
  Push-to-Talk-Latenz zu langsam (z. B. `medium` 8,17 s statt <0,2 s je Aeusserung) — GPU ist
  hier praktisch Pflicht, nicht nur "nice to have".
* **16 GB RAM.**

### Empfohlene Anforderungen

* **Dedizierte GPU mit 16 GB+ VRAM** (getestet mit einer RX 7900 XTX, 24 GB) — mehr Reserve
  bedeutet, dass der llama.cpp-Prozess waehrend des Spielens seltener aus dem VRAM verdraengt
  wird (siehe `CLAUDE.md`, Abschnitt "Latenz gemessen" zu den Folgen einer Verdraengung).
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

**Latenz** (gemessen mit der empfohlenen Hardware, siehe oben, 13.09.2026 gegen die aktuelle
llama-server-basierte Pipeline neu verifiziert): ein normaler Befehl braucht End-zu-Ende
(Spracherkennung + Klassifikation) **~0,24s** (Spracherkennung ~0,18s, Klassifikation ~0,065s
dank Prompt-Caching). Nur der allererste Befehl nach Programmstart oder einem Profilwechsel
dauert laenger (**~1,45s**, einmaliges Verarbeiten des langen System-Prompts) - danach bleibt es
durchgehend schnell.

**Tray-Menue:**

* **Status/Log anzeigen** — Fenster mit den letzten Logzeilen, inkl. der Latenz je Befehl
  (`Latenz: STT ...s, LLM ...s, ...`).
* **Profil** — aktives Spielprofil wechseln (Liste aller YAML-Dateien in `profiles/`).
* **Push-to-talk festlegen ...** — neue PTT-Taste (Tastatur oder Maustaste 4/5/Mitte) durch
  einmaliges Druecken festlegen.
* **Trainingsdaten aufzeichnen** — an-/abschaltbarer Haken, siehe Abschnitt "Trainingsdaten"
  unten.
* **Debug-Log aktiv** — an-/abschaltbarer Haken, schaltet ausfuehrlichere Log-Ausgaben ein
  (u. a. jeder einzelne Tastendruck, Details zur Feuergruppen-Berechnung bei Elite Dangerous) -
  wirkt sofort, ohne Neustart, sichtbar unter "Status/Log anzeigen".
* **Beenden**

Die Einstellungen (aktives Profil, PTT-Taste, Trainingsdaten-Aufzeichnung) werden automatisch in
`config.json` gespeichert und beim naechsten Start wiederhergestellt.

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
  Programmordners zugreift** — nur lesend, nie schreibend. Details: `Gaming_assistent.md`,
  Abschnitt "Aktionslisten-Format".

Details und Hintergrund zu jedem Feld: `Gaming_assistent.md`, Abschnitt "Aktionslisten-Format".

## Ein bestehendes Profil um Kommandos erweitern

Kommen z. B. bei Helldivers 2 neue Stratageme dazu, reicht es, einen weiteren Tag-Block im
selben Format wie die vorhandenen an die Profil-YAML anzuhaengen (siehe oben) - kein Code muss
angefasst werden. Zwei Dinge trotzdem im Blick behalten:

* **Namenskollisionen pruefen.** Ein neues Kommando mit aehnlichem Namen/Wortstamm wie ein
  bestehender Tag kann die Klassifikation durcheinanderbringen (siehe die dokumentierten
  Konfliktcluster am Anfang von `Helldivers2.yaml`). Am besten kurz mit ein paar
  Testformulierungen gegen den echten llama-server pruefen, bevor die Aenderung endgueltig ist.
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

Im Repo mitgelieferte Drittanbieter-Binaries stehen unter ihrer jeweils eigenen Lizenz, davon
unberuehrt (MIT ist mit GPL-3.0 vereinbar, es handelt sich um separate Werke):

* **`vendor/llama.cpp/`** — vorgefertigte Binaries aus dem offiziellen
  [llama.cpp](https://github.com/ggml-org/llama.cpp)-Release (MIT-Lizenz).
* **`vendor/whisper.cpp/`** — vorgefertigte Binaries aus dem offiziellen
  [whisper.cpp](https://github.com/ggml-org/whisper.cpp)-Projekt (MIT-Lizenz).

Nicht im Repo enthalten, aber per Skript nachgeladen: das **Gemma-4-E4B**-Modell
(`gemma-4-E4B-it-GGUF/`, Quelle `unsloth/gemma-4-E4B-it-GGUF` auf Hugging Face) steht unter der
**Apache-2.0**-Lizenz, das Whisper-Modell (`models/`) unter der Lizenz des jeweiligen
whisper.cpp-Modell-Downloads.
