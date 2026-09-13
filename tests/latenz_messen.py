"""Latenz-Messskript fuer die eigene Hardware.

Misst End-zu-Ende, wie lange ein einzelner Sprachbefehl auf dem eigenen
Rechner braucht: Spracherkennung (STT) und Klassifikation (LLM) getrennt,
plus Cold-Start (der erste Aufruf nach dem Start, spuerbar langsamer wegen
des einmaligen Verarbeitens des langen System-Prompts).

Nutzt echte, synthetisierte Sprache statt Stille/Rauschen als Testaudio -
wichtig, weil Whisper bei digitaler Stille gelegentlich halluziniert und
dadurch teure Wiederholungsdurchlaeufe ausloest, was die Zeitmessung
verfaelschen wuerde (siehe CLAUDE.md, Abschnitt "initial_prompt-Laenge").
Die Sprachsynthese laeuft ueber Windows' eingebautes System.Speech (per
PowerShell aufgerufen) - keine zusaetzliche Python-Abhaengigkeit noetig, und
es wird die auf dem jeweiligen Rechner ohnehin installierte Standardstimme
verwendet (nicht fest auf eine bestimmte deutsche Stimme wie "Hedda"
festgelegt, damit das Skript auch ohne diese eine Stimme laeuft - fuer die
reine Zeitmessung ist die inhaltliche Qualitaet der Erkennung nebensaechlich).

Testet gegen das aktuell in config.json aktive Profil (bzw. automatisch ein
verfuegbares, falls der eingetragene Name nicht mehr existiert - analog zur
Logik in __main__.py).

Aufruf:

    .venv\\Scripts\\python.exe tests\\latenz_messen.py
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

_PROJEKT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJEKT_ROOT))

from gaming_assistant import config, profile, prompt
from gaming_assistant.llama_proc import LlamaServer
from gaming_assistant.llm import LLMKlassifikator
from gaming_assistant.stt import WhisperEngine
from gaming_assistant.whisper_proc import WhisperServer

_TESTSATZ = "Ruf das Maschinengewehr"
_WIEDERHOLUNGEN = 10


def _testaudio_erzeugen(ziel_pfad: Path) -> None:
    """Erzeugt eine 16kHz-Mono-WAV-Datei mit Windows-eigener Sprachsynthese."""
    ps_skript = f"""
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$synth.SetOutputToWaveFile('{ziel_pfad}', $fmt)
$synth.Speak('{_TESTSATZ}')
$synth.SetOutputToNull()
"""
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_skript],
        check=True,
        capture_output=True,
        text=True,
    )


def main() -> None:
    cfg = config.load()
    verzeichnis = config.profil_verzeichnis(cfg)
    verfuegbare_profile = profile.liste_profile(verzeichnis)
    if not verfuegbare_profile:
        print(f"Kein Profil gefunden in {verzeichnis}")
        sys.exit(1)
    profil_name = cfg["profil"]["aktiv"]
    if profil_name not in verfuegbare_profile:
        profil_name = verfuegbare_profile[0]
    profil = profile.laden(verzeichnis / f"{profil_name}.yaml")
    system_prompt = prompt.system_prompt_bauen(profil)
    initial_prompt = prompt.initial_prompt_bauen(profil)

    print(f"Profil: {profil_name} ({len(profil.tags)} Tags, Kontextlaenge {profil.kontextlaenge})")
    print(f"Erzeuge Testaudio ({_TESTSATZ!r}) ueber Windows-Sprachsynthese ...")

    with tempfile.TemporaryDirectory() as tmp:
        wav_pfad = Path(tmp) / "testaudio.wav"
        _testaudio_erzeugen(wav_pfad)
        with wave.open(str(wav_pfad), "rb") as w:
            pcm = w.readframes(w.getnframes())

    print("Starte whisper-server und llama-server (kann beim ersten Mal etwas dauern) ...")
    whisper_server = WhisperServer(cfg)
    whisper_server.start()
    whisper_engine = WhisperEngine(cfg, whisper_server.base_url)

    llama_server = LlamaServer(cfg)
    llama_server.start(profil.kontextlaenge)
    klassifikator = LLMKlassifikator(cfg)

    try:
        stt_zeiten = []
        for _ in range(_WIEDERHOLUNGEN):
            start = time.monotonic()
            text = whisper_engine.transkribieren(pcm, initial_prompt)
            stt_zeiten.append(time.monotonic() - start)
        if not text:
            print("Warnung: Whisper hat keinen Text erkannt - Ergebnis evtl. nicht aussagekraeftig.")

        start = time.monotonic()
        klassifikator.klassifizieren(text, system_prompt, "gaming-llm")
        llm_cold_start = time.monotonic() - start

        llm_zeiten = []
        for _ in range(_WIEDERHOLUNGEN):
            start = time.monotonic()
            klassifikator.klassifizieren(text, system_prompt, "gaming-llm")
            llm_zeiten.append(time.monotonic() - start)
    finally:
        klassifikator.close()
        whisper_engine.close()
        llama_server.stop()
        whisper_server.stop()

    stt_min, stt_avg = min(stt_zeiten), sum(stt_zeiten) / len(stt_zeiten)
    llm_min, llm_avg = min(llm_zeiten), sum(llm_zeiten) / len(llm_zeiten)

    print(f"\nErkannter Text: {text!r}")
    print(f"\nSTT-Latenz:            {stt_min:.3f}s (min) / {stt_avg:.3f}s (avg) ueber {_WIEDERHOLUNGEN} Durchlaeufe")
    print(f"LLM Cold-Start:        {llm_cold_start:.3f}s (einmaliger erster Aufruf)")
    print(f"LLM Wiederholung:      {llm_min:.3f}s (min) / {llm_avg:.3f}s (avg) ueber {_WIEDERHOLUNGEN} Durchlaeufe")
    print(f"Geschaetzt End-zu-Ende: {stt_min + llm_min:.3f}s (min) / {stt_avg + llm_avg:.3f}s (avg)")


if __name__ == "__main__":
    main()
