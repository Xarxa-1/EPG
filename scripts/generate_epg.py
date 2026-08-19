import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timedelta
import requests
from dateutil import parser

URL = "https://dinamics.3cat.cat/wsarafem/arafem/tv/profile/noimage/geo/cat"

def fetch_data():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(URL, headers=headers)
    response.raise_for_status()
    return response.json()

def format_xmltv_date(date_obj):
    """Converteix un objecte datetime al format XMLTV: YYYYMMDDHHMMSS +0000"""
    if not date_obj:
        return ""
    return date_obj.strftime("%Y%m%d%H%M%S %z")

def parse_iso_date(date_str):
    if not date_str:
        return None
    try:
        return parser.parse(date_str)
    except Exception:
        return None

def extract_items(data):
    """Extreu la llista de programes independentment de l'estructura arrel del JSON"""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Cerquem en estructures habituals de l'API de 3Cat
        if "resposta" in data and isinstance(data["resposta"], dict):
            items = data["resposta"].get("item", [])
            return items if isinstance(items, list) else [items]
        if "items" in data and isinstance(data["items"], list):
            return data["items"]
        if "programes" in data and isinstance(data["programes"], list):
            return data["programes"]
        # Si té una clau principal amb llista
        for v in data.values():
            if isinstance(v, list):
                return v
    return []

def create_epg_xml(data):
    tv = ET.Element("tv", generator_info_name="3Cat EPG Generator")
    
    channels_added = set()
    items = extract_items(data)

    for item in items:
        if not isinstance(item, dict):
            continue

        # 1. Extracció de dades del canal
        codi_canal = str(
            item.get("codi_canal") or 
            item.get("cadena_id") or 
            item.get("channel_id") or 
            item.get("canal") or 
            "3cat"
        )
        
        nom_canal = str(
            item.get("nom_canal") or 
            item.get("cadena_nom") or 
            item.get("channel_name") or 
            "3Cat"
        )

        # Crear canal si encara no s'ha afegit a l'XML
        if codi_canal not in channels_added:
            channel_el = ET.SubElement(tv, "channel", id=codi_canal)
            display_el = ET.SubElement(channel_el, "display-name")
            display_el.text = nom_canal
            channels_added.add(codi_canal)

        # 2. Extracció de dates i durada
        start_str = (
            item.get("data_ini") or 
            item.get("hora_inici") or 
            item.get("data_emissio") or 
            item.get("start")
        )
        end_str = (
            item.get("data_fi") or 
            item.get("hora_fi") or 
            item.get("stop")
        )
        
        start_dt = parse_iso_date(start_str)
        end_dt = parse_iso_date(end_str)

        # Durada (en minuts o format text/segons)
        durada = item.get("durada") or item.get("duration")

        # Si no hi ha hora de fi però tenim inici i durada, la calculem
        if start_dt and not end_dt and durada:
            try:
                minuts = int(durada)
                end_dt = start_dt + timedelta(minutes=minuts)
            except ValueError:
                pass

        start_time = format_xmltv_date(start_dt)
        end_time = format_xmltv_date(end_dt)

        if not start_time:
            continue

        # Atributs del programa
        prog_attr = {"start": start_time, "channel": codi_canal}
        if end_time:
            prog_attr["stop"] = end_time

        programme = ET.SubElement(tv, "programme", prog_attr)

        # 3. Títol del programa
        titol_programa = str(
            item.get("titol_programa") or 
            item.get("titol") or 
            item.get("nom") or 
            "Sense títol"
        )
        title_el = ET.SubElement(programme, "title", lang="ca")
        title_el.text = titol_programa

        # 4. Títol del capítol (Subtítol en format XMLTV)
        titol_capitol = (
            item.get("titol_capitol") or 
            item.get("capitol") or 
            item.get("subtitle")
        )
        if titol_capitol:
            sub_title_el = ET.SubElement(programme, "sub-title", lang="ca")
            sub_title_el.text = str(titol_capitol)

        # 5. Sinopsi / Descripció
        sinopsi = (
            item.get("sinopsi") or 
            item.get("descripcio") or 
            item.get("desc")
        )
        if sinopsi:
            desc_el = ET.SubElement(programme, "desc", lang="ca")
            desc_el.text = str(sinopsi)

        # 6. Durada (etiqueta <length units="minutes">)
        if durada:
            length_el = ET.SubElement(programme, "length", units="minutes")
            length_el.text = str(durada)

    xml_str = minidom.parseString(ET.tostring(tv, encoding="utf-8")).toprettyxml(indent="  ")
    return xml_str

if __name__ == "__main__":
    try:
        raw_data = fetch_data()
        xml_content = create_epg_xml(raw_data)
        
        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
        print("EPG generat correctament amb tots els camps!")
    except Exception as e:
        print(f"Error generant l'EPG: {e}")
        raise e
