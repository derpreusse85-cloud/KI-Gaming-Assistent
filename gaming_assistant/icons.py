"""Zur Laufzeit gezeichnetes Tray-Icon - keine externe Bilddatei noetig.

Uebernommen als Vorlage aus dem Diktier-Tool (common/icons.py), auf ein
einziges Icon-Set reduziert (dort gab es getrennte Formen fuer Server/Client,
hier gibt es nur den einen Prozess).

Python-Hinweis: PIL (Pillow) ist eine Bildbearbeitungs-Bibliothek. Hier wird
kein Bild geladen, sondern eines komplett aus Formen (Kreis, Rechteck, Ellipse)
zusammengezeichnet - diesmal ein stilisiertes Gamepad statt eines Mikrofons,
passend zum Gaming-Thema des Tools.
"""

from __future__ import annotations

from PIL import Image, ImageDraw

SIZE = 64

# (Fuellfarbe, Rahmenfarbe) je Zustand
_FARBEN = {
    "bereit": ((40, 170, 90), (16, 74, 40)),        # gruen: wartet auf PTT
    "aufnahme": ((214, 40, 40), (110, 20, 20)),     # rot: PTT gehalten, Aufnahme laeuft
    "fehler": ((214, 40, 40), (110, 20, 20)),       # rot: z.B. whisper-server nicht gestartet
    "startet": ((130, 130, 130), (70, 70, 70)),     # grau: noch nicht bereit
}


def icon(zustand: str = "bereit") -> Image.Image:
    fill, outline = _FARBEN.get(zustand, _FARBEN["bereit"])
    bild = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    zeichner = ImageDraw.Draw(bild)
    zeichner.ellipse((5, 5, SIZE - 5, SIZE - 5), fill=fill, outline=outline, width=4)
    weiss = (255, 255, 255, 235)
    # Stilisiertes Gamepad statt Mikrofon (Gaming-Thema): breiter Rumpf mit
    # zwei nach unten ausgebeulten Griffen (klassische Controller-Silhouette,
    # aehnlich dem 🎮-Emoji), D-Pad-Kreuz links, zwei Aktionsknoepfe rechts.
    zeichner.rounded_rectangle((15, 22, 49, 38), radius=8, fill=weiss)   # Rumpf (schmaler, passt besser in den Kreis)
    zeichner.ellipse((12, 28, 26, 44), fill=weiss)                      # linker Griff
    zeichner.ellipse((38, 28, 52, 44), fill=weiss)                      # rechter Griff
    # D-Pad-Kreuz (links im Rumpf)
    zeichner.line((18, 30, 26, 30), fill=fill, width=3)
    zeichner.line((22, 26, 22, 34), fill=fill, width=3)
    # Zwei Aktionsknoepfe (rechts im Rumpf)
    zeichner.ellipse((36, 25, 41, 30), fill=fill)
    zeichner.ellipse((43, 30, 48, 35), fill=fill)
    return bild
