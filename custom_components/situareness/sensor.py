"""Read-only monitor health and redacted event summaries."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        [SituarenessSensor(hass.data[DOMAIN][entry.entry_id], entry.entry_id)]
    )


class SituarenessSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "Situareness monitoring"
    _attr_icon = "mdi:weather-lightning-rainy"

    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_monitoring"

    @property
    def native_value(self):
        return self.coordinator.data["active_count"]

    @property
    def extra_state_attributes(self):
        return self.coordinator.data
