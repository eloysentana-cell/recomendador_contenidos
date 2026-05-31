import csv
import os
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


# Scraper principal para descargar PDFs desde las secciones de recursos de CEEI.
# El indice CSV permite reanudar ejecuciones sin registrar dos veces el mismo
# documento dentro de una misma seccion.
BASE_URL = "https://ceeielche.emprenemjunts.es"
CARPETA_RAIZ = os.path.join("data", "raw", "ceei_elche", "pdf")
INDEX_PATH = os.path.join(CARPETA_RAIZ, "INDEX_DOCUMENTOS.csv")

MAX_NUEVOS = 40
MAX_ENLACES_POR_SECCION = 200

# Dejar la lista vacia para recorrer todas las secciones.
SECCIONES_OBJETIVO = ["Modelos_de_Negocio"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/134.0.0.0 Safari/537.36"
    )
}

SECCIONES = [
    {
        "nombre": "Fichas",
        "url_base": "https://ceeielche.emprenemjunts.es/?op=35&buscar=1&quebusco=3&cuantos=15&bbtipofic=1&bgcarga=1&estado=3&bgcanal=-1",
    },
    {
        "nombre": "Modelos_de_Negocio",
        "url_base": "https://ceeielche.emprenemjunts.es/?op=35&quebusco=3&bgcanal=-1&bbtipofic=26&estado=3&orlis=1&fmto=3&buscar=1",
    },
    {
        "nombre": "Infografias",
        "url_base": "https://ceeielche.emprenemjunts.es/?op=35&quebusco=20&bbtipoagru=991",
    },
    {
        "nombre": "Informes_y_Publicaciones",
        "url_base": "https://ceeielche.emprenemjunts.es/?op=35&buscar=1&quebusco=20&bbtipoagru=667",
    },
    {
        "nombre": "Manuales",
        "url_base": "https://ceeielche.emprenemjunts.es/?op=35&quebusco=20&bbtipoagru=673",
    },
]


def crear_carpetas():
    os.makedirs(CARPETA_RAIZ, exist_ok=True)


def limpiar_nombre_archivo(titulo):
    """Convierte un titulo web en un nombre de archivo valido para Windows."""
    nombre = "".join(c if c.isalnum() or c in " -_" else "_" for c in titulo)
    return nombre[:120].strip() or "documento"


def ruta_pdf(titulo, seccion):
    nombre_limpio = limpiar_nombre_archivo(titulo)
    return os.path.join(CARPETA_RAIZ, seccion, f"{nombre_limpio}.pdf")


def cargar_index_existente():
    """Carga el indice y crea claves por seccion para evitar duplicados."""
    if not os.path.exists(INDEX_PATH):
        return [], set()

    with open(INDEX_PATH, newline="", encoding="utf-8") as f:
        filas = list(csv.DictReader(f))

    claves = {
        (fila.get("seccion"), fila.get("url"))
        for fila in filas
        if fila.get("seccion") and fila.get("url")
    }
    return filas, claves


def es_pdf_valido(response):
    """Comprueba el tipo MIME y la cabecera magica del archivo."""
    content_type = response.headers.get("content-type", "").lower()
    return "pdf" in content_type or response.content[:4] == b"%PDF"


def extraer_enlaces_paginados(url_base, max_total=MAX_ENLACES_POR_SECCION):
    """Recorre la paginacion y recoge enlaces a fichas de documentos."""
    enlaces = []
    pagina = 0
    cuantos = 15

    while len(enlaces) < max_total:
        url = (
            f"{url_base}&empieza={pagina * cuantos}&cuantos={cuantos}"
            if pagina > 0
            else url_base
        )

        try:
            response = requests.get(url, headers=HEADERS, timeout=12)
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"   Error leyendo pagina {url}: {exc}")
            break

        soup = BeautifulSoup(response.text, "html.parser")
        nuevos = 0

        for a in soup.find_all("a", href=True):
            href = a["href"]
            titulo = a.get_text(strip=True)
            if "?op=13&n=" not in href or not titulo or len(titulo) <= 5:
                continue

            full_url = urljoin(BASE_URL, href)
            if any(full_url == enlace[0] for enlace in enlaces):
                continue

            enlaces.append((full_url, titulo))
            nuevos += 1
            if len(enlaces) >= max_total:
                return enlaces[:max_total]

        if nuevos == 0:
            break

        pagina += 1
        time.sleep(1.5)

    return enlaces[:max_total]


def localizar_enlace_descarga(soup):
    """Encuentra el enlace interno que entrega el PDF real."""
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if "contando2.php" in href or href.endswith(".pdf"):
            return urljoin(BASE_URL, a["href"])
    return None


def descargar_pdf(url_doc, titulo, seccion):
    """Entra en la ficha del documento, localiza el enlace real y guarda el PDF."""
    ruta = ruta_pdf(titulo, seccion)
    if os.path.exists(ruta):
        print(f"      Ya existe: {os.path.basename(ruta)[:75]}...")
        return False

    try:
        response = requests.get(url_doc, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        link_descarga = localizar_enlace_descarga(soup)
        if not link_descarga:
            return False

        pdf_response = requests.get(link_descarga, headers=HEADERS, stream=True, timeout=20)
        pdf_response.raise_for_status()

        if not es_pdf_valido(pdf_response):
            return False

        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "wb") as f:
            for chunk in pdf_response.iter_content(8192):
                f.write(chunk)

        print(f"      OK {limpiar_nombre_archivo(titulo)[:75]}...")
        return True
    except requests.RequestException as exc:
        print(f"      Error descargando: {exc}")
        return False


def obtener_secciones_objetivo():
    """Permite limitar ejecuciones sin tocar el resto de la configuracion."""
    if not SECCIONES_OBJETIVO:
        return SECCIONES
    return [sec for sec in SECCIONES if sec["nombre"] in SECCIONES_OBJETIVO]


def main():
    crear_carpetas()
    total_descargados = 0
    index, documentos_registrados = cargar_index_existente()

    for sec in obtener_secciones_objetivo():
        if total_descargados >= MAX_NUEVOS:
            break

        restantes = MAX_NUEVOS - total_descargados
        print(f"\nProcesando: {sec['nombre'].replace('_', ' ')} (faltan {restantes} nuevos)")

        enlaces = extraer_enlaces_paginados(sec["url_base"])
        print(f"   Encontrados: {len(enlaces)} enlaces")

        for url_doc, titulo in enlaces:
            if total_descargados >= MAX_NUEVOS:
                break

            clave_documento = (sec["nombre"], url_doc)
            if clave_documento in documentos_registrados:
                continue

            if descargar_pdf(url_doc, titulo, sec["nombre"]):
                total_descargados += 1
                index.append({"seccion": sec["nombre"], "titulo": titulo, "url": url_doc})
                documentos_registrados.add(clave_documento)

            time.sleep(1.7)

    # El indice se reescribe completo para conservar lo anterior y anadir lo nuevo.
    with open(INDEX_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["seccion", "titulo", "url"])
        writer.writeheader()
        writer.writerows(index)

    print("\nProceso terminado.")
    print(f"   PDFs nuevos descargados: {total_descargados}")
    print(f"   Total registrado en indice: {len(index)}")
    print(f"   Carpeta: {CARPETA_RAIZ}")


if __name__ == "__main__":
    main()
