"""Startet und ueberwacht den whisper-server-Subprozess.

Uebernommen als Vorlage aus dem Diktier-Tool (server/whisper_proc.py), aber
vereinfacht: kein Modellwechsel zur Laufzeit noetig, da das Whisper-Modell
laut Konzept fest auf large-v3-turbo-german-q5 steht.

Python-Hinweis: subprocess.Popen() startet ein externes Programm (hier die
.exe von whisper.cpp) als eigenen Prozess und gibt ein Handle darauf zurueck,
ueber das man es spaeter wieder beenden kann.
"""

from __future__ import annotations

import atexit
import logging
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

from gaming_assistant import config

log = logging.getLogger("whisper_proc")

# Verhindert unter pythonw.exe, dass kurz ein Konsolenfenster aufblitzt.
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


class WhisperServer:
    def __init__(self, cfg: dict) -> None:
        stt = cfg["stt"]
        self.binary = config.resolve_path(stt["whisper_bin"])
        self.model = config.resolve_path(stt["model"])
        self.language = stt["language"]
        self.threads = int(stt["threads"])
        self.host = stt["whisper_host"]
        self.port = int(stt["whisper_port"])
        self.startup_timeout = float(stt.get("startup_timeout_s", 180))
        self.proc: subprocess.Popen | None = None
        self._reader: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def start(self) -> None:
        if not self.binary.exists():
            raise FileNotFoundError(
                f"whisper-server nicht gefunden: {self.binary}\n"
                "Zuerst scripts\\build_whisper.ps1 ausfuehren."
            )
        if not self.model.exists():
            raise FileNotFoundError(
                f"Whisper-Modell nicht gefunden: {self.model}\n"
                "Zuerst scripts\\fetch_models.ps1 ausfuehren."
            )

        befehl = [
            str(self.binary),
            "-m", str(self.model),
            "-l", self.language,
            "-t", str(self.threads),
            "--host", self.host,
            "--port", str(self.port),
        ]
        log.info("Starte whisper-server: %s (Modell %s)", self.binary.name, self.model.name)
        self.proc = subprocess.Popen(
            befehl,
            cwd=str(config.ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=_NO_WINDOW,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        # atexit sorgt dafuer, dass der Subprozess auch bei einem regulaeren
        # Python-Beenden (nicht nur ueber unser eigenes stop()) mit runtergeht.
        atexit.register(self.stop)

        self._reader = threading.Thread(target=self._ausgabe_umleiten, daemon=True)
        self._reader.start()

        self._warten_bis_bereit()

    def _ausgabe_umleiten(self) -> None:
        """Leitet die Konsolenausgabe von whisper.cpp ins eigene Log um."""
        assert self.proc is not None and self.proc.stdout is not None
        for zeile in self.proc.stdout:
            zeile = zeile.rstrip()
            if zeile:
                log.debug("[whisper.cpp] %s", zeile)

    def _warten_bis_bereit(self) -> None:
        """Pollt den Server, bis er antwortet, oder wirft nach Timeout einen Fehler."""
        deadline = time.monotonic() + self.startup_timeout
        letzter_fehler: Exception | None = None
        while time.monotonic() < deadline:
            if self.proc is not None and self.proc.poll() is not None:
                raise RuntimeError(
                    f"whisper-server hat sich mit Code {self.proc.returncode} beendet. "
                    "Details im Log."
                )
            try:
                urllib.request.urlopen(self.base_url, timeout=2).close()
                log.info("whisper-server bereit auf %s", self.base_url)
                return
            except urllib.error.HTTPError:
                # Antwortet ueberhaupt mit einem Statuscode -> Server steht.
                log.info("whisper-server bereit auf %s", self.base_url)
                return
            except Exception as exc:
                letzter_fehler = exc
                time.sleep(0.5)
        raise TimeoutError(
            f"whisper-server war nach {self.startup_timeout:.0f}s nicht erreichbar: {letzter_fehler}"
        )

    def is_alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def stop(self) -> None:
        """Sauberes Beenden: erst hoeflich (terminate), dann notfalls hart (kill)."""
        proc, self.proc = self.proc, None
        if proc is None or proc.poll() is not None:
            return
        log.info("Beende whisper-server ...")
        try:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                log.warning("whisper-server reagiert nicht, erzwinge kill")
                proc.kill()
                proc.wait(timeout=5)
        except Exception as exc:  # pragma: no cover
            log.warning("Fehler beim Beenden von whisper-server: %s", exc)
        else:
            log.info("whisper-server beendet")
