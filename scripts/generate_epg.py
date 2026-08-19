import json
import xml.etree.ElementTree as ET
from xml.dom import minidrom
from datetime import datetime
import requests
from dateutil import parser

# URL de l'API de 3Cat
URL = "https://dinamics.3cat.cat/wsarafem/arafem/tv/profile/noimage/geo/cat"

def fetch_data():
    response = requests.get(URL)
    response.raise_for_status()
    return response.json()

def format_xmltv_date(date_str):
    """Converteix dates ISO/string al format XMLTV: YYYYMMDDHHMMSS +0000"""
    dt = parser.parse(date_str)
    return dt.strftime("%Y%m%d%H%M%S %z")

def create_epg_xml(data):
    tv = ET.Element("tv", generator_info_name="3Cat EPG Generator")
    
    # 1. Definir Canals (s'extreuen o es creen dinàmicament)
    channels_added = set()
    
    # Recórrer programes per registrar canals i emissions
    # Ajusta les claus JSON segons l'estructura exacta de la resposta de l'API
    items = data.get("resposta", {}).get("item", []) if isinstance(data, dict) else []

    for item in items:
        channel_id = item.get("cadena_id", "3cat.cat")
        channel_name = item.get("cadena_nom", "3Cat")
        
        if channel_id not in channels_added:
            channel_el = ET.SubElement(tv, "channel", id=str(channel_id))
            display_el = ET.SubElement(channel_el, "display-name")
            display_el.text = channel_name
            channels_added.add(channel_id)

        # 2. Afegir Programació (programme)
        start_time = format_xmltv_date(item.get("data_ini"))
        end_time = format_xmltv_date(item.get("data_fi"))
        
        programme = ET.SubElement(tv, "programme", {
            "start": start_time,
            "stop": end_time,
            "channel": str(channel_id)
        })
        
        # Títol del programa
        title = ET.SubElement(programme, "title", lang="ca")
        title.text = item.get("titol", "Sense títol")
        
        # Descripció (si existeix)
        if item.get("descripcio"):
            desc = ET.SubElement(programme, "desc", lang="ca")
            desc.text = item.get("descripcio")

    # Format de text XML net
    xml_str = minidom.parseString(ET.tostring(tv, encoding="utf-8")).toprettyxml(indent="  ")
    return xml_str

if __name__ == "__main__":
    raw_data = fetch_data()
    xml_content = create_epg_xml(raw_data)
    
    with open("epg.xml", "w", encoding="utf-8") as f:
        f.write(xml_content)
