"""Klassifikations-Anfrage an llama-server (OpenAI-kompatible Chat-API).

Anders als beim Diktier-Tool (server/llm.py, dort Bereinigung/Uebersetzung von
Fliesstext) macht das LLM hier keine freie Textgenerierung, sondern ordnet
genau einer festen Tag-Liste zu (siehe Gaming_assistent.md, Abschnitt
"Unterschied zur Diktier-Pipeline"). Deshalb entfaellt hier die
Plausibilitaets-Pruefung per Laengenverhaeltnis - die gibt es nur beim
Diktier-Tool, wo aus einem Satz wieder ein aehnlich langer Satz werden soll.

llama-server (gestartet/verwaltet von llama_proc.py) bringt von Haus aus
dieselbe OpenAI-kompatible /v1/chat/completions-API mit, die vorher LM Studio
lieferte - deshalb aendert sich an dieser Anfrage-Logik kaum etwas gegenueber
dem frueheren LM-Studio-Setup, nur die Ziel-URL und der zusaetzliche
"cache_prompt"-Parameter (siehe unten) sind neu.

Kein "/no_think" noetig: laut Testreihe (siehe CLAUDE.md) war der Denkmodus
fuer Gemma 4 im frueheren LM-Studio-Setup bereits ueber den GUI-Schalter aus;
bei llama-server gibt es diesen Schalter erst gar nicht, das Modell denkt hier
ebenfalls nicht unaufgefordert. "/no_think" waere ohnehin eine
Qwen-spezifische Konvention, die Gemma nicht kennt (waere nur Rauschen im
Prompt).
"""

from __future__ import annotations

import logging
import re

import requests

log = logging.getLogger("llm")

# Falls ein Modell trotzdem einmal einen <think>-Block ausgibt (z.B. nach
# einem versehentlichen Umschalten des LM-Studio-Schalters), wird er hier
# sicherheitshalber entfernt, bevor der Parser die Antwort sieht.
_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_WHITESPACE = re.compile(r"\s+")


class LLMKlassifikator:
    def __init__(self, cfg: dict) -> None:
        llm = cfg["llm"]
        self.url = f"http://{llm['llama_host']}:{llm['llama_port']}/v1/chat/completions"
        self.temperature = float(llm["temperature"])
        self.max_tokens = int(llm["max_tokens"])
        self.timeout = float(llm["timeout_s"])
        self._session = requests.Session()

    def klassifizieren(self, text: str, system_prompt: str, modell: str) -> tuple[str, str | None]:
        """Schickt den Rohtext an das LLM und liefert (Antworttext, finish_reason).

        Bei einem Fehler (Server nicht erreichbar, ungueltige Antwort, ...)
        wird ("", None) zurueckgegeben - der aufrufende Code (parser.py)
        behandelt das automatisch wie "kein Tag erkannt".
        """
        text = _WHITESPACE.sub(" ", text or "").strip()
        if not text:
            return "", None

        payload = {
            "model": modell,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
            # llama-server merkt sich den KV-Cache des zuletzt verarbeiteten
            # Prompts. Da sich der lange System-Prompt (Tag-Liste, mehrere
            # Tausend Tokens) zwischen zwei Befehlen NICHT aendert, muss er so
            # nicht bei jedem Befehl neu durchgerechnet werden - nur der kurze
            # neue Nutzertext am Ende ist wirklich neu. Das ist derselbe
            # Geschwindigkeitsgewinn, den vorher LM Studio automatisch
            # geliefert hat (siehe CLAUDE.md, "Latenz gemessen"); ohne dieses
            # Flag waere jeder Befehl wieder so langsam wie der allererste.
            "cache_prompt": True,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
        }
        try:
            antwort = self._session.post(self.url, json=payload, timeout=self.timeout)
            antwort.raise_for_status()
            daten = antwort.json()
        except Exception as exc:
            log.warning("LLM-Anfrage fehlgeschlagen: %s", exc)
            return "", None

        try:
            auswahl = daten["choices"][0]
            nachricht = auswahl["message"]
        except (KeyError, IndexError, TypeError):
            log.warning("Unerwartete LLM-Antwortstruktur: %r", daten)
            return "", None

        inhalt = _THINK_BLOCK.sub("", nachricht.get("content") or "").strip()
        finish_reason = auswahl.get("finish_reason")
        nutzung = daten.get("usage") or {}
        log.info(
            "LLM-Antwort: %r (finish_reason=%s, %s Completion-Tokens)",
            inhalt, finish_reason, nutzung.get("completion_tokens", "?"),
        )
        return inhalt, finish_reason

    def close(self) -> None:
        self._session.close()
