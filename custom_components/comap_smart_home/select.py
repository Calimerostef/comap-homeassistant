import logging
from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity


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
        self._name = "Planning " + coordinator.data["housing"].get("name") + " zone " + zone.get("title")
        self.zone_id = zone.get("id")
        self._attr_unique_id = "zone_mode_" + zone.get("id")
        self.zone_name = coordinator.data["housing"].get("name") + " " + zone.get("title")
        schedules = self.coordinator.data["schedules"]
        self.modes = self.parse_schedules(schedules)
        self._options = self.list_schedules(schedules)
    
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
        return self._options
    
    @property
    def current_option(self):
        active_program = self.coordinator.data["active_program"]
        schedules = self.coordinator.data["schedules"]
        return self.get_active_schedule_name(schedules,self.zone_id,active_program)

    async def async_select_option(self, option: str) -> None:
        schedule_id = self.modes.get(option)
        await self.client.set_schedule(schedule_id,self.zone_id)
        self._attr_current_option = option
        await self.coordinator.async_request_refresh()

    def list_schedules(self, r) -> list:
        schedules = []
        for schedule in r:
            schedules.append(schedule["title"])
        return schedules

    def parse_schedules(self, r) -> dict[str, str]:
        schedules = {}
        for schedule in r:
            schedules.update({schedule["title"]: schedule["id"]})
        return schedules

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
        self._name = "Programme " + coordinator.data["housing"].get("name")
        self.device_name = coordinator.data["housing"].get("name")
        self._unique_id = self.housing + "program"
        self._attr_options = []
        self._attr_current_option = None
        self.modes = {}

        programs = coordinator.data["programs"].get("programs")
        self._options = self.list_programs(programs)
        self.modes = self.parse_programs(programs)
    
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
        return self._options
    
    @property
    def current_option(self):
        programs = self.coordinator.data["programs"].get("programs")
        return self.get_active_program_name(programs)

    async def async_select_option(self, option: str) -> None:
        program_id = self.modes.get(option)
        await self.client.set_program(program_id)
        self._attr_current_option = option
        await self.coordinator.async_request_refresh()
    

    def list_programs(self, prglist) -> list:
        programs = []
        for program in prglist:
            programs.append(program["title"])
        return programs

    def parse_programs(self, prglist) -> dict[str, str]:
        programs = {}
        for schedule in prglist:
            programs.update({schedule["title"]: schedule["id"]})
        return programs

    def get_active_program_name(self,prglist) -> str:
        active_program = None
        for program in prglist:
            if program["is_activated"]:
                    active_program = program["title"] 
        return active_program
