"""Laden eines Spielprofils (YAML-Datei aus profiles/).

Format ist in Gaming_assistent.md, Abschnitt "Aktionslisten-Format" festgelegt:
ein YAML pro Spiel, ein Eintrag pro Tag mit schlagwort/beispiel/taste, optional
beschreibung (statt der wortgebundenen Standardbeschreibung) und optional eine
Taste, die waehrend der ganzen taste-Sequenz gehalten wird (halte_taste).

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

    schlagwort: str
    beispiel: str
    taste: list[str]
    # None = Standardbeschreibung ("nur wenn das Wort ... vorkommt") wird
    # spaeter in prompt.py erzeugt.
    beschreibung: str | None = None
    # Taste, die waehrend der taste-Sequenz gehalten wird (z.B. "ctrl" bei
    # Helldivers 2). Kommt normalerweise vom Profil, kann aber pro Tag
    # ueberschrieben werden.
    halte_taste: str | None = None


@dataclass
class Profil:
    name: str
    kontextlaenge: int
    tags: dict[str, TagEintrag] = field(default_factory=dict)

    def bekannte_tags(self) -> set[str]:
        """Menge aller gueltigen Tag-Namen - fuer den Parser (parser.py)."""
        return set(self.tags.keys())


def laden(pfad: Path) -> Profil:
    """Liest eine Profil-YAML-Datei ein und baut daraus ein Profil-Objekt."""
    with pfad.open(encoding="utf-8") as datei:
        rohdaten = yaml.safe_load(datei) or {}

    kontextlaenge = int(rohdaten.pop("kontextlaenge", 4096))
    # Profilweite Halte-Taste (z.B. "ctrl") - gilt als Vorgabe fuer jeden Tag,
    # der selbst keine eigene halte_taste angibt.
    profil_halte_taste = rohdaten.pop("halte_taste", None)

    tags: dict[str, TagEintrag] = {}
    for tag_name, eintrag in rohdaten.items():
        if not isinstance(eintrag, dict):
            # Ueberspringt z.B. reine Kommentarzeilen, die YAML nicht als
            # Dict einliest (sollte bei sauberem YAML nicht vorkommen).
            continue
        tags[tag_name] = TagEintrag(
            schlagwort=str(eintrag["schlagwort"]),
            beispiel=str(eintrag["beispiel"]),
            taste=[str(t) for t in eintrag["taste"]],
            beschreibung=eintrag.get("beschreibung"),
            halte_taste=eintrag.get("halte_taste", profil_halte_taste),
        )

    return Profil(name=pfad.stem, kontextlaenge=kontextlaenge, tags=tags)


def liste_profile(verzeichnis: Path) -> list[str]:
    """Namen (ohne .yaml) aller Profile im Profil-Verzeichnis, alphabetisch."""
    if not verzeichnis.exists():
        return []
    return sorted(p.stem for p in verzeichnis.glob("*.yaml"))
