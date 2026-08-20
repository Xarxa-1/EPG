import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timedelta
import requests
from dateutil import parser

# URL original confirmada
URL = "https://dinamics.3cat.cat/wsarafem/arafem/tv/profile/noimage/geo/cat"

def fetch_data():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(URL, headers=headers, timeout=15)
    response.raise_for_status()
    return response.json()

def parse_iso_date(date_str):
    if not date_str:
        return None
    try:
        return parser.parse(str(date_str))
    except Exception:
        return None

def create_epg_xml(data):
    tv = ET.Element("tv", generator_info_name="3Cat EPG Generator")
    
    # Canal principal
    channel_el = ET.SubElement(tv, "channel", id="tv3")
    display_el = ET.SubElement(channel_el, "display-name")
    display_el.text = "3Cat / TV3"

    # Neteja de la llista de programes
    items = []
    if isinstance(data, dict):
        resposta = data.get("resposta", {})
        if isinstance(resposta, dict):
            items = resposta.get("item", [])
            if isinstance(items, dict):
                items = [items]

    for item in items:
        if not isinstance(item, dict):
            continue

        # Cerca de títol en qualsevol clau possible del JSON
        titol = item.get("titol_programa") or item.get("titol") or item.get("nom") or item.get("titol_emissio")
        if not titol or not str(titol).strip():
            continue

        # Dates i durada
        start_raw = item.get("data_ini") or item.get("hora_inici") or item.get("data_emissio") or item.get("data")
        end_raw = item.get("data_fi") or item.get("hora_fi")
        durada = item.get("durada") or item.get("duracio")

        dt_start = parse_iso_date(start_raw)
        dt_end = parse_iso_date(end_raw)

        if dt_start and not dt_end and durada:
            try:
                dt_end = dt_start + timedelta(minutes=int(durada))
            except ValueError:
                pass

        # Si falla la data d'inici, assignem la data/hora actual
        start_str = dt_start.strftime("%Y%m%d%H%M%S +0000") if dt_start else datetime.utcnow().strftime("%Y%m%d%H%M%S +0000")
        
        attr = {"start": start_str, "channel": "tv3"}
        if dt_end:
            attr["stop"] = dt_end.strftime("%Y%m%d%H%M%S +0000")

        # Element programa i subetiquetes
        p_el = ET.SubElement(tv, "programme", attr)

        t_el = ET.SubElement(p_el, "title", lang="ca")
        t_el.text = str(titol).strip()

        subtitol = item.get("titol_capitol") or item.get("capitol") or item.get("subtitol")
        if subtitol and str(subtitol).strip() != str(titol).strip():
            s_el = ET.SubElement(p_el, "sub-title", lang="ca")
            s_el.text = str(subtitol).strip()

        sinopsi = item.get("sinopsi") or item.get("descripcio") or item.get("desc")
        if sinopsi and str(sinopsi).strip():
            d_el = ET.SubElement(p_el, "desc", lang="ca")
            d_el.text = str(sinopsi).strip()

        if durada:
            l_el = ET.SubElement(p_el, "length", units="minutes")
            l_el.text = str(durada)

    xml_str = minidom.parseString(ET.tostring(tv, encoding="utf-8")).toprettyxml(indent="  ")
    return xml_str

if __name__ == "__main__":
    try:
        raw_data = fetch_data()
        xml_content = create_epg_xml(raw_data)
        
        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
        print("Fitxer epg.xml regenerat correctament.")
    except Exception as e:
        print(f"Error generant l'EPG: {e}")
        raise e
