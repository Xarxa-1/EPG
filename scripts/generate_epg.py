import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
import requests
from dateutil import parser

URL = "https://dinamics.3cat.cat/wsarafem/arafem/tv/profile/noimage/geo/cat"

def fetch_data():
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(URL, headers=headers)
    response.raise_for_status()
    return response.json()

def format_xmltv_date(date_str):
    if not date_str:
        return ""
    try:
        dt = parser.parse(date_str)
        return dt.strftime("%Y%m%d%H%M%S %z")
    except Exception:
        return ""

def create_epg_xml(data):
    tv = ET.Element("tv", generator_info_name="3Cat EPG Generator")
    
    # Canal per defecte
    channel_el = ET.SubElement(tv, "channel", id="3cat")
    display_el = ET.SubElement(channel_el, "display-name")
    display_el.text = "3Cat"

    # L'API sol retornar la llista a resposta.items o directament una llista
    items = []
    if isinstance(data, dict):
        resposta = data.get("resposta", {})
        items = resposta.get("item", []) if isinstance(resposta, dict) else []
    elif isinstance(data, list):
        items = data

    for item in items:
        if not isinstance(item, dict):
            continue

        # Cerquem les claus de dates típiques de l'API de 3Cat
        start_raw = item.get("data_emissio") or item.get("data_ini") or item.get("data")
        end_raw = item.get("data_fi")
        
        start_time = format_xmltv_date(start_raw)
        end_time = format_xmltv_date(end_raw)

        # Si no hi ha data d'inici, saltem l'element
        if not start_time:
            continue

        prog_attr = {"start": start_time, "channel": "3cat"}
        if end_time:
            prog_attr["stop"] = end_time

        programme = ET.SubElement(tv, "programme", prog_attr)
        
        title_text = item.get("titol") or item.get("nom") or "Sense títol"
        title = ET.SubElement(programme, "title", lang="ca")
        title.text = str(title_text)
        
        desc_text = item.get("descripcio") or item.get("sinopsi")
        if desc_text:
            desc = ET.SubElement(programme, "desc", lang="ca")
            desc.text = str(desc_text)

    xml_str = minidom.parseString(ET.tostring(tv, encoding="utf-8")).toprettyxml(indent="  ")
    return xml_str

if __name__ == "__main__":
    try:
        raw_data = fetch_data()
        xml_content = create_epg_xml(raw_data)
        
        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
        print("EPG generat amb èxit!")
    except Exception as e:
        print(f"Error generant l'EPG: {e}")
        raise e
