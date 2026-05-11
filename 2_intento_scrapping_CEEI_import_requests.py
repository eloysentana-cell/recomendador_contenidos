import requests
from bs4 import BeautifulSoup
import os
import time
from urllib.parse import urljoin, urlparse

# Configuración
BASE_URL = "https://ceeielche.emprenemjunts.es"
START_URL = "https://ceeielche.emprenemjunts.es/?op=130&id=107"
DOWNLOAD_FOLDER = "documentos_ceei_elche"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def crear_carpeta():
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

def obtener_enlaces_documentos():
    """Extrae todos los enlaces del tipo ?op=13&n=XXXX"""
    response = requests.get(START_URL, headers=HEADERS)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    enlaces = []
    # Buscamos enlaces que contengan ?op=13&n=
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '?op=13&n=' in href:
            # Convertir enlace relativo a absoluto
            full_url = urljoin(BASE_URL, href)
            # Extraer el número para nombre de archivo
            n = href.split('n=')[-1].split('&')[0]
            titulo = a.get_text(strip=True) or f"documento_{n}"
            enlaces.append((full_url, n, titulo))
    
    # Eliminar duplicados
    return list(set(enlaces))  # por si hay repetidos

def descargar_archivo(url_documento, nombre_base):
    """Descarga el archivo PDF/DOC desde la página intermedia"""
    try:
        # Primero visitamos la página del documento
        resp = requests.get(url_documento, headers=HEADERS)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Buscamos el enlace de descarga (suele ser contando2.php o enlace directo a archivo)
        download_link = None
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'contando2.php' in href or href.endswith(('.pdf', '.doc', '.docx', '.zip')):
                download_link = urljoin(BASE_URL, href)
                break
        
        if not download_link:
            # Alternativa: buscar texto "Descargar archivo"
            for a in soup.find_all('a', string=lambda text: text and 'Descargar' in text):
                download_link = urljoin(BASE_URL, a['href'])
                break
        
        if not download_link:
            print(f"No se encontró enlace de descarga para {url_documento}")
            return False
        
        # Descargar el archivo
        file_resp = requests.get(download_link, headers=HEADERS, stream=True)
        file_resp.raise_for_status()
        
        # Determinar extensión
        content_type = file_resp.headers.get('content-type', '')
        if 'pdf' in content_type:
            ext = '.pdf'
        elif 'msword' in content_type or 'officedocument' in content_type:
            ext = '.docx'
        else:
            ext = '.pdf'  # por defecto
        
        filename = f"{nombre_base}{ext}"
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)
        
        with open(filepath, 'wb') as f:
            for chunk in file_resp.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✅ Descargado: {filename}")
        return True
        
    except Exception as e:
        print(f"❌ Error al descargar {url_documento}: {e}")
        return False

def main():
    crear_carpeta()
    print("Extrayendo enlaces de documentos...")
    
    enlaces = obtener_enlaces_documentos()
    print(f"Se encontraron {len(enlaces)} documentos.")
    
    for i, (url_doc, n, titulo) in enumerate(enlaces, 1):
        print(f"\n[{i}/{len(enlaces)}] Procesando: {titulo}")
        # Limpiar nombre para archivo
        nombre_seguro = "".join(c for c in titulo[:50] if c.isalnum() or c in " -_").strip()
        if not nombre_seguro:
            nombre_seguro = f"doc_{n}"
        
        descargar_archivo(url_doc, nombre_seguro)
        time.sleep(1)  # Pausa para no saturar el servidor

if __name__ == "__main__":
    main()