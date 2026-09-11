"""Baut den System-Prompt und den Whisper-initial_prompt aus einem Profil.

Beides wird komplett neu erzeugt, sobald ein anderes Profil gewaehlt wird (kein
spielübergreifender Basis-Prompt, siehe Gaming_assistent.md, Abschnitt
"Aktionslisten-Format").

Hinweis: Umlaute sind hier bewusst erlaubt (anders als im restlichen
Quelltext) - dieser Text geht als Prompt an das Sprachmodell, nicht in den
Python-Code selbst (siehe CLAUDE.md).
"""

from __future__ import annotations

import logging

from gaming_assistant.profile import Profil

log = logging.getLogger("prompt")

# Whisper beachtet ohnehin nur die letzten ~700 Zeichen des initial_prompt
# (siehe server/stt.py im Diktier-Tool, dieselbe Budget-Ueberlegung gilt hier).
_MAX_INITIAL_PROMPT_CHARS = 700

NONE_TAG = "NONE"


def system_prompt_bauen(profil: Profil) -> str:
    """Erzeugt den vollstaendigen System-Prompt fuer die LLM-Klassifikation.

    Aufbau (siehe Gaming_assistent.md, "LLM-Ausgabeformat"): kurzer Fliesstext
    statt Regelliste, ein Few-Shot-Beispiel pro Tag, ein einziges generisches
    Beispiel fuer Mehrfachbefehle (mit Platzhalter-Tags statt echten Namen) und
    eine explizite Regel fuer den Fall "kein Tag trifft zu".
    """
    zeilen: list[str] = [
        "Du ordnest gesprochene Anweisungen aus einem Spiel jeweils einem oder "
        "mehreren der folgenden Tags zu:",
        "",
    ]

    for tag_name, eintrag in profil.tags.items():
        if eintrag.beschreibung:
            beschreibung = eintrag.beschreibung
        elif len(eintrag.schlagwort) == 1:
            # Standard: wortgebundene Beschreibung, siehe "Bereits entschieden"
            # in Gaming_assistent.md (Praezision vor Vollstaendigkeit).
            beschreibung = f'nur wenn im Befehl das Wort "{eintrag.schlagwort[0]}" vorkommt'
        else:
            # Mehrere gleichwertige Woerter (z.B. offizieller Name + Spitzname).
            woerter = '" oder "'.join(eintrag.schlagwort)
            beschreibung = f'nur wenn im Befehl eines der Woerter "{woerter}" vorkommt'
        zeilen.append(f"&&{tag_name}&& - {beschreibung}")

    zeilen.append("")
    zeilen.append("Beispiele:")
    for tag_name, eintrag in profil.tags.items():
        zeilen.append(f'"{eintrag.beispiel}" -> &&{tag_name}&&')

    zeilen.append("")
    zeilen.append(
        "Nennt eine Aeusserung mehrere Aktionen, gib alle passenden Tags durch je "
        "ein Leerzeichen getrennt aus, in der genannten Reihenfolge, zum Beispiel: "
        '"mach zuerst A und dann B" -> &&AKTION_A&& &&AKTION_B&&.'
    )
    zeilen.append(
        f"Passt keine Aeusserung eindeutig zu einem der oben genannten Tags, "
        f"antworte ausschliesslich mit &&{NONE_TAG}&&. Rate niemals einen Tag, "
        f"wenn du dir nicht vollkommen sicher bist."
    )
    zeilen.append(
        "Antworte ausschliesslich mit dem oder den passenden Tags im Format "
        "&&TAG&&, ohne weiteren Text."
    )
    return "\n".join(zeilen)


def initial_prompt_bauen(profil: Profil) -> str:
    """Baut die Whisper-initial_prompt-Liste.

    Idee laut Gaming_assistent.md: Whisper bekommt ungewoehnliche Eigennamen
    vorab als Vokabular-Hinweis, bevor die LLM-Klassifikation ueberhaupt
    laeuft. Gemessen am 10.09.2026: ein laengerer initial_prompt kostet bei
    diesem Whisper-Modell spuerbar Latenz (grob eine Sekunde) - deshalb nutzt
    diese Funktion bevorzugt die kuratierte Kurzliste aus dem Profil
    (`initial_prompt_schlagwoerter`, nur echte Fremdwoerter/Akronyme/
    Eigennamen, die dem deutschen Modell erfahrungsgemaess eher Probleme
    machen als normale deutsche Komposita). Hat ein Profil diese Liste nicht
    gepflegt, faellt die Funktion auf die alte Vorgabe zurueck: alle
    Schlagwoerter automatisch sammeln.
    """
    if profil.initial_prompt_schlagwoerter:
        schlagwoerter = list(profil.initial_prompt_schlagwoerter)
    else:
        schlagwoerter = []
        for eintrag in profil.tags.values():
            for wort in eintrag.schlagwort:
                if wort not in schlagwoerter:
                    schlagwoerter.append(wort)

    text = ", ".join(schlagwoerter)
    if len(text) > _MAX_INITIAL_PROMPT_CHARS:
        log.warning(
            "initial_prompt fuer Profil %r gekuerzt: %d -> %d Zeichen",
            profil.name, len(text), _MAX_INITIAL_PROMPT_CHARS,
        )
        text = text[:_MAX_INITIAL_PROMPT_CHARS]
    return text
