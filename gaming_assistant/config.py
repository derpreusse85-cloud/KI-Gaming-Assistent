"""Globale Einstellungen des Gaming-Sprachassistenten.

Anders als beim Diktier-Tool gibt es hier nur EINE config.json fuer den ganzen
Prozess (kein Server/Client-Split, kein Netzwerk-Token). Die Datei wird beim
ersten Start automatisch mit den Vorgabewerten (DEFAULTS) angelegt.

Python-Hinweis fuer Einsteiger: ein "dict" (Python-Woerterbuch) ist hier die
Datenstruktur fuer die Einstellungen, verschachtelt wie das YAML/JSON, das es
beim Lesen/Schreiben abbildet. Zugriff per cfg["stt"]["sprache"] usw.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


def _root() -> Path:
    """Projekt-Wurzelverzeichnis, in dem config.json liegt.

    ``sys.frozen`` ist nur bei einem gepackten Programm (z.B. PyInstaller)
    gesetzt - fuer den normalen Start per ``python -m gaming_assistant``
    reicht der Ordner ueber diesem Modul.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


ROOT = _root()
CONFIG_PATH = ROOT / "config.json"

# Vorgabewerte. Eine unvollstaendige oder fehlende config.json wird beim Laden
# ueber diese Werte "gemergt" (siehe _deep_merge) - fehlende Schluessel werden
# ergaenzt, vorhandene bleiben wie vom Nutzer gesetzt.
DEFAULTS: dict[str, Any] = {
    "profil": {
        # Verzeichnis mit den Spiel-YAMLs, relativ zur Projekt-Wurzel.
        "verzeichnis": "profiles",
        # Dateiname (ohne .yaml) des beim Start aktiven Profils.
        "aktiv": "Helldivers2_Stratagems",
    },
    # Push-to-talk-Ausloeser. type "keyboard" -> key (z.B. "f9", einzelnes
    # Zeichen), type "mouse" -> button (left/middle/right/x1/x2).
    "ptt": {"type": "keyboard", "key": "f9"},
    # None = Systemstandard-Mikrofon.
    "mic_device_index": None,
    "stt": {
        "whisper_bin": "vendor/whisper.cpp/build/bin/Release/whisper-server.exe",
        "model": "models/ggml-large-v3-turbo-german-q5.bin",
        "language": "de",
        "threads": 8,
        # Eigener Port, damit ein parallel laufendes Diktier-Tool (Port 8910)
        # nicht kollidiert.
        "whisper_host": "127.0.0.1",
        "whisper_port": 8930,
        "startup_timeout_s": 180,
    },
    "llm": {
        "api_base": "http://localhost:1234/v1",
        "model": "google/gemma-4-e4b",
        # 0.0 = Greedy Decoding, siehe Gaming_assistent.md "Sampling-Parameter".
        "temperature": 0.0,
        "max_tokens": 40,
        "timeout_s": 30,
        "manage_loading": True,
        "gpu_offload": "max",
        "ttl_s": 0,
        "unload_other_models": True,
    },
    "log_level": "INFO",
    "training_log": {"verzeichnis": "training_data/raw"},
}


def resolve_path(wert: str) -> Path:
    """Macht aus einem relativen Config-Pfad einen absoluten Pfad ab ROOT."""
    pfad = Path(wert)
    return pfad if pfad.is_absolute() else ROOT / pfad


def _deep_merge(basis: dict, override: dict) -> dict:
    """Merged ``override`` rekursiv ueber eine Kopie von ``basis``.

    "Rekursiv" heisst: verschachtelte dicts (z.B. cfg["stt"]) werden selbst
    wieder per _deep_merge zusammengefuehrt, statt den ganzen Unterblock zu
    ersetzen. So bleiben in der config.json nur die vom Nutzer geaenderten
    Werte noetig, alles andere kommt aus DEFAULTS.
    """
    ergebnis = dict(basis)
    for schluessel, wert in override.items():
        if isinstance(wert, dict) and isinstance(ergebnis.get(schluessel), dict):
            ergebnis[schluessel] = _deep_merge(ergebnis[schluessel], wert)
        else:
            ergebnis[schluessel] = wert
    return ergebnis


def _write_json(pfad: Path, daten: dict) -> None:
    """Schreibt atomar: erst in eine Temp-Datei, dann per os.replace umbenennen.

    Damit bleibt eine evtl. vorhandene config.json auch dann intakt, wenn der
    Prozess mitten im Schreiben abstuerzt (os.replace ist auf Windows/NTFS
    eine einzelne, nicht unterbrechbare Operation).
    """
    pfad.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(pfad.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as datei:
            json.dump(daten, datei, indent=2, ensure_ascii=False)
            datei.write("\n")
        os.replace(tmp, pfad)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def load() -> dict:
    """Laedt config.json (legt sie beim ersten Start mit den Vorgaben an)."""
    if CONFIG_PATH.exists():
        # utf-8-sig statt utf-8: falls die Datei mit BOM gespeichert wurde
        # (z.B. durch PowerShell), stoert das hier nicht.
        with CONFIG_PATH.open(encoding="utf-8-sig") as datei:
            roh = json.load(datei)
        return _deep_merge(DEFAULTS, roh)
    cfg = _deep_merge(DEFAULTS, {})
    save(cfg)
    return cfg


def save(cfg: dict) -> None:
    _write_json(CONFIG_PATH, cfg)


def profil_verzeichnis(cfg: dict) -> Path:
    return resolve_path(cfg["profil"]["verzeichnis"])
