import requests
from bs4 import BeautifulSoup
import os
import time
from urllib.parse import urljoin

BASE_URL = "https://ceeielche.emprenemjunts.es"
START_URL = "https://ceeielche.emprenemjunts.es/?op=130&id=107"
CARPETA = "documentos_ceei_elche"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def main():
    if not os.path.exists(CARPETA):
        os.makedirs(CARPETA)

    print("🔍 Analizando la página principal...")
    enlaces = set()
    urls_a_visitar = [START_URL]

    for url in urls_a_visitar:
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Buscar todos los enlaces de documentos
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '?op=13&n=' in href:
                    full_url = urljoin(BASE_URL, href)
                    titulo = a.get_text(strip=True) or "sin_titulo"
                    nombre_limpio = "".join(c if c.isalnum() or c in " -_" else "_" for c in titulo)[:80]
                    enlaces.add((full_url, nombre_limpio))

            # Buscar enlace "ver más" o paginación
            for a in soup.find_all('a', href=True):
                text = a.get_text(strip=True).lower()
                if 'ver más' in text or 'siguiente' in text or 'más' in text:
                    next_url = urljoin(BASE_URL, a['href'])
                    if next_url not in urls_a_visitar:
                        urls_a_visitar.append(next_url)
                        print(f"→ Encontrado enlace adicional: {next_url}")

        except Exception as e:
            print(f"Error al procesar {url}: {e}")

    print(f"\n✅ Total de documentos encontrados: {len(enlaces)}\n")

    for i, (url_doc, nombre) in enumerate(enlaces, 1):
        print(f"[{i:02d}/{len(enlaces)}] → {nombre[:70]}")

        try:
            r = requests.get(url_doc, headers=HEADERS, timeout=10)
            s = BeautifulSoup(r.text, 'html.parser')

            link_descarga = None
            for link in s.find_all('a', href=True):
                href = link['href']
                if 'contando2.php' in href or href.endswith(('.pdf', '.doc', '.docx', '.zip')):
                    link_descarga = urljoin(BASE_URL, href)
                    break

            if link_descarga:
                archivo = requests.get(link_descarga, headers=HEADERS, stream=True, timeout=15)
                ext = ".pdf" if ".pdf" in link_descarga.lower() else ".docx"
                ruta = os.path.join(CARPETA, f"{nombre}{ext}")

                with open(ruta, 'wb') as f:
                    for chunk in archivo.iter_content(8192):
                        f.write(chunk)
                print("   ✅ Descargado")
            else:
                print("   ⚠️  No se encontró descarga directa")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        time.sleep(1.3)

    print("\n🎉 Proceso completado!")

if __name__ == "__main__":
    main()