"""Laden eines Spielprofils (YAML-Datei aus profiles/).

Format ist in Gaming_assistent.md, Abschnitt "Aktionslisten-Format" festgelegt:
ein YAML pro Spiel, ein Eintrag pro Tag mit beispiel/taste, dazu schlagwort
und/oder beschreibung (siehe unten), und optional eine Taste, die waehrend
der ganzen taste-Sequenz gehalten wird (halte_taste).

`schlagwort` und `beschreibung` haben zwei unabhaengige Aufgaben, die sich
nicht gegenseitig ausschliessen (11.09.2026, Nutzergespraech):
* `beschreibung` (falls gesetzt) steuert, wie das LLM den Tag im System-Prompt
  erklaert bekommt - frei formulierbar statt der wortgebundenen Standard-
  beschreibung. Ideal fuer Spiele mit wenigen, eindeutigen Kommandos, die
  keine Wortbindung brauchen (siehe "Aktionslisten-Format" in
  Gaming_assistent.md).
* `schlagwort` (falls gesetzt) speist unabhaengig davon die automatische
  Whisper-`initial_prompt`-Vokabelliste (siehe prompt.py). Praktisch auch
  bei einem Tag MIT `beschreibung`: steht dort z.B. ein Fremdwort, kann genau
  dieses Wort zusaetzlich als `schlagwort` eingetragen werden, nur damit es
  im initial_prompt landet - unabhaengig davon, ob es fuer die Klassifikation
  selbst gebraucht wird.
* Ein Tag braucht **mindestens eines von beiden** - fehlen beide, gibt es
  weder eine Klassifikations-Beschreibung noch ein initial_prompt-Wort, und
  `laden()` bricht mit einer klaren Fehlermeldung ab (siehe unten).

`schlagwort` darf in der YAML entweder ein einzelnes Wort (String) oder eine
Liste mehrerer gleichwertiger Woerter/Bezeichnungen sein (z.B. offizieller
Name und gaengiger Spitzname). Intern wird daraus immer eine Liste - siehe
TagEintrag.schlagwort unten.

Optionales Top-Level-Feld `initial_prompt_schlagwoerter`: eine kuratierte
Kurzliste fuer den Whisper-initial_prompt (siehe prompt.py), statt automatisch
ALLE Schlagwoerter zu verwenden. Grund: gemessen am 10.09.2026 kostet ein
laengerer initial_prompt bei diesem Whisper-Modell spuerbar Latenz (grob eine
Sekunde), waehrend die meisten Schlagwoerter normale deutsche Komposita sind,
die das deutsch trainierte Modell ohnehin zuverlaessig erkennt. Fehlt das
Feld, greift automatisch die alte Vorgabe (alle Schlagwoerter) - siehe
prompt.initial_prompt_bauen().

Optionales Top-Level-Feld `status_datei` (13.09.2026, nur fuers Elite-Dangerous-
Profil gebraucht): Pfad zu einer vom Spiel selbst laufend geschriebenen
Status-Datei (siehe ed_status.py). Ein Tag kann statt einer festen `taste`-
Liste ein `feuergruppe_ziel` (Ziel-Index einer Feuergruppe) angeben - die
noetige Tastensequenz wird dann erst zur Laufzeit anhand des in `status_datei`
gelesenen Ist-Zustands berechnet, statt fest in der YAML zu stehen. Hat
mindestens ein Tag `feuergruppe_ziel` gesetzt, muss `status_datei` im Profil
vorhanden sein, sonst bricht `laden()` mit klarer Fehlermeldung ab.

Python-Hinweis: "@dataclass" unten ist eine bequeme Kurzschreibweise fuer eine
Klasse, die nur Daten haelt - Python erzeugt __init__ usw. automatisch aus den
Feldern.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class TagEintrag:
    """Alle Angaben zu genau einem Tag (z.B. &&500kg_Bombe&&) aus dem Profil."""

    # Immer eine Liste, auch wenn die YAML nur ein einzelnes Wort angibt
    # (siehe _schlagwort_liste() beim Laden).
    schlagwort: list[str]
    beispiel: str
    taste: list[str]
    # None = Standardbeschreibung ("nur wenn das Wort ... vorkommt") wird
    # spaeter in prompt.py erzeugt.
    beschreibung: str | None = None
    # Taste, die waehrend der taste-Sequenz gehalten wird (z.B. "ctrl" bei
    # Helldivers 2). Kommt normalerweise vom Profil, kann aber pro Tag
    # ueberschrieben werden.
    halte_taste: str | None = None
    # Falls gesetzt: dieser Tag hat keine feste taste-Liste, sondern die
    # Tastensequenz wird zur Laufzeit aus Profil.status_datei berechnet
    # (siehe ed_status.py). Ziel-Index einer Feuergruppe (0=A, 1=B, ...).
    feuergruppe_ziel: int | None = None


@dataclass
class Profil:
    name: str
    kontextlaenge: int
    tags: dict[str, TagEintrag] = field(default_factory=dict)
    # Leere Liste = kein kuratierter initial_prompt hinterlegt, prompt.py
    # faellt dann auf "alle Schlagwoerter" zurueck.
    initial_prompt_schlagwoerter: list[str] = field(default_factory=list)
    # None = kein Tag im Profil braucht eine Status-Datei (siehe ed_status.py).
    status_datei: Path | None = None

    def bekannte_tags(self) -> set[str]:
        """Menge aller gueltigen Tag-Namen - fuer den Parser (parser.py)."""
        return set(self.tags.keys())


def _schlagwort_liste(wert) -> list[str]:
    """Normalisiert das schlagwort-Feld auf eine Liste - egal ob die YAML
    das Feld weglaesst (None), einen einzelnen String oder bereits eine
    Liste angibt."""
    if wert is None:
        return []
    if isinstance(wert, list):
        return [str(w) for w in wert]
    return [str(wert)]


def laden(pfad: Path) -> Profil:
    """Liest eine Profil-YAML-Datei ein und baut daraus ein Profil-Objekt."""
    with pfad.open(encoding="utf-8") as datei:
        rohdaten = yaml.safe_load(datei) or {}

    kontextlaenge = int(rohdaten.pop("kontextlaenge", 4096))
    # Profilweite Halte-Taste (z.B. "ctrl") - gilt als Vorgabe fuer jeden Tag,
    # der selbst keine eigene halte_taste angibt.
    profil_halte_taste = rohdaten.pop("halte_taste", None)
    initial_prompt_schlagwoerter = [str(w) for w in rohdaten.pop("initial_prompt_schlagwoerter", [])]
    status_datei_roh = rohdaten.pop("status_datei", None)
    status_datei = Path(status_datei_roh) if status_datei_roh else None

    tags: dict[str, TagEintrag] = {}
    for tag_name, eintrag in rohdaten.items():
        if not isinstance(eintrag, dict):
            # Ueberspringt z.B. reine Kommentarzeilen, die YAML nicht als
            # Dict einliest (sollte bei sauberem YAML nicht vorkommen).
            continue
        schlagwort = _schlagwort_liste(eintrag.get("schlagwort"))
        beschreibung = eintrag.get("beschreibung")
        if not schlagwort and not beschreibung:
            raise ValueError(
                f"Profil {pfad.name!r}, Tag {tag_name!r}: weder 'schlagwort' noch "
                "'beschreibung' angegeben - mindestens eines von beiden wird gebraucht "
                "(schlagwort fuers initial_prompt, beschreibung fuer den System-Prompt)."
            )
        feuergruppe_ziel = eintrag.get("feuergruppe_ziel")
        if feuergruppe_ziel is not None and status_datei is None:
            raise ValueError(
                f"Profil {pfad.name!r}, Tag {tag_name!r}: 'feuergruppe_ziel' gesetzt, aber "
                "kein 'status_datei'-Feld im Profil hinterlegt - wird gebraucht, um den "
                "aktuellen Spielzustand auszulesen."
            )
        tags[tag_name] = TagEintrag(
            schlagwort=schlagwort,
            beispiel=str(eintrag["beispiel"]),
            taste=[str(t) for t in eintrag["taste"]],
            beschreibung=beschreibung,
            halte_taste=eintrag.get("halte_taste", profil_halte_taste),
            feuergruppe_ziel=feuergruppe_ziel,
        )

    return Profil(
        name=pfad.stem,
        kontextlaenge=kontextlaenge,
        tags=tags,
        initial_prompt_schlagwoerter=initial_prompt_schlagwoerter,
        status_datei=status_datei,
    )


def liste_profile(verzeichnis: Path) -> list[str]:
    """Namen (ohne .yaml) aller Profile im Profil-Verzeichnis, alphabetisch."""
    if not verzeichnis.exists():
        return []
    return sorted(p.stem for p in verzeichnis.glob("*.yaml"))
