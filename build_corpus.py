"""
build_corpus.py

Este script construye el corpus documental del proyecto.

Objetivo:
- Recorrer la carpeta de documentos descargados.
- Leer archivos PDF y TXT.
- Extraer el texto de cada documento.
- Crear un CSV único con todos los documentos preparados para recomendación.
- Detectar documentos sin texto extraído.
- Crear una columna texto_recomendador para que todos los documentos puedan usarse en el recomendador.

Entrada:
- data/raw/ceei_elche/pdf/

Salida:
- data/processed/corpus_documental.csv
- outputs/corpus_documental.xlsx
"""

import os
import re
from datetime import datetime
import pandas as pd
from pypdf import PdfReader


# ------------------------------------------------------------
# 1. Rutas principales del proyecto
# ------------------------------------------------------------

# Carpeta donde están los PDFs y TXT descargados
CARPETA_DOCUMENTOS = os.path.join("data", "raw", "ceei_elche", "pdf")

# Archivos de salida
OUTPUT_CSV = "data/processed/corpus_documental.csv"
OUTPUT_XLSX = "outputs/corpus_documental.xlsx"
MAX_CARACTERES_EXCEL = 32767


# ------------------------------------------------------------
# 2. Limpieza básica de texto
# ------------------------------------------------------------

CARACTERES_ILEGALES_EXCEL = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")

def limpiar_texto(texto):
    """
    Limpia el texto extraído de los documentos.

    Acciones:
    - Convierte valores nulos en cadena vacía.
    - Elimina saltos de línea.
    - Elimina retornos de carro.
    - Reduce espacios múltiples a un solo espacio.
    """

    if texto is None:
        return ""

    texto = str(texto)
    texto = CARACTERES_ILEGALES_EXCEL.sub(" ", texto)
    texto = texto.replace("\n", " ")
    texto = texto.replace("\r", " ")
    texto = " ".join(texto.split())

    return texto.strip()
def extraer_urls(texto):
    """
    Extrae URLs presentes dentro de un texto.

    Sirve para detectar enlaces originales o referencias web
    que aparezcan dentro de documentos TXT o PDFs.
    """

    if texto is None:
        return []

    patron_url = r"https?://[^\s\)\]\}<>\"']+"
    urls = re.findall(patron_url, texto)

    # Eliminamos posibles duplicados manteniendo el orden
    urls_unicas = list(dict.fromkeys(urls))

    return urls_unicas


def extraer_emails(texto):
    """
    Extrae direcciones de correo electrónico presentes dentro de un texto.
    """

    if texto is None:
        return []

    patron_email = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    emails = re.findall(patron_email, texto)

    emails_unicos = list(dict.fromkeys(emails))

    return emails_unicos


def obtener_url_principal(urls):
    """
    Devuelve la primera URL detectada como URL principal.

    Si no hay URLs, devuelve una cadena vacía.
    """

    if len(urls) == 0:
        return ""

    return urls[0]

# ------------------------------------------------------------
# 3. Extracción de texto desde PDF
# ------------------------------------------------------------

def extraer_texto_pdf(ruta_pdf):
    """
    Extrae texto de un archivo PDF usando pypdf.

    Nota:
    - Si el PDF contiene texto real, pypdf normalmente lo extrae bien.
    - Si el PDF es una imagen escaneada o una infografía, puede devolver texto vacío.
    """

    texto_total = ""

    try:
        reader = PdfReader(ruta_pdf)

        for pagina in reader.pages:
            texto_pagina = pagina.extract_text()

            if texto_pagina:
                texto_total += texto_pagina + " "

    except Exception as e:
        print(f"Error leyendo PDF: {ruta_pdf}")
        print(f"Detalle del error: {e}")

    return limpiar_texto(texto_total)


# ------------------------------------------------------------
# 4. Extracción de texto desde TXT
# ------------------------------------------------------------

def extraer_texto_txt(ruta_txt):
    """
    Lee el contenido de un archivo TXT.

    Primero intenta leer en UTF-8.
    Si falla, intenta leer en latin-1.
    """

    try:
        with open(ruta_txt, "r", encoding="utf-8") as archivo:
            texto = archivo.read()

    except UnicodeDecodeError:
        try:
            with open(ruta_txt, "r", encoding="latin-1") as archivo:
                texto = archivo.read()
        except Exception as e:
            print(f"Error leyendo TXT: {ruta_txt}")
            print(f"Detalle del error: {e}")
            texto = ""

    except Exception as e:
        print(f"Error leyendo TXT: {ruta_txt}")
        print(f"Detalle del error: {e}")
        texto = ""

    return limpiar_texto(texto)


# ------------------------------------------------------------
# 5. Detección de sección documental
# ------------------------------------------------------------

def detectar_seccion(ruta_archivo):
    """
    Detecta la sección del documento a partir de la carpeta donde está guardado.

    Ejemplo:
    data/raw/ceei_elche/pdf/Infografias/documento.pdf

    Sección detectada:
    Infografias
    """

    partes = ruta_archivo.split(os.sep)

    if len(partes) >= 2:
        return partes[-2]

    return "Sin sección"


# ------------------------------------------------------------
# 6. Creación del texto para el recomendador
# ------------------------------------------------------------

def crear_texto_recomendador(titulo, seccion, tipo_archivo, texto, url_principal=""):
    """
    Crea el campo texto_recomendador.

    Combina título, sección, tipo de archivo, URL principal si existe
    y texto extraído.
    """

    partes = [
        titulo,
        seccion,
        tipo_archivo,
        url_principal,
        texto
    ]

    partes_limpias = []

    for parte in partes:
        parte_limpia = limpiar_texto(parte)

        if parte_limpia != "":
            partes_limpias.append(parte_limpia)

    return " | ".join(partes_limpias)



# ------------------------------------------------------------
# 7. Construcción del corpus documental
# ------------------------------------------------------------

def construir_corpus():
    """
    Recorre todos los documentos PDF y TXT de la carpeta principal
    y construye un DataFrame con una fila por documento.
    """

    registros = []

    if not os.path.exists(CARPETA_DOCUMENTOS):
        raise FileNotFoundError(f"No existe la carpeta: {CARPETA_DOCUMENTOS}")

    for raiz, carpetas, archivos in os.walk(CARPETA_DOCUMENTOS):
        for archivo in archivos:

            archivo_lower = archivo.lower()

            # Solo procesamos PDFs y archivos TXT
            if not archivo_lower.endswith((".pdf", ".txt")):
                continue

            ruta_completa = os.path.join(raiz, archivo)
            seccion = detectar_seccion(ruta_completa)

            print(f"Procesando: {ruta_completa}")

            # Extraemos texto según el tipo de archivo
            if archivo_lower.endswith(".pdf"):
                tipo_archivo = "PDF"
                texto = extraer_texto_pdf(ruta_completa)

            elif archivo_lower.endswith(".txt"):
                tipo_archivo = "TXT"
                texto = extraer_texto_txt(ruta_completa)

            else:
                continue

            # Título sin extensión
            titulo = os.path.splitext(archivo)[0]

            # Número de caracteres extraídos
            num_caracteres = len(texto) if texto is not None else 0

            # Estado de extracción del texto
            if num_caracteres == 0:
                estado_extraccion = "Sin texto extraído"
            elif num_caracteres < 100:
                estado_extraccion = "Texto insuficiente"
            else:
                estado_extraccion = "OK"
            urls_detectadas = extraer_urls(texto)
            emails_detectados = extraer_emails(texto)
            url_principal = obtener_url_principal(urls_detectadas)

            texto_recomendador = crear_texto_recomendador(
                titulo=titulo,
                seccion=seccion,
                tipo_archivo=tipo_archivo,
                texto=texto,
                url_principal=url_principal
            )
            registros.append({
                "titulo": titulo,
                "ruta_archivo": ruta_completa,
                "tipo_archivo": tipo_archivo,
                "seccion": seccion,
                "texto": texto,
                "num_caracteres": num_caracteres,
                "estado_extraccion": estado_extraccion,
                "texto_recomendador": texto_recomendador,
                "urls_detectadas": " | ".join(urls_detectadas),
                "url_principal": url_principal,
                "emails_detectados": " | ".join(emails_detectados)
            })

    df = pd.DataFrame(registros)

    if len(df) == 0:
        raise ValueError("No se ha encontrado ningún PDF o TXT para procesar.")

    # Añadimos un ID consecutivo
    df.insert(0, "id", range(1, len(df) + 1))

    return df


def guardar_excel(df, ruta_excel):
    """
    Guarda el Excel principal.

    Si el archivo esta abierto en Excel y Windows lo bloquea, guarda una copia
    con fecha y hora para que el proceso no falle despues de generar el CSV.
    """

    df_excel = preparar_dataframe_excel(df)

    try:
        df_excel.to_excel(ruta_excel, index=False)
        return ruta_excel

    except PermissionError:
        nombre_base, extension = os.path.splitext(ruta_excel)
        marca_tiempo = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta_alternativa = f"{nombre_base}_{marca_tiempo}{extension}"

        print(f"\nAviso: no se pudo sobrescribir {ruta_excel}.")
        print("Puede que el archivo este abierto en Excel.")
        print(f"Guardando copia alternativa: {ruta_alternativa}")

        df_excel.to_excel(ruta_alternativa, index=False)
        return ruta_alternativa


def preparar_dataframe_excel(df):
    """
    Adapta el DataFrame a las limitaciones de Excel.

    El CSV conserva el texto completo. Excel tiene un limite de 32.767
    caracteres por celda, asi que aqui se recortan solo las celdas del XLSX.
    """

    df_excel = df.copy()

    for columna in df_excel.select_dtypes(include=["object", "str"]).columns:
        df_excel[columna] = df_excel[columna].map(recortar_celda_excel)

    return df_excel


def recortar_celda_excel(valor):
    if not isinstance(valor, str):
        return valor

    if len(valor) <= MAX_CARACTERES_EXCEL:
        return valor

    return valor[:MAX_CARACTERES_EXCEL]


# ------------------------------------------------------------
# 8. Función principal
# ------------------------------------------------------------

def main():
    """
    Ejecuta todo el proceso de construcción del corpus.
    """

    print("Construyendo corpus documental...")

    df = construir_corpus()

    # Creamos carpetas de salida si no existen
    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)

    # Guardamos CSV
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    # Guardamos Excel
    excel_generado = guardar_excel(df, OUTPUT_XLSX)

    print("\nCorpus generado correctamente.")
    print(f"Documentos procesados: {len(df)}")
    print(f"CSV generado: {OUTPUT_CSV}")
    print(f"Excel generado: {excel_generado}")

    print("\nResumen por estado de extracción:")
    print(df["estado_extraccion"].value_counts())

    print("\nResumen por sección y tipo de archivo:")
    print(df.groupby(["seccion", "tipo_archivo"]).size())


# ------------------------------------------------------------
# 9. Punto de entrada del script
# ------------------------------------------------------------

if __name__ == "__main__":
    main()
