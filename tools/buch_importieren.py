#!/usr/bin/env python3
"""Farbkombinationen aus Sanzo Wadas „A Dictionary of Color Combinations“
(配色事典) in Lampenfarben umrechnen.

Erzeugt homeassistant/custom_templates/lichtstimmung_buch.jinja und schlägt
passende Kombinationen je Stimmung vor:

    python3 tools/buch_importieren.py            # Datei erzeugen
    python3 tools/buch_importieren.py --vorschlaege

Die Nummern (1–348) sind die Nummern aus dem Buch: 1–120 haben zwei Farben,
121–240 drei, 241–348 vier.

Druckfarben sind Oberflächen, Lampen leuchten. Deshalb:
- Farbton bleibt, Sättigung wird leicht angehoben (blasse Druckfarben würden
  sonst als fast weißes Licht erscheinen).
- Dunkle Farben werden zu gedimmtem Licht (Faktor für die Helligkeit).
- Helle Neutraltöne (Weiß, Elfenbein) werden zu warmweißem Licht.
- Schwarz und Grau lassen sich nicht leuchten und entfallen. Bleiben danach
  weniger als zwei unterscheidbare Farben übrig, ist die Kombination für
  Lampen ungeeignet und wird nicht übernommen.
"""

import colorsys
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATEN = REPO / "tools" / "wada" / "colors.json"
ZIEL = REPO / "homeassistant" / "custom_templates" / "lichtstimmung_buch.jinja"


def lade_kombinationen():
    farben = json.loads(DATEN.read_text(encoding="utf-8"))
    kombis = {}
    for farbe in farben:
        for nr in farbe["combinations"]:
            kombis.setdefault(nr, []).append(farbe)
    return dict(sorted(kombis.items()))


def als_licht(farbe):
    """Druckfarbe -> {'h': Farbton, 's': Sättigung %, 'f': Helligkeitsfaktor} oder None."""
    r, g, b = (x / 255 for x in farbe["rgb"])
    h, s, _v = colorsys.rgb_to_hsv(r, g, b)
    hell, a, bb = farbe["lab"]
    buntheit = math.hypot(a, bb)
    if buntheit < 9 or s < 0.1:
        if hell >= 70:  # Weiß, Elfenbein, helles Grau -> warmweiß
            return {"h": 40, "s": 12, "f": round(0.55 + 0.45 * hell / 100, 2), "weiss": True}
        return None  # Schwarz, Grau
    return {
        "h": round(h * 360) % 360,
        "s": min(100, round(100 * s**0.75)),
        "f": round(0.45 + 0.55 * hell / 100, 2),
        "weiss": False,
        "L": hell,
    }


def unterscheidbar(a, b):
    if a["weiss"] != b["weiss"]:
        return True
    dh = abs(a["h"] - b["h"]) % 360
    return min(dh, 360 - dh) >= 12 or abs(a["s"] - b["s"]) >= 25


def lampen_kombinationen():
    ergebnis = {}
    for nr, farben in lade_kombinationen().items():
        licht = [l for l in (als_licht(f) for f in farben) if l]
        verschieden = any(
            unterscheidbar(licht[i], licht[j])
            for i in range(len(licht))
            for j in range(i + 1, len(licht))
        )
        if len(licht) >= 2 and verschieden:
            ergebnis[nr] = licht
    return ergebnis


# ---------------------------------------------------------------- Stimmungen
def _bunt(licht):
    return [l for l in licht if not l["weiss"]]


def _im(h, von, bis):
    return von <= h <= bis if von <= bis else (h >= von or h <= bis)


def ist_cozy(licht):
    bunt = _bunt(licht)
    return (
        len(bunt) >= 2
        and all(_im(l["h"], 340, 50) for l in bunt)  # Oliv wird als Licht limettengrün
        and any(l["s"] >= 45 for l in bunt)
        and 30 <= sum(l["L"] for l in bunt) / len(bunt) <= 80
    )


def ist_cyberpunk(licht):
    bunt = _bunt(licht)
    return (
        all(_im(l["h"], 170, 10) for l in bunt)  # kein Gelb, Orange, Grün
        and any(_im(l["h"], 265, 340) and l["s"] >= 40 for l in bunt)
        and any(_im(l["h"], 170, 250) and l["s"] >= 40 for l in bunt)
    )


def ist_ruhig(licht):
    bunt = _bunt(licht)
    return (
        len(bunt) >= 1
        and all(l["s"] <= 55 and l["L"] >= 50 for l in bunt)
        and not any(_im(l["h"], 45, 100) and l["s"] > 35 for l in bunt)  # kein Limettengrün
        and any(_im(l["h"], 100, 280) for l in bunt)
        and max(l["L"] for l in bunt) - min(l["L"] for l in bunt) <= 35
    )


def ist_regen(licht):
    bunt = _bunt(licht)
    return (
        len(bunt) >= 2
        and all(_im(l["h"], 160, 290) for l in bunt)
        and any(l["L"] <= 55 for l in bunt)
        and any(l["s"] >= 30 for l in bunt)
    )


def ist_sonnenuntergang(licht):
    bunt = _bunt(licht)
    return (
        all(_im(l["h"], 280, 50) for l in bunt)
        and any(_im(l["h"], 290, 355) and l["s"] >= 35 for l in bunt)
        and any(_im(l["h"], 10, 50) and l["s"] >= 50 for l in bunt)
    )


def ist_ozean(licht):
    bunt = _bunt(licht)
    return (
        len(bunt) >= 2
        and all(_im(l["h"], 150, 235) for l in bunt)
        and any(_im(l["h"], 160, 200) and l["s"] >= 45 for l in bunt)
    )


def ist_nordlicht(licht):
    bunt = _bunt(licht)
    return (
        all(_im(l["h"], 90, 330) for l in bunt)
        and any(_im(l["h"], 100, 185) and l["s"] >= 30 for l in bunt)
        and any(_im(l["h"], 235, 330) and l["s"] >= 25 for l in bunt)
    )


def ist_wald(licht):
    bunt = _bunt(licht)
    return (
        len(bunt) >= 2
        and all(_im(l["h"], 15, 170) for l in bunt)
        and sum(_im(l["h"], 75, 170) for l in bunt) >= 1
        and sum(_im(l["h"], 15, 45) for l in bunt) >= 1
        and all(l["L"] <= 75 for l in bunt)
    )


STIMMUNGEN = {
    "Cozy": ist_cozy,
    "Cyberpunk": ist_cyberpunk,
    "Ruhig": ist_ruhig,
    "Regen / Gewitter": ist_regen,
    "Sonnenuntergang": ist_sonnenuntergang,
    "Ozean": ist_ozean,
    "Nordlicht": ist_nordlicht,
    "Wald": ist_wald,
}


def vorschlaege(kombis):
    return {name: [nr for nr, l in kombis.items() if test(l)] for name, test in STIMMUNGEN.items()}


# ---------------------------------------------------------------- Ausgabe
def jinja_inhalt(kombis):
    zeilen = []
    for nr, licht in kombis.items():
        werte = ", ".join(f"[{l['h']}, {l['s']}, {l['f']}]" for l in licht)
        zeilen.append(f"  {nr}: [{werte}],")
    inhalt = (
        "{#- =========================================================================\n"
        "  FARBWÖRTERBUCH – automatisch erzeugt von tools/buch_importieren.py\n"
        "  NICHT von Hand bearbeiten.\n"
        "\n"
        "  Kombinationen aus „A Dictionary of Color Combinations“ (配色事典) von\n"
        "  Sanzo Wada (1883–1967), Seigensha. Farbdaten: github.com/mattdesl/\n"
        "  dictionary-of-colour-combinations (MIT, © 2020 Matt DesLauriers).\n"
        "\n"
        "  Nr. im Buch: [[Farbton 0–360, Sättigung 0–100, Helligkeitsfaktor], …]\n"
        f"  {len(kombis)} von 348 Kombinationen sind als Licht geeignet; die übrigen\n"
        "  bestehen v. a. aus Schwarz/Grau und fehlen hier absichtlich.\n"
        "========================================================================= -#}\n"
        "{%- set BUCH = {\n" + "\n".join(zeilen) + "\n} -%}\n"
    )
    return inhalt


def schreibe_jinja(kombis):
    ZIEL.write_text(jinja_inhalt(kombis), encoding="utf-8")


def main():
    kombis = lampen_kombinationen()
    if "--vorschlaege" in sys.argv:
        for name, nummern in vorschlaege(kombis).items():
            print(f"{name} ({len(nummern)}): {nummern}")
        return
    schreibe_jinja(kombis)
    print(f"{ZIEL.relative_to(REPO)}: {len(kombis)} von 348 Kombinationen übernommen")


if __name__ == "__main__":
    main()
