"""Ungefiltertes Live-Logging fuer die spaetere Trainingsdaten-Aufbereitung.

Siehe Gaming_assistent.md, Abschnitt "Trainingsdaten-Sammlung fuer kuenftiges
Fine-Tuning": waehrend des Spielens wird jede Erkennung roh mitgeschrieben
(Whisper-Rohtext + erkannte Tags), ohne Filterung. Die zweistufige
Offline-Aufbereitung (Plausibilitaetspruefung/Korrektur durch ein groesseres
Modell) ist bewusst NICHT Teil dieses Moduls - das waere ein spaeterer,
eigenstaendiger Schritt.

Python-Hinweis: JSONL ("JSON Lines") heisst, dass jede Zeile der Datei fuer
sich ein eigenstaendiges JSON-Objekt ist. Das laesst sich einfach zeilenweise
anhaengen (append), ohne die ganze Datei neu einlesen und schreiben zu muessen
- praktisch fuer einen Log, der ueber Tage/Wochen waechst.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path

# Ein Lock, damit zwei Sprachbefehle kurz hintereinander sich beim Schreiben
# nicht gegenseitig die Zeilen vermischen (die Verarbeitung laeuft in einem
# Worker-Thread, siehe __main__.py).
_lock = threading.Lock()


def eintrag_anhaengen(verzeichnis: Path, profil: str, roh_text: str, tags: list[str]) -> None:
    """Haengt einen Trainingsdaten-Eintrag an die Tages-Log-Datei an."""
    verzeichnis.mkdir(parents=True, exist_ok=True)
    datei = verzeichnis / f"{datetime.now():%Y-%m-%d}.jsonl"
    eintrag = {
        "zeitstempel": datetime.now().isoformat(timespec="seconds"),
        "profil": profil,
        "roh_text": roh_text,
        "tags": tags,
    }
    zeile = json.dumps(eintrag, ensure_ascii=False)
    with _lock:
        with datei.open("a", encoding="utf-8") as fh:
            fh.write(zeile + "\n")
