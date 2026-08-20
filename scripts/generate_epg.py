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
    """Converteix la data al format d'EPG estàndard XMLTV: YYYYMMDDHHMMSS +0000"""
    if not date_obj:
        return ""
    return date_obj.strftime("%Y%m%d%H%M%S +0000")

def parse_iso_date(date_str):
    if not date_str:
        return None
    try:
        return parser.parse(str(date_str))
    except Exception:
        return None

def create_epg_xml(data):
    tv = ET.Element("tv", generator_info_name="3Cat EPG Generator")
    
    # 1. Extracció de la llista d'elements del JSON de 3Cat
    items = []
    if isinstance(data, dict):
        resposta = data.get("resposta", {})
        if isinstance(resposta, dict):
            items = resposta.get("items", []) or resposta.get("item", [])
        elif isinstance(resposta, list):
            items = resposta

    channels_added = set()

    for item in items:
        if not isinstance(item, dict):
            continue

        # Mapatge de dades del canal
        codi_canal = str(item.get("codi_canal") or item.get("cadena_id") or item.get("canal") or "tv3")
        nom_canal = str(item.get("nom_canal") or item.get("cadena_nom") or item.get("cadena") or "3Cat")

        # Afegir canal a l'XML si no s'ha afegit prèviament
        if codi_canal not in channels_added:
            channel_el = ET.SubElement(tv, "channel", id=codi_canal)
            display_el = ET.SubElement(channel_el, "display-name")
            display_el.text = nom_canal
            channels_added.add(codi_canal)

        # Mapatge de dates i durada
        start_str = item.get("hora_inici") or item.get("data_ini") or item.get("data_emissio")
        end_str = item.get("hora_fi") or item.get("data_fi")
        durada = item.get("durada") or item.get("duracio")

        start_dt = parse_iso_date(start_str)
        end_dt = parse_iso_date(end_str)

        # Si no hi ha hora de fi, la calculem amb la durada (en minuts)
        if start_dt and not end_dt and durada:
            try:
                end_dt = start_dt + timedelta(minutes=int(durada))
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

        # Títol del programa
        titol_prog = item.get("titol_programa") or item.get("titol") or item.get("nom") or "Sense títol"
        title_el = ET.SubElement(programme, "title", lang="ca")
        title_el.text = str(titol_prog)

        # Títol del capítol (subtítol)
        titol_cap = item.get("titol_capitol") or item.get("capitol") or item.get("subtitol")
        if titol_cap:
            sub_el = ET.SubElement(programme, "sub-title", lang="ca")
            sub_el.text = str(titol_cap)

        # Sinopsi / Descripció
        sinopsi = item.get("sinopsi") or item.get("descripcio") or item.get("resum")
        if sinopsi:
            desc_el = ET.SubElement(programme, "desc", lang="ca")
            desc_el.text = str(sinopsi)

        # Durada
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
        print("Fitxer epg.xml generat correctament.")
    except Exception as e:
        print(f"Error generant l'EPG: {e}")
        raise e
