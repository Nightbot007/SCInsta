"""Simulierte Lampen: Farbe (hs), nur Weiß (color_temp) oder nur Helligkeit."""

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)


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
        self._attr_hs_color = (0.0, 0.0) if ColorMode.HS in self._attr_supported_color_modes else None
        self._attr_color_temp_kelvin = (
            2700 if ColorMode.COLOR_TEMP in self._attr_supported_color_modes else None
        )
        self.befehle = []

    async def async_turn_on(self, **kwargs):
        self.befehle.append(("an", kwargs))
        self._attr_is_on = True
        if ATTR_BRIGHTNESS in kwargs:
            self._attr_brightness = kwargs[ATTR_BRIGHTNESS]
        if ATTR_HS_COLOR in kwargs:
            self._attr_hs_color = kwargs[ATTR_HS_COLOR]
            self._attr_color_mode = ColorMode.HS
        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            self._attr_color_temp_kelvin = kwargs[ATTR_COLOR_TEMP_KELVIN]
            self._attr_color_mode = ColorMode.COLOR_TEMP
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self.befehle.append(("aus", kwargs))
        self._attr_is_on = False
        self.async_write_ha_state()
