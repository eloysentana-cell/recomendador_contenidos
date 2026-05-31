import csv
import os
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://ceeielche.emprenemjunts.es"
URL_MODELOS = "https://ceeielche.emprenemjunts.es/?op=35&quebusco=3&bgcanal=-1&bbtipofic=26&estado=3&orlis=1&fmto=3&buscar=1"
CARPETA_SALIDA = os.path.join("data", "raw", "ceei_elche", "pdf", "Modelos_de_Negocio_texto")
INDEX_PATH = os.path.join(CARPETA_SALIDA, "INDEX_MODELOS_TEXTO.csv")
MAX_DOCUMENTOS = 40

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
}


def limpiar_nombre_archivo(titulo):
    """Normaliza titulos para usarlos como nombres de archivo en Windows."""
    nombre = "".join(c if c.isalnum() or c in " -_" else "_" for c in titulo)
    return nombre[:120].strip() or "modelo_de_negocio"


def extraer_enlaces_modelos(max_total=200):
    """Recorre la paginacion de Modelos de Negocio y recoge las fichas."""
    enlaces = []
    pagina = 0
    cuantos = 15

    while len(enlaces) < max_total:
        url = (
            f"{URL_MODELOS}&empieza={pagina * cuantos}&cuantos={cuantos}"
            if pagina > 0
            else URL_MODELOS
        )
        response = requests.get(url, headers=HEADERS, timeout=12)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        nuevos = 0
        for a in soup.find_all("a", href=True):
            href = a["href"]
            titulo = a.get_text(strip=True)
            if "?op=13&n=" not in href or not titulo or len(titulo) <= 5:
                continue

            full_url = urljoin(BASE_URL, href)
            if not any(full_url == enlace[0] for enlace in enlaces):
                enlaces.append((full_url, titulo))
                nuevos += 1

        if nuevos == 0:
            break

        pagina += 1
        time.sleep(1.0)

    return enlaces[:max_total]


def tiene_pdf_descargable(soup):
    """Distingue fichas con PDF real de fichas que solo son pagina web."""
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if "contando2.php" in href or href.endswith(".pdf"):
            return True
    return False


def extraer_texto_documento(soup):
    """Limpia HTML auxiliar y devuelve texto util para procesado posterior."""
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    titulo = soup.find("h1")
    partes = []
    if titulo:
        partes.append(titulo.get_text(" ", strip=True))

    main = soup.find("main") or soup.find("article") or soup.body or soup
    texto = main.get_text("\n", strip=True)
    lineas = []
    for linea in texto.splitlines():
        linea = " ".join(linea.split())
        if len(linea) >= 25 and linea not in lineas:
            lineas.append(linea)

    partes.extend(lineas)
    return "\n".join(partes).strip()


def cargar_urls_extraidas():
    """Evita repetir paginas ya exportadas a texto."""
    if not os.path.exists(INDEX_PATH):
        return []

    with open(INDEX_PATH, newline="", encoding="utf-8") as f:
        return [fila["url"] for fila in csv.DictReader(f) if fila.get("url")]


def main():
    os.makedirs(CARPETA_SALIDA, exist_ok=True)
    urls_extraidas = set(cargar_urls_extraidas())
    filas_index = []
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, newline="", encoding="utf-8") as f:
            filas_index = list(csv.DictReader(f))

    descargados = 0
    enlaces = extraer_enlaces_modelos()
    print(f"Encontradas {len(enlaces)} entradas de Modelos de Negocio")

    for url, titulo in enlaces:
        if descargados >= MAX_DOCUMENTOS:
            break
        if url in urls_extraidas:
            continue

        response = requests.get(url, headers=HEADERS, timeout=12)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        if tiene_pdf_descargable(soup):
            continue

        texto = extraer_texto_documento(soup)
        if not texto:
            continue

        nombre = limpiar_nombre_archivo(titulo)
        ruta = os.path.join(CARPETA_SALIDA, f"{nombre}.txt")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(f"Titulo: {titulo}\n")
            f.write(f"URL: {url}\n\n")
            f.write(texto)

        filas_index.append({"titulo": titulo, "url": url, "archivo": os.path.basename(ruta)})
        urls_extraidas.add(url)
        descargados += 1
        print(f"OK {nombre}")
        time.sleep(1.0)

    with open(INDEX_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["titulo", "url", "archivo"])
        writer.writeheader()
        writer.writerows(filas_index)

    print(f"Documentos de texto extraidos: {descargados}")
    print(f"Carpeta: {CARPETA_SALIDA}")


if __name__ == "__main__":
    main()
