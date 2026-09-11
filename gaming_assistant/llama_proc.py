"""Startet und ueberwacht den llama-server-Subprozess (llama.cpp).

Ersetzt lmstudio.py: statt ein separat installiertes LM Studio ueber die
lms-CLI fernzusteuern, startet dieses Modul llama.cpp's eigenen
llama-server.exe direkt als Hintergrundprozess - eigenstaendige Kopie unter
vendor/llama.cpp/ (siehe scripts/fetch_llama.ps1), keine externe Installation
noetig. Strukturell fast identisch zu whisper_proc.py (siehe dort fuer die
Grundidee von subprocess.Popen()).

Besonderheit gegenueber whisper_proc.py: die Kontextlaenge (wie viele Tokens
sich das Modell merken kann, hier v.a. der lange System-Prompt) wird
llama-server nur beim Start ueber "-c" mitgegeben und kann danach nicht mehr
geaendert werden. Da jedes Spielprofil eine eigene, im Profil hinterlegte
Kontextlaenge hat (profile.py::Profil.kontextlaenge), muss der Subprozess bei
einem Profilwechsel mit ANDERER Kontextlaenge neu gestartet werden. Deshalb
gibt es hier zusaetzlich sicherstellen(), das genau das entscheidet.
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

log = logging.getLogger("llama_proc")

# Verhindert unter pythonw.exe, dass kurz ein Konsolenfenster aufblitzt.
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


class LlamaServer:
    def __init__(self, cfg: dict) -> None:
        llm = cfg["llm"]
        self.binary = config.resolve_path(llm["llama_bin"])
        self.model = config.resolve_path(llm["model"])
        self.n_gpu_layers = int(llm["n_gpu_layers"])
        self.threads = int(llm["threads"])
        self.host = llm["llama_host"]
        self.port = int(llm["llama_port"])
        self.startup_timeout = float(llm.get("startup_timeout_s", 180))
        self.proc: subprocess.Popen | None = None
        self._reader: threading.Thread | None = None
        # Merkt sich, mit welcher Kontextlaenge der GERADE LAUFENDE Prozess
        # gestartet wurde - None heisst "noch nicht gestartet". sicherstellen()
        # vergleicht das mit der vom aktiven Profil gewuenschten Kontextlaenge.
        self._kontextlaenge: int | None = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def start(self, kontextlaenge: int) -> None:
        """Startet llama-server (neu) mit genau dieser Kontextlaenge.

        Laeuft bereits ein Prozess, wird er zuerst sauber gestoppt - so kann
        diese Methode bedenkenlos auch fuer einen Neustart aufgerufen werden,
        ohne dass der Aufrufer selbst an stop() denken muss.
        """
        if not self.binary.exists():
            raise FileNotFoundError(
                f"llama-server nicht gefunden: {self.binary}\n"
                "Zuerst scripts\\fetch_llama.ps1 ausfuehren."
            )
        if not self.model.exists():
            raise FileNotFoundError(
                f"LLM-Modelldatei nicht gefunden: {self.model}\n"
                "Zuerst scripts\\download_llm.ps1 ausfuehren."
            )
        if self.is_alive():
            self.stop()

        befehl = [
            str(self.binary),
            "-m", str(self.model),
            "-c", str(kontextlaenge),
            # Nur 1 Slot statt der llama-server-Vorgabe ("-1" = automatisch,
            # in der Praxis oft 4): bei mehreren Slots teilt sich die
            # Kontextlaenge/der VRAM-Bedarf unnoetig auf mehrere parallele
            # Gespraeche auf, obwohl hier immer nur ein Push-to-Talk-Nutzer
            # gleichzeitig spricht. Per curl-Test bestaetigt (siehe CLAUDE.md):
            # ohne "-np 1" wurden 4x so viel VRAM fuer den KV-Cache reserviert.
            "-np", "1",
            "-ngl", str(self.n_gpu_layers),
            "-t", str(self.threads),
            "--host", self.host,
            "--port", str(self.port),
            "--no-webui",
            # Ohne dieses Flag aktiviert der hier verwendete Gemma-4-Chat-
            # Template-Standard von llama-server automatisch den Denkmodus,
            # sobald eine System-Message vorhanden ist (bei uns immer der
            # Fall) - das Modell verbraucht dann seine max_tokens komplett
            # fuers Nachdenken und die eigentliche Tag-Antwort bleibt leer
            # (per Test bestaetigt, siehe CLAUDE.md). Entspricht dem frueher
            # in LM Studio manuell ausgeschalteten "Enable Thinking"-Schalter.
            "--reasoning", "off",
        ]
        log.info(
            "Starte llama-server: %s (Modell %s, Kontext %d)",
            self.binary.name, self.model.name, kontextlaenge,
        )
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
        # Bei einem Neustart (siehe oben) wird das mehrfach registriert - das
        # ist unschaedlich, da stop() selbst idempotent ist (mehrfacher Aufruf
        # macht beim zweiten Mal einfach nichts).
        atexit.register(self.stop)

        self._reader = threading.Thread(target=self._ausgabe_umleiten, daemon=True)
        self._reader.start()

        self._warten_bis_bereit()
        self._kontextlaenge = kontextlaenge

    def sicherstellen(self, kontextlaenge: int) -> None:
        """Sorgt dafuer, dass llama-server mit dieser Kontextlaenge laeuft.

        Das ist die Methode, die __main__.py bei jedem Profil-Laden (auch
        beim allerersten Start) aufruft. Laeuft der Server schon mit genau
        dieser Kontextlaenge, passiert nichts (kein unnoetiger Neustart beim
        Wechsel zwischen Profilen mit gleicher Kontextlaenge). Andernfalls
        wird ueber start() neu gestartet.
        """
        if self.is_alive() and self._kontextlaenge == kontextlaenge:
            log.info("llama-server laeuft bereits mit passender Kontextlaenge %d - kein Neustart", kontextlaenge)
            return
        log.info("llama-server-Neustart noetig (Kontext %s -> %d)", self._kontextlaenge, kontextlaenge)
        self.start(kontextlaenge)

    def _ausgabe_umleiten(self) -> None:
        """Leitet die Konsolenausgabe von llama.cpp ins eigene Log um."""
        assert self.proc is not None and self.proc.stdout is not None
        for zeile in self.proc.stdout:
            zeile = zeile.rstrip()
            if zeile:
                log.debug("[llama.cpp] %s", zeile)

    def _warten_bis_bereit(self) -> None:
        """Pollt den Server, bis er antwortet, oder wirft nach Timeout einen Fehler.

        Anders als bei whisper_proc.py (dort zaehlt jede Antwort als "bereit")
        liefert llama-server unter /health bewusst einen 503-Statuscode,
        solange das Modell noch laedt, und erst 200 wenn es fertig ist - das
        wird hier ausgewertet, damit wir nicht faelschlich "bereit" melden,
        waehrend das Modell noch in den VRAM geladen wird.
        """
        deadline = time.monotonic() + self.startup_timeout
        letzter_fehler: Exception | None = None
        url = f"{self.base_url}/health"
        while time.monotonic() < deadline:
            if self.proc is not None and self.proc.poll() is not None:
                raise RuntimeError(
                    f"llama-server hat sich mit Code {self.proc.returncode} beendet. "
                    "Details im Log."
                )
            try:
                urllib.request.urlopen(url, timeout=2).close()
                log.info("llama-server bereit auf %s", self.base_url)
                return
            except urllib.error.HTTPError as exc:
                if exc.code == 503:
                    letzter_fehler = exc
                    time.sleep(0.5)
                    continue
                # Jeder andere Statuscode heisst: der Server antwortet bereits
                # regulaer, das Modell ist geladen.
                log.info("llama-server bereit auf %s", self.base_url)
                return
            except Exception as exc:
                letzter_fehler = exc
                time.sleep(0.5)
        raise TimeoutError(
            f"llama-server war nach {self.startup_timeout:.0f}s nicht bereit: {letzter_fehler}"
        )

    def is_alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def stop(self) -> None:
        """Sauberes Beenden: erst hoeflich (terminate), dann notfalls hart (kill)."""
        proc, self.proc = self.proc, None
        self._kontextlaenge = None
        if proc is None or proc.poll() is not None:
            return
        log.info("Beende llama-server ...")
        try:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                log.warning("llama-server reagiert nicht, erzwinge kill")
                proc.kill()
                proc.wait(timeout=5)
        except Exception as exc:  # pragma: no cover
            log.warning("Fehler beim Beenden von llama-server: %s", exc)
        else:
            log.info("llama-server beendet")
