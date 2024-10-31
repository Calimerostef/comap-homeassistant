from datetime import datetime
from zoneinfo import ZoneInfo

def get_now():
    time_zone = ZoneInfo("Europe/Paris")
    return datetime.now(tz=time_zone).isoformat()


def get_connected_object_zone_infos(object_sn, thermal_details):
    zones = thermal_details.get("zones")
    zone_id = None
    zone_title = None
    for zone in zones:
        zone_obj = zone.get("connected_objects")
        for obj_serial in zone_obj:
            if obj_serial == object_sn:
                zone_title = zone.get("title")
                zone_id = zone.get("id")
    return {
        "id": zone_id,
        "title": zone_title
    }

def get_object_infos(serial_number,objects):
    retour = None
    for object in objects:
        if object.get("serial_number") == serial_number:
            retour = object
    return retour

def get_zone_infos(zone_id,thermal_details):
    retour = None
    zones = thermal_details.get("zones")
    for zone in zones:
        if zone.get("id") == zone_id:
            retour = zone
    return retour

def DateToHHMM (date_str):
    time_zone = ZoneInfo("Europe/Paris")
    date = datetime.fromisoformat(date_str)
    date_paris = date.astimezone(time_zone)
    heure_minutes = date_paris.strftime("%H:%M")
    return heure_minutes

def ModeToIcon (mode):
    if mode == "off":
        return "mdi:power-standby"
    elif mode == "away":
        return "mdi:home-export-outline"
    elif mode == "comfort -1":
        return "mdi:weather-sunny"
    elif mode == "comfort -2":
        return "mdi:weather-sunny"
    elif mode == "eco":
        return "mdi:weather-night"
    elif mode == "comfort":
        return "mdi:weather-sunny"
    else:
        return "mdi:help"