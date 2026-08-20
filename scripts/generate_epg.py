import json
import xml.etree.ElementTree as ET
from xml.dom import minidrom
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

def find_all_programmes(data):
    """Cerca recursiva per extreure TOTS els diccionaris que continguin un títol de programa."""
    programmes = []
    
    def search_recursive(node):
        if isinstance(node, dict):
            # Comprovem si aquest diccionari és un programa
            has_title = any(k in node for k in ["titol", "titol_programa", "nom", "titol_emissio"])
            has_date = any(k in node for k in ["data_ini", "hora_inici", "data_emissio", "data", "hora_ini"])
            
            if has_title and has_date:
                programmes.append(node)
            else:
                for v in node.values():
                    search_recursive(v)
        elif isinstance(node, list):
            for item in node:
                search_recursive(item)

    search_recursive(data)
    return programmes

def create_epg_xml(data):
    tv = ET.Element("tv", generator_info_name="3Cat Full EPG Generator")
    
    raw_programmes = find_all_programmes(data)
    print(f"S'han trobat {len(raw_programmes)} emissions/programes al JSON.")

    channels_dict = {}
    parsed_programmes = []

    for item in raw_programmes:
        # 1. Extracció del títol
        titol = item.get("titol_programa") or item.get("titol") or item.get("nom") or item.get("titol_emissio")
        if not titol or not str(titol).strip():
            continue

        # 2. Extracció i normalització del canal
        codi_canal = str(
            item.get("codi_canal") or 
            item.get("cadena_id") or 
            item.get("canal") or 
            item.get("id_cadena") or 
            "tv3"
        ).lower().replace(" ", "")

        nom_canal = str(
            item.get("nom_canal") or 
            item.get("cadena_nom") or 
            item.get("canal_nom") or 
            item.get("cadena") or 
            "3Cat"
        )

        channels_dict[codi_canal] = nom_canal

        # 3. Dates i durada
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

        # Subtítol i sinopsi
        titol_cap = item.get("titol_capitol") or item.get("capitol") or item.get("subtitol")
        sinopsi = item.get("sinopsi") or item.get("descripcio") or item.get("desc")

        parsed_programmes.append({
            "channel": codi_canal,
            "start": dt_start,
            "end": dt_end,
            "title": str(titol).strip(),
            "subtitle": str(titol_cap).strip() if titol_cap else None,
            "desc": str(sinopsi).strip() if sinopsi else None,
            "duration": str(durada) if durada else None
        })

    # Si no s'ha trobat cap canal, en creem un per defecte
    if not channels_dict:
        channels_dict["tv3"] = "3Cat / TV3"

    # Generar capçaleres <channel>
    for c_id, c_name in channels_dict.items():
        ch_el = ET.SubElement(tv, "channel", id=c_id)
        disp_el = ET.SubElement(ch_el, "display-name")
        disp_el.text = c_name

    # Generar tots els blocs <programme>
    for prog in parsed_programmes:
        start_str = prog["start"].strftime("%Y%m%d%H%M%S +0000") if prog["start"] else datetime.utcnow().strftime("%Y%m%d%H%M%S +0000")
        
        attr = {"start": start_str, "channel": prog["channel"]}
        if prog["end"]:
            attr["stop"] = prog["end"].strftime("%Y%m%d%H%M%S +0000")

        p_el = ET.SubElement(tv, "programme", attr)

        t_el = ET.SubElement(p_el, "title", lang="ca")
        t_el.text = prog["title"]

        if prog["subtitle"] and prog["subtitle"] != prog["title"]:
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
        print("EPG generat amb èxit!")
    except Exception as e:
        print(f"Error generant l'EPG: {e}")
        raise e
