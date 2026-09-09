"""Laedt das Klassifikations-Modell mit eigenen Parametern ueber die lms-CLI.

Uebernommen als Vorlage aus dem Diktier-Tool (server/lmstudio.py). Warum
ueberhaupt eigene Parameter: ``--identifier`` laedt das Modell unter einem
eigenen Namen (Praefix "gaming-"), so gelten Kontextlaenge und GPU-Offload nur
fuer diesen Prozess - eine parallele Nutzung desselben Modells in LM Studio
oder im Diktier-Tool bleibt unberuehrt.

Python-Hinweis: "subprocess.run(...)" startet ein externes Kommandozeilen-
programm (hier ``lms``) und wartet, bis es fertig ist - anders als
subprocess.Popen in whisper_proc.py, das im Hintergrund weiterlaeuft.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

import requests

log = logging.getLogger("lmstudio")

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

# Praefix, damit unsere Instanzen von allem anderen unterscheidbar sind, was
# in LM Studio geladen ist (z.B. vom Diktier-Tool, dessen Praefix "diktier-" ist).
PRAEFIX = "gaming-"


def _cli() -> str | None:
    """Pfad zur lms-CLI, oder None wenn sie nicht auffindbar ist."""
    gefunden = shutil.which("lms")
    if gefunden:
        return gefunden
    standard = Path(os.path.expanduser("~")) / ".lmstudio" / "bin" / "lms.exe"
    return str(standard) if standard.exists() else None


def bezeichner_fuer(modell: str) -> str:
    """google/gemma-4-e4b -> gaming-gemma-4-e4b"""
    return PRAEFIX + modell.split("/")[-1]


def _geladene_modelle(api_base: str, timeout: float = 5.0) -> set[str]:
    """Bezeichner aller aktuell in LM Studio geladenen Modelle."""
    url = api_base.rstrip("/").removesuffix("/v1") + "/api/v0/models"
    try:
        antwort = requests.get(url, timeout=timeout)
        antwort.raise_for_status()
        return {
            eintrag.get("id", "")
            for eintrag in (antwort.json().get("data") or [])
            if eintrag.get("state") not in (None, "not-loaded")
        }
    except Exception as exc:
        log.debug("Geladene Modelle nicht abfragbar: %s", exc)
        return set()


def sicherstellen_geladen(cfg: dict, kontextlaenge: int) -> str:
    """Sorgt dafuer, dass das konfigurierte LLM mit unseren Parametern geladen ist.

    Rueckgabe ist der Name, unter dem das Modell anzusprechen ist: unser
    eigener Bezeichner bei Erfolg, sonst der urspruengliche Modellname (dann
    laedt/verwaltet LM Studio das Modell selbst weiter wie bisher).
    """
    llm = cfg["llm"]
    modell = llm["model"]
    if not llm.get("manage_loading", True):
        return modell

    bezeichner = bezeichner_fuer(modell)
    if bezeichner in _geladene_modelle(llm["api_base"]):
        andere_entladen(cfg, behalten=bezeichner)
        return bezeichner

    cli = _cli()
    if cli is None:
        log.warning(
            "lms-CLI nicht gefunden - %s wird von LM Studio selbst geladen. "
            "Kontextlaenge und GPU-Offload bleiben dessen Vorgaben.", modell,
        )
        return modell

    befehl = [cli, "load", modell, "--identifier", bezeichner, "-y"]
    if kontextlaenge:
        befehl += ["--context-length", str(kontextlaenge)]
    if llm.get("gpu_offload"):
        befehl += ["--gpu", str(llm["gpu_offload"])]
    if llm.get("ttl_s"):
        befehl += ["--ttl", str(int(llm["ttl_s"]))]

    log.info(
        "Lade %s als %r (Kontext %s, GPU %s)",
        modell, bezeichner, kontextlaenge or "Vorgabe", llm.get("gpu_offload", "Vorgabe"),
    )
    try:
        ergebnis = subprocess.run(
            befehl, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=600, creationflags=_NO_WINDOW,
        )
    except Exception as exc:
        log.warning("lms load fehlgeschlagen (%s) - nutze %s direkt", exc, modell)
        return modell

    if ergebnis.returncode != 0:
        meldung = (ergebnis.stderr or ergebnis.stdout or "").strip().splitlines()
        log.warning(
            "lms load meldete Code %d (%s) - nutze %s direkt",
            ergebnis.returncode, meldung[-1] if meldung else "ohne Ausgabe", modell,
        )
        return modell

    log.info("%s ist als %r geladen", modell, bezeichner)
    andere_entladen(cfg, behalten=bezeichner)
    return bezeichner


def andere_entladen(cfg: dict, behalten: str) -> None:
    """Entlaedt unsere anderen geladenen Instanzen (z.B. nach einem Profilwechsel
    mit anderer Kontextlaenge). Ruehrt ausschliesslich Instanzen mit unserem
    eigenen Praefix an - was sonst in LM Studio laeuft, bleibt unberuehrt."""
    llm = cfg["llm"]
    if not llm.get("manage_loading", True) or not llm.get("unload_other_models", True):
        return
    cli = _cli()
    if cli is None:
        return
    for bezeichner in _geladene_modelle(llm["api_base"]):
        if not bezeichner.startswith(PRAEFIX) or bezeichner == behalten:
            continue
        try:
            ergebnis = subprocess.run(
                [cli, "unload", bezeichner], capture_output=True,
                timeout=60, creationflags=_NO_WINDOW,
            )
            if ergebnis.returncode == 0:
                log.info("%s entladen, um Speicher freizugeben", bezeichner)
        except Exception as exc:
            log.debug("Entladen von %s fehlgeschlagen: %s", bezeichner, exc)


def alle_entladen(cfg: dict) -> None:
    """Entlaedt alle von uns geladenen Instanzen - beim Beenden des Programms."""
    llm = cfg["llm"]
    if not llm.get("manage_loading", True):
        return
    cli = _cli()
    if cli is None:
        return
    for bezeichner in _geladene_modelle(llm["api_base"]):
        if not bezeichner.startswith(PRAEFIX):
            continue
        try:
            subprocess.run([cli, "unload", bezeichner], capture_output=True,
                            timeout=60, creationflags=_NO_WINDOW)
            log.info("%s entladen", bezeichner)
        except Exception as exc:
            log.debug("Entladen von %s fehlgeschlagen: %s", bezeichner, exc)
