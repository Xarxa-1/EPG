import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timedelta
import requests
from dateutil import parser

# Diccionari amb els canals i els seus endpoints directes
CHANNELS = {
    "tv3": {
        "name": "TV3",
        "url": "https://dinamics.3cat.cat/wsarafem/arafem/tv/profile/noimage/geo/cat"
    },
    "324": {
        "name": "3/24",
        "url": "https://dinamics.3cat.cat/wsarafem/arafem/324/profile/noimage/geo/cat"
    },
    "sx3": {
        "name": "SX3 / 33",
        "url": "https://dinamics.3cat.cat/wsarafem/arafem/33/profile/noimage/geo/cat"
    },
    "esport3": {
        "name": "Esport3",
        "url": "https://dinamics.3cat.cat/wsarafem/arafem/es3/profile/noimage/geo/cat"
    },
    "tv3cat": {
        "name": "TV3Cat",
        "url": "https://dinamics.3cat.cat/wsarafem/arafem/tvi/profile/noimage/geo/cat"
    }
}

def fetch_channel_items(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Extracció directa de la llista de programes de l'API de 3Cat
        if isinstance(data, dict):
            resposta = data.get("resposta", {})
            if isinstance(resposta, dict):
                items = resposta.get("item", [])
                if isinstance(items, list):
                    return items
                elif isinstance(items, dict):
                    return [items]
        return []
    except Exception as e:
        print(f"Error carregant {url}: {e}")
        return []

def parse_iso_date(date_str):
    if not date_str:
        return None
    try:
        return parser.parse(str(date_str))
    except Exception:
        return None

def create_epg_xml():
    tv = ET.Element("tv", generator_info_name="3Cat Multi-Channel EPG Generator")
    
    # 1. Definir els canals a l'capçalera XML
    for ch_id, ch_info in CHANNELS.items():
        ch_el = ET.SubElement(tv, "channel", id=ch_id)
        disp_el = ET.SubElement(ch_el, "display-name")
        disp_el.text = ch_info["name"]

    # 2. Llegir i processar cada canal de forma independent
    for ch_id, ch_info in CHANNELS.items():
        items = fetch_channel_items(ch_info["url"])
        print(f"Canal {ch_info['name']}: trobats {len(items)} programes.")

        for item in items:
            if not isinstance(item, dict):
                continue

            # Extracció del títol
            titol = item.get("titol_programa") or item.get("titol") or item.get("nom")
            if not titol or not str(titol).strip():
                continue

            # Extracció de dates
            start_raw = item.get("data_ini") or item.get("hora_inici") or item.get("data_emissio")
            end_raw = item.get("data_fi") or item.get("hora_fi")
            durada = item.get("durada") or item.get("duracio")

            dt_start = parse_iso_date(start_raw)
            dt_end = parse_iso_date(end_raw)

            if dt_start and not dt_end and durada:
                try:
                    dt_end = dt_start + timedelta(minutes=int(durada))
                except ValueError:
                    pass

            # Si no hi ha data inici vàlida, saltem l'element
            if not dt_start:
                continue

            start_str = dt_start.strftime("%Y%m%d%H%M%S +0000")
            
            attr = {"start": start_str, "channel": ch_id}
            if dt_end:
                attr["stop"] = dt_end.strftime("%Y%m%d%H%M%S +0000")

            # Creació de l'element <programme>
            p_el = ET.SubElement(tv, "programme", attr)

            t_el = ET.SubElement(p_el, "title", lang="ca")
            t_el.text = str(titol).strip()

            # Subtítol / Capítol
            subtitol = item.get("titol_capitol") or item.get("capitol") or item.get("subtitol")
            if subtitol and str(subtitol).strip() != str(titol).strip():
                s_el = ET.SubElement(p_el, "sub-title", lang="ca")
                s_el.text = str(subtitol).strip()

            # Descripció / Sinopsi
            sinopsi = item.get("sinopsi") or item.get("descripcio") or item.get("desc")
            if sinopsi and str(sinopsi).strip():
                d_el = ET.SubElement(p_el, "desc", lang="ca")
                d_el.text = str(sinopsi).strip()

            # Durada
            if durada:
                l_el = ET.SubElement(p_el, "length", units="minutes")
                l_el.text = str(durada)

    xml_str = minidom.parseString(ET.tostring(tv, encoding="utf-8")).toprettyxml(indent="  ")
    return xml_str

if __name__ == "__main__":
    try:
        xml_content = create_epg_xml()
        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
        print("EPG generat correctament amb la programació de tots els canals!")
    except Exception as e:
        print(f"Error: {e}")
        raise e
