from typing import Any
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .api import ComapClient
from .const import DOMAIN

from .comap_functions import get_zone_infos, build_name

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
) -> None:
    
    config = config_entry.data
    client = ComapClient(username=config[CONF_USERNAME], password=config[CONF_PASSWORD])
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    zones = coordinator.data["thermal_details"].get("zones")

    temporary_instructions_switches = [
        ComapZoneTemporarySwitch(coordinator, client, zone)
        for zone in zones
    ]

    housing_switches = [ComapHousingOnOff(coordinator, client),ComapHousingHoliday(coordinator, client),ComapHousingAbsence(coordinator, client)]
    zones_switches = temporary_instructions_switches

    switches = housing_switches + zones_switches

    async_add_entities(switches, update_before_add=True)

class ComapHousingOnOff(CoordinatorEntity,SwitchEntity):
    def __init__(self, coordinator, client) -> None:
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.client = client
        self.housing = coordinator.data["housing"].get("id")
        self._name = build_name(
            housing_name=coordinator.data["housing"].get("name"),
            entity_name="Global switch"
        )
        self._is_on = None
        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._id = self.housing + "_on_off"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.coordinator.data["housing"].get("id"))
            },
            name= self.coordinator.data["housing"].get("name"),
            manufacturer="comap",
        )

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self._id

    @property
    def is_on(self):
        zones = self.coordinator.data["thermal_details"]
        return zones["heating_system_state"] == "on"

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.client.turn_on()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.client.turn_off()
        await self.coordinator.async_request_refresh()
    
class ComapHousingHoliday(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, client) -> None:
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.client = client
        self.housing = coordinator.data["housing"].get("id")
        self._name = build_name(
            housing_name=coordinator.data["housing"].get("name"),
            entity_name="Holiday"
        )
        self._is_on = None
        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._extra_state_attributes = {}

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.coordinator.data["housing"].get("id"))
            },
            name=self.coordinator.data["housing"].get("name"),
            manufacturer="comap",
        )

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self.housing + "_holiday"

    @property
    def is_on(self):
        thermal_details = self.coordinator.data["thermal_details"]
        events = thermal_details.get("events")
        if ('absence' in events):
            return True
        else:
            return False
    
    @property
    def extra_state_attributes(self):
        thermal_details = self.coordinator.data["thermal_details"]
        events = thermal_details.get("events")
        return events.get("absence")
       
    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.client.set_holiday()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.client.delete_holiday()
        await self.coordinator.async_request_refresh()

class ComapHousingAbsence(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, client) -> None:
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.client = client
        self.housing = coordinator.data["housing"].get("id")
        self._name = build_name(
            housing_name=coordinator.data["housing"].get("name"),
            entity_name="Absence"
        )
        self._is_on = None
        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._extra_state_attributes = {}

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.coordinator.data["housing"].get("id"))
            },
            name=self.coordinator.data["housing"].get("name"),
            manufacturer="comap",
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        return self.housing + "_absence"

    @property
    def is_on(self):
        thermal_details = self.coordinator.data["thermal_details"]
        events = thermal_details.get("events")
        if ('time_shift' in events):
            return True
        else:
            return False
    
    @property
    def extra_state_attributes(self):
        thermal_details = self.coordinator.data["thermal_details"]
        events = thermal_details.get("events")
        return events.get("time_shift")
       
    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.client.set_absence()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.client.delete_absence()
        await self.coordinator.async_request_refresh()

class ComapZoneTemporarySwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, client, zone) -> None:
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.client = client
        self.housing = coordinator.data["housing"].get("id")
        self._name = build_name(
            housing_name=coordinator.data["housing"].get("name"),
            zone_name = zone.get("title"),
            entity_name="Temporary"
        )
        self._id = zone.get("id") + "_temporary"
        self.zone_name = zone.get("title")
        self.zone_id = zone.get("id")
        self._extra_state_attributes = {}

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.zone_id)
            },
            name= self.coordinator.data["housing"].get("name") + " " + self.zone_name,
            manufacturer="comap",
            serial_number = self.zone_id
        )
    
    @property
    def icon(self) -> str:
        if self.is_on:
            return "mdi:timer-minus"
        return "mdi:timer-off"

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name
    
    @property
    def extra_state_attributes(self):
        return self._extra_state_attributes

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self._id
    
    @property
    def extra_state_attributes(self):
        thermal_details = self.coordinator.data["thermal_details"]
        zone_data = get_zone_infos(self.zone_id,thermal_details)
        events = zone_data.get("events")
        attrs = {}
        attrs["temporary_instruction"] = events.get("temporary_instruction")
        if ('temporary_instruction' in events):
            temporary_instruction = events.get("temporary_instruction")
            attrs["end_at"] = temporary_instruction.get("end_at")
            attrs["instruction"] = temporary_instruction.get("set_point").get("instruction")
        else:
            attrs["end_at"] = None
            attrs["instruction"] = None

        return attrs
    
    @property
    def is_on(self):
        thermal_details = self.coordinator.data["thermal_details"]
        zone_data = get_zone_infos(self.zone_id,thermal_details)
        events = zone_data.get("events")
        if ('temporary_instruction' in events):
            return True
        else:
            return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        return
    
    async def async_turn_off(self, **kwargs: Any) -> None:
        response = await self.client.remove_temporary_instruction(self.zone_id)
        events = response.get("events")
        self.extra_state_attributes["temporary_instruction"] = events.get("temporary_instruction")
        await self.coordinator.async_request_refresh()