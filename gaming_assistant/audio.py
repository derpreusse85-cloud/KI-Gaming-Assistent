"""Mikrofon-Aufnahme ueber sounddevice, gesammelt in einem einzigen Puffer.

Uebernommen als Vorlage aus dem Diktier-Tool (client/audio.py), aber
vereinfacht: dort werden Audio-Haeppchen (Chunks) laufend per WebSocket an den
Server geschickt (Streaming), hier reicht es, sie waehrend der Aufnahme in
einem "bytearray" zu sammeln und das Ganze erst beim Loslassen der
Push-to-talk-Taste an Whisper zu schicken (siehe Gaming_assistent.md,
Abschnitt "Unterschied zur Diktier-Pipeline": kein rollierendes Fenster
noetig).

Geliefert wird immer rohes int16-Mono-PCM mit 16 kHz - das Format, das
whisper.cpp erwartet. Kann das Mikrofon 16 kHz nicht direkt, wird mit der
Geraete-Standardrate aufgenommen und heruntergerechnet.
"""

from __future__ import annotations

import logging

import numpy as np
import sounddevice as sd

log = logging.getLogger("audio")

ZIEL_RATE = 16_000
CHUNK_MS = 100


def eingabegeraete_auflisten() -> list[tuple[int, str]]:
    """(Index, Beschriftung) aller Mikrofon-Eingabegeraete."""
    geraete = []
    try:
        hostapis = sd.query_hostapis()
        for index, dev in enumerate(sd.query_devices()):
            if dev.get("max_input_channels", 0) < 1:
                continue
            api = hostapis[dev["hostapi"]]["name"] if dev.get("hostapi") is not None else "?"
            geraete.append((index, f"{dev['name']}  [{api}]"))
    except Exception as exc:
        log.warning("Geraeteliste nicht lesbar: %s", exc)
    return geraete


def _int16_umrechnen(daten: np.ndarray, quell_rate: int) -> np.ndarray:
    """Rechnet Samples von quell_rate auf ZIEL_RATE (16 kHz) herunter."""
    if quell_rate == ZIEL_RATE:
        return daten
    if quell_rate % ZIEL_RATE == 0:
        # Ganzzahliges Verhaeltnis (z.B. 48000 -> 16000): Mittelwert je Gruppe
        # wirkt zugleich als einfacher Tiefpass gegen Aliasing-Artefakte.
        faktor = quell_rate // ZIEL_RATE
        nutzbar = (len(daten) // faktor) * faktor
        if nutzbar == 0:
            return daten[:0]
        return daten[:nutzbar].astype(np.float32).reshape(-1, faktor).mean(axis=1).astype(np.int16)
    n_out = int(round(len(daten) * ZIEL_RATE / quell_rate))
    if n_out <= 0:
        return daten[:0]
    positionen = np.linspace(0, len(daten) - 1, n_out)
    return np.interp(positionen, np.arange(len(daten)), daten.astype(np.float32)).astype(np.int16)


class AudioCapture:
    """Oeffnet den Mikrofon-Stream beim Druecken von PTT, sammelt Samples,
    und liefert beim Loslassen die komplette Aufnahme als ein einziges bytes-Objekt.
    """

    def __init__(self) -> None:
        self.device: int | None = None
        self._stream: sd.InputStream | None = None
        self._rate = ZIEL_RATE
        # bytearray statt bytes: laesst sich effizient per .extend() erweitern,
        # ohne bei jedem Chunk eine komplette Kopie anzulegen.
        self._puffer = bytearray()

    def set_device(self, index: int | None) -> None:
        self.device = index

    def _callback(self, indata, _frames, _time, status) -> None:
        """Wird von sounddevice in einem eigenen Audio-Thread aufgerufen,
        sobald ein neues Haeppchen Mikrofondaten vorliegt."""
        if status:
            log.debug("Audio-Status: %s", status)
        samples = indata[:, 0] if indata.ndim > 1 else indata
        if self._rate != ZIEL_RATE:
            samples = _int16_umrechnen(np.asarray(samples), self._rate)
        self._puffer.extend(np.ascontiguousarray(samples).tobytes())

    def start(self) -> bool:
        """Beginnt die Aufnahme. Liefert False, wenn kein Mikrofon geoeffnet werden konnte."""
        if self._stream is not None:
            return True
        self._puffer = bytearray()
        for rate in self._kandidaten_raten():
            try:
                self._stream = sd.InputStream(
                    samplerate=rate,
                    channels=1,
                    dtype="int16",
                    blocksize=int(rate * CHUNK_MS / 1000),
                    device=self.device,
                    callback=self._callback,
                )
                self._stream.start()
                self._rate = rate
                if rate != ZIEL_RATE:
                    log.info("Aufnahme mit %d Hz, rechne auf %d Hz herunter", rate, ZIEL_RATE)
                return True
            except Exception as exc:
                log.debug("Aufnahme mit %d Hz nicht moeglich: %s", rate, exc)
                self._stream = None
        log.error("Mikrofon konnte nicht geoeffnet werden (Geraet %s)", self.device)
        return False

    def _kandidaten_raten(self) -> list[int]:
        raten = [ZIEL_RATE]
        try:
            info = sd.query_devices(self.device if self.device is not None else sd.default.device[0])
            nativ = int(info["default_samplerate"])
            if nativ != ZIEL_RATE:
                raten.append(nativ)
        except Exception:
            pass
        for fallback in (48_000, 44_100):
            if fallback not in raten:
                raten.append(fallback)
        return raten

    def stop(self) -> bytes:
        """Beendet die Aufnahme und liefert die gesammelten PCM-Samples."""
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception as exc:  # pragma: no cover
                log.warning("Fehler beim Schliessen des Audio-Streams: %s", exc)
        return bytes(self._puffer)
