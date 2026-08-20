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

def parse_iso_date(date_str):
    if not date_str:
        return None
    try:
        return parser.parse(str(date_str))
    except Exception:
        return None

def extract_all_dicts(obj):
    """Extreu tots els objectes/diccionaris del JSON de forma recursiva"""
    dicts = []
    if isinstance(obj, dict):
        dicts.append(obj)
        for v in obj.values():
            dicts.extend(extract_all_dicts(v))
    elif isinstance(obj, list):
        for item in obj:
            dicts.extend(extract_all_dicts(item))
    return dicts

def create_epg_xml(data):
    tv = ET.Element("tv", generator_info_name="3Cat EPG Generator")
    
    all_nodes = extract_all_dicts(data)
    channels_dict = {} # Guarda id: nom del canal
    programmes = []

    for node in all_nodes:
        # Cerquem el títol del programa
        titol = None
        for k in ["titol", "titol_programa", "nom", "title"]:
            if k in node and isinstance(node[k], str) and len(node[k].strip()) > 1:
                titol = node[k].strip()
                break
        
        # Només processem si hem trobat un títol de programa
        if titol:
            # 1. Identificar el canal real
            codi_canal = "3cat"
            nom_canal = "3Cat"
            
            # Cerca de claus de canal habituals de 3Cat
            for k in ["codi_canal", "cadena_id", "canal_id", "channel_id", "canal"]:
                if k in node and node[k]:
                    codi_canal = str(node[k]).lower().replace(" ", "")
                    break

            for k in ["nom_canal", "cadena_nom", "canal_nom", "channel_name", "cadena"]:
                if k in node and node[k]:
                    nom_canal = str(node[k]).strip()
                    break

            # Si tenim el nom del canal però el codi és genèric, creem un id a partir del nom
            if codi_canal == "3cat" and nom_canal != "3Cat":
                codi_canal = nom_canal.lower().replace(" ", "").replace("à","a").replace("é","e")

            channels_dict[codi_canal] = nom_canal

            # 2. Extracció de dates (inici i fi)
            data_ini_raw = None
            for k in ["data_ini", "hora_inici", "data_emissio", "start_time", "data", "hora_ini"]:
                if k in node and node[k]:
                    data_ini_raw = str(node[k])
                    break

            data_fi_raw = None
            for k in ["data_fi", "hora_fi", "stop_time", "end_time", "hora_fi"]:
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

            # Calcular hora de fi si no ve expressada
            if dt_start and not dt_end and durada:
                try:
                    dt_end = dt_start + timedelta(minutes=int(durada))
                except ValueError:
                    pass

            # 3. Altres camps
            titol_cap = None
            for k in ["titol_capitol", "capitol", "subtitol", "subtitle"]:
                if k in node and node[k] and str(node[k]) != titol:
                    titol_cap = str(node[k]).strip()
                    break

            sinopsi = None
            for k in ["sinopsi", "descripcio", "desc", "description"]:
                if k in node and node[k]:
                    sinopsi = str(node[k]).strip()
                    break

            programmes.append({
                "channel_id": codi_canal,
                "start": dt_start,
                "end": dt_end,
                "title": titol,
                "subtitle": titol_cap,
                "desc": sinopsi,
                "duration": durada
            })

    # Construcció de les etiquetes <channel>
    if not channels_dict:
        channels_dict["3cat"] = "3Cat"

    for c_id, c_name in channels_dict.items():
        ch_el = ET.SubElement(tv, "channel", id=c_id)
        disp_el = ET.SubElement(ch_el, "display-name")
        disp_el.text = c_name

    # Construcció de les etiquetes <programme>
    for prog in programmes:
        # Format XMLTV: YYYYMMDDHHMMSS +0000
        start_str = prog["start"].strftime("%Y%m%d%H%M%S +0000") if prog["start"] else datetime.utcnow().strftime("%Y%m%d%H%M%S +0000")
        
        attr = {"start": start_str, "channel": prog["channel_id"]}
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
        raw_data = fetch_data()
        xml_content = create_epg_xml(raw_data)
        
        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
        print("Fitxer epg.xml generat correctament amb tots els canals!")
    except Exception as e:
        print(f"Error generant l'EPG: {e}")
        raise e
