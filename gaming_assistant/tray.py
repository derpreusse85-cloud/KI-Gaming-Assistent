"""Tray-Icon mit Profil-Auswahl-Menue und PTT-Einstellung.

Uebernommen als Vorlage aus dem Diktier-Tool (client/tray.py), auf das
Wesentliche fuer diesen Anwendungsfall reduziert: hier gibt es keine
Modell-/Mikrofon-Untermenues (Whisper-Modell ist fest vorgegeben), nur die
Auswahl des aktiven Spielprofils und der Push-to-talk-Taste.

Python-Hinweis: pystray.Menu(...) baut ein Kontextmenue fuer das Tray-Icon.
"radio=True" bei einem MenuItem sorgt dafuer, dass genau ein Eintrag der
Gruppe als "aktiv" markiert erscheint (wie Radiobuttons in einem Dialog).
"""

from __future__ import annotations

import logging
from typing import Callable

import pystray

from gaming_assistant import icons, logbuf

log = logging.getLogger("tray")

TITEL = "Gaming-Assistent"


class Tray:
    def __init__(
        self,
        status_fn: Callable[[], str],
        profil_liste_fn: Callable[[], list[str]],
        aktives_profil_fn: Callable[[], str],
        on_profil_wechsel: Callable[[str], None],
        on_beenden: Callable[[], None],
        ptt_label: str,
        on_ptt_aendern: Callable[[], None],
    ) -> None:
        self.status_fn = status_fn
        self.profil_liste_fn = profil_liste_fn
        self.aktives_profil_fn = aktives_profil_fn
        self.on_profil_wechsel = on_profil_wechsel
        self.on_beenden = on_beenden
        self.ptt_label = ptt_label
        self.on_ptt_aendern = on_ptt_aendern
        self._zustand = "startet"
        self.icon = pystray.Icon(
            "gaming_assistant",
            icons.icon("startet"),
            f"{TITEL} - startet ...",
            menu=self._menu_bauen(),
        )

    def _menu_bauen(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(f"Push-to-talk: {self.ptt_label}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Status/Log anzeigen", self._log_anzeigen, default=True),
            pystray.MenuItem("Profil", self._profil_menu()),
            pystray.MenuItem("Push-to-talk festlegen ...", self._ptt_aendern),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Beenden", self._beenden),
        )

    def ptt_label_setzen(self, label: str) -> None:
        """Nach dem Festlegen eines neuen Ausloesers aufrufen - aktualisiert
        die Anzeige im Menue."""
        self.ptt_label = label
        self._menu_aktualisieren()

    def _ptt_aendern(self, *_args) -> None:
        self.on_ptt_aendern()

    def _profil_menu(self) -> pystray.Menu:
        namen = self.profil_liste_fn()
        if not namen:
            return pystray.Menu(pystray.MenuItem("keine Profile gefunden", None, enabled=False))
        eintraege = []
        for name in namen:
            eintraege.append(
                pystray.MenuItem(
                    name,
                    self._profil_auswahl_erzeugen(name),
                    radio=True,
                    checked=lambda _item, n=name: self.aktives_profil_fn() == n,
                )
            )
        return pystray.Menu(*eintraege)

    def _profil_auswahl_erzeugen(self, name: str) -> Callable:
        def auswaehlen(*_args) -> None:
            if name == self.aktives_profil_fn():
                return
            log.info("Profil ueber Tray gewaehlt: %s", name)
            self.on_profil_wechsel(name)
            self._menu_aktualisieren()

        return auswaehlen

    def _menu_aktualisieren(self, *_args) -> None:
        self.icon.menu = self._menu_bauen()
        self.icon.update_menu()

    def zustand_setzen(self, zustand: str) -> None:
        """zustand: startet | bereit | aufnahme | fehler"""
        if zustand != self._zustand:
            self._zustand = zustand
            self.aktualisieren()

    def aktualisieren(self) -> None:
        try:
            self.icon.icon = icons.icon(self._zustand)
            self.icon.title = f"{TITEL} - {self.status_fn()}"
        except Exception:  # pragma: no cover
            pass

    def _log_anzeigen(self, *_args) -> None:
        logbuf.fenster_zeigen(f"{TITEL} - Log", self.status_fn)

    def _beenden(self, *_args) -> None:
        log.info("Beenden ueber Tray-Menue angefordert")
        try:
            self.on_beenden()
        finally:
            self.icon.stop()

    def run(self) -> None:
        self.icon.run()
