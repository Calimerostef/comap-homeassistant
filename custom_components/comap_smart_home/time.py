import logging
from datetime import datetime, time
from homeassistant.components.time import TimeEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN

from .comap_functions import build_name

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
) -> None:
    
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    zones = coordinator.data["thermal_details"]["zones"]

    zones_timer = [
        ComapZoneTimer(coordinator, zone, hass)
        for zone in zones
    ]

    entities = zones_timer

    async_add_entities(entities, update_before_add=True)

class ComapZoneTimer (TimeEntity, RestoreEntity):
    def __init__(self, coordinator, zone, hass):
        self.coordinator = coordinator
        self.hass = hass
        self.zone_id = zone.get("id")
        self.zone_name = coordinator.data["housing"].get("name") + " " + zone.get("title")
        self._name = build_name(
            housing_name=coordinator.data["housing"].get("name"),
            zone_name=zone.get("title"),
            entity_name="Temporary instruction duration"
        )
        self.timer_id = self.zone_id + "_timer"
        self.tempo_id = self.zone_id + "_tempo_duration"
        self._min_time = time(0, 30)
        self._max_time = time(23,59)
        self._current_time = None

    @property
    def extra_state_attributes(self):
        """Retourne les attributs supplémentaires."""
        return {
            "min_time": self._min_time.strftime("%H:%M:%S"),
            "max_time": self._max_time.strftime("%H:%M:%S"),
        }
    
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
        return self.timer_id
    
    @property
    def icon(self) -> str:
        return "mdi:timer-outline"

    @property
    def state(self):
        """Retourne l'état actuel de l'entité sous forme de chaîne."""
        return self._current_time.strftime("%H:%M:%S")
    
    def time_to_minutes(self) -> int:
        """Convertit l'heure actuelle en nombre total de minutes."""
        return self._current_time.hour * 60 + self._current_time.minute


    def set_value(self, value: str):
        if isinstance(value, datetime):
            # Si value est un objet datetime, on extrait uniquement la partie time
            new_time = value.time()
        elif isinstance(value, time):
            # Si value est déjà un objet time
            new_time = value
        elif isinstance(value, str):
            # Si value est une chaîne de caractères au format "HH:MM:SS"
            new_time = time.fromisoformat(value)
        else:
            raise ValueError(f"Invalid value type: {type(value)}. Expected str, time, or datetime.")
        # Vérifie que la nouvelle heure est dans la plage autorisée
        
    async def async_added_to_hass(self):
        """Restore previous state when entity is added to hass."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "unknown", "unavailable"):
            self._current_time = time.fromisoformat(last_state.state)
        else:
            self._current_time = time(2, 0)
        self.hass.data[self.tempo_id] = self.time_to_minutes()