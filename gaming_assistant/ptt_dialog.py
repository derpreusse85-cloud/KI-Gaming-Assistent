"""Kleiner Dialog zum Festlegen der Push-to-talk-Taste.

Uebernommen als Vorlage aus dem Diktier-Tool (client/ptt_dialog.py). Der
Dialog laeuft wie das Logfenster (logbuf.py) in einem eigenen Thread mit
eigener Tk-Instanz, weil pystray den Hauptthread belegt (icon.run()
blockiert). Das Abfangen des Tastendrucks selbst uebernimmt der bereits
laufende PTTListener (ptt.py) - es wird kein zweiter Tastatur-/Maus-Hook
gestartet.
"""

from __future__ import annotations

import gc
import logging
import threading
from typing import Callable

from gaming_assistant.ptt import PTTListener, beschreiben

log = logging.getLogger("ptt_dialog")

# Kurze Sperre, damit der Klick, mit dem der Tray-Menuepunkt bedient wurde,
# nicht versehentlich selbst schon als neuer Ausloeser eingefangen wird.
_SCHARF_VERZOEGERUNG_MS = 500

_offen = threading.Event()


def zeigen(ptt_listener: PTTListener, aktuell: dict, bei_auswahl: Callable[[dict], None]) -> None:
    """Oeffnet den Dialog (idempotent - ein zweiter Aufruf tut nichts, solange
    der erste noch offen ist). bei_auswahl laeuft im Dialog-Thread."""
    if _offen.is_set():
        return
    _offen.set()
    threading.Thread(
        target=_ausfuehren, args=(ptt_listener, aktuell, bei_auswahl),
        daemon=True, name="ptt-dialog",
    ).start()


def _ausfuehren(ptt_listener: PTTListener, aktuell: dict, bei_auswahl: Callable[[dict], None]) -> None:
    """Duenne Huelle um _dialog: raeumt Tk-Objekte im selben Thread ab, in dem
    sie erzeugt wurden (siehe logbuf.py fuer die ausfuehrliche Begruendung)."""
    try:
        _dialog(ptt_listener, aktuell, bei_auswahl)
    except Exception as exc:  # pragma: no cover
        log.warning("Dialog fehlgeschlagen: %s", exc)
    finally:
        ptt_listener.abfangen_abbrechen()
        _offen.clear()
        gc.collect()


def _dialog(ptt_listener: PTTListener, aktuell: dict, bei_auswahl: Callable[[dict], None]) -> None:
    try:
        import tkinter as tk
    except Exception:  # pragma: no cover
        log.warning("Tkinter nicht verfuegbar - Ausloeser bitte direkt in config.json setzen")
        return

    ergebnis: dict = {}

    root = tk.Tk()
    root.title("Push-to-talk festlegen")
    root.geometry("420x210")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    tk.Label(root, text="Neue Push-to-talk-Taste", font=("Segoe UI", 12, "bold")).pack(pady=(18, 4))
    tk.Label(root, text=f"Aktuell: {beschreiben(aktuell)}", fg="#555").pack()

    # Bewusst kein tk.StringVar: dessen __del__ laeuft beim Aufraeumen im
    # Hauptthread und quittiert das mit "Tcl_AsyncDelete ... wrong thread".
    status = tk.Label(root, text="Moment ...", font=("Segoe UI", 10),
                       wraplength=380, justify="center")
    status.pack(pady=14)

    tk.Label(
        root,
        text="Tastatur oder Maustaste 4 / 5 / Mitte.\n"
             "Die linke Maustaste ist ausgenommen.",
        fg="#777", font=("Segoe UI", 8), justify="center",
    ).pack()

    def schliessen() -> None:
        ptt_listener.abfangen_abbrechen()
        _offen.clear()
        root.destroy()

    tk.Button(root, text="Abbrechen", command=schliessen, width=14).pack(pady=12)

    def uebernommen(cfg: dict | None) -> None:
        """Wird aus dem pynput-Thread aufgerufen (nicht dem Tk-Thread!) -
        deshalb hier nur den Zustand ablegen, statt direkt Tk-Widgets
        anzufassen. Die eigentliche Reaktion passiert in pruefen(), das
        Tk selbst per root.after() im richtigen Thread aufruft."""
        if cfg is None:
            ergebnis["fehler"] = True
        else:
            ergebnis["ptt"] = cfg

    def scharfschalten() -> None:
        status.config(text="Jetzt die gewuenschte Taste druecken ...")
        ptt_listener.abfangen_starten(uebernommen)

    def pruefen() -> None:
        if ergebnis.get("fehler"):
            ergebnis.pop("fehler")
            status.config(text="Diese Taste laesst sich nicht verwenden. Bitte eine andere.")
            ptt_listener.abfangen_starten(uebernommen)
        elif "ptt" in ergebnis:
            gewaehlt = ergebnis.pop("ptt")
            status.config(text=f"Uebernommen: {beschreiben(gewaehlt)}")
            try:
                bei_auswahl(gewaehlt)
            except Exception as exc:  # pragma: no cover
                log.warning("Ausloeser konnte nicht gespeichert werden: %s", exc)
            root.after(900, schliessen)
            return
        root.after(80, pruefen)

    root.protocol("WM_DELETE_WINDOW", schliessen)
    root.after(_SCHARF_VERZOEGERUNG_MS, scharfschalten)
    root.after(_SCHARF_VERZOEGERUNG_MS + 80, pruefen)
    root.mainloop()
