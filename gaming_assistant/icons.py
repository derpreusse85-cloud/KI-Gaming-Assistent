"""Zur Laufzeit gezeichnetes Tray-Icon - keine externe Bilddatei noetig.

Uebernommen als Vorlage aus dem Diktier-Tool (common/icons.py), auf ein
einziges Icon-Set reduziert (dort gab es getrennte Formen fuer Server/Client,
hier gibt es nur den einen Prozess).

Python-Hinweis: PIL (Pillow) ist eine Bildbearbeitungs-Bibliothek. Hier wird
kein Bild geladen, sondern eines komplett aus Formen (Kreis, Rechteck)
zusammengezeichnet.
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
    # Stilisiertes Mikrofon, wie beim Diktier-Client - macht auf einen Blick
    # klar, dass es sich um ein Sprach-Tool handelt.
    zeichner.rounded_rectangle((26, 16, 38, 38), radius=6, fill=(255, 255, 255, 235))
    zeichner.arc((20, 26, 44, 46), start=0, end=180, fill=(255, 255, 255, 235), width=4)
    zeichner.line((32, 46, 32, 52), fill=(255, 255, 255, 235), width=4)
    return bild
