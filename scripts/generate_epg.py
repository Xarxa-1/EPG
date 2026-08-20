import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timedelta
import requests
from dateutil import parser

# Diccionari amb tots els canals de 3Cat i les seves URLs de la graella
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

def fetch_channel_data(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error descarregant {url}: {e}")
        return None

def parse_iso_date(date_str):
    if not date_str:
        return None
    try:
        return parser.parse(str(date_str))
    except Exception:
        return None

def extract_all_dicts(obj):
    dicts = []
    if isinstance(obj, dict):
        dicts.append(obj)
        for v in obj.values():
            dicts.extend(extract_all_dicts(v))
    elif isinstance(obj, list):
        for item in obj:
            dicts.extend(extract_all_dicts(item))
    return dicts

def create_epg_xml():
    tv = ET.Element("tv", generator_info_name="3Cat Multi-Channel EPG Generator")
    
    # 1. Definir tots els canals a l'XML
    for ch_id, ch_info in CHANNELS.items():
        ch_el = ET.SubElement(tv, "channel", id=ch_id)
        disp_el = ET.SubElement(ch_el, "display-name")
        disp_el.text = ch_info["name"]

    # 2. Descarregar i afegir la programació de cada canal
    for ch_id, ch_info in CHANNELS.items():
        print(f"Processant canal: {ch_info['name']}...")
        data = fetch_channel_data(ch_info["url"])
        if not data:
            continue

        all_nodes = extract_all_dicts(data)

        for node in all_nodes:
            titol = None
            for k in ["titol", "titol_programa", "nom", "title"]:
                if k in node and isinstance(node[k], str) and len(node[k].strip()) > 1:
                    titol = node[k].strip()
                    break

            if not titol:
                continue

            # Extracció de dates
            data_ini_raw = None
            for k in ["data_ini", "hora_inici", "data_emissio", "start_time", "data"]:
                if k in node and node[k]:
                    data_ini_raw = str(node[k])
                    break

            data_fi_raw = None
            for k in ["data_fi", "hora_fi", "stop_time", "end_time"]:
                if k in node and node[k]:
                    data_fi_raw = str(node[k])
                    break

            durada = None
            for k in ["durada", "duration", "duracio"]:
                if k in node and node[k]:
                    durada = str(node[k])
                    break

            dt_start = parse_iso_date(data_ini_raw)
            dt_end = parse_iso_date(data_fi_raw)

            if dt_start and not dt_end and durada:
                try:
                    dt_end = dt_start + timedelta(minutes=int(durada))
                except ValueError:
                    pass

            # Subtítol i sinopsi
            titol_cap = None
            for k in ["titol_capitol", "capitol", "subtitol", "subtitle"]:
                if k in node and node[k] and str(node[k]) != titol:
                    titol_cap = str(node[k]).strip()
                    break

            sinopsi = None
            for k in ["sinopsi", "descripcio", "desc"]:
                if k in node and node[k]:
                    sinopsi = str(node[k]).strip()
                    break

            # Crear element <programme>
            start_str = dt_start.strftime("%Y%m%d%H%M%S +0000") if dt_start else datetime.utcnow().strftime("%Y%m%d%H%M%S +0000")
            
            attr = {"start": start_str, "channel": ch_id}
            if dt_end:
                attr["stop"] = dt_end.strftime("%Y%m%d%H%M%S +0000")

            p_el = ET.SubElement(tv, "programme", attr)

            t_el = ET.SubElement(p_el, "title", lang="ca")
            t_el.text = titol

            if titol_cap:
                s_el = ET.SubElement(p_el, "sub-title", lang="ca")
                s_el.text = titol_cap

            if sinopsi:
                d_el = ET.SubElement(p_el, "desc", lang="ca")
                d_el.text = sinopsi

            if durada:
                l_el = ET.SubElement(p_el, "length", units="minutes")
                l_el.text = durada

    xml_str = minidom.parseString(ET.tostring(tv, encoding="utf-8")).toprettyxml(indent="  ")
    return xml_str

if __name__ == "__main__":
    try:
        xml_content = create_epg_xml()
        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
        print("Fitxer epg.xml generat correctament amb TOTS els canals de 3Cat!")
    except Exception as e:
        print(f"Error generant l'EPG: {e}")
        raise e
