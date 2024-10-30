import logging
from homeassistant.components.number import NumberEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    UnitOfTemperature,
)

from .const import DOMAIN
from .api import ComapClient

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
) -> None:
    
    config = config_entry.data
    client = ComapClient(username=config[CONF_USERNAME], password=config[CONF_PASSWORD])
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    comap_temperatures = coordinator.data["comap_temperatures"]
    
    entities = [
        ComapCustomTemp(coordinator, client, custom_temp)
        for custom_temp in comap_temperatures
    ]

    async_add_entities(entities, update_before_add=True)


class ComapCustomTemp(CoordinatorEntity, NumberEntity):
    def __init__(self, coordinator, client, custom_temp):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.client = client
        self.housing_id = coordinator.data["housing"].get("id")
        self.housing_name = coordinator.data["housing"].get("name")
        self._attr_name = self.housing_name + " " + custom_temp.get("name")
        self.temp_id = custom_temp.get("id")
        self._attr_unique_id = self.housing_id + "_temp_" + self.temp_id
        self._attr_native_min_value = 5
        self._attr_native_max_value = 25
        self._attr_native_step = 0.5
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self):
        comap_temperatures = self.coordinator.data["comap_temperatures"]
        return self.getTempValue(self.temp_id,comap_temperatures)
    
    @property
    def icon(self) -> str:
        return "mdi:thermometer"
    
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
    
    async def async_set_native_value(self, value: float):
        await self.client.set_custom_temperature(self.temp_id, value)
        await self.coordinator.async_request_refresh()
    
    def getTempValue(self,temp_id, comap_temperatures):
        for temp in comap_temperatures:
            if temp.get("id") == temp_id:
                return temp.get("value")
        return None
