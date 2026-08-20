import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timedelta
import requests
from dateutil import parser

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

def normalize_to_list(data):
    """Garanteix que sempre tinguem una llista d'elements per iterar, sigui quin sigui el format del JSON."""
    items = []
    if isinstance(data, dict):
        resposta = data.get("resposta", data)
        if isinstance(resposta, dict):
            # Cerca en claus habituals
            target = resposta.get("item") or resposta.get("items") or resposta.get("programes") or resposta
            if isinstance(target, list):
                items = target
            elif isinstance(target, dict):
                # Si 'item' és un sol diccionari o conté una llista interna
                items = [target]
        elif isinstance(resposta, list):
            items = resposta
    elif isinstance(data, list):
        items = data
    return items

def create_epg_xml(data):
    tv = ET.Element("tv", generator_info_name="3Cat EPG Generator")
    
    # Canal principal
    channel_el = ET.SubElement(tv, "channel", id="tv3")
    display_el = ET.SubElement(channel_el, "display-name")
    display_el.text = "3Cat / TV3"

    raw_items = normalize_to_list(data)

    for item in raw_items:
        if not isinstance(item, dict):
            continue

        # Si l'element és un contenidor que té una llista interna d'emissions/programes
        sub_items = item.get("emissions") or item.get("items") or [item]
        if not isinstance(sub_items, list):
            sub_items = [sub_items]

        for prog in sub_items:
            if not isinstance(prog, dict):
                continue

            # Extracció de títol
            titol = (
                prog.get("titol_programa") or 
                prog.get("titol") or 
                prog.get("nom") or 
                prog.get("titol_emissio")
            )
            
            if not titol or not str(titol).strip():
                continue

            # Extracció de dates
            start_raw = (
                prog.get("data_ini") or 
                prog.get("hora_inici") or 
                prog.get("data_emissio") or 
                prog.get("data")
            )
            end_raw = prog.get("data_fi") or prog.get("hora_fi")
            durada = prog.get("durada") or prog.get("duracio")

            dt_start = parse_iso_date(start_raw)
            dt_end = parse_iso_date(end_raw)

            if dt_start and not dt_end and durada:
                try:
                    dt_end = dt_start + timedelta(minutes=int(durada))
                except ValueError:
                    pass

            start_str = dt_start.strftime("%Y%m%d%H%M%S +0000") if dt_start else datetime.utcnow().strftime("%Y%m%d%H%M%S +0000")
            
            attr = {"start": start_str, "channel": "tv3"}
            if dt_end:
                attr["stop"] = dt_end.strftime("%Y%m%d%H%M%S +0000")

            # Creació del node <programme>
            p_el = ET.SubElement(tv, "programme", attr)

            t_el = ET.SubElement(p_el, "title", lang="ca")
            t_el.text = str(titol).strip()

            subtitol = prog.get("titol_capitol") or prog.get("capitol") or prog.get("subtitol")
            if subtitol and str(subtitol).strip() != str(titol).strip():
                s_el = ET.SubElement(p_el, "sub-title", lang="ca")
                s_el.text = str(subtitol).strip()

            sinopsi = prog.get("sinopsi") or prog.get("descripcio") or prog.get("desc")
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
        print("EPG generat correctament!")
    except Exception as e:
        print(f"Error generant l'EPG: {e}")
        raise e
