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

def extract_all_dicts(obj):
    """Busca qualsevol diccionari/objecte dins del JSON de forma recursiva"""
    dicts = []
    if isinstance(obj, dict):
        # Si te camps que semblen d'un programa, el guardem
        dicts.append(obj)
        for v in obj.values():
            dicts.extend(extract_all_dicts(v))
    elif isinstance(obj, list):
        for item in obj:
            dicts.extend(extract_all_dicts(item))
    return dicts

def create_epg_xml(data):
    tv = ET.Element("tv", generator_info_name="3Cat EPG Generator")
    
    # Imprimim les claus principals del JSON per al registre
    if isinstance(data, dict):
        print(f"--- CLAUS PRINCIPALS DEL JSON: {list(data.keys())} ---")
        if "resposta" in data and isinstance(data["resposta"], dict):
            print(f"--- CLAUS DINS DE 'resposta': {list(data['resposta'].keys())} ---")

    all_nodes = extract_all_dicts(data)
    
    # Filtrem quins nodos tenen informació util
    programmes_found = 0
    channel_el = ET.SubElement(tv, "channel", id="3cat")
    display_el = ET.SubElement(channel_el, "display-name")
    display_el.text = "3Cat"

    for node in all_nodes:
        # Cerquem qualsevol clau que pugui contenir el títol
        titol = None
        for k in ["titol", "titol_programa", "nom", "title", "text"]:
            if k in node and isinstance(node[k], str) and len(node[k]) > 1:
                titol = node[k]
                break
        
        # Cerquem qualsevol clau que pugui contenir la data
        data_ini = None
        for k in ["data_ini", "hora_inici", "data_emissio", "start", "data", "hora"]:
            if k in node and node[k]:
                data_ini = str(node[k])
                break

        # Si hem trobat com a mínim un títol, el tractem com a programa
        if titol:
            programmes_found += 1
            
            # Intentem formatejar data o fem servir un valor genèric
            try:
                dt = parser.parse(data_ini) if data_ini else None
                start_str = dt.strftime("%Y%m%d%H%M%S +0000") if dt else "20260101000000 +0000"
            except Exception:
                start_str = "20260101000000 +0000"

            prog = ET.SubElement(tv, "programme", start=start_str, channel="3cat")
            
            t_el = ET.SubElement(prog, "title", lang="ca")
            t_el.text = titol
            
            # Subtítol / Capítol
            for k in ["titol_capitol", "capitol", "subtitol"]:
                if k in node and node[k]:
                    sub_el = ET.SubElement(prog, "sub-title", lang="ca")
                    sub_el.text = str(node[k])
                    break
                    
            # Descripció / Sinopsi
            for k in ["sinopsi", "descripcio", "desc"]:
                if k in node and node[k]:
                    desc_el = ET.SubElement(prog, "desc", lang="ca")
                    desc_el.text = str(node[k])
                    break

    print(f"--- TOTAL PROGRAMES DETECTATS I CREATS: {programmes_found} ---")

    xml_str = minidom.parseString(ET.tostring(tv, encoding="utf-8")).toprettyxml(indent="  ")
    return xml_str

if __name__ == "__main__":
    raw_data = fetch_data()
    xml_content = create_epg_xml(raw_data)
    
    with open("epg.xml", "w", encoding="utf-8") as f:
        f.write(xml_content)
