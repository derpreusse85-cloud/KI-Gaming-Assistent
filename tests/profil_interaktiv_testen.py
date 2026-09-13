"""Interaktives Testwerkzeug fuer ein Spielprofil - ohne Spiel, ohne Mikrofon.

Gedacht fuer alle, die eine Profil-YAML neu anlegen oder aendern und
ausprobieren wollen, wie das LLM auf verschiedene Formulierungen reagiert,
BEVOR sie es im echten Spiel testen. Man waehlt ein Profil, tippt dann
beliebige Saetze ein (so, wie man sie auch sprechen wuerde) und sieht sofort
den erkannten Tag und die zugehoerige Tastenfolge - es wird dabei NICHTS
wirklich gedrueckt (reiner Trockentest), damit man das auch bequem am
Schreibtisch machen kann, ohne dass irgendwo im Hintergrund eine Taste
ausgeloest wird.

Anders als tests/test_elite_dangerous_klassifikation.py (feste Testfaelle mit
bekannt richtiger Antwort) gibt es hier keine "erwartete" Antwort - man schaut
sich das Ergebnis einfach selbst an und entscheidet, ob es passt.

Aufruf (braucht kein Mikrofon, aber einen laufenden llama-server, den dieses
Skript selbst startet):

    .venv\\Scripts\\python.exe tests\\profil_interaktiv_testen.py
    .venv\\Scripts\\python.exe tests\\profil_interaktiv_testen.py EliteDangerous

Ohne Profilnamen als Argument wird eine Auswahlliste angezeigt.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJEKT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJEKT_ROOT))

from gaming_assistant import config, parser, profile, prompt
from gaming_assistant.llama_proc import LlamaServer
from gaming_assistant.llm import LLMKlassifikator


def profil_auswaehlen(cfg: dict) -> str:
    verzeichnis = config.profil_verzeichnis(cfg)
    namen = profile.liste_profile(verzeichnis)
    if not namen:
        print(f"Keine Profile gefunden in {verzeichnis}")
        sys.exit(1)
    if len(sys.argv) > 1:
        gewuenscht = sys.argv[1]
        if gewuenscht in namen:
            return gewuenscht
        print(f"Profil {gewuenscht!r} nicht gefunden. Verfuegbar: {', '.join(namen)}")
        sys.exit(1)
    print("Verfuegbare Profile:")
    for i, name in enumerate(namen, start=1):
        print(f"  {i}) {name}")
    while True:
        eingabe = input("Welches Profil testen? (Zahl oder Name): ").strip()
        if eingabe.isdigit() and 1 <= int(eingabe) <= len(namen):
            return namen[int(eingabe) - 1]
        if eingabe in namen:
            return eingabe
        print("Ungueltige Auswahl, bitte nochmal.")


def main() -> None:
    cfg = config.load()
    name = profil_auswaehlen(cfg)
    verzeichnis = config.profil_verzeichnis(cfg)
    profil = profile.laden(verzeichnis / f"{name}.yaml")
    system_prompt = prompt.system_prompt_bauen(profil)

    print(f"\nLade Profil {name!r} ({len(profil.tags)} Tags, Kontextlaenge {profil.kontextlaenge}) ...")
    server = LlamaServer(cfg)
    server.start(profil.kontextlaenge)
    klassifikator = LLMKlassifikator(cfg)

    print(
        "\nBereit. Tippe einen gesprochenen Befehl ein (oder 'exit'/'quit' zum Beenden).\n"
        "Es wird NICHTS wirklich gedrueckt - reiner Trockentest.\n"
    )
    try:
        while True:
            try:
                text = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                continue
            if text.lower() in ("exit", "quit", "ende"):
                break

            antwort, finish_reason = klassifikator.klassifizieren(text, system_prompt, "gaming-llm")
            tags = parser.tags_extrahieren(antwort, profil.bekannte_tags(), finish_reason)

            if not tags:
                print(f"  -> kein Tag erkannt (Rohantwort: {antwort!r})")
                continue
            for tag_name in tags:
                eintrag = profil.tags[tag_name]
                if eintrag.feuergruppe_ziel is not None:
                    print(f"  -> &&{tag_name}&& (Taste wird zur Laufzeit aus dem Spielzustand berechnet)")
                else:
                    halte = f"[{eintrag.halte_taste}]+" if eintrag.halte_taste else ""
                    print(f"  -> &&{tag_name}&& -> Taste(n): {halte}{eintrag.taste}")
    finally:
        klassifikator.close()
        server.stop()
        print("\nBeendet.")


if __name__ == "__main__":
    main()
