"""ComapSmartHome custom component."""

from asyncio import timeout
from datetime import timedelta
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ComapClient
from .const import DOMAIN, COMAP_SENSOR_SCAN_INTERVAL

from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "climate", "switch", "select", "binary_sensor", "button", "number", "time"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry
):
    
    config = entry.data
    api_client = ComapClient(username=config[CONF_USERNAME], password=config[CONF_PASSWORD])

    refresh_interval = entry.options.get(COMAP_SENSOR_SCAN_INTERVAL, 5)

    # Fonction qui récupère les données de l'API
    async def async_fetch_data():
        try:
            data = {}
            temperatures = await api_client.get_custom_temperatures()
            housing = await api_client.async_gethousing_data()
            connected_objects = await api_client.get_housing_connected_objects()
            thermal_details = await api_client.get_thermal_details()
            for zone in thermal_details.get("zones"):
                zone["heating_system_state"] = thermal_details["heating_system_state"]
            programs = await api_client.get_programs()
            prglist = programs.get("programs")
            parsed_programs = {}
            active_program_name = None
            for program in prglist:
                parsed_programs.update({program["title"]: program["id"]})
                if program["is_activated"]:
                    active_program_name = program["title"]
            active_program = await api_client.get_active_program()

            schedules = await api_client.get_schedules()
            parsed_schedules = {}
            for schedule in schedules:
                parsed_schedules.update({schedule["title"]: schedule["id"]})


            comap_temperatures = [
                {
                    "id": "night",
                    "name": "Nuit",
                    "value": temperatures["night"],
                    "icon": "mdi:weather-night"
                },
                {
                    "id": "away",
                    "name": "Absence",
                    "value": temperatures["away"],
                    "icon": "mdi:home-export-outline"
                },
                {
                    "id": "frost_protection",
                    "name": "Hors Gel",
                    "value": temperatures["frost_protection"],
                    "icon": "mdi:snowflake"
                },
                {
                    "id": "presence_1",
                    "name": "Présence 1",
                    "value": temperatures["connected"]["presence_1"],
                    "icon": "mdi:numeric-1-circle-outline"
                },
                {
                    "id": "presence_2",
                    "name": "Présence 2",
                    "value": temperatures["connected"]["presence_2"],
                    "icon": "mdi:numeric-2-circle-outline"
                },
                {
                    "id": "presence_3",
                    "name": "Présence 3",
                    "value": temperatures["connected"]["presence_3"],
                    "icon": "mdi:numeric-3-circle-outline"
                },
                {
                    "id": "presence_4",
                    "name": "Présence 4",
                    "value": temperatures["connected"]["presence_4"],
                    "icon": "mdi:numeric-4-circle-outline"

                }
            ]

            data = {
                "temperatures": temperatures,
                "housing" : housing,
                "thermal_details": thermal_details,
                "connected_objects": connected_objects,
                "schedules": schedules,
                "programs": programs,
                "parsed_programs": parsed_programs,
                "active_program": active_program,
                "active_program_name" : active_program_name,
                "parsed_schedules": parsed_schedules,
                "comap_temperatures": comap_temperatures,
            }

            return data
        
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}")
        
    # Configure le coordinateur
    coordinator = DataUpdateCoordinator(
        hass,
        logging.getLogger(__name__),
        name="Comap Smart Home Data",
        update_method=async_fetch_data,
        update_interval=timedelta(minutes=refresh_interval),
    )

    # Charge les données pour la première fois
    await coordinator.async_config_entry_first_refresh()

    # Stocke le coordinateur dans hass.data pour qu'il soit accessible par les sensors
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Charge les entités
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # service

    async def set_temporary_instruction_service(call):
        """Handle the service call to set a custom temperature."""
        entity_id = call.data["entity_id"]
        instruction = call.data["instruction"]
        duration = call.data["duration"]

        entity = hass.states.get(entity_id)
        if not entity:
            raise ValueError(f"Entity {entity_id} not found")
        
        # Récupérer l'attribut `zone_id`
        zone_id = entity.attributes.get("zone_id")
        if not zone_id:
            raise ValueError(f"zone_id for {entity_id} not found")

        # Appeler l'API pour définir la nouvelle température
        try:
            await api_client.set_temporary_instruction(zone_id, instruction, duration)
            _LOGGER.info(f"Successfully set {entity_id} temperature to {instruction}")
        except Exception as err:
            _LOGGER.error(f"Failed to set temperature: {err}")
            raise ValueError("Unable to set instruction")

        # Mettre à jour les données via le coordinateur
        await coordinator.async_request_refresh()

    # Enregistrer le service
    hass.services.async_register(
        DOMAIN,
        "set_temporary_instruction",
        set_temporary_instruction_service,
    )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Handle removal of an entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok