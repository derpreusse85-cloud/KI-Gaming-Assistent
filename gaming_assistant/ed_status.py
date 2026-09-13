"""Liest die von Elite Dangerous selbst laufend geschriebene Status.json.

Nur fuer das Elite-Dangerous-Profil gebraucht (siehe profiles/EliteDangerous.yaml,
Feld "status_datei" + "feuergruppe_ziel" pro Tag). Das Spiel schreibt diese Datei
regelmaessig komplett neu, u.a. mit dem Feld "FireGroup" (0-indiziert: A=0, B=1,
...) fuer die gerade aktive Feuergruppe. Elite Dangerous kennt dafuer nur eine
einzige Zyklus-Taste ("naechste Gruppe"), keine Direktwahl - dieses Modul
berechnet deshalb bei Bedarf, wie oft diese Taste (oder die Rueckwaerts-Taste)
gedrueckt werden muss, um von der aktuellen zur gewuenschten Gruppe zu kommen.

Wichtig: Diese Datei wird NUR gelesen, nie veraendert - sie ist reine
Diagnoseausgabe des Spiels, kein Steuerkanal.

Python-Hinweis: json.load() kann fehlschlagen, wenn genau in dem Moment gelesen
wird, in dem das Spiel die Datei komplett neu schreibt (kurzzeitig unvollstaendiger
Inhalt) - deshalb hier ein paar kurze Wiederholungsversuche statt beim ersten
Fehler sofort aufzugeben.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

log = logging.getLogger("ed_status")

# Vorgabewerte, falls im Profil nicht anders angegeben (siehe profile.py):
# "n" ist die Standard-Spielbelegung fuer "naechste Feuergruppe". Fuer
# "vorherige Feuergruppe" gibt es keine Standardbelegung - der Nutzer muss "b"
# selbst in den Elite-Dangerous-Optionen dafuer eintragen (siehe Kommentar in
# der Profil-YAML). Beide Tasten sind im Profil ueberschreibbar, falls sie bei
# jemandem mit einer anderen Belegung kollidieren.
TASTE_VORWAERTS_STANDARD = "n"
TASTE_RUECKWAERTS_STANDARD = "b"

# Elite Dangerous erlaubt maximal 8 Feuergruppen (A-H, Index 0-7). Ob der Nutzer
# tatsaechlich alle 8 mit Waffen belegt hat, liegt in seiner eigenen Verantwortung.
_ANZAHL_GRUPPEN = 8

_LESE_VERSUCHE = 3
_LESE_PAUSE_S = 0.02


def _status_lesen(status_pfad: Path) -> dict | None:
    """Liest und parst die Status.json, mit kurzen Wiederholungsversuchen.

    Gibt None zurueck, wenn die Datei fehlt oder auch nach mehreren Versuchen
    kein gueltiges JSON gelesen werden konnte - der Aufrufer behandelt das wie
    "Spielzustand unbekannt", nicht wie einen harten Fehler.
    """
    letzter_fehler: Exception | None = None
    for _ in range(_LESE_VERSUCHE):
        try:
            with status_pfad.open(encoding="utf-8") as datei:
                return json.load(datei)
        except FileNotFoundError:
            log.warning("Status.json nicht gefunden: %s", status_pfad)
            return None
        except json.JSONDecodeError as exc:
            # Vermutlich mitten in einem Schreibvorgang erwischt - kurz warten
            # und nochmal versuchen, bevor aufgegeben wird.
            letzter_fehler = exc
            time.sleep(_LESE_PAUSE_S)
    log.warning("Status.json auch nach %d Versuchen nicht lesbar: %s", _LESE_VERSUCHE, letzter_fehler)
    return None


def feuergruppen_tasten(
    status_pfad: Path,
    ziel_index: int,
    taste_vorwaerts: str = TASTE_VORWAERTS_STANDARD,
    taste_rueckwaerts: str = TASTE_RUECKWAERTS_STANDARD,
) -> list[str] | None:
    """Berechnet die Tastensequenz, um von der aktuellen zur Ziel-Feuergruppe zu wechseln.

    Liefert None, wenn der aktuelle Spielzustand nicht bekannt ist (Datei fehlt,
    kaputt, oder das Feld "FireGroup" fehlt - z.B. weil das Spiel gerade nicht
    laeuft oder man sich nicht im Schiff befindet). Der Aufrufer (__main__.py)
    loest dann bewusst KEINEN Tastendruck aus, statt zu raten.
    """
    status = _status_lesen(status_pfad)
    if status is None:
        return None

    aktueller_index = status.get("FireGroup")
    if aktueller_index is None:
        log.warning("Status.json enthaelt kein Feld 'FireGroup' - Spiel laeuft nicht oder kein Schiff aktiv")
        return None

    if aktueller_index == ziel_index:
        log.debug("Feuergruppe: bereits auf Ziel %d, keine Taste noetig", ziel_index)
        return []

    vorwaerts = (ziel_index - aktueller_index) % _ANZAHL_GRUPPEN
    rueckwaerts = (aktueller_index - ziel_index) % _ANZAHL_GRUPPEN

    if vorwaerts <= rueckwaerts:
        sequenz = [taste_vorwaerts] * vorwaerts
    else:
        sequenz = [taste_rueckwaerts] * rueckwaerts
    log.debug(
        "Feuergruppe: aktuell=%d, ziel=%d -> Sequenz %s",
        aktueller_index, ziel_index, sequenz,
    )
    return sequenz
