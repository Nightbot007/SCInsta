"""Verhaltenstests der Lichtstimmung gegen ein echtes Home Assistant."""

import asyncio
import re
import sys
from datetime import timedelta

import pytest
from homeassistant.helpers.template import Template
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from conftest import BLITZ_LAMPEN, LAMPEN, LAMPEN_IDS, NACHSENDE_LAMPEN, REPO, richte_ein

sys.path.insert(0, str(REPO / "tools"))
import buch_importieren  # noqa: E402

FARBLAMPEN = LAMPEN_IDS  # alle deine Lampen können Farbe
MODI = ["Cozy", "Cyberpunk", "Ruhig", "Regen / Gewitter", "Farbwörterbuch"]
BUCH = buch_importieren.lampen_kombinationen()


# --------------------------------------------------------------------------- Hilfen
async def fertig(hass):
    """Warten, bis alle Automationen durch sind (Template-Sensoren folgen einen Tick später)."""
    for _ in range(3):
        await hass.async_block_till_done(wait_background_tasks=True)


async def taste(hass):
    await hass.services.async_call(
        "input_button", "press", {"entity_id": "input_button.lichtstimmung_taste"}, blocking=True
    )
    await fertig(hass)


async def licht(hass, aktion, entity_id, **daten):
    await hass.services.async_call(
        "light", f"turn_{aktion}", {"entity_id": entity_id, **daten}, blocking=True
    )
    await fertig(hass)


async def skript(hass, skriptname, **daten):
    await hass.services.async_call("script", skriptname, daten, blocking=True)
    await fertig(hass)


async def waehle(hass, option):
    await hass.services.async_call(
        "input_select",
        "select_option",
        {"entity_id": "input_select.lichtstimmung_modus", "option": option},
        blocking=True,
    )
    await fertig(hass)


def zustand(hass):
    return hass.states.get("sensor.lichtstimmung_zustand")


def modus(hass):
    return zustand(hass).state


def auswahl(hass):
    return hass.states.get("input_select.lichtstimmung_modus")


def farbton(hass, entity_id):
    return hass.states.get(entity_id).attributes["hs_color"][0]


def ist_an(hass, entity_id):
    return hass.states.get(entity_id).state == "on"


def flag(hass):
    return hass.states.get("input_boolean.lichtstimmung_wechsel_faellig").state


def hs(hass, entity_id):
    h, s = hass.states.get(entity_id).attributes["hs_color"]
    return round(h), round(s)


def quelle(hass):
    return zustand(hass).attributes["quelle"]


def gleiche_farbe(ist, soll, farbton_tol=3.0, saettigung_tol=6.0):
    """Hue (xy) und Govee (rgb) bekommen umgerechnete Farben. Home Assistants Umrechnung
    hs -> xy -> hs weicht gemessen um bis zu 2,7° Farbton und 5,1 % Sättigung ab.
    Bei fast weißem Licht ist der Farbton unscharf und bekommt mehr Spielraum."""
    dh = abs(ist[0] - soll[0]) % 360
    if min(ist[1], soll[1]) < 20:
        farbton_tol = 25
    return min(dh, 360 - dh) <= farbton_tol and abs(ist[1] - soll[1]) <= saettigung_tol


def folgt_dem_plan(hass):
    """Jede eingeschaltete Lampe leuchtet genau so, wie im Zustand gespeichert."""
    plan = zustand(hass).attributes["zuweisung"]
    for l in LAMPEN_IDS:
        w = plan[l]
        assert ist_an(hass, l) == w["an"], l
        if w.get("hs"):
            ist = hass.states.get(l).attributes["hs_color"]
            assert gleiche_farbe(ist, w["hs"]), (l, ist, w["hs"])
            assert round(hass.states.get(l).attributes["brightness"] / 2.55) == w["hell"], l
        if w.get("kelvin"):
            assert hass.states.get(l).attributes["color_temp_kelvin"] == w["kelvin"], l


def nah_an(h, farbtoene, toleranz):
    return any(min(abs(h - f) % 360, 360 - abs(h - f) % 360) <= toleranz for f in farbtoene)


def anpassen(modus, ersatz):
    """Ersetzt in der Jinja den Block eines Modus bis 'hell' (für gezielte Tests)."""

    def f(jinja):
        neu, n = re.subn(
            rf"('{re.escape(modus)}': \{{\n).*?(\n    'hell')", rf"\g<1>{ersatz}\g<2>", jinja, count=1, flags=re.S
        )
        assert n == 1
        return neu

    return f


def im_bereich(h, von, bis, toleranz=10):
    """Farbton (mit Streuung) liegt im Bereich der Palette, auch über 0° hinweg."""
    von, bis = (von - toleranz) % 360, (bis + toleranz) % 360
    return von <= h <= bis if von <= bis else (h >= von or h <= bis)


# --------------------------------------------------------------------------- Tests
async def test_einrichtung_und_konfig_check(lichtstimmung):
    hass = lichtstimmung
    assert auswahl(hass).attributes["options"] == MODI
    bericht = Template(
        "{% from 'lichtstimmung.jinja' import pruefen %}{{ pruefen() }}", hass
    ).async_render()
    assert "❌" not in bericht and "⚠️" not in bericht, bericht
    assert "light.hue_play_3 [play, blitzt]: off · Farbe" in bericht
    assert "light.h6079 [steh, sendet nach]: off · Farbe" in bericht
    assert "light.3_hdmi_2_1_fancy_sync_box [tv, sendet nach]: off · Farbe" in bericht
    assert "Sonnenuntergang (inaktiv)" in bericht
    assert f"Farbwörterbuch: {len(BUCH)} Kombinationen als Licht geeignet" in bericht
    assert "- Cozy: 26 aus dem Buch, 1 eigene" in bericht
    assert f"- Farbwörterbuch: {len(BUCH)} aus dem Buch, 0 eigene" in bericht


async def test_taste_schaltet_alles_an_mit_passenden_unterschiedlichen_farben(lichtstimmung):
    hass = lichtstimmung
    await taste(hass)
    assert all(ist_an(hass, l) for l in LAMPEN_IDS)
    assert modus(hass) == "Cozy"
    assert re.fullmatch(r"Buch Nr\. \d+|Eigene Palette 1", quelle(hass)), quelle(hass)
    folgt_dem_plan(hass)
    farben = [hs(hass, l) for l in FARBLAMPEN]
    assert len(set(farben)) >= 2, farben  # nie alle gleich
    # Cozy: nur warme Töne (Rot bis Gelb) oder warmweiß
    assert all(im_bereich(h, 340, 50, toleranz=4) or s <= 20 for h, s in farben), farben
    assert 1 <= round(hass.states.get("light.h6079").attributes["brightness"] / 2.55) <= 60
    assert flag(hass) == "off"


async def test_alles_aus_ueber_taste_wechselt_beim_naechsten_einschalten(lichtstimmung):
    hass = lichtstimmung
    await taste(hass)  # an – Cozy
    await taste(hass)  # aus
    assert not any(ist_an(hass, l) for l in LAMPEN_IDS)
    assert flag(hass) == "on"
    assert modus(hass) == "Cozy"  # wechselt erst beim Einschalten

    await taste(hass)  # an – nächster Modus
    assert modus(hass) == "Cyberpunk"
    assert auswahl(hass).state == "Cyberpunk"
    assert flag(hass) == "off"
    folgt_dem_plan(hass)
    # Cyberpunk: Blau, Türkis, Violett, Magenta, Pink, Karmin – kein Gelb/Grün
    assert all(im_bereich(h, 165, 15, toleranz=6) or s <= 20 for h, s in (hs(hass, l) for l in FARBLAMPEN))

    await taste(hass)
    await taste(hass)
    assert modus(hass) == "Ruhig"
    await taste(hass)
    await taste(hass)
    assert modus(hass) == "Regen / Gewitter"
    assert all(ist_an(hass, l) for l in LAMPEN_IDS)
    await taste(hass)
    await taste(hass)
    assert modus(hass) == "Farbwörterbuch"
    assert quelle(hass).startswith("Buch Nr. ")
    folgt_dem_plan(hass)
    await taste(hass)
    await taste(hass)
    assert modus(hass) == "Cozy"  # einmal rum


async def test_einzelne_lampen_aendern_den_modus_nie(lichtstimmung):
    hass = lichtstimmung
    await taste(hass)
    farben = {l: farbton(hass, l) for l in FARBLAMPEN}

    await licht(hass, "off", "light.h6079")
    await licht(hass, "on", "light.h6079")
    assert modus(hass) == "Cozy"
    assert farbton(hass, "light.h6079") == farben["light.h6079"]

    # Alle Lampen einzeln aus – das ist NICHT die Taste.
    for l in LAMPEN_IDS:
        await licht(hass, "off", l)
    assert flag(hass) == "off"
    await licht(hass, "on", "light.3_hdmi_2_1_fancy_sync_box")
    assert modus(hass) == "Cozy"

    # Taste schaltet alles wieder in derselben Stimmung und Verteilung ein.
    await taste(hass)  # TV-Backlight ist an -> aus
    await taste(hass)  # an
    assert modus(hass) == "Cyberpunk"  # weil die Taste davor alles ausgemacht hat

    for l in LAMPEN_IDS:
        await licht(hass, "off", l)
    await taste(hass)
    assert modus(hass) == "Cyberpunk"
    folgt_dem_plan(hass)


async def test_nach_taste_aus_startet_auch_eine_einzelne_lampe_den_neuen_modus(lichtstimmung):
    hass = lichtstimmung
    await taste(hass)  # Cozy
    await taste(hass)  # alles aus

    await licht(hass, "on", "light.h6079")
    assert modus(hass) == "Cyberpunk"
    assert flag(hass) == "off"
    assert gleiche_farbe(
        hass.states.get("light.h6079").attributes["hs_color"],
        zustand(hass).attributes["zuweisung"]["light.h6079"]["hs"],
    )
    assert not ist_an(hass, "light.3_hdmi_2_1_fancy_sync_box")
    assert set(zustand(hass).attributes["offen"]) == set(LAMPEN_IDS) - {"light.h6079"}

    # Eine weitere Lampe bekommt beim Einschalten ihre Cyberpunk-Farbe.
    await licht(hass, "on", "light.3_hdmi_2_1_fancy_sync_box")
    plan = zustand(hass).attributes["zuweisung"]
    assert gleiche_farbe(
        hass.states.get("light.3_hdmi_2_1_fancy_sync_box").attributes["hs_color"],
        plan["light.3_hdmi_2_1_fancy_sync_box"]["hs"],
    )
    assert "light.3_hdmi_2_1_fancy_sync_box" not in zustand(hass).attributes["offen"]
    assert modus(hass) == "Cyberpunk"


async def test_modus_im_dashboard_waehlen(lichtstimmung):
    hass = lichtstimmung
    await taste(hass)  # Cozy
    await waehle(hass, "Ruhig")
    assert modus(hass) == "Ruhig"
    folgt_dem_plan(hass)

    # Nach „Alles aus“ eine Auswahl treffen: die Wahl gilt, kein weiterer Wechsel.
    await taste(hass)
    assert flag(hass) == "on"
    await waehle(hass, "Cozy")
    assert flag(hass) == "off"
    await taste(hass)
    assert modus(hass) == "Cozy"
    assert all(ist_an(hass, l) for l in LAMPEN_IDS)


async def test_neu_wuerfeln_gibt_neue_verteilung(lichtstimmung):
    hass = lichtstimmung
    await taste(hass)
    vorher = zustand(hass).attributes["stand"]
    varianten, quellen = set(), [quelle(hass)]
    for _ in range(8):
        await skript(hass, "lichtstimmung_neu_wuerfeln")
        folgt_dem_plan(hass)
        varianten.add(tuple(hs(hass, l) for l in FARBLAMPEN))
        quellen.append(quelle(hass))
    assert zustand(hass).attributes["stand"] != vorher
    assert modus(hass) == "Cozy"
    assert len(varianten) > 1
    assert all(a != b for a, b in zip(quellen, quellen[1:])), quellen  # nie zweimal hintereinander


async def test_favorit_speichern_abrufen_und_loeschen(lichtstimmung):
    hass = lichtstimmung
    await taste(hass)  # Cozy
    herkunft = quelle(hass)
    await licht(hass, "on", "light.h6079", hs_color=[5, 100], brightness=200)
    await hass.services.async_call(
        "input_text",
        "set_value",
        {"entity_id": "input_text.lichtstimmung_favorit_name", "value": "Abendrot"},
        blocking=True,
    )
    await skript(hass, "lichtstimmung_favorit_speichern")

    fav = hass.states.get("sensor.lichtstimmung_favoriten")
    assert fav.state == "1"
    assert fav.attributes["favoriten"]["Abendrot"]["basis"] == "Cozy"
    assert fav.attributes["favoriten"]["Abendrot"]["quelle"] == herkunft
    lampen = fav.attributes["favoriten"]["Abendrot"]["lampen"]
    assert lampen["light.hue_play_3"].keys() == {"an", "xy", "bri"}  # Hue
    assert lampen["light.h6079"].keys() == {"an", "rgb", "bri"}  # Govee
    assert lampen["light.synced_fancyleds"].keys() == {"an", "hs", "bri"}  # Tuya
    assert "★ Abendrot" in auswahl(hass).attributes["options"]
    assert auswahl(hass).state == "★ Abendrot"
    assert modus(hass) == "★ Abendrot"
    assert hass.states.get("input_text.lichtstimmung_favorit_name").state == ""
    gespeichert = {l: hass.states.get(l).attributes["hs_color"] for l in FARBLAMPEN}
    assert gleiche_farbe(gespeichert["light.h6079"], (5, 100))

    await waehle(hass, "Cyberpunk")
    assert not gleiche_farbe(hass.states.get("light.h6079").attributes["hs_color"], (5, 100))

    await waehle(hass, "★ Abendrot")
    for l in FARBLAMPEN:
        # exakt – Favoriten speichern die Farbe im Format der Lampe (xy/rgb/hs)
        assert hass.states.get(l).attributes["hs_color"] == gespeichert[l], l
    assert hass.states.get("light.h6079").attributes["brightness"] == 200
    assert quelle(hass) == herkunft

    # Aktiven Favoriten löschen: Auswahl springt auf den ersten Modus, Lampen bleiben.
    vorher = {l: hass.states.get(l).attributes["hs_color"] for l in FARBLAMPEN}
    await skript(hass, "lichtstimmung_favorit_loeschen")
    assert "★ Abendrot" not in auswahl(hass).attributes["options"]
    assert auswahl(hass).state == "Cozy"
    assert hass.states.get("sensor.lichtstimmung_favoriten").state == "0"
    assert {l: hass.states.get(l).attributes["hs_color"] for l in FARBLAMPEN} == vorher


async def test_favorit_ohne_namen_und_ohne_licht(lichtstimmung):
    hass = lichtstimmung
    await skript(hass, "lichtstimmung_favorit_speichern")  # alles aus
    assert hass.states.get("sensor.lichtstimmung_favoriten").state in ("unknown", "0")

    await taste(hass)
    await skript(hass, "lichtstimmung_favorit_speichern")
    namen = list(hass.states.get("sensor.lichtstimmung_favoriten").attributes["favoriten"])
    assert len(namen) == 1 and namen[0].startswith("Cozy ")


async def test_favoriten_im_wechsel_und_zufall(lichtstimmung):
    hass = lichtstimmung
    await taste(hass)
    await skript(hass, "lichtstimmung_favorit_speichern", name="Liebling")
    assert modus(hass) == "★ Liebling"

    # Ohne „Favoriten im Wechsel“: vom Favoriten geht es mit dem nächsten Modus weiter.
    await taste(hass)
    await taste(hass)
    assert modus(hass) == "Cozy"
    for erwartet in ("Cyberpunk", "Ruhig", "Regen / Gewitter", "Farbwörterbuch", "Cozy"):
        await taste(hass)
        await taste(hass)
        assert modus(hass) == erwartet

    await hass.services.async_call(
        "input_boolean",
        "turn_on",
        {"entity_id": "input_boolean.lichtstimmung_favoriten_im_wechsel"},
        blocking=True,
    )
    for erwartet in ("Cyberpunk", "Ruhig", "Regen / Gewitter", "Farbwörterbuch", "★ Liebling", "Cozy"):
        await taste(hass)
        await taste(hass)
        assert modus(hass) == erwartet

    await hass.services.async_call(
        "input_boolean", "turn_on", {"entity_id": "input_boolean.lichtstimmung_zufall"}, blocking=True
    )
    for _ in range(8):
        alt = modus(hass)
        await taste(hass)
        await taste(hass)
        assert modus(hass) != alt


async def test_gewitter_blitze(lichtstimmung, freezer):
    hass = lichtstimmung
    await taste(hass)
    await waehle(hass, "Regen / Gewitter")
    assert hass.states.get("binary_sensor.lichtstimmung_blitze_aktiv").state == "off"

    blitze = []

    def merke(event):
        daten = event.data["service_data"]
        if event.data["domain"] == "light" and daten.get("color_temp_kelvin") == 6500:
            ziele = daten["entity_id"]
            blitze.append([ziele] if isinstance(ziele, str) else list(ziele))

    hass.bus.async_listen("call_service", merke)
    def bild():
        return {
            l: (a.get("hs_color"), a.get("color_temp_kelvin"), a.get("brightness"))
            for l in LAMPEN_IDS
            if ist_an(hass, l)
            for a in [hass.states.get(l).attributes]
        }

    vorher = bild()

    # Ab hier läuft die Blitz-Schleife endlos (mit Pausen). async_block_till_done
    # würde auf ihr Ende warten – daher nur ein paar Event-Loop-Takte.
    async def takte():
        for _ in range(50):
            await asyncio.sleep(0)

    await hass.services.async_call(
        "input_boolean", "turn_on", {"entity_id": "input_boolean.lichtstimmung_effekte"}, blocking=True
    )
    await takte()
    assert hass.states.get("binary_sensor.lichtstimmung_blitze_aktiv").state == "on"

    async def zeit_vor(sekunden):
        for _ in range(int(sekunden * 10)):
            freezer.tick(timedelta(milliseconds=100))
            async_fire_time_changed(hass)
            await takte()

    await zeit_vor(65)
    assert blitze, "kein Blitz innerhalb von 65 s"
    assert all(set(ziele) <= set(vorher) for ziele in blitze)
    assert all(set(ziele) <= BLITZ_LAMPEN for ziele in blitze), blitze  # nur Hue blitzt
    await zeit_vor(3)  # Blitz-Sequenz zu Ende
    assert bild() == vorher

    # Schalter aus -> Schleife endet nach der laufenden Pause.
    await hass.services.async_call(
        "input_boolean", "turn_off", {"entity_id": "input_boolean.lichtstimmung_effekte"}, blocking=True
    )
    await takte()
    assert hass.states.get("binary_sensor.lichtstimmung_blitze_aktiv").state == "off"
    anzahl = len(blitze)
    await zeit_vor(65)
    assert len(blitze) == anzahl
    assert hass.states.get("automation.lichtstimmung_gewitter_blitze").attributes["current"] == 0

    # Blitze nur im Gewitter-Modus.
    await hass.services.async_call(
        "input_boolean", "turn_on", {"entity_id": "input_boolean.lichtstimmung_effekte"}, blocking=True
    )
    await takte()
    await zeit_vor(1)
    await hass.services.async_call(
        "input_select",
        "select_option",
        {"entity_id": "input_select.lichtstimmung_modus", "option": "Cozy"},
        blocking=True,
    )
    await zeit_vor(65)
    assert hass.states.get("binary_sensor.lichtstimmung_blitze_aktiv").state == "off"
    assert modus(hass) == "Cozy"
    assert hass.states.get("automation.lichtstimmung_gewitter_blitze").attributes["current"] == 0


async def test_lampe_nur_weiss_nur_helligkeit_und_fehlende_lampe(hass, tmp_path):
    lampen = [
        *LAMPEN,
        {"name": "Tischlampe", "modi": ["brightness"]},
        {"name": "Nachtlicht", "modi": ["color_temp"]},
    ]

    def anpassen(jinja):
        zeile = re.search(r"^  \{'id': 'light\.hue_go_1',.*\n", jinja, re.M).group(0)
        return jinja.replace(
            zeile,
            zeile
            + "  {'id': 'light.tischlampe', 'typ': 'tisch'},\n"
            + "  {'id': 'light.nachtlicht', 'typ': 'nacht'},\n"
            + "  {'id': 'light.gibt_es_nicht', 'typ': 'spot'},\n",
        )

    await richte_ein(hass, tmp_path, lampen=lampen, jinja_anpassen=anpassen)
    bericht = Template(
        "{% from 'lichtstimmung.jinja' import pruefen %}{{ pruefen() }}", hass
    ).async_render()
    assert "light.tischlampe [tisch, blitzt]: off · nur Helligkeit" in bericht
    assert "light.nachtlicht [nacht, blitzt]: off · nur Weiß (Kelvin)" in bericht
    assert "light.gibt_es_nicht [spot, blitzt]: ❌ nicht gefunden" in bericht

    await taste(hass)
    assert all(ist_an(hass, l) for l in LAMPEN_IDS)
    folgt_dem_plan(hass)
    tisch = hass.states.get("light.tischlampe")
    assert tisch.state == "on"
    # 'standard' bei Cozy = 45 %, gedämpft nach Helligkeit der Buchfarbe
    plan = zustand(hass).attributes["zuweisung"]["light.tischlampe"]
    assert plan.keys() == {"an", "hell"}
    assert round(tisch.attributes["brightness"] / 2.55) == plan["hell"]
    assert 1 <= plan["hell"] <= 45
    nacht = hass.states.get("light.nachtlicht")
    assert nacht.attributes["color_mode"] == "color_temp"
    assert nacht.attributes["color_temp_kelvin"] == 2200  # 'kelvin' von Cozy

    await waehle(hass, "Ruhig")
    assert hass.states.get("light.nachtlicht").attributes["color_temp_kelvin"] == 2700


async def test_nach_neustart_wird_die_auswahl_wiederhergestellt(lichtstimmung):
    """Beim Start ist die Auswahl evtl. falsch – der gespeicherte Zustand gewinnt, ohne umzufärben."""
    hass = lichtstimmung
    await taste(hass)
    await waehle(hass, "Ruhig")
    farben = {l: farbton(hass, l) for l in FARBLAMPEN}

    # Simuliert den Start: input_select fällt auf den Eintrag aus der YAML zurück,
    # der Speicher-Sensor kennt noch „Ruhig“. Beim echten Start passiert das,
    # bevor Automationen laufen – daher die Automation kurz deaktivieren.
    automation = "automation.lichtstimmung_modus_von_hand_gewahlt"
    await hass.services.async_call("automation", "turn_off", {"entity_id": automation}, blocking=True)
    await hass.services.async_call(
        "input_select", "set_options",
        {"entity_id": "input_select.lichtstimmung_modus", "options": ["Cozy"]},
        blocking=True,
    )
    await fertig(hass)
    await hass.services.async_call("automation", "turn_on", {"entity_id": automation}, blocking=True)
    assert auswahl(hass).state == "Cozy"
    assert modus(hass) == "Ruhig"

    await skript(hass, "lichtstimmung_neu_laden")
    assert auswahl(hass).attributes["options"] == MODI
    assert auswahl(hass).state == "Ruhig"
    assert {l: farbton(hass, l) for l in FARBLAMPEN} == farben


# --------------------------------------------------------------------------- Farbwörterbuch
def test_buchdatei_ist_aktuell():
    """lichtstimmung_buch.jinja entspricht dem, was tools/buch_importieren.py erzeugt."""
    erwartet = buch_importieren.jinja_inhalt(BUCH)
    assert buch_importieren.ZIEL.read_text(encoding="utf-8") == erwartet, (
        "Bitte `python3 tools/buch_importieren.py` ausführen"
    )
    assert len(BUCH) == 333
    assert all(2 <= len(farben) <= 4 for farben in BUCH.values())


async def test_buch_kombination_wird_originalgetreu_verteilt(hass, tmp_path):
    nr = 236  # drei Farben
    farben = BUCH[nr]
    await richte_ein(
        hass,
        tmp_path,
        jinja_anpassen=anpassen(
            "Cozy",
            f"    'aktiv': true,\n    'buch': [{nr}],\n"
            "    'eigene': [[[38, 70], [30, 88], [22, 92]]],\n    'eigene_anteil': 0,",
        ),
    )
    await taste(hass)
    assert quelle(hass) == f"Buch Nr. {nr}"
    folgt_dem_plan(hass)
    for l, hell in (("light.hue_play_3", 55), ("light.h6079", 60), ("light.3_hdmi_2_1_fancy_sync_box", 45)):
        h, s = hass.states.get(l).attributes["hs_color"]
        prozent = round(hass.states.get(l).attributes["brightness"] / 2.55)
        # passende Buchfarbe: Farbton ± Streuung, Helligkeit = Typ-Helligkeit × Faktor der Farbe
        assert any(
            nah_an(h, [f["h"]], 4 + 3) and abs(s - f["s"]) <= 4 + 6 and prozent == max(round(hell * f["f"]), 1)
            for f in farben
        ), (l, h, s, prozent, farben)
    # Alle Farben der Kombination kommen vor (9 Lampen, 3 Farben).
    def naechste(h):
        return min(range(3), key=lambda i: min(abs(farben[i]["h"] - h) % 360, 360 - abs(farben[i]["h"] - h) % 360))

    assert {naechste(hs(hass, l)[0]) for l in FARBLAMPEN} == {0, 1, 2}


async def test_eigene_palette(hass, tmp_path):
    await richte_ein(
        hass,
        tmp_path,
        jinja_anpassen=anpassen(
            "Cozy",
            "    'aktiv': true,\n    'buch': [236],\n"
            "    'eigene': [[[38, 70], [30, 88], [22, 92]]],\n    'eigene_anteil': 100,",
        ),
    )
    await taste(hass)
    assert quelle(hass) == "Eigene Palette 1"
    folgt_dem_plan(hass)
    assert all(nah_an(hs(hass, l)[0], [38, 30, 22], 5) for l in FARBLAMPEN)
    assert round(hass.states.get("light.h6079").attributes["brightness"] / 2.55) == 60


async def test_farbwoerterbuch_modus(lichtstimmung):
    hass = lichtstimmung
    await taste(hass)
    await waehle(hass, "Farbwörterbuch")
    quellen = [quelle(hass)]
    for _ in range(6):
        await skript(hass, "lichtstimmung_neu_wuerfeln")
        folgt_dem_plan(hass)
        quellen.append(quelle(hass))
    nummern = [int(q.removeprefix("Buch Nr. ")) for q in quellen]
    assert all(n in BUCH for n in nummern), quellen
    assert all(a != b for a, b in zip(nummern, nummern[1:])), nummern


async def test_konfig_check_meldet_falsche_buchnummern(hass, tmp_path):
    ungeeignet = min(set(range(1, 349)) - set(BUCH))
    await richte_ein(
        hass,
        tmp_path,
        jinja_anpassen=anpassen("Cozy", f"    'aktiv': true,\n    'buch': [236, 999, {ungeeignet}],"),
    )
    bericht = Template(
        "{% from 'lichtstimmung.jinja' import pruefen %}{{ pruefen() }}", hass
    ).async_render()
    assert f"- Cozy: 1 aus dem Buch, 0 eigene ⚠️ Buch-Nr. unbekannt oder als Licht ungeeignet: 999, {ungeeignet}" in bericht


async def test_nie_zweimal_dieselbe_kombination(hass, tmp_path):
    """Nur eine eigene Palette und immer eigene bevorzugt: es muss abwechseln."""
    await richte_ein(
        hass,
        tmp_path,
        jinja_anpassen=anpassen(
            "Cozy",
            "    'aktiv': true,\n    'buch': [236],\n"
            "    'eigene': [[[38, 70], [30, 88], [22, 92]]],\n    'eigene_anteil': 100,",
        ),
    )
    await taste(hass)
    quellen = [quelle(hass)]
    for _ in range(4):
        await skript(hass, "lichtstimmung_neu_wuerfeln")
        quellen.append(quelle(hass))
    assert quellen == ["Eigene Palette 1", "Buch Nr. 236"] * 2 + ["Eigene Palette 1"]


def test_readme_beispiel_ist_gueltiges_jinja():
    import jinja2

    readme = (REPO / "README.md").read_text(encoding="utf-8")
    block = re.search(r"```jinja\n(.*?)```", readme, re.S).group(1)
    modi = jinja2.Environment().from_string("{%- set M = {\n" + block + "} -%}{{ M | list }}").render()
    assert modi == "['Kino']"


@pytest.mark.parametrize("datei", ["lichtstimmung-dashboard.yaml", "lichtstimmung-karte.yaml"])
async def test_dashboard_zeigt_nur_vorhandene_entitaeten(lichtstimmung, datei):
    import yaml

    hass = lichtstimmung
    inhalt = yaml.safe_load((REPO / "homeassistant" / "dashboard" / datei).read_text(encoding="utf-8"))
    entitaeten, aktionen = set(), set()

    def sammeln(knoten):
        if isinstance(knoten, dict):
            for k, v in knoten.items():
                if k == "entity":
                    entitaeten.add(v)
                elif k == "perform_action":
                    aktionen.add(v)
                else:
                    sammeln(v)
        elif isinstance(knoten, list):
            for v in knoten:
                sammeln(v)

    sammeln(inhalt)
    assert entitaeten and aktionen
    fehlend = [e for e in entitaeten if hass.states.get(e) is None]
    assert not fehlend, fehlend
    for aktion in aktionen:
        domain, service = aktion.split(".")
        assert hass.services.has_service(domain, service), aktion
    if datei == "lichtstimmung-dashboard.yaml":
        assert set(LAMPEN_IDS) <= entitaeten  # alle Lampen auf dem Dashboard


# --------------------------------------------------------------------------- verlorene Befehle
def mit_verlust(**verlust):
    """Deine Lampen, aber einzelne verlieren ihre ersten Befehle (wie verlorene UDP-Pakete)."""
    return [
        {**l, "verliert": verlust.get(l["name"], {})} for l in LAMPEN
    ]


def zaehle_befehle(hass, dienst):
    zaehler = {}

    def merke(event):
        if event.data["domain"] == "light" and event.data["service"] == dienst:
            ziele = event.data["service_data"]["entity_id"]
            for e in [ziele] if isinstance(ziele, str) else ziele:
                zaehler[e] = zaehler.get(e, 0) + 1

    hass.bus.async_listen("call_service", merke)
    return zaehler


async def test_alles_aus_sendet_nach_wenn_befehle_verloren_gehen(hass, tmp_path):
    # Floor Lamp Pro verliert zwei „Aus“-Befehle, M1 Pro - Unten einen.
    await richte_ein(hass, tmp_path, lampen=mit_verlust(**{"H6079": {"aus": 2}, "H61F5 2": {"aus": 1}}))
    await taste(hass)
    assert all(ist_an(hass, l) for l in LAMPEN_IDS)

    aus = zaehle_befehle(hass, "turn_off")
    await taste(hass)
    assert not any(ist_an(hass, l) for l in LAMPEN_IDS), [l for l in LAMPEN_IDS if ist_an(hass, l)]
    # Nur Govee/FancyLEDs bekommen „Aus“ dreimal, Hue einmal.
    assert {l: aus[l] for l in LAMPEN_IDS} == {l: 3 if l in NACHSENDE_LAMPEN else 1 for l in LAMPEN_IDS}
    assert flag(hass) == "on"


async def test_farbe_wird_nachgesendet_wenn_befehl_verloren_geht(hass, tmp_path):
    await richte_ein(hass, tmp_path, lampen=mit_verlust(**{"H6079": {"an": 1}}))
    an = zaehle_befehle(hass, "turn_on")
    await taste(hass)
    folgt_dem_plan(hass)  # Floor Lamp Pro ist trotzdem an und hat ihre Farbe
    assert an["light.h6079"] == 2
    assert an["light.hue_play_3"] == 1


async def test_alles_aus_stoppt_nachsenden_und_nichts_geht_wieder_an(hass, tmp_path, freezer):
    """Mit echter Pause: „An“ und sofort „Aus“ – nachgesendete Farbbefehle dürfen
    keine Lampe wieder einschalten."""
    await richte_ein(hass, tmp_path, nachsende_pause=3)

    async def takte():
        for _ in range(50):
            await asyncio.sleep(0)

    async def zeit_vor(sekunden):
        for _ in range(int(sekunden * 10)):
            freezer.tick(timedelta(milliseconds=100))
            async_fire_time_changed(hass)
            await takte()

    knopf = {"entity_id": "input_button.lichtstimmung_taste"}
    await hass.services.async_call("input_button", "press", knopf, blocking=True)
    await takte()
    assert all(ist_an(hass, l) for l in LAMPEN_IDS)  # erster Befehl, Nachsenden steht noch aus

    await zeit_vor(0.5)  # deutlich weniger als die Pause
    an = zaehle_befehle(hass, "turn_on")
    await hass.services.async_call("input_button", "press", knopf, blocking=True)
    await zeit_vor(10)
    assert not any(ist_an(hass, l) for l in LAMPEN_IDS), [l for l in LAMPEN_IDS if ist_an(hass, l)]
    assert an == {}, an  # nach „Aus“ geht kein einziger Einschaltbefehl mehr raus
    assert hass.states.get("script.lichtstimmung_lampe_setzen").state == "off"
    assert hass.states.get("script.lichtstimmung_alles_aus").state == "off"


# --------------------------------------------------------------------------- Volle Helligkeit
async def volle_helligkeit(hass):
    await skript(hass, "lichtstimmung_volle_helligkeit")


def helligkeiten(hass):
    return {l: hass.states.get(l).attributes.get("brightness") if ist_an(hass, l) else None for l in LAMPEN_IDS}


def farben(hass):
    return {l: hass.states.get(l).attributes.get("hs_color") for l in LAMPEN_IDS if ist_an(hass, l)}


async def test_volle_helligkeit_und_wieder_zurueck(lichtstimmung):
    hass = lichtstimmung
    await taste(hass)
    hell_vorher, farben_vorher = helligkeiten(hass), farben(hass)
    assert all(b < 255 for b in hell_vorher.values()), hell_vorher

    await volle_helligkeit(hass)
    assert all(b == 255 for b in helligkeiten(hass).values()), helligkeiten(hass)
    assert farben(hass) == farben_vorher  # Farben bleiben

    await volle_helligkeit(hass)
    assert helligkeiten(hass) == hell_vorher  # exakt wie vorher
    assert farben(hass) == farben_vorher
    folgt_dem_plan(hass)


async def test_volle_helligkeit_schaltet_aus_lampen_mit_an_und_wieder_aus(lichtstimmung):
    hass = lichtstimmung
    await taste(hass)
    await licht(hass, "off", "light.h6079")
    await licht(hass, "off", "light.hue_go_1")
    plan = zustand(hass).attributes["zuweisung"]

    await volle_helligkeit(hass)
    assert all(b == 255 for b in helligkeiten(hass).values()), helligkeiten(hass)
    for l in ("light.h6079", "light.hue_go_1"):  # kommen in der Farbe der Stimmung
        assert gleiche_farbe(hass.states.get(l).attributes["hs_color"], plan[l]["hs"]), l

    await volle_helligkeit(hass)
    assert not ist_an(hass, "light.h6079")
    assert not ist_an(hass, "light.hue_go_1")
    assert all(ist_an(hass, l) for l in LAMPEN_IDS if l not in ("light.h6079", "light.hue_go_1"))


async def test_volle_helligkeit_nach_neuer_stimmung_wieder_hoch(lichtstimmung):
    hass = lichtstimmung
    await taste(hass)
    await volle_helligkeit(hass)
    await skript(hass, "lichtstimmung_neu_wuerfeln")
    assert any(b < 255 for b in helligkeiten(hass).values())

    await volle_helligkeit(hass)  # nicht auf die alte Stimmung zurück, sondern hoch
    assert all(b == 255 for b in helligkeiten(hass).values())
    await volle_helligkeit(hass)  # zurück auf die neue Stimmung
    folgt_dem_plan(hass)


async def test_volle_helligkeit_aus_dem_dunkeln(lichtstimmung):
    hass = lichtstimmung
    await taste(hass)
    await taste(hass)  # alles aus -> Moduswechsel fällig
    await volle_helligkeit(hass)
    assert all(b == 255 for b in helligkeiten(hass).values())
    assert modus(hass) == "Cozy"  # kein Moduswechsel durch „Volle Helligkeit“
    await volle_helligkeit(hass)
    assert not any(ist_an(hass, l) for l in LAMPEN_IDS)
    assert flag(hass) == "on"  # der fällige Wechsel ist wieder da
    await taste(hass)
    assert modus(hass) == "Cyberpunk"
