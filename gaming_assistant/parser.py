"""Extrahiert Tags aus einer LLM-Antwort - sicherheitsbewusst statt raetend.

Grundprinzip aus Gaming_assistent.md, Abschnitt "Parser-Sicherheit": bei jedem
Zweifel wird NICHTS ausgeloest statt zu raten. Anders als beim Diktier-Tool
(dort bleibt bei einem LLM-Fehler wenigstens der Rohtext erhalten) gibt es hier
kein sinnvolles Fallback - ein falscher Tastendruck im Spiel waere schlimmer
als gar keiner.

Python-Hinweis: "re" ist Pythons Regex-Modul (regulaere Ausdruecke, ein
Mini-Suchmuster fuer Text). re.findall() findet ALLE Treffer eines Musters in
einem Text und gibt sie als Liste zurueck.
"""

from __future__ import annotations

import logging
import re

log = logging.getLogger("parser")

# &&([^&]+?)&& sucht alles zwischen zwei doppelten Und-Zeichen, das selbst
# keine weiteren & enthaelt. "+?" ist "so wenig wie moeglich" (non-greedy),
# damit "&&A&& &&B&&" als zwei Treffer A und B erkannt wird, nicht als ein
# einziger Treffer "A&& &&B".
_TAG_MUSTER = re.compile(r"&&([^&]+?)&&")

NONE_TAG = "NONE"


def tags_extrahieren(
    antwort_text: str,
    bekannte_tags: set[str],
    finish_reason: str | None,
) -> list[str]:
    """Liefert die Liste gueltiger Tags in Nennreihenfolge, oder [] bei Zweifel.

    Verwirft die komplette Antwort (statt nur den fraglichen Teil), wenn:
    - die Antwort bei max_tokens abgeschnitten wurde (finish_reason "length"),
    - ein unbekannter Marker auftaucht (Tippfehler/Halluzination des Modells),
    - NONE zusammen mit einem echten Tag auftaucht (widerspruechliche Antwort).
    """
    if finish_reason == "length":
        log.warning("LLM-Antwort abgeschnitten (max_tokens) - verworfen, kein Tastendruck")
        return []

    treffer = _TAG_MUSTER.findall(antwort_text or "")
    if not treffer:
        log.debug("Keine Tags in der LLM-Antwort gefunden")
        return []

    gueltige_menge = bekannte_tags | {NONE_TAG}
    for tag in treffer:
        if tag not in gueltige_menge:
            log.warning("Unbekannter Marker &&%s&& in der LLM-Antwort - alles verworfen", tag)
            return []

    if NONE_TAG in treffer:
        if len(treffer) > 1:
            log.warning("NONE zusammen mit echten Tags in der Antwort - alles verworfen")
        return []

    return treffer
