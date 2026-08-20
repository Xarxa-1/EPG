import json
import requests

URL = "https://dinamics.3cat.cat/wsarafem/arafem/tv/profile/noimage/geo/cat"

def fetch_data():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(URL, headers=headers)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    try:
        raw_data = fetch_data()
        
        # Desa les dades originals purament per analitzar-les
        with open("debug.json", "w", encoding="utf-8") as f:
            json.dump(raw_data, f, indent=2, ensure_ascii=False)
            
        # Crea un epg temporal per no trencar l'acció
        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" ?><tv generator_info_name="Diagnostic"></tv>')
            
        print("Dades capturades correctament.")
    except Exception as e:
        print(f"Error: {e}")
        raise e
