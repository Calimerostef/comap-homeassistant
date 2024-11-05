from datetime import datetime, timedelta, timezone

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, COMAP_PRESENCE_INTERVAL
from .comap_functions import get_zone_infos

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
) -> None:

    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    zones = coordinator.data["thermal_details"].get("zones")

    entities = list()
    for zone in zones:
        if (
            "last_presence_detected" in zone.keys()
            and zone["last_presence_detected"] != None
        ):
            entities.append(
                ComapPresenceSensor(
                    coordinator=coordinator, zone_id=zone.get("id"), zone_name=zone.get("title"), config_entry=config_entry
                )
            )
    # entities: entities
    async_add_entities(entities)

class ComapPresenceSensor(CoordinatorEntity,BinarySensorEntity):
    def __init__(self, coordinator, zone_id, zone_name, config_entry):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.zone_id = zone_id
        self.zone_name = zone_name
        self.config_entry = config_entry  # Config entry pour accéder aux options
        self._attr_device_class = BinarySensorDeviceClass.OCCUPANCY
        self._name = zone_name + " presence"
        self._id = coordinator.data["housing"].get("id") + "_" + zone_id + "_presence"
        self._is_on = None

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
        thermal_details = self.coordinator.data["thermal_details"]
        zone = get_zone_infos(self.zone_id, thermal_details)
        last_presence_detected = zone.get("last_presence_detected")
        return self.is_occupied(last_presence_detected)

    @property
    def extra_state_attributes(self) -> dict:
        thermal_details = self.coordinator.data["thermal_details"]
        zone = get_zone_infos(self.zone_id, thermal_details)
        last_presence_detected = zone.get("last_presence_detected")
        return {
            "last_presence_detected": last_presence_detected,
            "presence_interval": self.config_entry.options.get(COMAP_PRESENCE_INTERVAL)
        }


    def is_occupied(self, timestamp):
        now = datetime.now(timezone.utc)
        presence = datetime.fromisoformat(timestamp)
        presence_interval = self.config_entry.options.get(COMAP_PRESENCE_INTERVAL, 60)
        interval_timedelta = timedelta(minutes=presence_interval)
        return now - presence < interval_timedelta