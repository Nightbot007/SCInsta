"""Verhaltenstests der Lichtstimmung gegen ein echtes Home Assistant."""

import asyncio
from datetime import timedelta

import pytest
from homeassistant.helpers.template import Template
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from conftest import LAMPEN, LAMPEN_IDS, richte_ein

FARBLAMPEN = ["light.deckenlampe", "light.stehlampe", "light.led_streifen"]


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


def im_bereich(h, von, bis, toleranz=10):
    """Farbton (mit Streuung) liegt im Bereich der Palette, auch über 0° hinweg."""
    von, bis = (von - toleranz) % 360, (bis + toleranz) % 360
    return von <= h <= bis if von <= bis else (h >= von or h <= bis)


# --------------------------------------------------------------------------- Tests
async def test_einrichtung_und_konfig_check(lichtstimmung):
    hass = lichtstimmung
    assert auswahl(hass).attributes["options"] == ["Cozy", "Cyberpunk", "Ruhig", "Regen / Gewitter"]
    bericht = Template(
        "{% from 'lichtstimmung.jinja' import pruefen %}{{ pruefen() }}", hass
    ).async_render()
    assert "❌" not in bericht and "⚠️" not in bericht, bericht
    assert "light.nachttischlampe [nacht]: off · nur Weiß (Kelvin)" in bericht
    assert "light.stehlampe [steh]: off · Farbe" in bericht
    assert "Sonnenuntergang (inaktiv)" in bericht


async def test_taste_schaltet_alles_an_mit_passenden_unterschiedlichen_farben(lichtstimmung):
    hass = lichtstimmung
    await taste(hass)
    assert all(ist_an(hass, l) for l in LAMPEN_IDS)
    assert modus(hass) == "Cozy"
    farben = [farbton(hass, l) for l in FARBLAMPEN]
    assert len({round(f) for f in farben}) == 3, farben
    assert all(im_bereich(f, 12, 45) for f in farben), farben
    nacht = hass.states.get("light.nachttischlampe")
    assert nacht.attributes["color_mode"] == "color_temp"
    assert nacht.attributes["color_temp_kelvin"] == 2200
    assert round(hass.states.get("light.stehlampe").attributes["brightness"] / 2.55) == 60
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
    assert all(im_bereich(farbton(hass, l), 190, 325) for l in FARBLAMPEN)

    await taste(hass)
    await taste(hass)
    assert modus(hass) == "Ruhig"
    await taste(hass)
    await taste(hass)
    assert modus(hass) == "Regen / Gewitter"
    assert not ist_an(hass, "light.deckenlampe")  # Helligkeit 0 in diesem Modus
    await taste(hass)
    await taste(hass)
    assert modus(hass) == "Cozy"  # einmal rum


async def test_einzelne_lampen_aendern_den_modus_nie(lichtstimmung):
    hass = lichtstimmung
    await taste(hass)
    farben = {l: farbton(hass, l) for l in FARBLAMPEN}

    await licht(hass, "off", "light.stehlampe")
    await licht(hass, "on", "light.stehlampe")
    assert modus(hass) == "Cozy"
    assert farbton(hass, "light.stehlampe") == farben["light.stehlampe"]

    # Alle Lampen einzeln aus – das ist NICHT die Taste.
    for l in LAMPEN_IDS:
        await licht(hass, "off", l)
    assert flag(hass) == "off"
    await licht(hass, "on", "light.led_streifen")
    assert modus(hass) == "Cozy"

    # Taste schaltet alles wieder in derselben Stimmung und Verteilung ein.
    await taste(hass)  # led_streifen ist an -> aus
    await taste(hass)  # an
    assert modus(hass) == "Cyberpunk"  # weil die Taste davor alles ausgemacht hat

    for l in LAMPEN_IDS:
        await licht(hass, "off", l)
    await taste(hass)
    assert modus(hass) == "Cyberpunk"
    plan = zustand(hass).attributes["zuweisung"]
    for l in FARBLAMPEN:
        assert farbton(hass, l) == pytest.approx(plan[l]["hs"][0])


async def test_nach_taste_aus_startet_auch_eine_einzelne_lampe_den_neuen_modus(lichtstimmung):
    hass = lichtstimmung
    await taste(hass)  # Cozy
    await taste(hass)  # alles aus

    await licht(hass, "on", "light.stehlampe")
    assert modus(hass) == "Cyberpunk"
    assert flag(hass) == "off"
    assert im_bereich(farbton(hass, "light.stehlampe"), 190, 325)
    assert not ist_an(hass, "light.led_streifen")
    assert set(zustand(hass).attributes["offen"]) == {
        "light.deckenlampe",
        "light.led_streifen",
        "light.nachttischlampe",
    }

    # Eine weitere Lampe bekommt beim Einschalten ihre Cyberpunk-Farbe.
    await licht(hass, "on", "light.led_streifen")
    plan = zustand(hass).attributes["zuweisung"]
    assert farbton(hass, "light.led_streifen") == pytest.approx(plan["light.led_streifen"]["hs"][0])
    assert "light.led_streifen" not in zustand(hass).attributes["offen"]
    assert modus(hass) == "Cyberpunk"


async def test_modus_im_dashboard_waehlen(lichtstimmung):
    hass = lichtstimmung
    await taste(hass)  # Cozy
    await waehle(hass, "Ruhig")
    assert modus(hass) == "Ruhig"
    assert all(im_bereich(farbton(hass, l), 175, 250) for l in FARBLAMPEN)
    assert hass.states.get("light.nachttischlampe").attributes["color_temp_kelvin"] == 2700

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
    varianten = set()
    for _ in range(6):
        await skript(hass, "lichtstimmung_neu_wuerfeln")
        varianten.add(tuple(round(farbton(hass, l)) for l in FARBLAMPEN))
    assert zustand(hass).attributes["stand"] != vorher
    assert modus(hass) == "Cozy"
    assert len(varianten) > 1


async def test_favorit_speichern_abrufen_und_loeschen(lichtstimmung):
    hass = lichtstimmung
    await taste(hass)  # Cozy
    await licht(hass, "on", "light.stehlampe", hs_color=[5, 100], brightness=200)
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
    assert "★ Abendrot" in auswahl(hass).attributes["options"]
    assert auswahl(hass).state == "★ Abendrot"
    assert modus(hass) == "★ Abendrot"
    assert hass.states.get("input_text.lichtstimmung_favorit_name").state == ""
    gespeichert = {l: hass.states.get(l).attributes["hs_color"] for l in FARBLAMPEN}
    assert gespeichert["light.stehlampe"] == (5, 100)

    await waehle(hass, "Cyberpunk")
    assert farbton(hass, "light.stehlampe") != 5

    await waehle(hass, "★ Abendrot")
    for l in FARBLAMPEN:
        assert hass.states.get(l).attributes["hs_color"] == pytest.approx(gespeichert[l], abs=0.1)
    assert hass.states.get("light.stehlampe").attributes["brightness"] == 200
    assert hass.states.get("light.nachttischlampe").attributes["color_temp_kelvin"] == 2200

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
    for erwartet in ("Cyberpunk", "Ruhig", "Regen / Gewitter", "Cozy"):
        await taste(hass)
        await taste(hass)
        assert modus(hass) == erwartet

    await hass.services.async_call(
        "input_boolean",
        "turn_on",
        {"entity_id": "input_boolean.lichtstimmung_favoriten_im_wechsel"},
        blocking=True,
    )
    for erwartet in ("Cyberpunk", "Ruhig", "Regen / Gewitter", "★ Liebling", "Cozy"):
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
    assert not ist_an(hass, "light.deckenlampe")
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


async def test_lampe_nur_helligkeit_und_fehlende_lampe(hass, tmp_path):
    lampen = [*LAMPEN, {"name": "Tischlampe", "modi": ["brightness"]}]

    def anpassen(jinja):
        return jinja.replace(
            "{'id': 'light.nachttischlampe', 'typ': 'nacht'},",
            "{'id': 'light.nachttischlampe', 'typ': 'nacht'},\n"
            "  {'id': 'light.tischlampe', 'typ': 'tisch'},\n"
            "  {'id': 'light.gibt_es_nicht', 'typ': 'spot'},",
        )

    await richte_ein(hass, tmp_path, lampen=lampen, jinja_anpassen=anpassen)
    bericht = Template(
        "{% from 'lichtstimmung.jinja' import pruefen %}{{ pruefen() }}", hass
    ).async_render()
    assert "light.tischlampe [tisch]: off · nur Helligkeit" in bericht
    assert "light.gibt_es_nicht [spot]: ❌ nicht gefunden" in bericht

    await taste(hass)
    tisch = hass.states.get("light.tischlampe")
    assert tisch.state == "on"
    assert round(tisch.attributes["brightness"] / 2.55) == 45  # 'standard' bei Cozy
    assert all(ist_an(hass, l) for l in LAMPEN_IDS)


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
    assert auswahl(hass).attributes["options"] == ["Cozy", "Cyberpunk", "Ruhig", "Regen / Gewitter"]
    assert auswahl(hass).state == "Ruhig"
    assert {l: farbton(hass, l) for l in FARBLAMPEN} == farben
