"""Simuliert eine Tastensequenz im aktiven Fenster (dem Spiel) per pynput.

Die "taste"-Liste im Profil ist normalerweise eine Sequenz von Tipp-Vorgaengen
(Druecken+Loslassen nacheinander). Einzelne Eintraege koennen aber auch eine
Zusatztaste ueber mehrere Schritte hinweg gedrueckt HALTEN statt sie zu
tippen - Vorbild dafuer ist AutoHotkeys eigene Schreibweise ({Ctrl down} ...
{Ctrl up}): ein Eintrag wie "ctrl_down" haelt Strg gedrueckt, "ctrl_up" laesst
es wieder los. Dazwischen liegende normale Eintraege werden ganz normal
getippt, waehrend die Halte-Taste(n) weiter unten bleiben. Bei Helldivers 2/1
z.B. steht deshalb in jedem Stratagem-Eintrag "ctrl_down" vor und "ctrl_up"
nach der Pfeiltasten-Sequenz (bis 14.09.2026 gab es dafuer noch ein separates
"halte_taste"-Profilfeld - das ist jetzt direkt Teil der taste-Liste selbst,
kein Sonderfall im Code/Profil mehr noetig).

Python-Hinweis: pynput.keyboard.Controller() ist ein virtuelles Keyboard, das
Tastendruecke an das Betriebssystem meldet, als kaeme es von echter Hardware.
"press()" simuliert das Herunterdruecken, "release()" das Loslassen - beides
muss man selbst aufrufen, es passiert nicht automatisch.
"""

from __future__ import annotations

import logging
import time

from pynput.keyboard import Controller, Key, KeyCode

log = logging.getLogger("keypress")

# Kurze Pause zwischen den einzelnen Tipp-Schritten, damit das Spiel jeden
# einzelnen Tastendruck auch als solchen registriert (ohne Pause koennten
# schnelle Press/Release-Paare bei manchen Spielen verschluckt werden).
_PAUSE_S = 0.04

# Namen fuer Sondertasten, wie sie in einer Profil-YAML stehen koennen
# (klein geschrieben). Ergaenzbar bei Bedarf um weitere Modifier.
_SONDERTASTEN: dict[str, Key] = {
    "ctrl": Key.ctrl,
    "strg": Key.ctrl,
    "shift": Key.shift,
    "alt": Key.alt,
    "tab": Key.tab,
    "space": Key.space,
    "leertaste": Key.space,
    "enter": Key.enter,
    "esc": Key.esc,
}

_controller = Controller()

# Endungen, die einen Eintrag als "Taste halten/loslassen" statt "tippen"
# markieren - siehe _halte_marker().
_ENDUNG_DRUECKEN = "_down"
_ENDUNG_LOSLASSEN = "_up"


def _zu_taste(name: str) -> Key | KeyCode:
    """Wandelt einen Tasten-Namen aus dem Profil in ein pynput-Tasten-Objekt um."""
    kleinname = name.lower()
    if kleinname in _SONDERTASTEN:
        return _SONDERTASTEN[kleinname]
    if len(name) == 1:
        # KeyCode.from_char() ist pynputs Weg, ein einzelnes Zeichen (z.B. "S")
        # als simulierbare Taste darzustellen.
        return KeyCode.from_char(kleinname)
    # Letzter Versuch: passt der Name zu einem Attribut von pynput.keyboard.Key
    # (z.B. "f1", "page_up")?
    try:
        return Key[kleinname]
    except KeyError:
        raise ValueError(f"Unbekannte Taste in Profil: {name!r}") from None


def _halte_marker(name: str) -> tuple[str, bool] | None:
    """Erkennt Eintraege wie "ctrl_down"/"ctrl_up" (Taste halten/loslassen
    statt tippen). Liefert (Basis-Tastenname, wird_gedrueckt) oder None, wenn
    es sich um eine ganz normale Taste handelt.

    Wichtig: ein Name gilt NUR dann als Halte-Marker, wenn er sich nicht
    schon selbst ueber _zu_taste() als eigenstaendige Taste aufloesen laesst
    - sonst wuerden echte pynput-Tastennamen, die zufaellig auf "_down"/"_up"
    enden (z.B. "page_down", "media_volume_up"), faelschlich als Halte-Marker
    interpretiert statt als das, was sie sind.
    """
    try:
        _zu_taste(name)
        return None  # loest sich selbst auf -> ganz normale Taste, kein Marker
    except ValueError:
        pass

    kleinname = name.lower()
    if kleinname.endswith(_ENDUNG_DRUECKEN):
        basis, wird_gedrueckt = kleinname[: -len(_ENDUNG_DRUECKEN)], True
    elif kleinname.endswith(_ENDUNG_LOSLASSEN):
        basis, wird_gedrueckt = kleinname[: -len(_ENDUNG_LOSLASSEN)], False
    else:
        return None

    try:
        _zu_taste(basis)
    except ValueError:
        return None  # z.B. "media_volume_down" - Praefix "media_volume" ist keine Taste
    return basis, wird_gedrueckt


def ausloesen(taste_sequenz: list[str]) -> None:
    """Fuehrt eine Tasten-Sequenz aus. Normale Eintraege werden getippt
    (Druecken+kurze Pause+Loslassen+kurze Pause). Halte-Marker (siehe
    _halte_marker()) drueecken bzw. lassen stattdessen eine Zusatztaste los,
    die dann waehrend der folgenden Eintraege gehalten bleibt.

    Beispiel: ["ctrl_down", "down", "left", "ctrl_up"] haelt Strg, waehrend
    "down" und "left" getippt werden, laesst es danach wieder los.
    """
    # Aktuell gehaltene Tasten, Basis-Name -> pynput-Tastenobjekt - falls am
    # Ende noch welche offen sind (vergessenes "_up" oder Fehler mittendrin),
    # werden sie im finally-Block sicherheitshalber trotzdem losgelassen.
    gehalten: dict[str, Key | KeyCode] = {}

    try:
        for name in taste_sequenz:
            marker = _halte_marker(name)
            if marker is not None:
                basis, wird_gedrueckt = marker
                taste = _zu_taste(basis)
                if wird_gedrueckt:
                    _controller.press(taste)
                    gehalten[basis] = taste
                    log.debug("Taste gehalten: %r", basis)
                else:
                    _controller.release(taste)
                    gehalten.pop(basis, None)
                    log.debug("Taste losgelassen (Halte-Ende): %r", basis)
                time.sleep(_PAUSE_S)
                continue

            taste = _zu_taste(name)
            _controller.press(taste)
            log.debug("Taste gedrueckt: %r", name)
            time.sleep(_PAUSE_S)
            _controller.release(taste)
            log.debug("Taste losgelassen: %r", name)
            time.sleep(_PAUSE_S)
    finally:
        # Sicherheitsnetz: laesst jede noch offen gehaltene Taste los, auch
        # wenn mittendrin ein Fehler auftrat - sonst bliebe z.B. Strg
        # dauerhaft gedrueckt haengen.
        for taste in gehalten.values():
            _controller.release(taste)

    log.info("Tasten ausgeloest: %s", taste_sequenz)
