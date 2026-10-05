"""Simulierte Lampen: Farbe (hs, xy, rgb), nur Weiß (color_temp) oder nur Helligkeit.

Wie echte Lampen bekommen sie Farben in ihrem eigenen Farbmodus: Home Assistant
rechnet z. B. hs_color für Hue-Lampen in xy_color und für Govee in rgb_color um.
"""

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ATTR_RGB_COLOR,
    ATTR_XY_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)

FARBEN = {
    ATTR_HS_COLOR: (ColorMode.HS, "_attr_hs_color"),
    ATTR_XY_COLOR: (ColorMode.XY, "_attr_xy_color"),
    ATTR_RGB_COLOR: (ColorMode.RGB, "_attr_rgb_color"),
}
START = {
    ColorMode.HS: ("_attr_hs_color", (0.0, 0.0)),
    ColorMode.XY: ("_attr_xy_color", (0.3127, 0.329)),
    ColorMode.RGB: ("_attr_rgb_color", (255, 255, 255)),
}


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    async_add_entities(TestLicht(l["name"], l["modi"]) for l in config["lampen"])


class TestLicht(LightEntity):
    _attr_should_poll = False
    _attr_supported_features = LightEntityFeature.TRANSITION
    _attr_min_color_temp_kelvin = 2000
    _attr_max_color_temp_kelvin = 6500

    def __init__(self, name, modi):
        self._attr_name = name
        self._attr_unique_id = f"testlicht_{name}"
        self._attr_supported_color_modes = {ColorMode(m) for m in modi}
        self._attr_color_mode = ColorMode(modi[0])
        self._attr_is_on = False
        self._attr_brightness = 255
        for modus, (feld, wert) in START.items():
            if modus in self._attr_supported_color_modes:
                setattr(self, feld, wert)
        self._attr_color_temp_kelvin = (
            2700 if ColorMode.COLOR_TEMP in self._attr_supported_color_modes else None
        )
        self.befehle = []

    async def async_turn_on(self, **kwargs):
        self.befehle.append(("an", kwargs))
        self._attr_is_on = True
        if ATTR_BRIGHTNESS in kwargs:
            self._attr_brightness = kwargs[ATTR_BRIGHTNESS]
        for attr, (modus, feld) in FARBEN.items():
            if attr in kwargs:
                setattr(self, feld, kwargs[attr])
                self._attr_color_mode = modus
        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            self._attr_color_temp_kelvin = kwargs[ATTR_COLOR_TEMP_KELVIN]
            self._attr_color_mode = ColorMode.COLOR_TEMP
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self.befehle.append(("aus", kwargs))
        self._attr_is_on = False
        self.async_write_ha_state()
