
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.const import PERCENTAGE

from .const import DOMAIN
from .comap_functions import get_connected_object_zone_infos, get_object_infos, get_now, get_zone_infos, DateToHHMM, ModeToIcon

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    themal_details = coordinator.data["thermal_details"]
    connected_objects = coordinator.data["connected_objects"]

    zones = themal_details.get("zones")
    obj_zone_names = {}
    obj_zone_ids = {}
    for zone in zones:
        zone_obj = zone.get("connected_objects")
        for obj_serial in zone_obj:
            obj_zone_names[obj_serial] = zone.get("title")
            obj_zone_ids[obj_serial] = zone.get("id")

    next_instr = [
        NextInstructionSensor(coordinator, zone)
        for zone in zones
    ]

    batt_list = []
    for object in connected_objects:
        if ('voltage_percent' in object):
            batt_list.append(object)

    batt_list = []
    for object in connected_objects:
        if ('voltage_percent' in object):
            batt_list.append(object)
    
    batt_sensors = [
        ComapBatterySensor(coordinator, batt_sensor)
        for batt_sensor in batt_list
    ]

    housing_sensors = [ComapHousingSensor(coordinator)]

    device_sensors = [
        ComapDeviceSensor(coordinator, device_sensor)
        for device_sensor in connected_objects
    ]

    sensors = batt_sensors + housing_sensors + device_sensors + next_instr

    async_add_entities(sensors, True)

class NextInstructionSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, zone):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.housing_id = coordinator.data["housing"].get("id")
        self.housing_name = coordinator.data["housing"].get("name")
        self.zone_id = zone.get("id")
        self.zone_name = self.housing_name + " " + zone.get("title")
        self.is_pilot_wire = zone.get("set_point_type") == "pilot_wire"

    @property
    def name(self):
        return self.zone_name + " Next instruction"
    
    @property
    def icon(self):
        thermal_details = self.coordinator.data["thermal_details"]
        zone_data = get_zone_infos(self.zone_id,thermal_details)
        next_timeslot = zone_data["next_timeslot"]
        instr = next_timeslot["set_point"]["instruction"]
        if self.is_pilot_wire:
            return ModeToIcon(instr)
        else:
            if zone_data.get("set_point_type") == "defined_temperature":
                comap_temperatures = self.coordinator.data["comap_temperatures"]
                for temp in comap_temperatures:
                    if temp.get("id") == instr:
                        return temp.get("icon")
            return "mdi:help"

    
    @property
    def state(self):
        thermal_details = self.coordinator.data["thermal_details"]
        zone_data = get_zone_infos(self.zone_id,thermal_details)
        next_timeslot = zone_data["next_timeslot"]
        instr = next_timeslot["set_point"]["instruction"]
        if zone_data.get("set_point_type") == "defined_temperature":
            comap_temperatures = self.coordinator.data["comap_temperatures"]
            for temp in comap_temperatures:
                if temp.get("id") == instr:
                    instr = temp.get("value")
        return instr
    
    @property
    def extra_state_attributes(self):
        attrs = {}
        thermal_details = self.coordinator.data["thermal_details"]
        zone_data = get_zone_infos(self.zone_id,thermal_details)
        next_timeslot = zone_data["next_timeslot"]
        attrs["next_timeslot"] = DateToHHMM(next_timeslot["begin_at"])
        attrs["next_instruction"] = next_timeslot["set_point"]["instruction"]
        return attrs
    
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
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self.zone_id + "_next_instruction"
    
    
        


class ComapBatterySensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, batt_sensor):
        super().__init__(coordinator)
        self.housing = coordinator.data["housing"].get("id")
        self.sn = batt_sensor.get("serial_number")
        self.model = batt_sensor.get("model")
        obj_zone_infos = get_connected_object_zone_infos(self.sn, coordinator.data["thermal_details"])
        self.zone_name = obj_zone_infos.get("title")
        if self.zone_name is None:
            self.zone_name = ""
        self._name = "Batterie " + self.model + " " + self.zone_name + " " +  coordinator.data["housing"].get("name")
        self.zone_id = obj_zone_infos.get("id")
        if self.zone_id is None:
            self.zone_id = self.housing
        self._unique_id = self.housing + "_" + self.zone_id + "_battery_" + self.model + "_"+ self.sn
        self.attrs = {}
        self.coordinator = coordinator


    @property
    def name(self):
        return self._name

    @property
    def state(self):
        objects = self.coordinator.data.get("connected_objects")
        infos = get_object_infos(self.sn, objects)
        return infos.get("voltage_percent")
    
    @property
    def device_class(self):
        return "battery"

    @property
    def unit_of_measurement(self):
        return PERCENTAGE
    
    @property
    def unique_id(self):
        return self._unique_id
    
    @property
    def extra_state_attributes(self):
        objects = self.coordinator.data.get("connected_objects")
        infos = get_object_infos(self.sn, objects)
        return {
            "voltage": infos.get("voltage"),
            "voltage_status" : infos.get("voltage_status")
        }
    
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.zone_id)
            },
            name = self.coordinator.data["housing"].get("name") + " " + self.zone_name,
            manufacturer = "comap",
            serial_number = self.zone_id
        )
    
class ComapHousingSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.housing_id = coordinator.data["housing"].get("id")
        self._name = "Infos " + coordinator.data["housing"].get("name")
        self._state = self._state = coordinator.data["thermal_details"].get("services_available")
        self.attrs = {}
        self._id = self.housing_id + "_sensor"

    @property
    def name(self):
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self):
        """Return the unique ID of the sensor."""
        return self._id

    @property
    def state(self):
        thermal_details = self.coordinator.data["thermal_details"]
        return thermal_details.get("services_available")

    @property
    def extra_state_attributes(self):
        housing = self.coordinator.data["housing"]
        attrs = {
            "automatic_update_value": get_now(),
            "automatic_update_label": "Mise à jour depuis comap : ",
            "address":  housing.get("address")
        }
        return attrs

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.housing_id)
            },
            name=self.name,
            manufacturer="comap",
            serial_number = self.housing_id
        )

class ComapDeviceSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, device_sensor):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.housing = coordinator.data["housing"].get("id")
        self._state = None
        self.sn = device_sensor.get("serial_number")
        self.model = device_sensor.get("model")
        self.attrs = {}
        self.device_sensor = device_sensor
        obj_zone_infos = get_connected_object_zone_infos(self.sn, coordinator.data["thermal_details"])
        self.zone_name = obj_zone_infos.get("title")
        if self.zone_name is None:
            self.zone_name = ""
        self._name = self.model.capitalize() + " " + self.zone_name

        self.zone_id = obj_zone_infos.get("id")
        if self.zone_id is None:
            self.zone_id = self.housing
        self._unique_id = self.housing + "_" + self.zone_id + "_" + self.model + "_"+ self.sn
    
    @property
    def name(self):
        return self._name

    @property
    def icon(self):
        icons = {
            "gateway": "mdi:network",
            "heating_module": "mdi:access-point",
            "thermostat": "mdi:home-thermometer"
        }
        if (self.model in icons):
            return icons.get(self.model)
        
        return "mdi:help-rhombus"

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def state(self):
        objects = self.coordinator.data["connected_objects"]
        infos = get_object_infos(self.sn, objects)
        return infos.get("communication_status")

    @property
    def extra_state_attributes(self):
        objects = self.coordinator.data["connected_objects"]
        attrs = get_object_infos(self.sn, objects)
        attrs["automatic_update_value"] = get_now()
        attrs["automatic_update_label"] = "Mise à jour depuis comap : "        
        return attrs

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.zone_id)
            },
            name = self.coordinator.data["housing"].get("name") + " " + self.zone_name,
            manufacturer = "comap",
            serial_number = self.zone_id
        )