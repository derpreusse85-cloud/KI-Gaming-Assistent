"""Regressionstest fuer die Tag-Klassifikation - funktioniert fuer JEDES Profil.

Grundidee: jedes Tag in einer Profil-YAML hat bereits ein eigenes `beispiel`-
Feld (das Few-Shot-Beispiel im System-Prompt) - genau dieser Satz sollte beim
Klassifizieren auch wieder zu genau diesem Tag fuehren. Daraus lassen sich
automatisch Testfaelle fuer jedes beliebige Profil ableiten, ohne dass jemand
von Hand eine Liste pflegen muesste. Zusaetzlich lassen sich in
`ZUSATZFAELLE` unten handverlesene Faelle je Profil ergaenzen (Paraphrasen,
Mehrfachbefehle, bekannte Kollisionskandidaten) - Profile ohne eigenen
Eintrag dort laufen trotzdem mit den automatisch abgeleiteten Grundfaellen.

Kein Ersatz fuer einen echten Test im laufenden Spiel, aber faengt
Regressionen ab, wenn sich am Profil oder am System-Prompt-Aufbau etwas
aendert (z.B. neue Tags, die mit bestehenden kollidieren).

Aufruf (braucht die ueblichen Modelle/Server, kein Mikrofon noetig, reine
Text-Klassifikation ohne Whisper):

    .venv\\Scripts\\python.exe tests\\test_profil_klassifikation.py
        -> testet alle Profile in profiles/
    .venv\\Scripts\\python.exe tests\\test_profil_klassifikation.py EliteDangerous Helldivers1
        -> testet nur die genannten Profile
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJEKT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJEKT_ROOT))

from gaming_assistant import config, parser, profile, prompt
from gaming_assistant.llama_proc import LlamaServer
from gaming_assistant.llm import LLMKlassifikator
from gaming_assistant.profile import Profil

# Handverlesene Zusatzfaelle je Profil (Aeusserung, erwartete Tag-Liste in
# Nennreihenfolge) - ergaenzen die automatisch aus jedem "beispiel"-Feld
# abgeleiteten Grundfaelle.
ZUSATZFAELLE: dict[str, list[tuple[str, list[str]]]] = {
    "EliteDangerous": [
        ("Pump die Energie in die Waffen", ["WaffenMAX"]),
        ("Landing Gear ausfahren", ["Fahrgestell"]),
        ("Spring in den Hyperraum", ["Frameshiftdrive"]),
        ("Mach die Cargo Hatch auf", ["Ladeluke"]),
        ("Frachtluke oeffnen", ["Ladeluke"]),
        ("All Stop", ["Stop"]),
        ("Fahr die Hardpoints aus", ["Aufhaengungen"]),
        ("Wechsle in den Combat Mode", ["Moduswechsel"]),
        ("Aktivier die Shield Cell Bank", ["Schildzellenbank"]),
        ("Aktiviere Feuergruppe D", ["FeuergruppeD"]),
        ("Gib mir Feuergruppe A", ["FeuergruppeA"]),
        ("Fahrgestell ausfahren und Ladeluke oeffnen", ["Fahrgestell", "Ladeluke"]),
        ("Ladeluke oeffnen und Fahrgestell ausfahren", ["Ladeluke", "Fahrgestell"]),
    ],
}

# Gilt fuer jedes Profil zusaetzlich: Saetze ohne jeden Bezug zu einem Tag
# sollen zuverlaessig zu &&NONE&& fuehren (leere Tag-Liste).
NONE_FAELLE = [
    "Wie ist das Wetter heute",
    "Erzaehl mir einen Witz",
]


def _faelle_ableiten(profil: Profil) -> list[tuple[str, list[str]]]:
    faelle = [(eintrag.beispiel, [tag_name]) for tag_name, eintrag in profil.tags.items()]
    faelle += ZUSATZFAELLE.get(profil.name, [])
    faelle += [(text, []) for text in NONE_FAELLE]
    return faelle


def profil_testen(cfg: dict, name: str) -> tuple[int, int]:
    """Testet ein einzelnes Profil, gibt (Anzahl richtig, Anzahl gesamt) zurueck."""
    verzeichnis = config.profil_verzeichnis(cfg)
    profil = profile.laden(verzeichnis / f"{name}.yaml")
    system_prompt = prompt.system_prompt_bauen(profil)
    faelle = _faelle_ableiten(profil)

    print(f"\n=== Profil {name!r} ({len(profil.tags)} Tags, {len(faelle)} Testfaelle) ===")
    server = LlamaServer(cfg)
    server.start(profil.kontextlaenge)
    klassifikator = LLMKlassifikator(cfg)

    richtig = 0
    try:
        for text, erwartet in faelle:
            antwort, finish_reason = klassifikator.klassifizieren(text, system_prompt, "gaming-llm")
            tags = parser.tags_extrahieren(antwort, profil.bekannte_tags(), finish_reason)
            treffer = tags == erwartet
            richtig += treffer
            status = "OK" if treffer else "ABWEICHUNG"
            print(f"[{status}] {text!r} -> tags={tags} erwartet={erwartet}")
    finally:
        klassifikator.close()
        server.stop()

    print(f"{richtig}/{len(faelle)} korrekt fuer Profil {name!r}")
    return richtig, len(faelle)


def main() -> int:
    cfg = config.load()
    verzeichnis = config.profil_verzeichnis(cfg)
    namen = sys.argv[1:] if len(sys.argv) > 1 else profile.liste_profile(verzeichnis)
    if not namen:
        print(f"Kein Profil gefunden in {verzeichnis}")
        return 1

    gesamt_richtig = gesamt_faelle = 0
    for name in namen:
        richtig, anzahl = profil_testen(cfg, name)
        gesamt_richtig += richtig
        gesamt_faelle += anzahl

    print(f"\nGesamt: {gesamt_richtig}/{gesamt_faelle} korrekt ueber {len(namen)} Profil(e)")
    return 0 if gesamt_richtig == gesamt_faelle else 1


if __name__ == "__main__":
    sys.exit(main())
