"""Logging mit Ringpuffer und einem einfachen Tkinter-Fenster zur Anzeige.

1:1 als Vorlage aus dem Diktier-Tool uebernommen (common/logbuf.py) - diese
Logik ist unabhaengig vom eigentlichen Diktier-/Gaming-Zweck.

Python-Hinweis: pystray blockiert mit icon.run() den Hauptthread der
Anwendung. Das Log-Fenster (Tkinter) braucht deshalb einen eigenen Thread mit
eigener Tk-Instanz - alle Tk-Aufrufe passieren ausschliesslich dort, sonst
gibt es Abstuerze durch fensterfremde Threads.
"""

from __future__ import annotations

import gc
import logging
import threading
from collections import deque
from typing import Callable

_FORMAT = "%(asctime)s  %(levelname)-7s %(name)-14s %(message)s"
_DATEFMT = "%H:%M:%S"


class RingHandler(logging.Handler):
    """Haelt die letzten N formatierten Logzeilen im Speicher (ein "deque" ist
    eine Liste, die beim Ueberschreiten von maxlen automatisch die aeltesten
    Eintraege verwirft)."""

    def __init__(self, kapazitaet: int = 500) -> None:
        super().__init__()
        self.zeilen: deque[str] = deque(maxlen=kapazitaet)
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            zeile = self.format(record)
        except Exception:  # Logging darf die Anwendung nie zum Absturz bringen
            return
        with self._lock:
            self.zeilen.append(zeile)

    def snapshot(self) -> list[str]:
        with self._lock:
            return list(self.zeilen)


_ring: RingHandler | None = None


def setup(level: str = "INFO", ring_groesse: int = 500) -> RingHandler:
    """Konfiguriert das Root-Logging mit Ringpuffer und Konsolenausgabe."""
    global _ring
    if _ring is not None:
        return _ring

    formatter = logging.Formatter(_FORMAT, datefmt=_DATEFMT)
    _ring = RingHandler(ring_groesse)
    _ring.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(getattr(logging, str(level).upper(), logging.INFO))
    root.addHandler(_ring)

    import sys

    if sys.stderr is not None:
        konsole = logging.StreamHandler()
        konsole.setFormatter(formatter)
        root.addHandler(konsole)

    return _ring


def get_ring() -> RingHandler:
    return _ring if _ring is not None else setup()


_fenster_offen = threading.Event()


def fenster_zeigen(titel: str, status_fn: Callable[[], str] | None = None) -> None:
    """Oeffnet das Logfenster (idempotent - ein zweiter Aufruf tut nichts)."""
    if _fenster_offen.is_set():
        return
    _fenster_offen.set()
    threading.Thread(target=_fenster_ausfuehren, args=(titel, status_fn), daemon=True).start()


def _fenster_ausfuehren(titel: str, status_fn: Callable[[], str] | None) -> None:
    """Duenne Huelle um _fenster: raeumt Tk-Objekte im selben Thread ab, in dem
    sie erzeugt wurden (siehe Modulkommentar oben)."""
    try:
        _fenster(titel, status_fn)
    except Exception as exc:  # pragma: no cover
        logging.getLogger("logbuf").warning("Logfenster fehlgeschlagen: %s", exc)
    finally:
        _fenster_offen.clear()
        gc.collect()


def _fenster(titel: str, status_fn: Callable[[], str] | None) -> None:
    try:
        import tkinter as tk
        from tkinter import scrolledtext
    except Exception:  # pragma: no cover - Tk fehlt in manchen Python-Installationen
        logging.getLogger("logbuf").warning("Tkinter nicht verfuegbar, Logfenster entfaellt")
        return

    ring = get_ring()

    root = tk.Tk()
    root.title(titel)
    root.geometry("900x520")

    status_label = None
    if status_fn is not None:
        status_label = tk.Label(root, text="", anchor="w", padx=8, pady=4)
        status_label.pack(fill="x")

    text = scrolledtext.ScrolledText(root, wrap="none", font=("Consolas", 9))
    text.pack(fill="both", expand=True)

    zustand = {"anzahl": 0, "autoscroll": True}

    def scroll_umschalten() -> None:
        zustand["autoscroll"] = not zustand["autoscroll"]
        haken = "x" if zustand["autoscroll"] else " "
        scroll_btn.config(text=f"[{haken}] Automatisch scrollen")

    scroll_btn = tk.Button(root, text="[x] Automatisch scrollen", command=scroll_umschalten,
                            relief="flat", anchor="w")
    scroll_btn.pack(anchor="w", fill="x")

    def aktualisieren() -> None:
        zeilen = ring.snapshot()
        if len(zeilen) != zustand["anzahl"]:
            zustand["anzahl"] = len(zeilen)
            text.configure(state="normal")
            text.delete("1.0", "end")
            text.insert("end", "\n".join(zeilen))
            text.configure(state="disabled")
            if zustand["autoscroll"]:
                text.see("end")
        if status_label is not None and status_fn is not None:
            try:
                status_label.config(text=status_fn())
            except Exception:
                pass
        root.after(500, aktualisieren)

    def schliessen() -> None:
        _fenster_offen.clear()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", schliessen)
    aktualisieren()
    root.mainloop()
