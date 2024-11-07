import logging
from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .comap_functions import build_name

from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
)

from .api import ComapClient

from .const import (
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
) -> None:
    
    config = config_entry.data
    client = ComapClient(username=config[CONF_USERNAME], password=config[CONF_PASSWORD])
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    thermal_details = coordinator.data["thermal_details"]
    zones = thermal_details.get("zones")

    zones_selects = [
        ZoneScheduleSelect(coordinator, client, zone)
        for zone in zones
    ]


    central_program = ProgramSelect(coordinator, client)

    selects = zones_selects + [central_program]

    async_add_entities(selects, update_before_add=True)

class ZoneScheduleSelect(CoordinatorEntity, SelectEntity):

    def __init__(self, coordinator, client, zone):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.client = client
        self.housing = coordinator.data["housing"].get("id")
        self._name = build_name(
            housing_name=coordinator.data["housing"].get("name"),
            zone_name=zone.get("title"),
            entity_name="Planning"
        )
        self.zone_id = zone.get("id")
        self._attr_unique_id = "zone_mode_" + zone.get("id")
        self.zone_name = coordinator.data["housing"].get("name") + " " + zone.get("title")
    
    @property
    def icon(self) -> str:
        return "mdi:form-select"

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self.zone_id + "_schedule"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.zone_id)
            },
            name=self.zone_name,
            manufacturer="comap",
            serial_number = self.zone_id
        )
    
    @property
    def options(self):
        list = [
            lib
            for lib in self.coordinator.data["parsed_schedules"]
        ]
        return list
    
    @property
    def current_option(self):
        active_program = self.coordinator.data["active_program"]
        schedules = self.coordinator.data["schedules"]
        return self.get_active_schedule_name(schedules,self.zone_id,active_program)

    async def async_select_option(self, option: str) -> None:
        schedule_id = self.coordinator.data["parsed_schedules"][option]
        await self.client.set_schedule(schedule_id,self.zone_id)
        self._attr_current_option = option
        await self.coordinator.async_request_refresh()

    def get_active_schedule_name(self, schedules, zone_id, active_program) -> str:
        zones = active_program["zones"]
        for zone in zones:
            if zone["id"] == zone_id:
                id = zone["schedule_id"]
        for schedule in schedules:
            if (schedule["id"]) == id:
                return schedule["title"]
            
class ProgramSelect(CoordinatorEntity, SelectEntity):

    def __init__(self, coordinator, client):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.client = client
        self.housing = coordinator.data["housing"].get("id")
        self._name = build_name(
            housing_name=coordinator.data["housing"].get("name"),
            entity_name="Program"
        )
        self.device_name = coordinator.data["housing"].get("name")
        self._unique_id = self.housing + "program"
    
    @property
    def icon(self) -> str:
        return "mdi:form-select"

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

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
    
    @property
    def options(self):
        list = [
            lib
            for lib in self.coordinator.data["parsed_programs"]
        ]
        return list
    
    @property
    def current_option(self):
        return self.coordinator.data["active_program_name"]

    async def async_select_option(self, option: str) -> None:
        program_id = self.coordinator.data["parsed_programs"][option]
        await self.client.set_program(program_id)
        self._attr_current_option = option
        await self.coordinator.async_request_refresh()
