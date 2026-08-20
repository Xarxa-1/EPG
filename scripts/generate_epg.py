import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timedelta
import requests
from dateutil import parser

# URL base per a la informació de TV3 i 3Cat
URL_TV3 = "https://dinamics.3cat.cat/wsarafem/arafem/tv/profile/noimage/geo/cat"

def fetch_data(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error en carregar la URL {url}: {e}")
        return None

def parse_iso_date(date_str):
    if not date_str:
        return None
    try:
        return parser.parse(str(date_str))
    except Exception:
        return None

def create_epg_xml():
    tv = ET.Element("tv", generator_info_name="3Cat EPG Generator")
    
    # 1. Definició del canal principal
    channel_el = ET.SubElement(tv, "channel", id="tv3")
    display_el = ET.SubElement(channel_el, "display-name")
    display_el.text = "3Cat / TV3"

    # 2. Afegir la data d'avui a la URL per assegurar dades fresques
    today_str = datetime.now().strftime("%Y-%m-%d")
    url_with_date = f"{URL_TV3}/{today_str}"
    
    print(f"Consultant l'API: {url_with_date}")
    data = fetch_data(url_with_date)
    
    # Si la URL amb data falla, fem servir la URL base
    if not data:
        print("Fallback a la URL base...")
        data = fetch_data(URL_TV3)

    items = []
    if isinstance(data, dict):
        resposta = data.get("resposta", {})
        if isinstance(resposta, dict):
            items = resposta.get("item", [])
            if isinstance(items, dict):
                items = [items]

    print(f"Programes trobats: {len(items)}")

    for item in items:
        if not isinstance(item, dict):
            continue

        titol = item.get("titol_programa") or item.get("titol") or item.get("nom")
        if not titol or not str(titol).strip():
            continue

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

        if not dt_start:
            dt_start = datetime.utcnow()

        start_str = dt_start.strftime("%Y%m%d%H%M%S +0000")
        
        attr = {"start": start_str, "channel": "tv3"}
        if dt_end:
            attr["stop"] = dt_end.strftime("%Y%m%d%H%M%S +0000")

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
        xml_content = create_epg_xml()
        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
        print("EPG generat amb èxit!")
    except Exception as e:
        print(f"Error generant l'EPG: {e}")
        raise e
