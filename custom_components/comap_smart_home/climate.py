import logging
from typing import Any

from bidict import bidict
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
)
from homeassistant.components.climate.const import (
    PRESET_AWAY,
    PRESET_COMFORT,
    PRESET_ECO,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .api import ComapClient
from .const import DOMAIN
from .comap_functions import get_zone_infos

_LOGGER = logging.getLogger(__name__)

PRESET_MODE_MAP = bidict(
    {
        "stop": "off",
        "frost_protection": PRESET_AWAY,
        "eco": PRESET_ECO,
        "comfort": PRESET_COMFORT,
        "comfort_minus1": "comfort -1",
        "comfort_minus2": "comfort -2",
    }
)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
):
    config = config_entry.data
    client = ComapClient(username=config[CONF_USERNAME], password=config[CONF_PASSWORD])

    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    assist_compatibility = False

    housing_details = coordinator.data["thermal_details"]
    heating_system_state = housing_details.get("heating_system_state")
    for zone in housing_details.get("zones"):
        zone.update({"heating_system_state": heating_system_state})

    zones = [
        ComapZoneThermostat(coordinator, client, zone, assist_compatibility)
        for zone in housing_details.get("zones")
    ]

    async_add_entities(zones)

    return True

class ComapZoneThermostat(CoordinatorEntity,ClimateEntity):
    _attr_target_temperature_step = 0.5
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    #_attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF, HVACMode.AUTO]
    _attr_preset_modes = [
        "off",
        PRESET_AWAY,
        "comfort -1",
        "comfort -2",
        PRESET_ECO,
        PRESET_COMFORT,
    ]
    _attr_hvac_mode: HVACMode | None
    _attr_hvac_action: HVACAction | None

    def __init__(self, coordinator, client, zone, assist_compatibility):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._assist_compatibility = assist_compatibility
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
        if not assist_compatibility:
            self._attr_hvac_modes.append(HVACMode.AUTO)
        self.client = client
        self.zone_id = zone.get("id")
        self.zone_name = coordinator.data["housing"].get("name") + " " + zone.get("title")
        self._name = "Thermostat " + coordinator.data["housing"].get("name") + " zone " + zone.get("title")
        self.set_point_type = zone.get("set_point_type")
        if (self.set_point_type == "custom_temperature") | (
            self.set_point_type == "defined_temperature"
        ):
            self.zone_type = "thermostat"
            self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
        if self.set_point_type == "pilot_wire":
            self.zone_type = "pilot_wire"
            self._attr_supported_features = ClimateEntityFeature.PRESET_MODE
        self._enable_turn_on_off_backwards_compatibility = False

#fixes

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.zone_id)
            },
            name = self.zone_name,
            manufacturer = "comap",
            serial_number = self.zone_id
        )

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self.zone_id

#variables

    @property
    def current_temperature(self) -> float:
        thermal_details = self.coordinator.data["thermal_details"]
        zone_data = get_zone_infos(self.zone_id,thermal_details)
        return zone_data.get("temperature")
    
    @property
    def target_temperature(self) -> float:
        thermal_details = self.coordinator.data["thermal_details"]
        zone_data = get_zone_infos(self.zone_id,thermal_details)
        target_temp = None
        if self.zone_type == "thermostat":
            target_temp = self.get_target_temperature(zone_data.get("set_point").get("instruction"), zone_data.get("set_point_type"))
        return target_temp
            
    @property
    def current_humidity(self) -> int:
        thermal_details = self.coordinator.data["thermal_details"]
        zone_data = get_zone_infos(self.zone_id,thermal_details)
        return zone_data.get("humidity")

    @property
    def hvac_mode(self) -> HVACMode:
        thermal_details = self.coordinator.data["thermal_details"]
        zone_data = get_zone_infos(self.zone_id,thermal_details)
        return self.map_hvac_mode(zone_data)
    
    @property
    def hvac_action(self) -> HVACAction:
        thermal_details = self.coordinator.data["thermal_details"]
        zone_data = get_zone_infos(self.zone_id,thermal_details)
        return self.map_hvac_action(zone_data)

    @property
    def preset_mode(self) -> str | None:
        thermal_details = self.coordinator.data["thermal_details"]
        zone_data = get_zone_infos(self.zone_id,thermal_details)
        preset_mode = None
        if self.zone_type == "pilot_wire":
            preset_mode = self.map_preset_mode(
                zone_data.get("set_point").get("instruction")
            )
        return preset_mode

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        attrs = {}
        thermal_details = self.coordinator.data["thermal_details"]
        zone_data = get_zone_infos(self.zone_id,thermal_details)
        next_timeslot = zone_data["next_timeslot"]
        attrs["next_timeslot"] = next_timeslot["begin_at"]
        attrs["next_instruction"] = next_timeslot["set_point"]["instruction"]
        return attrs
    

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        await self.client.set_temporary_instruction(
            self.zone_id, self.map_comap_mode(preset_mode)
        )
        #await self.async_update()

    async def async_reset_temporary (self):
        await self.client.remove_temporary_instruction(self.zone_id)

    async def async_set_hvac_mode(self, hvac_mode: str) -> bool:
        """Set new hvac mode."""

        if (hvac_mode == HVACMode.AUTO):
            await self.async_reset_temporary()
            await self.coordinator.async_request_refresh()
        elif (hvac_mode == HVACMode.OFF) & (self.zone_type == "pilot_wire"):
            await self.async_set_preset_mode("off")
            await self.coordinator.async_request_refresh()
        elif (hvac_mode == HVACMode.HEAT) & (self.zone_type == "pilot_wire"):
            await self.async_set_preset_mode(PRESET_COMFORT)
            await self.coordinator.async_request_refresh()
        elif (hvac_mode == HVACMode.OFF) & (self.zone_type == "thermostat"):
            await self.client.set_temporary_instruction(self.zone_id, 7)
            await self.coordinator.async_request_refresh()
        elif (hvac_mode == HVACMode.HEAT) & (self.zone_type == "thermostat"):
            await self.client.set_temporary_instruction(self.zone_id, 20)
            await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs) -> None:
        await self.client.set_temporary_instruction(self.zone_id, kwargs["temperature"])
        await self.coordinator.async_request_refresh()
     

    def map_hvac_mode(self, zone_data):
        heating_system_state = zone_data.get("heating_system_state")
        type = zone_data.get("set_point_type")
        temporary_instruction = zone_data.get("events").get("temporary_instruction")
        if temporary_instruction is None:
            hvac_mode_map = {"off": HVACMode.OFF, "on": HVACMode.AUTO}
            if self._assist_compatibility is True:
               hvac_mode_map = {"off": HVACMode.OFF, "on": HVACMode.HEAT} 
            if (heating_system_state is None):
                return HVACMode.OFF
            else:
                if type == "pilot_wire":
                    return hvac_mode_map.get(heating_system_state)
                else:
                    return hvac_mode_map.get(heating_system_state)
        else:
            return HVACMode.HEAT
        
    def map_hvac_action(self, zone_data):
        heating_status = zone_data.get("heating_status")
        heating_system_state = zone_data.get("heating_system_state")
        if heating_system_state == "off":
            return HVACAction.OFF
        hvac_action_map = {"cooling": HVACAction.IDLE, "heating": HVACAction.HEATING}
        if heating_status is None:
            return HVACAction.IDLE
        else:
            return hvac_action_map.get(heating_status)

    def map_preset_mode(self, comap_mode):
        return PRESET_MODE_MAP.get(comap_mode)

    def map_comap_mode(self, ha_mode):
        return PRESET_MODE_MAP.inverse[ha_mode]

    def get_target_temperature(self, instruction, set_point_type):
        target_temperature = None
        if set_point_type == "custom_temperature":
            target_temperature = instruction
        elif set_point_type == "defined_temperature":
            try:
                temperatures = self.coordinator.data["temperatures"]
                if instruction in temperatures:
                    target_temperature = temperatures[instruction]
                elif instruction in temperatures["connected"]:
                    target_temperature = temperatures["connected"][
                        instruction
                    ]
                elif instruction in temperatures["smart"]:
                    target_temperature = temperatures["smart"][instruction]
                else:
                    target_temperature = 0
            except:
                target_temperature = 0
        return target_temperature
