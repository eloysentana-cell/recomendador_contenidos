"""
scraper_playwright.py

Scraper avanzado para extraer recursos documentales del CEEI Elche.

Motivo de esta versión:
La web del CEEI Elche carga parte de los documentos de forma dinámica.
Por eso, requests + BeautifulSoup solo obtiene una parte de los recursos.
Esta versión usa Playwright para abrir la web como un navegador real,
hacer scroll y extraer el HTML ya renderizado.

El resultado se guarda en CSV y Excel.
"""

# Librería para automatizar un navegador real.
from playwright.sync_api import sync_playwright

# BeautifulSoup analiza el HTML renderizado.
from bs4 import BeautifulSoup

# Pandas permite crear tablas y exportar CSV/Excel.
import pandas as pd

# Path permite crear carpetas de salida.
from pathlib import Path

# urljoin convierte enlaces relativos en URLs absolutas.
from urllib.parse import urljoin, urlparse

# time permite introducir pausas durante el scroll.
import time

# re permite limpiar textos.
import re


# URL base del portal.
BASE_URL = "https://ceeielche.emprenemjunts.es/"

# Dominio permitido.
DOMINIO_PERMITIDO = "ceeielche.emprenemjunts.es"

# Número máximo de scrolls por página.
MAX_SCROLLS = 25

# Tiempo de espera entre scrolls en milisegundos.
ESPERA_SCROLL_MS = 1000


# URLs reales de listado observadas en navegador.
# Manuales ya se ha verificado visualmente con bbtipoagru=657.
# Para el resto, partimos de las URLs de sección y dejamos que el script extraiga los enlaces útiles.
SECCIONES = {
    "manuales": {
        "url": "https://ceeielche.emprenemjunts.es/?op=35&quebusco=20&bbtipoagru=657",
        "limite_paginas": 1,
        "total_esperado_aproximado": 73,
    },
    "guias": {
        "url": "https://ceeielche.emprenemjunts.es/?op=8&n=1215",
        "limite_paginas": 20,
        "total_esperado_aproximado": None,
    },
    "fichas": {
        "url": "https://ceeielche.emprenemjunts.es/?op=8&n=1216",
        "limite_paginas": 20,
        "total_esperado_aproximado": None,
    },
    "infografias": {
        "url": "https://ceeielche.emprenemjunts.es/?op=8&n=1217",
        "limite_paginas": 1,
        "total_esperado_aproximado": None,
    },
    "informes": {
        "url": "https://ceeielche.emprenemjunts.es/?op=8&n=1218",
        "limite_paginas": 1,
        "total_esperado_aproximado": None,
    },
    "videocapsulas": {
        "url": "https://ceeielche.emprenemjunts.es/?op=8&n=1219",
        "limite_paginas": 1,
        "total_esperado_aproximado": None,
    },
    "modelos_de_negocio": {
        "url": "https://ceeielche.emprenemjunts.es/?op=8&n=1220",
        "limite_paginas": 20,
        "total_esperado_aproximado": None,
    },
    "cuadernos_de_trabajo": {
        "url": "https://ceeielche.emprenemjunts.es/?op=8&n=1221",
        "limite_paginas": 1,
        "total_esperado_aproximado": None,
    },
    "webinars": {
        "url": "https://ceeielche.emprenemjunts.es/?op=8&n=1222",
        "limite_paginas": 1,
        "total_esperado_aproximado": None,
    },
}


def crear_carpetas_salida():
    """
    Crea las carpetas donde se guardarán los resultados del scraping.
    """

    Path("data/processed").mkdir(parents=True, exist_ok=True)
    Path("outputs").mkdir(parents=True, exist_ok=True)


def normalizar_texto(texto):
    """
    Limpia texto eliminando saltos de línea, tabulaciones y espacios duplicados.
    """

    if texto is None:
        return ""

    texto = str(texto)
    texto = texto.replace("\n", " ")
    texto = texto.replace("\t", " ")
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def normalizar_minusculas(texto):
    """
    Limpia texto y lo pasa a minúsculas para poder comparar mejor.
    """

    return normalizar_texto(texto).lower()


def es_url_interna(url):
    """
    Comprueba si una URL pertenece al dominio del CEEI Elche.
    """

    dominio = urlparse(url).netloc
    return DOMINIO_PERMITIDO in dominio


def abrir_pagina_y_hacer_scroll(page, url):
    """
    Abre una página con Playwright y hace scroll hasta que no aparezca contenido nuevo.

    Parámetros:
        page: página del navegador controlada por Playwright.
        url: URL que se quiere abrir.

    Devuelve:
        HTML final renderizado después del scroll.
    """

    print(f"  Abriendo URL: {url}")

    # Abrimos la página y esperamos a que cargue la red.
    page.goto(url, wait_until="networkidle", timeout=60000)

    # Obtenemos la altura inicial de la página.
    altura_anterior = page.evaluate("document.body.scrollHeight")

    scrolls_realizados = 0

    while scrolls_realizados < MAX_SCROLLS:

        # Bajamos hasta el final de la página.
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        # Esperamos por si la web carga más elementos dinámicamente.
        page.wait_for_timeout(ESPERA_SCROLL_MS)

        # Calculamos la nueva altura.
        altura_nueva = page.evaluate("document.body.scrollHeight")

        scrolls_realizados += 1

        print(f"    Scroll {scrolls_realizados}: altura {altura_nueva}")

        # Si la altura no cambia, asumimos que ya no se ha cargado más contenido.
        if altura_nueva == altura_anterior:
            break

        altura_anterior = altura_nueva

    # Devolvemos el HTML renderizado después del scroll.
    return page.content()


def detectar_total_items(html):
    """
    Detecta si la página muestra un texto del tipo '73 items'.
    """

    soup = BeautifulSoup(html, "lxml")
    texto = soup.get_text(" ", strip=True)

    coincidencia = re.search(r"(\d+)\s+items", texto, re.IGNORECASE)

    if coincidencia:
        return int(coincidencia.group(1))

    return None


def extraer_url_listado_si_existe(html, url_origen):
    """
    Busca dentro de una página de sección si existe un enlace real de listado.

    En esta web el listado suele usar:
    op=35
    bbtipoagru=...
    """

    soup = BeautifulSoup(html, "lxml")

    for etiqueta_a in soup.find_all("a"):
        href = etiqueta_a.get("href")

        if not href:
            continue

        url = urljoin(url_origen, href)
        url_norm = normalizar_minusculas(url)

        if "op=35" in url_norm and "bbtipoagru=" in url_norm:
            return url

    return url_origen


def parece_recurso_documental(texto, url):
    """
    Determina si un enlace parece corresponder a un documento o recurso útil.
    """

    texto_norm = normalizar_minusculas(texto)
    url_norm = normalizar_minusculas(url)

    if len(texto_norm) < 5:
        return False

    # Descartamos navegación general.
    descartes = [
        "inicio",
        "actualidad",
        "agenda",
        "convocatorias",
        "agentes del ecosistema",
        "empresas",
        "quiénes somos",
        "quienes somos",
        "contacto",
        "acceder",
        "inicia sesión",
        "inicia sesion",
        "registrarse",
        "registro",
        "aviso legal",
        "política",
        "politica",
        "privacidad",
        "cookies",
        "facebook",
        "twitter",
        "linkedin",
        "instagram",
        "youtube",
        "newsletter",
        "buscar",
        "ver el listado",
        "listado ordenado",
        "emprenemjunts",
    ]

    if any(palabra in texto_norm for palabra in descartes):
        return False

    # Descartamos páginas de listado.
    if "op=35" in url_norm and "bbtipoagru=" in url_norm:
        return False

    # Documentos internos habituales.
    if "op=8" in url_norm and "n=" in url_norm:
        return True

    if "op=" in url_norm and "id=" in url_norm:
        return True

    # En algunos casos la URL puede no ser suficiente, pero el título sí.
    palabras_recurso = [
        "manual",
        "guía",
        "guia",
        "ficha",
        "infografía",
        "infografia",
        "informe",
        "videocápsula",
        "videocapsula",
        "webinar",
        "modelo",
        "negocio",
        "cuaderno",
        "empresa",
        "emprendedor",
        "financiación",
        "financiacion",
        "innovación",
        "innovacion",
        "marketing",
        "dafo",
        "plan",
    ]

    if any(palabra in texto_norm for palabra in palabras_recurso):
        return True

    return False


def extraer_recursos_desde_html(html, url_origen, seccion):
    """
    Extrae documentos desde el HTML renderizado.

    Devuelve una lista de recursos con sección, título y URL.
    """

    soup = BeautifulSoup(html, "lxml")

    recursos = []

    for etiqueta_a in soup.find_all("a"):
        texto = normalizar_texto(etiqueta_a.get_text(" ", strip=True))
        href = etiqueta_a.get("href")

        if not href:
            continue

        url = urljoin(url_origen, href)

        if not es_url_interna(url):
            continue

        if not parece_recurso_documental(texto, url):
            continue

        recursos.append({
            "seccion_origen": seccion,
            "titulo": texto,
            "url": url,
            "pagina_origen": url_origen,
        })

    return recursos


def rastrear_seccion(page, nombre_seccion, url_inicial):
    """
    Rastrea una sección.

    Primero abre la URL indicada.
    Si esa URL es una página de sección que enlaza a un listado real,
    entra en el listado real y vuelve a hacer scroll.
    """

    print(f"\nRastreando sección: {nombre_seccion}")

    # Abrimos la URL inicial y hacemos scroll.
    html_inicial = abrir_pagina_y_hacer_scroll(page, url_inicial)

    # Intentamos localizar la URL real del listado.
    url_listado = extraer_url_listado_si_existe(html_inicial, url_inicial)

    if url_listado != url_inicial:
        print(f"  URL de listado detectada: {url_listado}")

        # Abrimos el listado real y hacemos scroll.
        html_final = abrir_pagina_y_hacer_scroll(page, url_listado)
        url_origen = url_listado
    else:
        print("  No se detecta URL de listado distinta. Se usa la URL inicial.")

        html_final = html_inicial
        url_origen = url_inicial

    total_items = detectar_total_items(html_final)

    if total_items is not None:
        print(f"  Total de items indicado por la web: {total_items}")

    recursos = extraer_recursos_desde_html(
        html=html_final,
        url_origen=url_origen,
        seccion=nombre_seccion,
    )

    # Eliminamos duplicados dentro de la sección.
    recursos_unicos = []
    urls_vistas = set()

    for recurso in recursos:
        if recurso["url"] not in urls_vistas:
            recursos_unicos.append(recurso)
            urls_vistas.add(recurso["url"])

    print(f"  Recursos únicos extraídos: {len(recursos_unicos)}")

    return recursos_unicos, total_items, url_origen


def crear_dataset(recursos):
    """
    Convierte la lista de recursos en un DataFrame ordenado.
    """

    df = pd.DataFrame(recursos)

    if df.empty:
        return df

    df = df.drop_duplicates(subset=["seccion_origen", "titulo", "url"])
    df = df.reset_index(drop=True)
    df.insert(0, "id", range(1, len(df) + 1))

    return df


def guardar_resultados(df, resumen):
    """
    Guarda el dataset principal y un resumen por sección.
    """

    ruta_csv = "data/processed/documentos_ceei_playwright.csv"
    ruta_excel = "outputs/documentos_ceei_playwright.xlsx"
    ruta_resumen = "outputs/resumen_scraping_playwright.xlsx"

    df.to_csv(ruta_csv, index=False, encoding="utf-8-sig")
    df.to_excel(ruta_excel, index=False)

    df_resumen = pd.DataFrame(resumen)
    df_resumen.to_excel(ruta_resumen, index=False)

    print("\nArchivos generados:")
    print(f"- CSV: {ruta_csv}")
    print(f"- Excel: {ruta_excel}")
    print(f"- Resumen: {ruta_resumen}")


def main():
    """
    Función principal del scraper con Playwright.
    """

    print("Iniciando scraper con Playwright...")

    crear_carpetas_salida()

    todos_los_recursos = []
    resumen = []

    with sync_playwright() as playwright:

        # Abrimos Chromium en modo visible.
        # Si quieres que no se vea el navegador, cambia headless=False por headless=True.
        browser = playwright.chromium.launch(headless=False)

        page = browser.new_page(
            viewport={"width": 1400, "height": 1000},
            locale="es-ES",
        )

        for nombre_seccion, datos in SECCIONES.items():
            url = datos["url"]
            total_esperado = datos["total_esperado_aproximado"]

            try:
                recursos, total_detectado, url_final = rastrear_seccion(
                    page=page,
                    nombre_seccion=nombre_seccion,
                    url_inicial=url,
                )

                todos_los_recursos.extend(recursos)

                resumen.append({
                    "seccion": nombre_seccion,
                    "url_final_usada": url_final,
                    "total_detectado_web": total_detectado,
                    "total_esperado_aproximado": total_esperado,
                    "recursos_extraidos": len(recursos),
                    "estado": "OK",
                    "error": "",
                })

            except Exception as error:
                print(f"ERROR en sección {nombre_seccion}: {error}")

                resumen.append({
                    "seccion": nombre_seccion,
                    "url_final_usada": url,
                    "total_detectado_web": None,
                    "total_esperado_aproximado": total_esperado,
                    "recursos_extraidos": 0,
                    "estado": "ERROR",
                    "error": str(error),
                })

        browser.close()

    df = crear_dataset(todos_los_recursos)

    guardar_resultados(df, resumen)

    print(f"\nNúmero total de recursos extraídos: {len(df)}")

    if not df.empty:
        print("\nResumen por sección:")
        print(df.groupby("seccion_origen").size())

    print("\nProceso finalizado correctamente.")


if __name__ == "__main__":
    main()