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
            break
    return retour

def get_zone_infos(zone_id,thermal_details):
    retour = None
    zones = thermal_details.get("zones")
    for zone in zones:
        if zone.get("id") == zone_id:
            retour = zone
            break
    return retour

def find_in_array(key_id,key_value,array_of_objects):
    r = None
    for object in array_of_objects:
        if object.get(key_id) == key_value:
            r = object
            break
    return r

def filter_an_array(key_id,key_value,array_of_objects):
    r = None
    for object in array_of_objects:
        if object.get(key_id) == key_value:
            if r is None:
                r = []
            r.append(object)
    return r

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
        return "mdi:account-arrow-right"
    elif mode == "comfort -1":
        return "mdi:sofa"
    elif mode == "comfort -2":
        return "mdi:sofa"
    elif mode == "eco":
        return "mdi:leaf"
    elif mode == "comfort":
        return "mdi:sofa"
    else:
        return "mdi:help"
    
def build_name (housing_name=None, zone_name=None, entity_name=None):
    txt = ""
    cnt = 0
    #if not housing_name is None:
        #txt += housing_name + " "
        #cnt += 1
    if not zone_name is None:
        txt += zone_name + " "
        cnt += 1
    if not entity_name is None:
        txt += entity_name
        cnt += 1
    if cnt > 0:
        return txt
    return "no_name_entity"
