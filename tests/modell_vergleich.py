"""Vergleicht mehrere LLM-Modelle (GGUF) bei der Tag-Klassifikation.

Nutzt dieselben Testfaelle wie test_profil_klassifikation.py (automatisch aus
den `beispiel`-Feldern + ZUSATZFAELLE + NONE-Faelle) und misst zusaetzlich die
Latenz pro Anfrage. Pro Modell und Profil wird llama-server frisch gestartet.

Aufruf:

    .venv\\Scripts\\python.exe tests\\modell_vergleich.py ^
        gemma-4-E4B-it-GGUF/gemma-4-E4B-it-Q4_K_M.gguf ^
        gemma-4-E2B-it-GGUF/gemma-4-E2B-it-Q4_K_M.gguf
"""

from __future__ import annotations

import copy
import statistics
import sys
import time
from pathlib import Path

_PROJEKT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJEKT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gaming_assistant import config, parser, profile, prompt
from gaming_assistant.llama_proc import LlamaServer
from gaming_assistant.llm import LLMKlassifikator
from test_profil_klassifikation import _faelle_ableiten

# Persoenliche Kopie von EliteDangerous - wuerde nur doppelt zaehlen.
IGNORIEREN = {"EliteDangerous_Lokal"}


def modell_testen(cfg: dict, modell: str, namen: list[str]) -> dict:
    cfg = copy.deepcopy(cfg)
    cfg["llm"]["model"] = modell
    ergebnis = {"richtig": 0, "gesamt": 0, "zeiten": [], "cold": [], "fehler": []}
    for name in namen:
        profil = profile.laden(config.profil_verzeichnis(cfg) / f"{name}.yaml")
        system_prompt = prompt.system_prompt_bauen(profil)
        faelle = _faelle_ableiten(profil)
        server = LlamaServer(cfg)
        server.start(profil.kontextlaenge)
        klassifikator = LLMKlassifikator(cfg)
        try:
            for i, (text, erwartet) in enumerate(faelle):
                t0 = time.perf_counter()
                antwort, finish = klassifikator.klassifizieren(text, system_prompt, "gaming-llm")
                dauer = time.perf_counter() - t0
                (ergebnis["cold"] if i == 0 else ergebnis["zeiten"]).append(dauer)
                tags = parser.tags_extrahieren(antwort, profil.bekannte_tags(), finish,
                                                profil.schlagwort_zuordnung())
                ergebnis["gesamt"] += 1
                if tags == erwartet:
                    ergebnis["richtig"] += 1
                else:
                    ergebnis["fehler"].append((name, text, tags, erwartet))
        finally:
            klassifikator.close()
            server.stop()
        print(f"  {name}: fertig", flush=True)
    return ergebnis


def main() -> int:
    modelle = sys.argv[1:]
    if not modelle:
        print(__doc__)
        return 1
    cfg = config.load()
    namen = [n for n in profile.liste_profile(config.profil_verzeichnis(cfg)) if n not in IGNORIEREN]

    alle = {}
    for modell in modelle:
        print(f"\n### {modell}", flush=True)
        alle[modell] = modell_testen(cfg, modell, namen)

    print("\n\n===== ZUSAMMENFASSUNG =====")
    for modell, e in alle.items():
        z = sorted(e["zeiten"])
        print(f"\n{modell}")
        print(f"  korrekt: {e['richtig']}/{e['gesamt']}")
        print(f"  Latenz warm: Median {statistics.median(z):.3f}s, "
              f"Mittel {statistics.mean(z):.3f}s, P95 {z[int(len(z) * 0.95)]:.3f}s")
        print(f"  Cold-Start (erster Aufruf je Profil): Mittel {statistics.mean(e['cold']):.2f}s")
        for name, text, tags, erwartet in e["fehler"]:
            print(f"  ABWEICHUNG [{name}] {text!r} -> {tags} erwartet {erwartet}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
