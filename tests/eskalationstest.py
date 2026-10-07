"""Eskalationstest: Klassifikation mit stufenweise schwerer werdenden Aufgaben.

Baut die urspruengliche Testreihe vom 08.-09.09.2026 nach (siehe
Gaming_assistent.md, Abschnitt "Testreihe"), damit sie nicht wieder als
Wegwerf-Skript verloren geht. Laeuft gegen beliebig viele Modelle nacheinander
und zeigt das Ergebnis pro Stufe, damit man sieht, WO ein Modell einbricht.

Stufen:
  1  8 Tags Helldivers 2, frei formuliert (ohne "Ruf ...")
  2  13 Waffen-Stratageme, frei formuliert
  3  alle Tags Helldivers 2, je zwei Varianten aus Schlagwort + Satzrahmen
  4  Namens-Konfliktcluster mit Whisper-typischen Verhoerern und Alltagssaetzen
  5  Elite Dangerous: Mehrfachbefehle, Wiederholungen, Wartezeiten (Sleeps)
  6  frische Faelle (nach der Prompt-Optimierung vom Oktober 2026 NEU
     geschrieben, nie zum Abstimmen des Prompts benutzt): Helldivers 2,
     Elite Dangerous, Diablo 4 - zeigt, ob eine Prompt-Aenderung nur auf die
     Stufen 1-5 zugeschnitten ist

Aufruf (ohne Argumente: aktuelles Modell aus config.json):

    .venv\\Scripts\\python.exe tests\\eskalationstest.py
    .venv\\Scripts\\python.exe tests\\eskalationstest.py ^
        gemma-4-E4B-it-GGUF/gemma-4-E4B-it-Q4_K_M.gguf ^
        gemma-4-E2B-it-GGUF/gemma-4-E2B-it-Q4_K_M.gguf
"""

from __future__ import annotations

import copy
import statistics
import sys
import time
from pathlib import Path

_PROJEKT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJEKT_ROOT))

from gaming_assistant import config, parser, profile, prompt
from gaming_assistant.llama_proc import LlamaServer
from gaming_assistant.llm import LLMKlassifikator

Fall = tuple[str, list[str]]

# --- Stufe 1: 8 Tags, frei formuliert ---
STUFE1: list[Fall] = [
    ("Gib mir bitte mal das MG-43", ["MG43"]),
    ("Ich brauch den Orbitallaser", ["Orbital_Laser"]),
    ("Wirf die Hellbombe", ["Hellbombe"]),
    ("Schick Verstaerkung", ["Verstaerkung"]),
    ("Die Railgun bitte", ["Railgun"]),
    ("Ich will den Flammenwerfer", ["Flammenwerfer"]),
    ("Brauche Nachschub, Resupply", ["Resupply"]),
    ("Mach die 500 Kilo Bombe fertig", ["500kg_Bombe"]),
]

# --- Stufe 2: 13 Waffen-Stratageme ---
STUFE2: list[Fall] = [
    ("Gib mir das Anti-Materie-Gewehr", ["Antimateriegewehr"]),
    ("Ich nehm den Stalwart", ["Stalwart"]),
    ("EAT bitte", ["EAT"]),
    ("Das rueckstossfreie Gewehr", ["Rueckstossfreies_Gewehr"]),
    ("Autocannon", ["Automatische_Kanone"]),
    ("Das schwere Maschinengewehr her", ["Schweres_MG"]),
    ("Airburst Raketenwerfer", ["Luftdetonations_Raketenwerfer"]),
    ("Spear, aeh, den Speer", ["Speer"]),
    ("Gib mir den WASP", ["WASP"]),
    ("Granatwerfer bitte", ["Granatwerfer"]),
    ("Die Laserkanone", ["Laserkanone"]),
    ("Den Bogenwerfer rufen", ["Bogenwerfer"]),
    ("Quasarkanone, schnell", ["Quasarkanone"]),
]

# --- Stufe 3: Satzrahmen, automatisch auf alle Tags angewendet ---
SATZRAHMEN = [
    "Schnell, {x}!",
    "Ich brauche jetzt {x}",
    "{x} bitte",
    "Hey, kannst du {x} holen",
    "Los, {x}",
]


def stufe3_faelle(prof: profile.Profil) -> list[Fall]:
    faelle: list[Fall] = []
    i = 0
    for tag, eintrag in prof.tags.items():
        # Erstes Schlagwort plus (falls vorhanden) das letzte als Alternative.
        woerter = eintrag.schlagwort
        if not woerter:
            continue
        auswahl = [woerter[0]] + ([woerter[-1]] if len(woerter) > 1 else [])
        for wort in auswahl:
            faelle.append((SATZRAHMEN[i % len(SATZRAHMEN)].format(x=wort), [tag]))
            i += 1
    return faelle


# --- Stufe 4: Konfliktcluster, Verhoerer, Alltagssaetze ---
STUFE4: list[Fall] = [
    # Cluster A Gatling
    ("Gatling Orbitalsperrfeuer", ["Orbital_Gatling"]),
    ("Das Gatlinggeschuetz", ["Gatlinggeschuetz"]),
    # Cluster B Rauchbeschuss
    ("Orbital Rauchbeschuss", ["Orbital_Rauchbeschuss"]),
    ("Adler Rauchbeschuss", ["Adler_Rauchbeschuss"]),
    # Cluster C/H Kanonen
    ("Autocannon", ["Automatische_Kanone"]),
    ("Autocannon Geschuetz", ["Kanonengeschuetz"]),
    ("Die schwere MG-Stellung", ["MG_Stellung"]),
    ("Das MG-Geschuetz", ["MG_Geschuetz"]),
    # Cluster D Schildgenerator
    ("Schildgenerator Relais", ["Schildgenerator_Relais"]),
    ("Schildgenerator Rucksack", ["Schildgenerator_Rucksack"]),
    # Cluster E Guard Dog
    ("Guard Dog Rover", ["Guard_Dog_Rover"]),
    ("Guard Dog", ["Guard_Dog"]),
    ("Guard Dog Hunde-Atem", ["Guard_Dog_Hunde_Atem"]),
    # Cluster F Panzerabwehr
    ("Panzerabwehrkanone", ["EAT"]),
    ("Panzerabwehrminen", ["Panzerabwehrminen"]),
    ("Panzerabwehrstellung", ["Panzerabwehrstellung"]),
    # Cluster G Moerser
    ("Moersergeschuetz", ["Moersergeschuetz"]),
    ("EMP Moerser", ["EMP_Moersergeschuetz"]),
    # Cluster I Flammen
    ("Flammenwerfer", ["Flammenwerfer"]),
    ("Flammengeschuetz", ["Flammengeschuetz"]),
    # Whisper-Verhoerer (z.B. "Rufe autocennen" aus dem echten Test)
    ("Rufe autocennen", ["Automatische_Kanone"]),
    ("Ruf die Rail Gun", ["Railgun"]),
    ("Ruf den Tesla Turm", ["Tesla_Turm"]),
    ("Hol die Hellbomb", ["Hellbombe"]),
    # Mehrfachbefehle
    ("Ruf die Railgun und dann den Orbitallaser", ["Railgun", "Orbital_Laser"]),
    ("Hellbombe und danach Verstaerkung", ["Hellbombe", "Verstaerkung"]),
    # Alltagssaetze, die Schlagwoerter wie "Kommando"/"Speer" enthalten
    ("Wie ist das Wetter heute", []),
    ("Ich geh kurz Kaffee holen", []),
    ("Der Weihnachtsmann kommt bald", []),
    ("Nicht die Railgun, die andere", []),
]

# --- Stufe 5: Elite Dangerous, Mehrfachbefehle und Sleeps ---
STUFE5: list[Fall] = [
    ("Fahr das Fahrgestell aus und mach die Ladeluke auf", ["Fahrgestell", "Ladeluke"]),
    ("Erst die Ladeluke, dann das Fahrgestell", ["Ladeluke", "Fahrgestell"]),
    ("Waffen auf Maximum und die Hardpoints ausfahren", ["WaffenMAX", "Aufhaengungen"]),
    ("Oeffne die Ladeluke, warte 5 Sekunden, dann fahr das Fahrgestell aus",
     ["Ladeluke", "sleep:5", "Fahrgestell"]),
    ("Warte zwei Minuten und dann Boost", ["sleep:120", "Boost"]),
    ("Warte kurz, dann Heatsink", ["sleep:0", "Heatsink"]),
    ("Ladeluke dreimal oeffnen", ["Ladeluke", "Ladeluke", "Ladeluke"]),
    ("Oeffne die Frachtluke, dann das Landegestell, und wiederhole alles drei mal",
     ["Ladeluke", "Fahrgestell"] * 3),
    ("Fahrgestell ausfahren, 3 Sekunden warten, Ladeluke auf, 3 Sekunden warten, Schilde auf Maximum",
     ["Fahrgestell", "sleep:3", "Ladeluke", "sleep:3", "SchildeMAX"]),
    ("Mach die Ladeluke auf und warte danach 5 Sekunden", ["Ladeluke"]),
    ("Aktiviere Feuergruppe C und danach Feuergruppe A", ["FeuergruppeC", "FeuergruppeA"]),
    ("Erzaehl mir einen Witz", []),
]


# --- Stufe 6: frische Faelle (Holdout), je Profil ---
STUFE6_HD2: list[Fall] = [
    ("Wirf mir mal den Orbitallaser rueber", ["Orbital_Laser"]),
    ("Ich haette gern die Quasarkanone und danach den Tesla-Turm", ["Quasarkanone", "Tesla_Turm"]),
    ("Gib mir bitte den Guard Dog Rover, nicht den Hunde-Atem", ["Guard_Dog_Rover"]),
    ("Nein, doch kein Flammenwerfer", []),
    ("Ruf zweimal die 500 Kilo Bombe", ["500kg_Bombe", "500kg_Bombe"]),
    ("Schildgenerator Rucksack bitte", ["Schildgenerator_Rucksack"]),
    ("Napalm Orbitalsperrfeuer, schnell", ["Orbital_Napalm"]),
    ("Rufe das Raketengeschuetz", ["Raketengeschuetz"]),
    ("Mach den Datenupload und hol dann die Ueber-Erde-Flagge", ["Datenupload", "Ueber_Erde_Flagge"]),
    ("Panzerabwehrminen legen", ["Panzerabwehrminen"]),
    ("Der Kaffee ist kalt geworden", []),
    ("Emancipator Exoanzug", ["Emancipator_Exoanzug"]),
    ("Dreimal Resupply hintereinander", ["Resupply", "Resupply", "Resupply"]),
]
STUFE6_ED: list[Fall] = [
    ("Schilde auf Maximum und danach Boost", ["SchildeMAX", "Boost"]),
    ("Wirf einen Heatsink raus", ["Heatsink"]),
    ("Antrieb voll aufdrehen, dann zwei Sekunden warten und die Hardpoints ausfahren",
     ["AntriebMAX", "sleep:2", "Aufhaengungen"]),
    ("Doch nicht das Fahrgestell, sondern die Ladeluke", ["Ladeluke"]),
    ("Mach zweimal Boost", ["Boost", "Boost"]),
    ("Wiederhole Ladeluke und Fahrgestell zweimal", ["Ladeluke", "Fahrgestell", "Ladeluke", "Fahrgestell"]),
    ("Spring jetzt", ["Frameshiftdrive"]),
    ("Warte eine halbe Minute, dann Stop", ["sleep:30", "Stop"]),
    ("Feuergruppe B", ["FeuergruppeB"]),
]
STUFE6_D4: list[Fall] = [
    ("Trink einen Trank und oeffne dann die Karte", ["Trank", "Karte"]),
    ("Ich will nicht reiten, zeig mir den Skillbaum", ["Skillbaum"]),
    ("Zweimal Trank bitte", ["Trank", "Trank"]),
    ("Teleport in die Stadt", ["Stadtteleport"]),
]


def _lauf(klassifikator, system_prompt, bekannte, schlagwoerter, faelle):
    """Fuehrt Faelle aus, liefert (Fehlerliste, Zeiten)."""
    fehler, zeiten = [], []
    for text, erwartet in faelle:
        t0 = time.perf_counter()
        antwort, finish = klassifikator.klassifizieren(text, system_prompt, "gaming-llm")
        zeiten.append(time.perf_counter() - t0)
        tags = parser.tags_extrahieren(antwort, bekannte, finish, schlagwoerter)
        if tags != erwartet:
            fehler.append((text, tags, erwartet, antwort.strip()))
    return fehler, zeiten


def modell_testen(cfg: dict, modell: str) -> dict:
    cfg = copy.deepcopy(cfg)
    cfg["llm"]["model"] = modell
    verzeichnis = config.profil_verzeichnis(cfg)
    stufen: dict[str, dict] = {}

    for profilname, stufendefs in [
        ("Helldivers2", None),
        ("EliteDangerous", [("5 Elite Dangerous Mehrfach/Sleep", STUFE5),
                            ("6b frisch Elite Dangerous", STUFE6_ED)]),
        ("Diablo4", [("6c frisch Diablo 4", STUFE6_D4)]),
    ]:
        prof = profile.laden(verzeichnis / f"{profilname}.yaml")
        if stufendefs is None:
            stufendefs = [
                ("1 Grundtags (8)", STUFE1),
                ("2 Waffen (13)", STUFE2),
                ("3 alle Tags, Satzrahmen", stufe3_faelle(prof)),
                ("4 Konflikte/Verhoerer/Alltag", STUFE4),
                ("6a frisch Helldivers 2", STUFE6_HD2),
            ]
        system_prompt = prompt.system_prompt_bauen(prof)
        server = LlamaServer(cfg)
        server.start(prof.kontextlaenge)
        klassifikator = LLMKlassifikator(cfg)
        try:
            # Ersten Aufruf (Cold-Start) separat ausserhalb der Zeitstatistik.
            klassifikator.klassifizieren("Hallo", system_prompt, "gaming-llm")
            for name, faelle in stufendefs:
                fehler, zeiten = _lauf(klassifikator, system_prompt, prof.bekannte_tags(), prof.schlagwort_zuordnung(), faelle)
                stufen[name] = {"gesamt": len(faelle), "fehler": fehler, "zeiten": zeiten}
                print(f"  Stufe {name}: {len(faelle) - len(fehler)}/{len(faelle)}", flush=True)
        finally:
            klassifikator.close()
            server.stop()
    return stufen


def main() -> int:
    cfg = config.load()
    modelle = sys.argv[1:] or [cfg["llm"]["model"]]
    alle = {}
    for modell in modelle:
        print(f"\n### {modell}", flush=True)
        alle[modell] = modell_testen(cfg, modell)

    print("\n\n===== ZUSAMMENFASSUNG =====")
    for modell, stufen in alle.items():
        zeiten = [z for s in stufen.values() for z in s["zeiten"]]
        richtig = sum(s["gesamt"] - len(s["fehler"]) for s in stufen.values())
        gesamt = sum(s["gesamt"] for s in stufen.values())
        print(f"\n{modell}\n  Gesamt: {richtig}/{gesamt}, Latenz Median {statistics.median(zeiten):.3f}s")
        for name, s in stufen.items():
            print(f"  Stufe {name}: {s['gesamt'] - len(s['fehler'])}/{s['gesamt']}")
        for name, s in stufen.items():
            for text, tags, erwartet, roh in s["fehler"]:
                print(f"    ABWEICHUNG [{name}] {text!r} -> {tags} erwartet {erwartet} (Rohantwort: {roh})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
