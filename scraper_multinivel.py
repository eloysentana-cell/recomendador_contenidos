"""
scraper_multinivel.py

Scraper multinivel para extraer recursos documentales del CEEI Elche.

Versión mejorada:
- Parte de las páginas de cada sección: Manuales, Guías, Fichas, etc.
- Busca automáticamente la URL real del listado de documentos.
- Entra en el listado real, normalmente con estructura op=35 y bbtipoagru.
- Extrae las tarjetas/documentos disponibles.
- Detecta enlaces de paginación reales dentro del HTML.
- Respeta límites máximos de páginas por sección.
- Exporta resultados a CSV y Excel.

Este código está comentado para que pueda revisarse en GitHub
como parte de un proyecto académico.
"""

# Librería para realizar peticiones HTTP.
import requests

# BeautifulSoup permite analizar el HTML de las páginas web.
from bs4 import BeautifulSoup

# Pandas permite trabajar con tablas de datos.
import pandas as pd

# Funciones para trabajar con URLs.
from urllib.parse import urljoin, urlparse, parse_qs

# Path permite crear carpetas de forma segura.
from pathlib import Path

# time permite introducir pausas entre peticiones.
import time

# re permite usar expresiones regulares para limpiar textos y detectar patrones.
import re


# Dominio base del portal.
BASE_URL = "https://ceeielche.emprenemjunts.es/"

# Dominio permitido. Evita que el scraper siga enlaces externos.
DOMINIO_PERMITIDO = "ceeielche.emprenemjunts.es"

# Pausa entre peticiones para evitar una descarga agresiva.
PAUSA_SEGUNDOS = 1


# Secciones iniciales facilitadas por el usuario.
# Estas páginas no siempre contienen directamente todos los documentos,
# pero sí suelen enlazar con el listado real de recursos.
SECCIONES = {
    "manuales": {
        "url_seccion": "https://ceeielche.emprenemjunts.es/?op=8&n=1214",
        "limite_paginas": 1,
    },
    "guias": {
        "url_seccion": "https://ceeielche.emprenemjunts.es/?op=8&n=1215",
        "limite_paginas": 20,
    },
    "fichas": {
        "url_seccion": "https://ceeielche.emprenemjunts.es/?op=8&n=1216",
        "limite_paginas": 20,
    },
    "infografias": {
        "url_seccion": "https://ceeielche.emprenemjunts.es/?op=8&n=1217",
        "limite_paginas": 1,
    },
    "informes": {
        "url_seccion": "https://ceeielche.emprenemjunts.es/?op=8&n=1218",
        "limite_paginas": 1,
    },
    "videocapsulas": {
        "url_seccion": "https://ceeielche.emprenemjunts.es/?op=8&n=1219",
        "limite_paginas": 1,
    },
    "modelos_de_negocio": {
        "url_seccion": "https://ceeielche.emprenemjunts.es/?op=8&n=1220",
        "limite_paginas": 20,
    },
    "cuadernos_de_trabajo": {
        "url_seccion": "https://ceeielche.emprenemjunts.es/?op=8&n=1221",
        "limite_paginas": 1,
    },
    "webinars": {
        "url_seccion": "https://ceeielche.emprenemjunts.es/?op=8&n=1222",
        "limite_paginas": 1,
    },
}


def crear_carpetas_salida():
    """
    Crea las carpetas donde se guardarán los resultados.
    """

    Path("data/processed").mkdir(parents=True, exist_ok=True)
    Path("outputs").mkdir(parents=True, exist_ok=True)


def crear_sesion():
    """
    Crea una sesión HTTP con cabeceras similares a las de un navegador real.

    Esto es importante porque algunas webs bloquean peticiones demasiado simples.
    """

    session = requests.Session()

    session.headers.update({
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
        "Referer": BASE_URL,
    })

    return session


def descargar_html(session, url):
    """
    Descarga el HTML de una URL.

    Parámetros:
        session: sesión HTTP configurada.
        url: dirección web a descargar.

    Devuelve:
        HTML de la página.
    """

    response = session.get(url, timeout=20)
    response.encoding = response.apparent_encoding

    if response.status_code != 200:
        raise Exception(f"Código HTTP {response.status_code}")

    return response.text


def normalizar_texto(texto):
    """
    Limpia un texto eliminando saltos de línea, tabulaciones y espacios duplicados.
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
    Limpia un texto y lo convierte a minúsculas.
    """

    return normalizar_texto(texto).lower()


def es_url_interna(url):
    """
    Comprueba si una URL pertenece al dominio del CEEI Elche.
    """

    dominio = urlparse(url).netloc
    return DOMINIO_PERMITIDO in dominio


def extraer_enlaces(html, url_origen):
    """
    Extrae todos los enlaces internos de una página.

    Devuelve una lista de diccionarios con:
    - texto visible del enlace
    - URL completa
    """

    soup = BeautifulSoup(html, "lxml")
    enlaces = []

    for etiqueta_a in soup.find_all("a"):
        texto = normalizar_texto(etiqueta_a.get_text(" ", strip=True))
        href = etiqueta_a.get("href")

        if not href:
            continue

        url_completa = urljoin(url_origen, href)

        if not es_url_interna(url_completa):
            continue

        enlaces.append({
            "texto": texto,
            "url": url_completa,
        })

    return enlaces


def obtener_parametro_url(url, nombre_parametro):
    """
    Obtiene el valor de un parámetro de una URL.

    Por ejemplo, en:
    https://web.com/?op=35&bbtipoagru=657

    obtener_parametro_url(url, "bbtipoagru") devolvería "657".
    """

    partes = urlparse(url)
    parametros = parse_qs(partes.query)

    valores = parametros.get(nombre_parametro, [])

    if not valores:
        return ""

    return valores[0]


def localizar_url_listado(html, url_seccion):
    """
    Localiza la URL real del listado de documentos dentro de una página de sección.

    En la web observada, el listado real suele tener:
    - op=35
    - bbtipoagru=...

    Si no encuentra una URL de listado, devuelve la URL original de la sección.
    """

    enlaces = extraer_enlaces(html, url_seccion)

    candidatos = []

    for enlace in enlaces:
        url = enlace["url"]
        url_minusculas = normalizar_minusculas(url)

        # La URL real del listado suele contener op=35 y bbtipoagru.
        if "op=35" in url_minusculas and "bbtipoagru=" in url_minusculas:
            candidatos.append(url)

    # Si encontramos varios candidatos, usamos el primero.
    if candidatos:
        return candidatos[0]

    # Si no se encuentra listado específico, se usa la página de sección.
    return url_seccion


def detectar_total_items(html):
    """
    Intenta detectar el número total de ítems indicado por la página.

    En la captura aparece algo como:
    '73 items'

    Esta función busca ese patrón en el texto de la página.
    """

    soup = BeautifulSoup(html, "lxml")
    texto_pagina = soup.get_text(" ", strip=True)

    coincidencia = re.search(r"(\d+)\s+items", texto_pagina, re.IGNORECASE)

    if coincidencia:
        return int(coincidencia.group(1))

    return None


def es_enlace_de_listado(url):
    """
    Determina si una URL es una página de listado y no un documento final.
    """

    url_norm = normalizar_minusculas(url)

    if "op=35" in url_norm and "bbtipoagru=" in url_norm:
        return True

    return False


def parece_recurso_documental(texto, url):
    """
    Decide si un enlace parece un recurso documental útil.

    Se descartan enlaces de menú, navegación, acceso, redes sociales y legales.
    """

    texto_norm = normalizar_minusculas(texto)
    url_norm = normalizar_minusculas(url)

    if len(texto_norm) < 5:
        return False

    # Excluimos páginas de listado porque no son documentos finales.
    if es_enlace_de_listado(url):
        return False

    palabras_descartadas = [
        "inicio",
        "actualidad",
        "agenda",
        "convocatorias",
        "recursos",
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
        "mapa web",
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
        "emprenemjunts",
        "newsletter",
        "buscar",
        "ver el listado",
        "ver el listado ordenado",
        "listado ordenado",
    ]

    if any(palabra in texto_norm for palabra in palabras_descartadas):
        return False

    # Muchos documentos finales del portal son URLs internas con op=8 y n=...
    if "op=8" in url_norm and "n=" in url_norm:
        return True

    # También admitimos enlaces con id si contienen texto suficientemente descriptivo.
    if "op=" in url_norm and "id=" in url_norm:
        return True

    return False


def extraer_recursos_de_listado(html, url_listado, seccion, numero_pagina):
    """
    Extrae recursos documentales desde una página de listado.

    Cada recurso tendrá:
    - sección de origen
    - página del listado
    - título
    - URL del documento
    """

    enlaces = extraer_enlaces(html, url_listado)
    recursos = []

    for enlace in enlaces:
        texto = enlace["texto"]
        url = enlace["url"]

        if not parece_recurso_documental(texto, url):
            continue

        recursos.append({
            "seccion_origen": seccion,
            "pagina_numero": numero_pagina,
            "pagina_origen": url_listado,
            "titulo": texto,
            "url": url,
        })

    return recursos


def detectar_enlaces_paginacion(html, url_actual, url_listado_base):
    """
    Detecta enlaces de paginación reales dentro del HTML.

    En vez de inventar parámetros como pag=2, esta función busca enlaces
    internos que mantengan op=35 y bbtipoagru, porque probablemente son
    páginas del mismo listado.
    """

    enlaces = extraer_enlaces(html, url_actual)

    bbtipoagru_base = obtener_parametro_url(url_listado_base, "bbtipoagru")

    enlaces_paginacion = []

    for enlace in enlaces:
        url = enlace["url"]
        texto = normalizar_minusculas(enlace["texto"])

        if not es_enlace_de_listado(url):
            continue

        bbtipoagru_url = obtener_parametro_url(url, "bbtipoagru")

        # Solo aceptamos paginación de la misma categoría.
        if bbtipoagru_base and bbtipoagru_url != bbtipoagru_base:
            continue

        # Evitamos añadir la misma URL actual.
        if url == url_actual:
            continue

        # Criterios frecuentes de paginación.
        texto_es_paginacion = (
            texto.isdigit()
            or "siguiente" in texto
            or "anterior" in texto
            or ">" in texto
            or "»" in texto
        )

        # También aceptamos la URL si contiene parámetros frecuentes de desplazamiento.
        url_norm = normalizar_minusculas(url)

        url_parece_paginacion = (
            "pag=" in url_norm
            or "p=" in url_norm
            or "pagina=" in url_norm
            or "pagactual=" in url_norm
            or "offset=" in url_norm
            or "inicio=" in url_norm
        )

        if texto_es_paginacion or url_parece_paginacion:
            enlaces_paginacion.append(url)

    # Eliminamos duplicados manteniendo el orden.
    enlaces_unicos = []

    for url in enlaces_paginacion:
        if url not in enlaces_unicos:
            enlaces_unicos.append(url)

    return enlaces_unicos


def rastrear_seccion(session, nombre_seccion, url_seccion, limite_paginas):
    """
    Rastrea una sección completa:
    1. Accede a la URL de sección.
    2. Localiza el listado real.
    3. Extrae recursos.
    4. Sigue enlaces de paginación reales hasta el límite establecido.
    """

    print(f"\nRastreando sección: {nombre_seccion}")
    print(f"URL de sección: {url_seccion}")
    print(f"Límite de páginas: {limite_paginas}")

    recursos_seccion = []
    urls_documentos_vistas = set()
    urls_paginas_visitadas = set()

    # Paso 1: descargar la página de sección.
    html_seccion = descargar_html(session, url_seccion)

    # Paso 2: localizar el listado real.
    url_listado = localizar_url_listado(html_seccion, url_seccion)

    print(f"URL de listado detectada: {url_listado}")

    # Cola de páginas pendientes de procesar.
    paginas_pendientes = [url_listado]

    numero_pagina_procesada = 0

    while paginas_pendientes and numero_pagina_procesada < limite_paginas:
        url_pagina = paginas_pendientes.pop(0)

        if url_pagina in urls_paginas_visitadas:
            continue

        urls_paginas_visitadas.add(url_pagina)
        numero_pagina_procesada += 1

        print(f"  Procesando página {numero_pagina_procesada}: {url_pagina}")

        html_pagina = descargar_html(session, url_pagina)

        total_items_detectado = detectar_total_items(html_pagina)

        if total_items_detectado is not None:
            print(f"    Total de items indicado por la web: {total_items_detectado}")

        recursos_pagina = extraer_recursos_de_listado(
            html=html_pagina,
            url_listado=url_pagina,
            seccion=nombre_seccion,
            numero_pagina=numero_pagina_procesada,
        )

        recursos_nuevos = []

        for recurso in recursos_pagina:
            if recurso["url"] not in urls_documentos_vistas:
                urls_documentos_vistas.add(recurso["url"])
                recursos_nuevos.append(recurso)

        print(f"    Recursos nuevos extraídos: {len(recursos_nuevos)}")

        recursos_seccion.extend(recursos_nuevos)

        # Paso 4: detectar enlaces reales de paginación.
        enlaces_paginacion = detectar_enlaces_paginacion(
            html=html_pagina,
            url_actual=url_pagina,
            url_listado_base=url_listado,
        )

        for url_paginacion in enlaces_paginacion:
            if (
                url_paginacion not in urls_paginas_visitadas
                and url_paginacion not in paginas_pendientes
            ):
                paginas_pendientes.append(url_paginacion)

        print(f"    Páginas pendientes detectadas: {len(paginas_pendientes)}")

        time.sleep(PAUSA_SEGUNDOS)

    print(f"  Total extraído en sección {nombre_seccion}: {len(recursos_seccion)}")

    return recursos_seccion


def crear_dataset(recursos):
    """
    Convierte la lista de recursos en un DataFrame limpio.
    """

    df = pd.DataFrame(recursos)

    if df.empty:
        return df

    df = df.drop_duplicates(subset=["seccion_origen", "titulo", "url"])
    df = df.reset_index(drop=True)
    df.insert(0, "id", range(1, len(df) + 1))

    return df


def guardar_resultados(df):
    """
    Guarda el dataset en CSV y Excel.

    Si el Excel está abierto, Windows puede impedir sobrescribirlo.
    Por eso conviene cerrar el archivo antes de ejecutar el scraper.
    """

    ruta_csv = "data/processed/documentos_ceei_multinivel.csv"
    ruta_excel = "outputs/documentos_ceei_multinivel.xlsx"

    df.to_csv(ruta_csv, index=False, encoding="utf-8-sig")
    df.to_excel(ruta_excel, index=False)

    print("\nArchivos generados:")
    print(f"- CSV: {ruta_csv}")
    print(f"- Excel: {ruta_excel}")


def main():
    """
    Función principal del scraper multinivel.
    """

    print("Iniciando scraper multinivel mejorado del CEEI Elche...")

    crear_carpetas_salida()

    session = crear_sesion()

    todos_los_recursos = []

    for nombre_seccion, datos in SECCIONES.items():
        url_seccion = datos["url_seccion"]
        limite_paginas = datos["limite_paginas"]

        try:
            recursos = rastrear_seccion(
                session=session,
                nombre_seccion=nombre_seccion,
                url_seccion=url_seccion,
                limite_paginas=limite_paginas,
            )

            todos_los_recursos.extend(recursos)

        except Exception as error:
            print(f"ERROR en sección {nombre_seccion}: {error}")

    df = crear_dataset(todos_los_recursos)

    guardar_resultados(df)

    print(f"\nNúmero total de recursos extraídos: {len(df)}")

    if not df.empty:
        print("\nResumen por sección:")
        print(df.groupby("seccion_origen").size())

    print("\nProceso finalizado correctamente.")


if __name__ == "__main__":
    main()