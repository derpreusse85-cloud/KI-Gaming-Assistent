"""Einstiegspunkt: verdrahtet alle Module zur eigentlichen Pipeline.

Start ueber ``python -m gaming_assistant`` (der Python-Interpreter sucht dann
automatisch diese Datei, weil ihr Name __main__.py ein Python-Konvention ist).

Ablauf pro Sprachbefehl (siehe Gaming_assistent.md, Abschnitt "Pipeline"):

    PTT gedrueckt -> Mikrofon aufnehmen -> PTT losgelassen -> Whisper (STT)
    -> LLM-Klassifikation -> Tag-Parser -> Tastendruck-Simulation

Python-Hinweis zum "laufzeit"-Dict weiter unten: mehrere Funktionen in dieser
Datei (z.B. bei_ptt_druecken) brauchen Zugriff auf Objekte, die erst NACH
dieser Funktion angelegt werden (z.B. das Tray-Icon). Ein normales dict, das
alle Funktionen gemeinsam nutzen, loest das: der Lookup "laufzeit['tray']"
passiert erst, wenn die Funktion tatsaechlich AUFGERUFEN wird - zu diesem
Zeitpunkt ist der Eintrag laengst gesetzt, auch wenn er beim Definieren der
Funktion noch fehlte.
"""

from __future__ import annotations

import argparse
import logging
import queue
import threading
import time

from gaming_assistant import (
    audio,
    config,
    ed_status,
    keypress,
    llama_proc,
    llm,
    logbuf,
    parser,
    profile,
    prompt,
    ptt,
    ptt_dialog,
    stt,
    training_log,
    tray,
    whisper_proc,
)

log = logging.getLogger("main")
# Eigener Logger nur fuer die kompakte Anzeige (Transkription/Tag/Tasten) -
# siehe logbuf.py::_KompaktFilter und "--kompakt" weiter unten. Laeuft immer
# mit, unabhaengig vom Schalter - der Filter entscheidet nur, ob die normale
# Konsole zusaetzlich noch alles andere zeigt oder nicht.
anzeige_log = logging.getLogger("main.anzeige")


def main() -> None:
    cli_argumente = argparse.ArgumentParser(
        description="Gaming-Sprachassistent: Push-to-Talk -> Whisper -> LLM-Klassifikation -> Tastensequenz"
    )
    cli_argumente.add_argument(
        "--kompakt", action="store_true",
        help="Zeigt in der Konsole nur Transkription, erkannten Tag und ausgeloeste Tasten "
             "an, ohne die uebrigen Debug-/Info-Zeilen - gedacht fuers Demo-Video. Die Log-"
             "Datei und das Tray-Log-Fenster bleiben davon unberuehrt (weiterhin vollstaendig).",
    )
    args = cli_argumente.parse_args()

    cfg = config.load()
    logbuf.setup(cfg.get("log_level", "INFO"), kompakt=args.kompakt)
    log.info("Gaming-Assistent startet ...")

    profil_verzeichnis = config.profil_verzeichnis(cfg)
    training_verzeichnis = config.resolve_path(cfg["training_log"]["verzeichnis"])

    # "zustand" haelt alles, was sich bei einem Profilwechsel zur Laufzeit
    # aendert (anders als "laufzeit" unten, das feste Objekte wie das Tray-Icon
    # haelt, die nur einmal beim Start entstehen).
    zustand: dict = {"profil": None, "system_prompt": "", "initial_prompt": "", "llm_bezeichner": ""}

    # Muss VOR dem ersten profil_laden()-Aufruf angelegt sein, da profil_laden
    # bereits beim allerersten Start (siehe unten) llama_server.sicherstellen()
    # aufruft.
    llama_server = llama_proc.LlamaServer(cfg)

    def profil_laden(name: str) -> None:
        pfad = profil_verzeichnis / f"{name}.yaml"
        profil_obj = profile.laden(pfad)
        zustand["profil"] = profil_obj
        zustand["system_prompt"] = prompt.system_prompt_bauen(profil_obj)
        zustand["initial_prompt"] = prompt.initial_prompt_bauen(profil_obj)
        # Startet (oder - falls die Kontextlaenge sich geaendert hat - startet
        # neu) den llama-server-Subprozess mit der im Profil hinterlegten
        # Kontextlaenge - siehe Gaming_assistent.md, Abschnitt "Sampling-Parameter",
        # und llama_proc.py fuer die Neustart-Logik.
        llama_server.sicherstellen(profil_obj.kontextlaenge)
        # llama-server bedient immer nur ein einziges Modell - anders als bei
        # LM Studio frueher gibt es keinen echten "Bezeichner" mehr zu waehlen,
        # der Wert hier ist nur noch Log-/Protokoll-Kosmetik in llm.py/training_log.py.
        zustand["llm_bezeichner"] = "gaming-llm"
        cfg["profil"]["aktiv"] = name
        config.save(cfg)
        log.info("Profil aktiv: %s (%d Tags, Kontext %d)", name, len(profil_obj.tags), profil_obj.kontextlaenge)

    # Faellt automatisch auf ein tatsaechlich vorhandenes Profil zurueck, falls
    # der in config.json gespeicherte Name zu keiner Datei mehr passt (z.B.
    # nach einer Umbenennung/Loeschung) - so muss ausser dieser Fallback-Logik
    # nirgends im Code ein konkreter Profilname hinterlegt sein, nur der
    # Ordner selbst wird gebraucht (profile.liste_profile() scannt profiles/).
    verfuegbare_profile = profile.liste_profile(profil_verzeichnis)
    aktives_profil = cfg["profil"]["aktiv"]
    if aktives_profil not in verfuegbare_profile:
        if not verfuegbare_profile:
            raise RuntimeError(
                f"Kein Spielprofil gefunden in {profil_verzeichnis} - mindestens eine "
                "YAML-Datei wird benoetigt."
            )
        log.warning(
            "Konfiguriertes Profil %r nicht gefunden (umbenannt/geloescht?) - "
            "verwende stattdessen %r.", aktives_profil, verfuegbare_profile[0],
        )
        aktives_profil = verfuegbare_profile[0]
    profil_laden(aktives_profil)

    # -- Whisper-Subprozess + STT-Engine -------------------------------------
    whisper_server = whisper_proc.WhisperServer(cfg)
    whisper_server.start()
    whisper_engine = stt.WhisperEngine(cfg, whisper_server.base_url)

    # -- LLM-Klassifikator ----------------------------------------------------
    klassifikator = llm.LLMKlassifikator(cfg)

    # -- Mikrofon --------------------------------------------------------------
    audio_capture = audio.AudioCapture()
    audio_capture.set_device(cfg.get("mic_device_index"))

    laufzeit: dict = {}

    def verarbeiten(pcm: bytes) -> None:
        """Laeuft im eigenen Verarbeitungs-Worker-Thread (siehe
        verarbeitungs_worker weiter unten), damit der Push-to-talk-Listener
        waehrend Whisper/LLM/Sleep-Tags nicht blockiert. Mehrere Befehle
        werden dabei strikt nacheinander abgearbeitet, nie parallel - wichtig
        bei einem laufenden &&sleep:N&&, siehe verarbeitungs_worker.

        Misst nebenbei, wie lange jeder Pipeline-Schritt braucht (Latenz-Frage
        vom 10.09.2026) - time.monotonic() liefert eine Uhr, die nur fuer
        Zeitdifferenzen gedacht ist (im Gegensatz zu time.time() laeuft sie nie
        rueckwaerts, z.B. bei einer Systemzeit-Korrektur)."""
        start = time.monotonic()
        profil_obj = zustand["profil"]
        roh_text = whisper_engine.transkribieren(pcm, zustand["initial_prompt"])
        nach_stt = time.monotonic()
        if not roh_text:
            log.debug("Keine Sprache erkannt - nichts zu tun (STT: %.2fs)", nach_stt - start)
            return

        antwort, finish_reason = klassifikator.klassifizieren(
            roh_text, zustand["system_prompt"], zustand["llm_bezeichner"]
        )
        nach_llm = time.monotonic()
        tags = parser.tags_extrahieren(antwort, profil_obj.bekannte_tags(), finish_reason,
                                       profil_obj.schlagwort_zuordnung())

        # Sammelt (Tag, tatsaechlich ausgeloeste Tasten) fuer die kompakte
        # Anzeige unten - bei Feuergruppen ist das erst nach der Berechnung
        # gegen den aktuellen Spielzustand bekannt, nicht schon vorher aus dem
        # Profil (dort steht wegen der Laufzeitberechnung nur "taste: []").
        ausgeloeste_tasten: list[tuple[str, list[str]]] = []

        for tag_name in tags:
            sleep_sekunden = parser.sleep_dauer(tag_name)
            if sleep_sekunden is not None:
                # Sicherheitsobergrenze statt der vom LLM genannten Zahl
                # blind zu vertrauen - siehe parser.py, MAX_SLEEP_SEKUNDEN.
                if sleep_sekunden > parser.MAX_SLEEP_SEKUNDEN:
                    log.warning(
                        "Wartezeit %ds auf Obergrenze %ds gekappt",
                        sleep_sekunden, parser.MAX_SLEEP_SEKUNDEN,
                    )
                    sleep_sekunden = parser.MAX_SLEEP_SEKUNDEN
                time.sleep(sleep_sekunden)
                # Zeigt die tatsaechlich gewartete (ggf. gekappte) Sekundenzahl
                # an, nicht den urspruenglichen tag_name - relevant fuer die
                # Anzeige-Zeile unten, falls die Obergrenze gegriffen hat.
                ausgeloeste_tasten.append((f"sleep:{sleep_sekunden}", []))
                continue
            eintrag = profil_obj.tags[tag_name]
            if eintrag.feuergruppe_ziel is not None:
                # Keine feste Tastenliste - wird aus dem aktuellen Spielzustand
                # berechnet (siehe ed_status.py). None heisst "Zustand gerade
                # nicht bekannt" (Spiel laeuft nicht, Status.json fehlt/kaputt)
                # - dann bewusst KEIN Tastendruck statt zu raten.
                berechnete_taste = ed_status.feuergruppen_tasten(
                    profil_obj.status_datei,
                    eintrag.feuergruppe_ziel,
                    profil_obj.feuergruppe_vorwaerts_taste,
                    profil_obj.feuergruppe_rueckwaerts_taste,
                )
                if berechnete_taste is None:
                    log.warning(
                        "Feuergruppe %r nicht ausgeloest - aktueller Spielzustand unbekannt",
                        tag_name,
                    )
                    continue
                keypress.ausloesen(berechnete_taste)
                ausgeloeste_tasten.append((tag_name, berechnete_taste))
            else:
                keypress.ausloesen(eintrag.taste)
                ausgeloeste_tasten.append((tag_name, eintrag.taste))
        nach_tasten = time.monotonic()

        log.info(
            "Latenz: STT %.2fs, LLM %.2fs, Tasten %.2fs, gesamt %.2fs (Text: %r, Tags: %s)",
            nach_stt - start, nach_llm - nach_stt, nach_tasten - nach_llm, nach_tasten - start,
            roh_text, tags,
        )

        # Kompakte Anzeige-Zeile (siehe --kompakt weiter oben) - unabhaengig
        # vom Schalter immer geloggt, der Konsolen-Filter in logbuf.py
        # entscheidet, ob sie zusaetzlich zu allem anderen oder allein
        # angezeigt wird. Latenz mit dabei (Nutzerwunsch: gut fuers
        # Demo-Video) - sowohl bis zum ersten Tastendruck (STT+LLM, Zeitpunkt
        # nach_llm) als auch gesamt (inkl. aller Tastendruecke, Zeitpunkt
        # nach_tasten), dieselben Werte wie in der "Latenz: ..."-Zeile oben,
        # nur kompakter zusammengefasst.
        latenz_bis_taste = nach_llm - start
        gesamt_latenz = nach_tasten - start
        if ausgeloeste_tasten:
            anzeige_log.info(
                "Gehoert: %r -> %s (gesamt: %.2fs)", roh_text,
                " | ".join(
                    f"(wartet {t2}s)" if (t2 := parser.sleep_dauer(n)) is not None
                    else f"{n}: ({latenz_bis_taste:.2f}s) {t}"
                    for n, t in ausgeloeste_tasten
                ),
                gesamt_latenz,
            )
        else:
            anzeige_log.info(
                "Gehoert: %r -> kein Tag erkannt (NONE) (%.2fs)", roh_text, latenz_bis_taste,
            )

        # Ungefiltertes Live-Logging fuer die spaetere Trainingsdaten-Aufbereitung
        # (siehe Gaming_assistent.md) - passiert unabhaengig davon, ob ein Tag
        # erkannt wurde oder nicht, ausser der Nutzer hat es ueber das
        # Tray-Menue abgeschaltet.
        if cfg["training_log"]["aktiv"]:
            training_log.eintrag_anhaengen(training_verzeichnis, profil_obj.name, roh_text, tags)

    # Waehrend einer laufenden Aufnahme darf der PTT-Aenderungsdialog nicht
    # geoeffnet werden - sonst faengt der Listener den naechsten Tastendruck
    # als neuen Ausloeser ab, statt (wie erwartet) die Aufnahme zu beenden.
    zustand["aufnahme_laeuft"] = False

    # Verarbeitung laeuft strikt nacheinander ueber diese Queue statt (wie vor
    # den Sleep-Tags) in einem eigenen Thread PRO Befehl: waehrend eines
    # &&sleep:N&&-Tags (siehe oben) darf ein waehrenddessen per PTT
    # aufgenommener neuer Befehl nicht parallel dazwischenfunken (z.B. gleich-
    # zeitige Tastendruecke), sondern soll erst dran sein, wenn der aktuelle
    # Befehl (inkl. seiner Wartezeiten) fertig ist - Nutzerentscheidung
    # 17.09.2026 (siehe CLAUDE.md, "Verschachtelte Kommandos mit Pausenzeiten").
    verarbeitungs_queue: queue.Queue = queue.Queue()

    def verarbeitungs_worker() -> None:
        while True:
            pcm = verarbeitungs_queue.get()
            try:
                verarbeiten(pcm)
            except Exception:
                log.exception("Fehler bei der Verarbeitung eines Sprachbefehls")

    threading.Thread(target=verarbeitungs_worker, daemon=True).start()

    def bei_ptt_druecken() -> None:
        zustand["aufnahme_laeuft"] = True
        laufzeit["tray"].zustand_setzen("aufnahme")
        audio_capture.start()

    def bei_ptt_loslassen() -> None:
        pcm = audio_capture.stop()
        zustand["aufnahme_laeuft"] = False
        laufzeit["tray"].zustand_setzen("bereit")
        verarbeitungs_queue.put(pcm)

    ptt_listener = ptt.PTTListener(cfg["ptt"], bei_ptt_druecken, bei_ptt_loslassen)
    laufzeit["ptt_listener"] = ptt_listener
    ptt_listener.start()

    def bei_ptt_gewaehlt(neuer_ptt: dict) -> None:
        """Wird vom Dialog aufgerufen, sobald der Nutzer eine neue Taste
        gedrueckt hat (siehe ptt_dialog.py)."""
        ptt_listener.trigger_setzen(neuer_ptt)
        cfg["ptt"] = neuer_ptt
        config.save(cfg)
        laufzeit["tray"].ptt_label_setzen(ptt.beschreiben(neuer_ptt))

    def ptt_dialog_oeffnen() -> None:
        if zustand["aufnahme_laeuft"]:
            log.warning("Push-to-talk-Aenderung waehrend einer laufenden Aufnahme nicht moeglich")
            return
        ptt_dialog.zeigen(ptt_listener, cfg["ptt"], bei_ptt_gewaehlt)

    def training_log_umschalten() -> None:
        cfg["training_log"]["aktiv"] = not cfg["training_log"]["aktiv"]
        config.save(cfg)
        log.info("Trainingsdaten-Aufzeichnung ueber Tray %s", "aktiviert" if cfg["training_log"]["aktiv"] else "deaktiviert")

    def debug_umschalten() -> None:
        cfg["log_level"] = "INFO" if cfg.get("log_level") == "DEBUG" else "DEBUG"
        config.save(cfg)
        logbuf.set_level(cfg["log_level"])
        log.info("Log-Level ueber Tray auf %s gesetzt", cfg["log_level"])

    def modell_wechseln(modell_pfad: str) -> None:
        if zustand["aufnahme_laeuft"]:
            log.warning("Modellwechsel waehrend einer laufenden Aufnahme nicht moeglich")
            return
        log.info("Wechsle Sprachmodell auf %s (llama-server-Neustart) ...", modell_pfad)
        try:
            llama_server.modell_wechseln(modell_pfad, zustand["profil"].kontextlaenge)
        except Exception:
            log.exception("Modellwechsel fehlgeschlagen - bisheriges Modell bleibt aktiv")
            return
        cfg["llm"]["model"] = modell_pfad
        config.save(cfg)
        log.info("Sprachmodell aktiv: %s", modell_pfad)

    def beenden() -> None:
        log.info("Gaming-Assistent wird beendet ...")
        ptt_listener.stop()
        whisper_server.stop()
        llama_server.stop()
        whisper_engine.close()
        klassifikator.close()

    tray_obj = tray.Tray(
        status_fn=lambda: f"Profil: {zustand['profil'].name}",
        profil_liste_fn=lambda: profile.liste_profile(profil_verzeichnis),
        aktives_profil_fn=lambda: zustand["profil"].name,
        on_profil_wechsel=profil_laden,
        on_beenden=beenden,
        ptt_label=ptt.beschreiben(cfg["ptt"]),
        on_ptt_aendern=ptt_dialog_oeffnen,
        training_log_aktiv_fn=lambda: cfg["training_log"]["aktiv"],
        on_training_log_umschalten=training_log_umschalten,
        debug_aktiv_fn=lambda: cfg.get("log_level") == "DEBUG",
        on_debug_umschalten=debug_umschalten,
        modell_liste_fn=lambda: config.modelle_finden(cfg),
        aktives_modell_fn=lambda: cfg["llm"]["model"],
        on_modell_wechsel=modell_wechseln,
    )
    laufzeit["tray"] = tray_obj
    tray_obj.zustand_setzen("bereit")

    log.info("Bereit. Push-to-talk-Taste halten und sprechen.")
    # icon.run() blockiert den Hauptthread, bis "Beenden" im Tray-Menue
    # gewaehlt wird - alles andere (PTT-Listener, Audio, Verarbeitung) laeuft
    # bereits in eigenen Threads/Prozessen im Hintergrund.
    tray_obj.run()


if __name__ == "__main__":
    main()
