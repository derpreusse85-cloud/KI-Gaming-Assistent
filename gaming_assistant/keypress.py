"""Simuliert eine Tastensequenz im aktiven Fenster (dem Spiel) per pynput.

Wichtige Design-Entscheidung (siehe Implementierungsplan): die "taste"-Liste
im Profil ist IMMER eine Sequenz von Tipp-Vorgaengen (Druecken+Loslassen
nacheinander), niemals eine gleichzeitig gehaltene Tastenkombination. Bei
Helldivers 2 wird waehrend der ganzen Sequenz zusaetzlich eine Taste gehalten
(Standard: Strg) - das ist die optionale "halte_taste".

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


def ausloesen(taste_sequenz: list[str], halte_taste: str | None = None) -> None:
    """Tippt die Tasten der Sequenz nacheinander, waehrend halte_taste gehalten wird.

    Ablauf bei z.B. taste=["S","A","S","W","D"], halte_taste="ctrl":
    Strg druecken (halten) -> S tippen -> A tippen -> ... -> Strg loslassen.
    """
    halte_key = _zu_taste(halte_taste) if halte_taste else None

    if halte_key is not None:
        _controller.press(halte_key)
        time.sleep(_PAUSE_S)

    try:
        for name in taste_sequenz:
            taste = _zu_taste(name)
            _controller.press(taste)
            time.sleep(_PAUSE_S)
            _controller.release(taste)
            time.sleep(_PAUSE_S)
    finally:
        # "finally" stellt sicher, dass die Halte-Taste auch dann losgelassen
        # wird, wenn beim Tippen ein Fehler auftritt - sonst bliebe z.B. Strg
        # dauerhaft gedrueckt haengen.
        if halte_key is not None:
            _controller.release(halte_key)

    log.info("Tasten ausgeloest: %s%s", f"[{halte_taste}]+" if halte_taste else "", taste_sequenz)
