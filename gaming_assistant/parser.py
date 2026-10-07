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

# Erkennt einen Sleep-Pseudo-Tag wie "sleep:5" (siehe prompt.py und CLAUDE.md,
# "Verschachtelte Kommandos mit Pausenzeiten") - kein echter Aktions-Tag aus
# dem Profil, sondern ein generisches, profilunabhaengiges Muster mit der
# Wartezeit in Sekunden direkt im Marker.
_SLEEP_MUSTER = re.compile(r"^sleep:(\d+)$")

# Sicherheitsobergrenze fuer eine einzelne Wartezeit - eine falsch verstandene
# oder missbraeuchlich lange Zeitangabe soll die Pipeline nicht fuer sehr
# lange Zeit blockieren (siehe __main__.py, wo diese Grenze angewendet wird).
MAX_SLEEP_SEKUNDEN = 30

NONE_TAG = "NONE"


def schreibweise_normalisieren(name: str) -> str:
    """Klein geschrieben, Bindestrich/Leerzeichen als Unterstrich."""
    return name.strip().lower().replace("-", "_").replace(" ", "_")


def _auf_bekannten_tag_abbilden(
    marker: str, bekannte_tags: set[str], schlagwoerter: dict[str, str] | None = None
) -> str:
    """Korrigiert NUR eine abweichende Schreibweise eines bekannten Tags.

    Kleine Modelle geben gelegentlich den Tag mit Bindestrich statt
    Unterstrich aus (z.B. &&Patriot-Exoanzug&& statt &&Patriot_Exoanzug&&,
    weil das Schlagwort so geschrieben ist). Das ist verlustfrei eindeutig
    und kein Raten - es wird nur umgesetzt, wenn genau EIN bekannter Tag
    nach der Normalisierung passt. Dasselbe gilt, wenn das Modell statt des
    Tag-Namens ein (eindeutiges) Schlagwort des Tags ausgibt (``schlagwoerter``,
    siehe Profil.schlagwort_zuordnung()). Alles andere bleibt unveraendert und wird
    danach wie gehabt als unbekannter Marker verworfen.
    """
    if marker in bekannte_tags:
        return marker
    ziel = schreibweise_normalisieren(marker)
    passende = [t for t in bekannte_tags if schreibweise_normalisieren(t) == ziel]
    if len(passende) == 1:
        log.debug("Schreibweise &&%s&& auf bekannten Tag &&%s&& abgebildet", marker, passende[0])
        return passende[0]
    tag = (schlagwoerter or {}).get(ziel)
    if tag in bekannte_tags:
        log.debug("Schlagwort &&%s&& auf Tag &&%s&& abgebildet", marker, tag)
        return tag
    return marker


def sleep_dauer(tag: str) -> int | None:
    """Sekundenzahl, falls ``tag`` ein &&sleep:N&&-Marker ist, sonst None."""
    treffer = _SLEEP_MUSTER.match(tag)
    return int(treffer.group(1)) if treffer else None


def tags_extrahieren(
    antwort_text: str,
    bekannte_tags: set[str],
    finish_reason: str | None,
    schlagwoerter: dict[str, str] | None = None,
) -> list[str]:
    """Liefert die Liste gueltiger Tags in Nennreihenfolge, oder [] bei Zweifel.

    Verwirft die komplette Antwort (statt nur den fraglichen Teil), wenn:
    - die Antwort bei max_tokens abgeschnitten wurde (finish_reason "length"),
    - ein unbekannter Marker auftaucht (Tippfehler/Halluzination des Modells),
    - NONE zusammen mit einem echten Tag auftaucht (widerspruechliche Antwort).

    Sleep-Marker (&&sleep:N&&, siehe sleep_dauer()) gelten dabei wie ein
    normaler gueltiger Tag, unabhaengig vom jeweiligen Profil. Ein Sleep ganz
    am Ende der Sequenz ist sinnlos (keine folgende Aktion mehr) und wird
    entfernt - ein bekannter, harmloser LLM-Fehler an Sequenz-/Block-Grenzen
    (siehe Auto-Memory projekt_sleep_tag_machbarkeit).
    """
    if finish_reason == "length":
        log.warning("LLM-Antwort abgeschnitten (max_tokens) - verworfen, kein Tastendruck")
        return []

    treffer = _TAG_MUSTER.findall(antwort_text or "")
    if not treffer:
        log.debug("Keine Tags in der LLM-Antwort gefunden")
        return []

    treffer = [
        t if sleep_dauer(t) is not None or t == NONE_TAG
        else _auf_bekannten_tag_abbilden(t, bekannte_tags, schlagwoerter)
        for t in treffer
    ]

    gueltige_menge = bekannte_tags | {NONE_TAG}
    for tag in treffer:
        if tag not in gueltige_menge and sleep_dauer(tag) is None:
            log.warning("Unbekannter Marker &&%s&& in der LLM-Antwort - alles verworfen", tag)
            return []

    if NONE_TAG in treffer:
        if len(treffer) > 1:
            log.warning("NONE zusammen mit echten Tags in der Antwort - alles verworfen")
        return []

    while treffer and sleep_dauer(treffer[-1]) is not None:
        log.debug("Ueberfluessiger &&%s&& am Sequenzende entfernt", treffer[-1])
        treffer = treffer[:-1]

    return treffer
