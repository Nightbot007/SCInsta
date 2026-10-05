"""Gemeinsame Test-Einrichtung: echtes Home Assistant mit simulierten Lampen."""

from pathlib import Path

import pytest
from homeassistant.config import merge_packages_config
from homeassistant.helpers.template import async_load_custom_templates
from homeassistant.setup import async_setup_component
from homeassistant.util.yaml import load_yaml

REPO = Path(__file__).parent.parent
JINJA = REPO / "homeassistant" / "custom_templates" / "lichtstimmung.jinja"
JINJA_BUCH = REPO / "homeassistant" / "custom_templates" / "lichtstimmung_buch.jinja"
PACKAGE = REPO / "homeassistant" / "packages" / "lichtstimmung.yaml"

# Deine Lampen (siehe lichtstimmung.jinja) mit den Farbmodi aus deinem Home Assistant.
# Der Name ergibt die Entity-ID (z. B. „H61F5 2“ -> light.h61f5_2).
LAMPEN = [
    {"name": "Hue Play 3", "modi": ["xy", "color_temp"]},
    {"name": "3 HDMI 2.1 Fancy Sync Box", "modi": ["hs", "color_temp"]},
    {"name": "Synced Fancyleds", "modi": ["hs", "color_temp"]},
    {"name": "H61F5 2", "modi": ["rgb", "color_temp"]},
    {"name": "H61F5", "modi": ["rgb", "color_temp"]},
    {"name": "H6079", "modi": ["rgb", "color_temp"]},
    {"name": "Hue Play 4", "modi": ["xy", "color_temp"]},
    {"name": "Hue Go 2", "modi": ["xy", "color_temp"]},
    {"name": "Hue Go 1", "modi": ["xy", "color_temp"]},
]
LAMPEN_IDS = [
    "light.hue_play_3",
    "light.3_hdmi_2_1_fancy_sync_box",
    "light.synced_fancyleds",
    "light.h61f5_2",
    "light.h61f5",
    "light.h6079",
    "light.hue_play_4",
    "light.hue_go_2",
    "light.hue_go_1",
]
BLITZ_LAMPEN = {
    "light.hue_play_3",
    "light.hue_play_4",
    "light.hue_go_2",
    "light.hue_go_1",
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    # Die simulierten Lampen (tests/custom_components/testlicht) bekannt machen.
    import custom_components

    pfad = str(Path(__file__).parent / "custom_components")
    if pfad not in custom_components.__path__:
        custom_components.__path__.append(pfad)
    yield


def package_skripte(config):
    return list(config["script"])


async def richte_ein(hass, config_dir, lampen=LAMPEN, jinja_anpassen=None):
    """Lädt Package + Jinja wie in einer echten Installation."""
    hass.config.config_dir = str(config_dir)
    (config_dir / "custom_templates").mkdir(exist_ok=True)
    jinja = JINJA.read_text(encoding="utf-8")
    if jinja_anpassen:
        jinja = jinja_anpassen(jinja)
    (config_dir / "custom_templates" / "lichtstimmung.jinja").write_text(jinja, encoding="utf-8")
    (config_dir / "custom_templates" / "lichtstimmung_buch.jinja").write_text(
        JINJA_BUCH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    await async_load_custom_templates(hass)

    for domain in ("homeassistant", "persistent_notification", "scene"):
        assert await async_setup_component(hass, domain, {})
    assert await async_setup_component(
        hass, "light", {"light": [{"platform": "testlicht", "lampen": lampen}]}
    )

    # Genau wie „homeassistant: packages: !include_dir_named packages“ zusammenführen
    # (dabei verwirft Home Assistant z. B. leere {}-Einträge).
    config = await merge_packages_config(hass, {}, {"lichtstimmung": load_yaml(PACKAGE)})
    for domain in (
        "input_select",
        "input_boolean",
        "input_text",
        "input_button",
        "template",
        "script",
        "automation",
    ):
        assert await async_setup_component(hass, domain, {domain: config[domain]}), domain
    await hass.async_block_till_done(wait_background_tasks=True)
    for skript in package_skripte(config):
        assert hass.states.get(f"script.{skript}") is not None, skript
        assert hass.states.get(f"script.{skript}").state != "unavailable", skript

    # Entspricht dem Abgleich beim Start von Home Assistant.
    await hass.services.async_call("script", "lichtstimmung_neu_laden", blocking=True)
    await hass.async_block_till_done(wait_background_tasks=True)


@pytest.fixture
async def lichtstimmung(hass, tmp_path):
    await richte_ein(hass, tmp_path)
    return hass
