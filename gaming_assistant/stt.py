"""Einmalige Whisper-Transkription nach dem Loslassen der Push-to-talk-Taste.

Anders als beim Diktier-Tool (server/stt.py, dort als Vorlage genutzt) gibt es
hier KEIN rollierendes Fenster: ein Sprachbefehl ist kurz, eine einzelne
Transkription der kompletten Aufnahme reicht (siehe Gaming_assistent.md,
Abschnitt "Unterschied zur Diktier-Pipeline").

Python-Hinweis: "requests" ist eine Bibliothek fuer HTTP-Anfragen (wie ein
Browser-Aufruf, nur aus Python heraus). whisper-server ist selbst ein kleiner
lokaler Webserver; wir schicken ihm die Audiodatei per HTTP-POST.
"""

from __future__ import annotations

import io
import logging
import re
import wave

import requests

log = logging.getLogger("stt")

SAMPLE_RATE = 16_000
SAMPLE_WIDTH = 2  # int16 = 2 Bytes je Messwert

# Schwelle fuer whisper.cpps eigenes no_speech_prob je Segment. Bei kurzem oder
# leisem Audio halluziniert Whisper gerne feste Redewendungen aus den
# Trainingsdaten ("Thank you.") statt nichts auszugeben. 0.6 ist der Wert, den
# whisper.cpp selbst als Vorgabe verwendet (uebernommen aus dem Diktier-Tool).
_NO_SPEECH_THOLD = 0.6

# whisper.cpp markiert Nicht-Sprache in Klammern/Sternchen (z.B. "(Stille)").
# Bei Push-to-talk entsteht das haeufig durch Stille vor dem ersten Wort.
_NOISE_WOERTER = (
    "blank_audio|stille|silence|musik|music|applaus|applause|lachen|laughter|"
    "geraeusch|geräusch|noise|husten|räuspern|raeuspern|pause|inaudible|"
    "unverständlich|unverstaendlich|seufzen|atmen|breathing"
)
_ECKIGE_KLAMMERN = re.compile(r"\[[^\]]{0,40}\]")
_NOISE_KLAMMERN = re.compile(rf"\((?:\s*{_NOISE_WOERTER}\s*)\)", re.IGNORECASE)
_NOISE_STERNE = re.compile(rf"\*(?:\s*{_NOISE_WOERTER}\s*)\*", re.IGNORECASE)
_WHITESPACE = re.compile(r"\s+")


def _halluzinierte_segmente_verwerfen(segmente: list[dict]) -> list[dict]:
    """Verwirft Segmente, die Whisper selbst als vermutlich Nicht-Sprache einstuft."""
    return [s for s in segmente if float(s.get("no_speech_prob", 0.0)) < _NO_SPEECH_THOLD]


def text_bereinigen(text: str) -> str:
    """Entfernt Nicht-Sprache-Marker und ueberfluessige Leerzeichen."""
    text = _ECKIGE_KLAMMERN.sub(" ", text)
    text = _NOISE_KLAMMERN.sub(" ", text)
    text = _NOISE_STERNE.sub(" ", text)
    text = _WHITESPACE.sub(" ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text.strip()


def pcm_zu_wav(pcm: bytes) -> bytes:
    """Verpackt rohe int16-Mono-Samples in einen WAV-Container (nur im Speicher).

    "io.BytesIO()" ist ein Speicherpuffer, der sich wie eine Datei verhaelt -
    so muss fuer diese kurze Aufnahme keine echte Datei auf die Festplatte
    geschrieben werden.
    """
    puffer = io.BytesIO()
    with wave.open(puffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(SAMPLE_WIDTH)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm)
    return puffer.getvalue()


class WhisperEngine:
    """Schickt eine fertige Aufnahme an whisper-server und liefert den Text."""

    def __init__(self, cfg: dict, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.sprache = cfg["stt"]["language"]
        self._session = requests.Session()

    def transkribieren(self, pcm: bytes, initial_prompt: str = "") -> str:
        """Fuehrt die Transkription durch und liefert den bereinigten Text.

        Bei einem Fehler (Server nicht erreichbar, Timeout, ...) wird ein
        leerer String zurueckgegeben statt eine Ausnahme durchzureichen - im
        Zweifel passiert dann einfach nichts, statt den Prozess abstuerzen
        zu lassen (siehe Parser-Sicherheits-Prinzip in Gaming_assistent.md).
        """
        wav = pcm_zu_wav(pcm)
        try:
            ergebnis = self._anfrage(wav, initial_prompt)
        except Exception as exc:
            log.warning("Whisper-Anfrage fehlgeschlagen: %s", exc)
            return ""

        segmente = ergebnis.get("segments") or []
        segmente = _halluzinierte_segmente_verwerfen(segmente)
        text = text_bereinigen(" ".join(str(s.get("text", "")) for s in segmente))
        log.debug("Whisper-Rohtext: %r", text)
        return text

    def _anfrage(self, wav: bytes, prompt: str) -> dict:
        daten = {
            "temperature": "0.0",
            "temperature_inc": "0.2",
            "response_format": "verbose_json",
            "language": self.sprache,
            # Ohne split_on_word schneidet whisper-server mitten durch Woerter
            # (seine Vorgabe fuer max_len ist 0, was intern zu 60 Zeichen wird).
            # Uebernommen aus dem Diktier-Tool, dort an acht Testsaetzen belegt.
            "split_on_word": "true",
        }
        if prompt:
            daten["prompt"] = prompt
        antwort = self._session.post(
            f"{self.base_url}/inference",
            data=daten,
            files={"file": ("audio.wav", wav, "audio/wav")},
            timeout=120,
        )
        antwort.raise_for_status()
        return antwort.json()

    def close(self) -> None:
        self._session.close()
