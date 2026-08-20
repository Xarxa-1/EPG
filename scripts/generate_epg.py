import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timedelta
import requests
from dateutil import parser

# Noms i identificadors estàndard dels canals de 3Cat
CANALS_MAP = {
    "tv3": "TV3",
    "324": "3/24",
    "33": "SX3 / 33",
    "sx3": "SX3 / 33",
    "es3": "Esport3",
    "esport3": "Esport3",
    "tvi": "TV3Cat",
    "tv3cat": "TV3Cat"
}

# URL principal que conté totes les dades del grup 3Cat
URL_PRINCIPAL = "https://dinamics.3cat.cat/wsarafem/arafem/tv/profile/noimage/geo/cat"

def fetch_data(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error descarregant dades: {e}")
        return None

def parse_iso_date(date_str):
    if not date_str:
        return None
    try:
        return parser.parse(str(date_str))
    except Exception:
        return None

def extract_all_dicts(obj):
    """Cerca recursiva de tots els objectes al JSON."""
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
    print("Descarregant informació de 3Cat...")
    data = fetch_data(URL_PRINCIPAL)
    if not data:
        raise Exception("No s'han pogut obtenir les dades de l'API.")

    all_nodes = extract_all_dicts(data)
    
    # 1. Trobar programes i identificar canals presents a la resposta
    programmes_by_channel = {}
    channels_found = set()

    for node in all_nodes:
        # Cercar títol
        titol = None
        for k in ["titol", "titol_programa", "nom", "title", "titol_emissio"]:
            if k in node and isinstance(node[k], str) and len(node[k].strip()) > 1:
                titol = node[k].strip()
                break

        if not titol:
            continue

        # Determinació del canal de l'element
        channel_id = "tv3"
        for k in ["codi_canal", "canal", "cadena_id", "id_cadena", "channel"]:
            if k in node and node[k]:
                val = str(node[k]).lower().strip()
                if val in CANALS_MAP:
                    channel_id = val
                    break

        channels_found.add(channel_id)

        # Dates i durada
        data_ini_raw = None
        for k in ["data_ini", "hora_inici", "data_emissio", "start_time", "data", "hora_ini"]:
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

        prog_info = {
            "title": titol,
            "start": dt_start,
            "end": dt_end,
            "subtitle": titol_cap,
            "desc": sinopsi,
            "duration": durada
        }

        if channel_id not in programmes_by_channel:
            programmes_by_channel[channel_id] = []
        programmes_by_channel[channel_id].append(prog_info)

    # 2. Construcció de l'XML final
    tv = ET.Element("tv", generator_info_name="3Cat Multi-Channel EPG Generator")

    # Crear capçaleres de tots els canals detectats (o els per defecte)
    active_channels = channels_found if channels_found else CANALS_MAP.keys()
    for ch_id in active_channels:
        ch_name = CANALS_MAP.get(ch_id, ch_id.upper())
        ch_el = ET.SubElement(tv, "channel", id=ch_id)
        disp_el = ET.SubElement(ch_el, "display-name")
        disp_el.text = ch_name

    # Afegir la programació de cada canal
    for ch_id, prog_list in programmes_by_channel.items():
        for prog in prog_list:
            dt_start = prog["start"]
            start_str = dt_start.strftime("%Y%m%d%H%M%S +0000") if dt_start else datetime.utcnow().strftime("%Y%m%d%H%M%S +0000")
            
            attr = {"start": start_str, "channel": ch_id}
            if prog["end"]:
                attr["stop"] = prog["end"].strftime("%Y%m%d%H%M%S +0000")

            p_el = ET.SubElement(tv, "programme", attr)

            t_el = ET.SubElement(p_el, "title", lang="ca")
            t_el.text = prog["title"]

            if prog["subtitle"]:
                s_el = ET.SubElement(p_el, "sub-title", lang="ca")
                s_el.text = prog["subtitle"]

            if prog["desc"]:
                d_el = ET.SubElement(p_el, "desc", lang="ca")
                d_el.text = prog["desc"]

            if prog["duration"]:
                l_el = ET.SubElement(p_el, "length", units="minutes")
                l_el.text = prog["duration"]

    xml_str = minidom.parseString(ET.tostring(tv, encoding="utf-8")).toprettyxml(indent="  ")
    return xml_str

if __name__ == "__main__":
    try:
        xml_content = create_epg_xml()
        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
        print("Fitxer epg.xml generat correctament amb la informació de tots els canals disponibles!")
    except Exception as e:
        print(f"Error generant l'EPG: {e}")
        raise e
