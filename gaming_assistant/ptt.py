"""Push-to-talk-Ausloeser ueber pynput - Tastatur und Maus einheitlich.

Uebernommen als Vorlage aus dem Diktier-Tool (client/ptt.py), aber vereinfacht:
das Diktier-Tool beobachtet zusaetzlich JEDE fremde Tastatur-/Mauseingabe
waehrend einer Session ("dirty"-Erkennung), weil es aktiv in ein Textfeld
tippt und das durcheinanderbringen wuerde. Der Gaming-Assistent tippt nur kurz
eine feste Tastensequenz und beobachtet sonst nichts - die dirty-Erkennung
und der EchoGuard aus dem Diktier-Tool werden deshalb nicht gebraucht.

Die "naechste Taste abfangen"-Logik (fuer den Tray-Menuepunkt "Push-to-talk
festlegen ...", siehe ptt_dialog.py) wird dagegen 1:1 uebernommen: derselbe,
bereits laufende Listener faengt einmalig den naechsten Tastendruck ab, statt
dass ein zweiter Hook dafuer gestartet wird.

Konfiguration (Abschnitt "ptt" in config.json):
    {"type": "keyboard", "key": "f9"}          Sondertaste aus pynput.keyboard.Key
    {"type": "keyboard", "key": "y"}           einzelnes Zeichen
    {"type": "mouse",    "button": "x2"}       Maustaste 5 (x1 = Maustaste 4)

Python-Hinweis: pynput.keyboard.Listener/mouse.Listener starten je einen
eigenen Hintergrund-Thread, der system-weit (nicht nur in unserem eigenen
Fenster) auf Tastatur-/Mausereignisse lauscht - das ist noetig, damit
Push-to-talk auch funktioniert, waehrend das Spiel im Vordergrund ist.
"""

from __future__ import annotations

import logging
from typing import Callable

from pynput import keyboard, mouse

log = logging.getLogger("ptt")


class PTTConfigError(ValueError):
    pass


def trigger_parsen(ptt_cfg: dict):
    """Liest die ptt-Config und liefert (art, ziel) mit art in {"keyboard", "mouse"}."""
    art = str(ptt_cfg.get("type", "")).lower()
    if art == "mouse":
        name = str(ptt_cfg.get("button", "")).lower()
        try:
            return "mouse", mouse.Button[name]
        except KeyError:
            gueltig = ", ".join(b.name for b in mouse.Button if b.name != "unknown")
            raise PTTConfigError(f"Unbekannte Maustaste {name!r}. Moeglich: {gueltig}") from None
    if art == "keyboard":
        name = str(ptt_cfg.get("key", ""))
        if len(name) == 1:
            return "keyboard", keyboard.KeyCode.from_char(name.lower())
        try:
            return "keyboard", keyboard.Key[name.lower()]
        except KeyError:
            raise PTTConfigError(
                f"Unbekannte Taste {name!r}. Beispiele: f9, scroll_lock, ctrl_r, pause"
            ) from None
    raise PTTConfigError(f"ptt.type muss 'keyboard' oder 'mouse' sein, nicht {art!r}")


_HUEBSCHE_NAMEN = {
    "x1": "Maustaste 4", "x2": "Maustaste 5", "middle": "Mittlere Maustaste",
    "left": "Linke Maustaste", "right": "Rechte Maustaste",
}


def zu_config(art: str, ziel) -> dict | None:
    """Umkehrung von trigger_parsen: pynput-Objekt -> Config-Eintrag.

    Liefert None, wenn sich die Taste nicht sinnvoll abbilden laesst (z.B.
    eine Sondertaste ohne Zeichen und ohne bekannten Namen).
    """
    if art == "mouse":
        return {"type": "mouse", "button": ziel.name}
    if isinstance(ziel, keyboard.Key):
        return {"type": "keyboard", "key": ziel.name}
    zeichen = getattr(ziel, "char", None)
    if zeichen:
        return {"type": "keyboard", "key": zeichen.lower()}
    return None


def beschreiben(ptt_cfg: dict) -> str:
    """Menschenlesbare Kurzbeschreibung des Ausloesers, fuer Tray/Dialog."""
    art = str(ptt_cfg.get("type", "")).lower()
    if art == "mouse":
        name = str(ptt_cfg.get("button", "")).lower()
        return _HUEBSCHE_NAMEN.get(name, f"Maustaste {name}")
    return str(ptt_cfg.get("key", "?")).upper()


class PTTListener:
    def __init__(
        self,
        ptt_cfg: dict,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
    ) -> None:
        self.art, self.ziel = trigger_parsen(ptt_cfg)
        self._on_press = on_press
        self._on_release = on_release
        # Windows wiederholt eine gehaltene Taste als Dauerfeuer von
        # Press-Events - _gehalten verhindert, dass on_press mehrfach feuert.
        self._gehalten = False
        self._kb: keyboard.Listener | None = None
        self._maus: mouse.Listener | None = None
        # Ist gesetzt, waehrend der Tray-Dialog "Push-to-talk festlegen ..."
        # offen ist - dann faengt der naechste Tastendruck/Mausklick den neuen
        # Ausloeser ab, statt die normale PTT-Logik auszufuehren.
        self._abfangen: Callable[[dict | None], None] | None = None

    # -- Ausloeser zur Laufzeit aendern --------------------------------------

    def trigger_setzen(self, ptt_cfg: dict) -> None:
        """Uebernimmt einen neuen Ausloeser ohne Neustart des Listeners."""
        self.art, self.ziel = trigger_parsen(ptt_cfg)
        self._gehalten = False
        log.info("Push-to-talk umgestellt auf: %s", beschreiben(ptt_cfg))

    def abfangen_starten(self, callback: Callable[[dict | None], None]) -> None:
        """Faengt den naechsten Tastendruck/Mausklick ab und meldet ihn an
        ``callback`` als Config-Eintrag (oder None, wenn er sich nicht
        sinnvoll abbilden liess). Die linke Maustaste bleibt ausgenommen -
        sonst liesse sich der Dialog nicht mehr per Klick bedienen."""
        self._abfangen = callback

    def abfangen_abbrechen(self) -> None:
        self._abfangen = None

    @property
    def faengt_ab(self) -> bool:
        return self._abfangen is not None

    def _abfangen_liefern(self, art: str, ziel) -> None:
        callback, self._abfangen = self._abfangen, None
        try:
            callback(zu_config(art, ziel))
        except Exception as exc:  # pragma: no cover
            log.warning("Fehler beim Uebernehmen des neuen Ausloesers: %s", exc)

    def _taste_passt(self, taste) -> bool:
        if self.art != "keyboard":
            return False
        if isinstance(self.ziel, keyboard.Key):
            return taste == self.ziel
        # Bei einem einzelnen Zeichen (KeyCode) ueber .char vergleichen, damit
        # es auch bei unterschiedlichen Tastaturlayouts zuverlaessig passt.
        return getattr(taste, "char", None) == getattr(self.ziel, "char", None)

    def _bei_tastendruck(self, taste) -> None:
        if self._abfangen is not None:
            self._abfangen_liefern("keyboard", taste)
            return
        if self._taste_passt(taste) and not self._gehalten:
            self._gehalten = True
            self._on_press()

    def _bei_tastenloslassen(self, taste) -> None:
        if self._taste_passt(taste) and self._gehalten:
            self._gehalten = False
            self._on_release()

    def _bei_mausklick(self, _x, _y, taste, gedrueckt) -> None:
        if self._abfangen is not None:
            # Linke Taste ausgenommen: mit ihr wird der Dialog bedient.
            if gedrueckt and taste != mouse.Button.left:
                self._abfangen_liefern("mouse", taste)
            return
        if self.art != "mouse" or taste != self.ziel:
            return
        if gedrueckt and not self._gehalten:
            self._gehalten = True
            self._on_press()
        elif not gedrueckt and self._gehalten:
            self._gehalten = False
            self._on_release()

    def start(self) -> None:
        self._kb = keyboard.Listener(
            on_press=self._bei_tastendruck, on_release=self._bei_tastenloslassen
        )
        self._kb.start()
        self._maus = mouse.Listener(on_click=self._bei_mausklick)
        self._maus.start()
        log.info("Push-to-talk aktiv auf: %s", self.ziel)

    def stop(self) -> None:
        for listener in (self._kb, self._maus):
            if listener is not None:
                try:
                    listener.stop()
                except Exception:
                    pass
        self._kb = self._maus = None
