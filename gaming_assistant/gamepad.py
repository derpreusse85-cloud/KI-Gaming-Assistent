"""Push-to-talk-Ausloeser ueber Controller-/HOTAS-Knoepfe, per pywinusb (HID).

Ergaenzt ptt.py (Tastatur/Maus ueber pynput) um eine dritte Quelle. Warum eine
andere Bibliothek als pynput noetig ist: pynput kann nur Tastatur und Maus,
nicht die vielen Knoepfe eines Gamepads oder HOTAS (Joystick/Schubregler-
Kombi, z.B. fuer Elite Dangerous). Die naheliegende Bibliothek dafuer waere
pygame gewesen, laesst sich auf der hier verwendeten Python-3.14-Umgebung aber
nicht installieren (Build-Fehler, siehe Projekt-Notizen) - deshalb pywinusb:
spricht direkt mit Windows' eigenem HID-Treiber (kein Kompilieren, keine
zusaetzliche DLL, kein Treiber-Tausch noetig - Controller/HOTAS melden sich
bei Windows ohnehin schon als Standard-HID-Geraete).

Python-Hinweis: ein Controller meldet sich oft nicht als EIN HID-Geraet,
sondern als mehrere "Interfaces" unter derselben Vendor-/Product-ID (z.B.
eines fuer die eigentlichen Knoepfe, eines fuer Medientasten, eines fuer
Zusatzfunktionen wie Akkustand). Das richtige Interface wird daran erkannt,
dass es Usages auf der HID-"Button"-Page (0x09) hat - das ist der Bereich im
HID-Standard, der fuer einfache Ein/Aus-Knoepfe reserviert ist.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable

import pywinusb.hid as hid

log = logging.getLogger("gamepad")

_BUTTON_PAGE = 0x09


def _button_usages(geraet: hid.HidDevice) -> list[int]:
    """Liefert die Button-Nummern (1, 2, 3, ...), die dieses Geraet ueber
    seine Input-Reports meldet - leer, wenn es keine "echten" Knoepfe hat
    (z.B. ein Interface, das nur Medientasten oder Akkustand meldet)."""
    nummern = []
    for report in geraet.find_input_reports():
        for full_usage_id in report.keys():
            page = full_usage_id >> 16
            usage = full_usage_id & 0xFFFF
            if page == _BUTTON_PAGE:
                nummern.append(usage)
    return sorted(set(nummern))


def _passende_interfaces() -> list[hid.HidDevice]:
    """Alle HID-Interfaces, die mindestens einen Knopf melden (siehe
    _button_usages) - unabhaengig vom Hersteller/Modell."""
    treffer = []
    for geraet in hid.HidDeviceFilter().get_devices():
        try:
            geraet.open()
            hat_knoepfe = bool(_button_usages(geraet))
        except Exception as exc:
            log.debug("HID-Geraet nicht abfragbar: %s", exc)
            hat_knoepfe = False
        finally:
            geraet.close()
        if hat_knoepfe:
            treffer.append(geraet)
    return treffer


def geraete_auflisten() -> list[dict]:
    """(Vendor-ID, Product-ID, Name, Anzahl Knoepfe) aller erkannten
    Controller/HOTAS-Interfaces - fuer die Anzeige im Tray-Dialog."""
    ergebnis = []
    try:
        for geraet in _passende_interfaces():
            geraet.open()
            try:
                anzahl = len(_button_usages(geraet))
            finally:
                geraet.close()
            ergebnis.append({
                "vendor_id": geraet.vendor_id,
                "product_id": geraet.product_id,
                "name": geraet.product_name,
                "button_anzahl": anzahl,
            })
    except Exception as exc:
        log.warning("Controller-Liste nicht lesbar: %s", exc)
    return ergebnis


def _geraet_finden(vendor_id: int, product_id: int) -> hid.HidDevice | None:
    """Erstes passendes, knopf-fuehrendes Interface fuer diese Vendor-/
    Product-ID. Bei mehreren baugleichen Controllern (gleiche IDs) gewinnt der
    erste Treffer - eine echte, eindeutige Unterscheidung ist ueber HID meist
    nicht moeglich, da die meisten Controller keine Seriennummer melden."""
    for geraet in hid.HidDeviceFilter(vendor_id=vendor_id, product_id=product_id).get_devices():
        try:
            geraet.open()
            hat_knoepfe = bool(_button_usages(geraet))
        except Exception:
            hat_knoepfe = False
        finally:
            geraet.close()
        if hat_knoepfe:
            return geraet
    return None


class GamepadListener:
    """Ueberwacht GENAU einen Knopf auf GENAU einem Controller/HOTAS - das
    Gegenstueck zu pynputs Tastatur-/Maus-Listener in ptt.py, nur HID-basiert
    statt ueber einen systemweiten Eingabe-Hook."""

    def __init__(
        self,
        vendor_id: int,
        product_id: int,
        button: int,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
    ) -> None:
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.button = button
        self._on_press = on_press
        self._on_release = on_release
        self._geraet: hid.HidDevice | None = None
        # None = Ausgangszustand noch nicht bekannt. Wichtig fuer den Fall,
        # dass der Knopf im selben Moment, in dem dieser Listener startet
        # (z.B. direkt nach dem Festlegen im Tray-Dialog: derselbe Knopfdruck,
        # mit dem der Ausloeser gewaehlt wurde, kann beim Start noch physisch
        # gehalten sein), bereits gedrueckt ist - der erste Report legt dann
        # nur den Ausgangszustand fest, statt sofort ein (zu kurzes,
        # ungewolltes) Press-Release-Paar auszuloesen.
        self._gehalten: bool | None = None
        # Nur gesetzt, wenn DIESER Listener selbst on_press ausgeloest hat -
        # verhindert ein verwaistes on_release, falls der Ausgangszustand
        # (s.o.) bereits "gedrueckt" war.
        self._press_ausgeloest = False

    def start(self) -> None:
        geraet = _geraet_finden(self.vendor_id, self.product_id)
        if geraet is None:
            log.warning(
                "Controller fuer Push-to-talk nicht gefunden (Vendor %s, Product %s) - "
                "kein Ausloeser aktiv, solange er nicht angeschlossen ist.",
                self.vendor_id, self.product_id,
            )
            return
        try:
            geraet.open()
            geraet.set_raw_data_handler(self._bei_report)
            self._geraet = geraet
            log.info("Push-to-talk aktiv auf Controller-Knopf %d (%s)", self.button, geraet.product_name)
        except Exception as exc:
            log.warning("Controller konnte nicht geoeffnet werden: %s", exc)
            self._geraet = None

    def stop(self) -> None:
        if self._geraet is not None:
            try:
                self._geraet.close()
            except Exception:
                pass
        self._geraet = None
        self._gehalten = None
        self._press_ausgeloest = False

    def _bei_report(self, daten: list[int]) -> None:
        # pywinusb liefert hier die rohen Report-Bytes, nicht die geparsten
        # Usages - deshalb ueber das zuletzt geoeffnete Geraet-Objekt den
        # zugehoerigen Report samt Wert der gesuchten Button-Usage erfragen.
        geraet = self._geraet
        if geraet is None:
            return
        gedrueckt = self._button_wert(geraet, daten)
        if gedrueckt is None:
            return
        if self._gehalten is None:
            # Allererster Report seit dem Start: nur Ausgangszustand merken,
            # siehe Kommentar in __init__.
            self._gehalten = gedrueckt
            return
        if gedrueckt and not self._gehalten:
            self._gehalten = True
            self._press_ausgeloest = True
            self._on_press()
        elif not gedrueckt and self._gehalten:
            self._gehalten = False
            if self._press_ausgeloest:
                self._press_ausgeloest = False
                self._on_release()

    def _button_wert(self, geraet: hid.HidDevice, daten: list[int]) -> bool | None:
        report_id = daten[0] if daten else 0
        for report in geraet.find_input_reports():
            if report.report_id != report_id:
                continue
            # set_raw_data() laesst pywinusb die rohen Bytes ueber die
            # Windows-HID-API in die einzelnen Usage-Werte zerlegen - ohne
            # diesen Aufruf blieben report[...].value auf ihrem letzten
            # (evtl. veralteten) Stand stehen.
            report.set_raw_data(daten)
            voller_usage_id = (_BUTTON_PAGE << 16) | self.button
            try:
                return bool(report[voller_usage_id].value)
            except KeyError:
                return None
        return None


class AbfangListener:
    """Fuer den Tray-Dialog "Push-to-talk festlegen ...": oeffnet zeitweise
    ALLE erkannten Controller/HOTAS-Interfaces und meldet den ersten
    Knopfdruck, egal auf welchem Geraet. Laeuft nur waehrend der Dialog offen
    ist, nicht dauerhaft im Hintergrund - so blockiert es kein Geraet, das
    das Spiel selbst gerade braucht, wenn der Dialog nicht offen ist."""

    def __init__(self, callback: Callable[[int, int, int, str], None]) -> None:
        # callback(vendor_id, product_id, button, name)
        self._callback = callback
        self._geraete: list[hid.HidDevice] = []
        self._gemeldet = threading.Event()

    def start(self) -> None:
        for geraet in _passende_interfaces():
            try:
                geraet.open()
                geraet.set_raw_data_handler(self._bei_report_erzeugen(geraet))
                self._geraete.append(geraet)
            except Exception as exc:
                log.debug("Controller %s konnte nicht zum Abfangen geoeffnet werden: %s", geraet, exc)

    def stop(self) -> None:
        for geraet in self._geraete:
            try:
                geraet.close()
            except Exception:
                pass
        self._geraete = []

    def _bei_report_erzeugen(self, geraet: hid.HidDevice) -> Callable[[list[int]], None]:
        def handler(daten: list[int]) -> None:
            if self._gemeldet.is_set():
                return
            report_id = daten[0] if daten else 0
            for report in geraet.find_input_reports():
                if report.report_id != report_id:
                    continue
                report.set_raw_data(daten)
                for full_usage_id, eintrag in report.items():
                    if (full_usage_id >> 16) != _BUTTON_PAGE:
                        continue
                    if eintrag.value:
                        self._gemeldet.set()
                        button = full_usage_id & 0xFFFF
                        self._callback(geraet.vendor_id, geraet.product_id, button, geraet.product_name)
                        return

        return handler
