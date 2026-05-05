"""
scraper.py

Este script realiza la primera fase del proyecto:
1. Accede a la página pública del CEEI Elche.
2. Extrae enlaces y títulos visibles.
3. Normaliza las URLs.
4. Elimina duplicados.
5. Guarda los resultados en CSV y Excel.

Este archivo forma parte del proyecto:
"Sistema inteligente de recomendación de recursos para emprendedores".
"""

# Importamos requests para descargar páginas web.
import requests

# Importamos BeautifulSoup para analizar el contenido HTML.
from bs4 import BeautifulSoup

# Importamos pandas para trabajar con los datos en forma de tabla.
import pandas as pd

# Importamos urljoin para convertir enlaces relativos en URLs completas.
from urllib.parse import urljoin

# Importamos Path para crear rutas de archivos de forma ordenada.
from pathlib import Path


# URL base del sitio web.
BASE_URL = "https://ceeielche.emprenemjunts.es/"

# URL inicial desde la que se extraerán los recursos.
START_URL = "https://ceeielche.emprenemjunts.es/?op=130&id=107"


def crear_carpetas_salida():
    """
    Crea las carpetas necesarias para guardar los resultados.

    Esto evita errores si las carpetas no existen todavía.
    """

    # Carpeta para los datos procesados.
    Path("data/processed").mkdir(parents=True, exist_ok=True)

    # Carpeta para archivos finales de salida.
    Path("outputs").mkdir(parents=True, exist_ok=True)


def descargar_html(url):
    """
    Descarga el contenido HTML de una página web.

    En algunas páginas, el servidor bloquea peticiones demasiado simples
    realizadas desde scripts. Por eso se incluyen cabeceras HTTP similares
    a las de un navegador real.

    Parámetros:
        url (str): dirección web que se quiere descargar.

    Devuelve:
        str: código HTML de la página.
    """

    # Creamos una sesión HTTP. La sesión permite mantener cierta información
    # entre peticiones, como haría un navegador normal.
    session = requests.Session()

    # Cabeceras más completas para reducir el riesgo de bloqueo HTTP 403.
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
        "Referer": "https://ceeielche.emprenemjunts.es/",
    }

    # Realizamos la petición HTTP con la sesión y las cabeceras anteriores.
    response = session.get(url, headers=headers, timeout=20)

    # Detectamos automáticamente la codificación para conservar tildes y eñes.
    response.encoding = response.apparent_encoding

    # Si la web sigue bloqueando la petición, mostramos un mensaje claro.
    if response.status_code == 403:
        raise Exception(
            "Error 403: la web ha bloqueado la petición automática. "
            "Se debe usar una estrategia alternativa, como guardar el HTML "
            "manualmente desde el navegador o usar Playwright."
        )

    # Si aparece cualquier otro error HTTP, lo indicamos.
    if response.status_code != 200:
        raise Exception(f"Error al acceder a la web. Código HTTP: {response.status_code}")

    # Devolvemos el HTML descargado.
    return response.text


def extraer_enlaces(html):
    """
    Extrae enlaces y textos visibles de una página HTML.

    Parámetros:
        html (str): código HTML de la página.

    Devuelve:
        list: lista de diccionarios con título y URL.
    """

    # Analizamos el HTML con BeautifulSoup.
    soup = BeautifulSoup(html, "lxml")

    # Lista donde guardaremos los recursos encontrados.
    recursos = []

    # Buscamos todas las etiquetas <a>, que representan enlaces.
    enlaces = soup.find_all("a")

    # Recorremos todos los enlaces encontrados.
    for enlace in enlaces:

        # Extraemos el texto visible del enlace.
        titulo = enlace.get_text(strip=True)

        # Extraemos la URL del enlace.
        href = enlace.get("href")

        # Descartamos enlaces vacíos.
        if not titulo or not href:
            continue

        # Convertimos enlaces relativos en URLs completas.
        url_completa = urljoin(BASE_URL, href)

        # Descartamos textos demasiado cortos porque suelen ser menús.
        if len(titulo) < 5:
            continue

        # Guardamos el recurso.
        recursos.append({
            "titulo": titulo,
            "url": url_completa
        })

    return recursos


def crear_dataframe(recursos):
    """
    Convierte la lista de recursos en una tabla de pandas.

    Parámetros:
        recursos (list): lista de diccionarios con título y URL.

    Devuelve:
        pandas.DataFrame: tabla limpia con identificador, título y URL.
    """

    # Convertimos la lista de recursos en DataFrame.
    df = pd.DataFrame(recursos)

    # Eliminamos duplicados.
    df = df.drop_duplicates(subset=["titulo", "url"])

    # Reiniciamos el índice.
    df = df.reset_index(drop=True)

    # Añadimos un identificador numérico.
    df.insert(0, "id", range(1, len(df) + 1))

    return df


def guardar_resultados(df):
    """
    Guarda la tabla resultante en CSV y Excel.

    Parámetros:
        df (pandas.DataFrame): tabla de recursos extraídos.
    """

    # Ruta del archivo CSV.
    ruta_csv = "data/processed/documentos_ceei.csv"

    # Ruta del archivo Excel.
    ruta_excel = "outputs/documentos_ceei.xlsx"

    # Guardamos en CSV con codificación compatible con Excel.
    df.to_csv(ruta_csv, index=False, encoding="utf-8-sig")

    # Guardamos también en formato Excel.
    df.to_excel(ruta_excel, index=False)

    print(f"Archivo CSV guardado en: {ruta_csv}")
    print(f"Archivo Excel guardado en: {ruta_excel}")


def main():
    """
    Función principal del programa.

    Coordina todo el proceso de scraping:
    1. Crear carpetas.
    2. Descargar HTML.
    3. Extraer enlaces.
    4. Crear tabla.
    5. Guardar resultados.
    """

    print("Iniciando scraping de recursos del CEEI Elche...")

    crear_carpetas_salida()

    html = descargar_html(START_URL)

    recursos = extraer_enlaces(html)

    df = crear_dataframe(recursos)

    guardar_resultados(df)

    print(f"Número total de recursos extraídos: {len(df)}")
    print("Proceso finalizado correctamente.")


# Esta condición permite ejecutar el programa solo si se lanza directamente.
if __name__ == "__main__":
    main()