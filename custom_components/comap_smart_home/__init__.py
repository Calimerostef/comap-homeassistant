"""ComapSmartHome custom component."""

from asyncio import timeout
from datetime import timedelta
import logging

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ComapClient
from .const import DOMAIN

from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "climate", "switch", "select", "binary_sensor"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry
):
    
    config = entry.data
    api_client = ComapClient(username=config[CONF_USERNAME], password=config[CONF_PASSWORD])

    # Fonction qui récupère les données de l'API
    async def async_fetch_data():
        try:
            data = {}
            data["temperatures"] = await api_client.get_custom_temperatures()
            data["housing"] = await api_client.async_gethousing_data()
            thermal_details = await api_client.get_thermal_details()
            for zone in thermal_details["zones"]:
                zone["heating_system_state"] = thermal_details["heating_system_state"]
            data["thermal_details"] = thermal_details
            data["connected_objects"] = await api_client.get_housing_connected_objects()
            data["schedules"] = await api_client.get_schedules()
            data["programs"] = await api_client.get_programs()
            data["active_program"] = await api_client.get_active_program()
            return data
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}")
        
    # Configure le coordinateur
    coordinator = DataUpdateCoordinator(
        hass,
        logging.getLogger(__name__),
        name="Comap Smart Home Data",
        update_method=async_fetch_data,
        update_interval=timedelta(minutes=5),
    )

    # Charge les données pour la première fois
    await coordinator.async_config_entry_first_refresh()

    # Stocke le coordinateur dans hass.data pour qu'il soit accessible par les sensors
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Charge les entités
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Handle removal of an entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok