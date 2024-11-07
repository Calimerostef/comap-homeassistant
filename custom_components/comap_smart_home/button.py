import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.button import ButtonEntity
from .comap_functions import build_name

from .const import (
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
) -> None:
    
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([RefreshButton(coordinator)])

class RefreshButton(ButtonEntity, CoordinatorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_name = build_name(
            housing_name=coordinator.data["housing"].get("name"),
            entity_name=" Refresh data button"
        )
        self.housing = coordinator.data["housing"].get("id")
        self.device_name = coordinator.data["housing"].get("name")
        self._unique_id = self.housing + "refresh"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self._unique_id
    
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.coordinator.data["housing"].get("id"))
            },
            name = self.coordinator.data["housing"].get("name"),
            manufacturer="comap",
        )
    
    async def async_press(self):
        """Appelée lorsque le bouton est pressé."""
        await self.coordinator.async_request_refresh()