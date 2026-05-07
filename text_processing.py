"""
text_processing.py

Este script forma parte del Día 2 del proyecto TFM / práctica de IA.

Objetivo:
- Leer el dataset generado por el scraper multinivel.
- Limpiar recursos duplicados o poco útiles.
- Eliminar enlaces de navegación.
- Clasificar cada recurso por tipo documental.
- Estimar una categoría temática.
- Crear una columna de texto preparada para el sistema de recomendación.
- Guardar el resultado limpio en CSV y Excel.

Dataset de entrada:
- data/processed/documentos_ceei_multinivel.csv

Datasets de salida:
- data/processed/documentos_ceei_limpio.csv
- outputs/documentos_ceei_limpio.xlsx
"""

import os
import re
import pandas as pd


# ------------------------------------------------------------
# 1. Definición de rutas del proyecto
# ------------------------------------------------------------

INPUT_CSV = "data/processed/documentos_ceei_multinivel.csv"

OUTPUT_CSV = "data/processed/documentos_ceei_limpio.csv"
OUTPUT_XLSX = "outputs/documentos_ceei_limpio.xlsx"


# ------------------------------------------------------------
# 2. Funciones auxiliares de limpieza de texto
# ------------------------------------------------------------

def limpiar_texto(texto):
    """
    Limpia un texto básico:
    - Convierte valores vacíos en cadena vacía.
    - Elimina espacios repetidos.
    - Elimina saltos de línea innecesarios.
    """

    if pd.isna(texto):
        return ""

    texto = str(texto)
    texto = texto.replace("\n", " ")
    texto = texto.replace("\r", " ")
    texto = re.sub(r"\s+", " ", texto)
    texto = texto.strip()

    return texto


def normalizar_url(url):
    """
    Normaliza una URL:
    - Convierte valores nulos en cadena vacía.
    - Elimina espacios.
    - Elimina barras finales innecesarias.
    """

    if pd.isna(url):
        return ""

    url = str(url).strip()
    url = url.rstrip("/")

    return url


# ------------------------------------------------------------
# 3. Eliminación de enlaces de navegación
# ------------------------------------------------------------

def es_enlace_navegacion(titulo, url):
    """
    Detecta si una fila parece un enlace de navegación y no un recurso documental.

    Algunos ejemplos de ruido detectado en el dataset:
    - CEEI Elche MENÚ
    - Qué es el CEEI
    - Qué ofrecemos
    - A quién nos dirigimos
    - Ley de Transparencia
    - Contacta con nosotros
    - Páginas de usuario o autor
    """

    titulo_limpio = limpiar_texto(titulo).lower()
    url_limpia = normalizar_url(url).lower()

    # Títulos claramente institucionales o de navegación
    titulos_ruido = [
        "ceei elche menú",
        "qué es el ceei",
        "que es el ceei",
        "qué ofrecemos",
        "que ofrecemos",
        "a quién nos dirigimos",
        "a quien nos dirigimos",
        "ley de transparencia",
        "contacta con nosotros",
        "contacto",
        "mapa web",
        "aviso legal",
        "política de privacidad",
        "politica de privacidad",
        "política de cookies",
        "politica de cookies",
    ]

    if titulo_limpio in titulos_ruido:
        return True

    # Títulos demasiado cortos suelen ser nombres de usuario, autores o elementos de menú
    if len(titulo_limpio) <= 3:
        return True

    # Páginas de usuarios/autores de la plataforma
    if "op=52" in url_limpia:
        return True

    # Páginas institucionales concretas del CEEI, no recursos documentales
    if "op=130&id=249" in url_limpia:
        return True

    if "op=130&id=250" in url_limpia:
        return True

    if "op=130&id=251" in url_limpia:
        return True

    if "op=130&id=253" in url_limpia:
        return True

    if "op=130&id=254" in url_limpia:
        return True

    return False


# ------------------------------------------------------------
# 4. Clasificación por tipo documental
# ------------------------------------------------------------

def clasificar_tipo_documento(seccion_origen, titulo):
    """
    Clasifica el tipo de documento usando principalmente la sección de origen.

    Esta clasificación es útil porque el scraping se hizo desde secciones como:
    - manuales
    - guías
    - fichas
    - infografías
    - informes
    - videocápsulas
    - modelos de negocio
    - cuadernos de trabajo
    - webinars
    """

    seccion = limpiar_texto(seccion_origen).lower()
    titulo_limpio = limpiar_texto(titulo).lower()

    if "manual" in seccion:
        return "Manual"

    if "guía" in seccion or "guia" in seccion:
        return "Guía"

    if "ficha" in seccion:
        return "Ficha"

    if "infografía" in seccion or "infografia" in seccion:
        return "Infografía"

    if "informe" in seccion:
        return "Informe"

    if "video" in seccion or "videocápsula" in seccion or "videocapsula" in seccion:
        return "Videocápsula"

    if "modelo" in seccion and "negocio" in seccion:
        return "Modelo de negocio"

    if "cuaderno" in seccion:
        return "Cuaderno de trabajo"

    if "webinar" in seccion:
        return "Webinar"

    # Regla secundaria basada en el título
    if "webinar" in titulo_limpio:
        return "Webinar"

    if "guía" in titulo_limpio or "guia" in titulo_limpio:
        return "Guía"

    if "manual" in titulo_limpio:
        return "Manual"

    if "informe" in titulo_limpio:
        return "Informe"

    return "Otro"


# ------------------------------------------------------------
# 5. Estimación de categoría temática
# ------------------------------------------------------------

def estimar_categoria(titulo):
    """
    Estima la categoría temática del recurso a partir de palabras clave.

    Esta categoría no es perfecta, pero sirve como primera aproximación
    para un sistema de recomendación documental.
    """

    titulo_limpio = limpiar_texto(titulo).lower()

    categorias = {
        "Financiación": [
            "financiación",
            "financiacion",
            "ayuda",
            "ayudas",
            "subvención",
            "subvencion",
            "fondos",
            "inversión",
            "inversion",
            "capital",
            "préstamo",
            "prestamo",
        ],
        "Emprendimiento": [
            "emprendimiento",
            "emprendedor",
            "emprendedora",
            "startup",
            "empresa",
            "negocio",
            "crear una empresa",
            "idea de negocio",
        ],
        "Modelo de negocio": [
            "modelo de negocio",
            "canvas",
            "propuesta de valor",
            "clientes",
            "segmentos",
            "canales",
        ],
        "Marketing y ventas": [
            "marketing",
            "ventas",
            "comercial",
            "cliente",
            "clientes",
            "marca",
            "redes sociales",
            "publicidad",
        ],
        "Innovación": [
            "innovación",
            "innovacion",
            "i+d",
            "tecnología",
            "tecnologia",
            "digitalización",
            "digitalizacion",
            "transformación digital",
            "transformacion digital",
        ],
        "Internacionalización": [
            "internacionalización",
            "internacionalizacion",
            "exportación",
            "exportacion",
            "mercado exterior",
            "comercio exterior",
        ],
        "Fiscalidad y legal": [
            "fiscal",
            "impuesto",
            "iva",
            "legal",
            "jurídico",
            "juridico",
            "contrato",
            "normativa",
        ],
        "Gestión empresarial": [
            "gestión",
            "gestion",
            "organización",
            "organizacion",
            "plan de empresa",
            "estrategia",
            "productividad",
            "recursos humanos",
        ],
    }

    for categoria, palabras_clave in categorias.items():
        for palabra in palabras_clave:
            if palabra in titulo_limpio:
                return categoria

    return "General"


# ------------------------------------------------------------
# 6. Creación del texto para el recomendador
# ------------------------------------------------------------

def crear_texto_recomendador(row):
    """
    Crea un texto combinado para utilizarlo después en el recomendador.

    Este campo será útil para:
    - vectorización TF-IDF,
    - embeddings,
    - búsqueda semántica,
    - recomendación documental.
    """

    partes = [
        row.get("titulo", ""),
        row.get("seccion_origen", ""),
        row.get("tipo_documento", ""),
        row.get("categoria_estimada", ""),
    ]

    partes_limpias = [limpiar_texto(parte) for parte in partes if limpiar_texto(parte) != ""]

    return " | ".join(partes_limpias)


# ------------------------------------------------------------
# 7. Proceso principal
# ------------------------------------------------------------

def main():
    """
    Ejecuta todo el proceso de limpieza y clasificación.
    """

    print("Iniciando limpieza del dataset...")

    # Comprobamos que existe el archivo de entrada
    if not os.path.exists(INPUT_CSV):
        raise FileNotFoundError(f"No se ha encontrado el archivo de entrada: {INPUT_CSV}")

    # Leemos el CSV generado por el scraper multinivel
    df = pd.read_csv(INPUT_CSV)

    print(f"Filas iniciales: {len(df)}")

    # Limpiamos campos básicos
    df["seccion_origen"] = df["seccion_origen"].apply(limpiar_texto)
    df["titulo"] = df["titulo"].apply(limpiar_texto)
    df["url"] = df["url"].apply(normalizar_url)

    # Eliminamos filas sin título o sin URL
    df = df[df["titulo"] != ""]
    df = df[df["url"] != ""]

    print(f"Filas tras eliminar registros vacíos: {len(df)}")

    # Eliminamos enlaces de navegación
    df["es_ruido"] = df.apply(
        lambda row: es_enlace_navegacion(row["titulo"], row["url"]),
        axis=1
    )

    df = df[df["es_ruido"] == False].copy()

    print(f"Filas tras eliminar enlaces de navegación: {len(df)}")

    # Eliminamos duplicados por URL
    df = df.drop_duplicates(subset=["url"], keep="first").copy()

    print(f"Filas tras eliminar duplicados por URL: {len(df)}")

    # Clasificamos por tipo documental
    df["tipo_documento"] = df.apply(
        lambda row: clasificar_tipo_documento(row["seccion_origen"], row["titulo"]),
        axis=1
    )

    # Estimamos categoría temática
    df["categoria_estimada"] = df["titulo"].apply(estimar_categoria)

    # Creamos texto para el recomendador
    df["texto_recomendador"] = df.apply(crear_texto_recomendador, axis=1)

    # Reordenamos columnas
    columnas_finales = [
        "id",
        "seccion_origen",
        "titulo",
        "url",
        "tipo_documento",
        "categoria_estimada",
        "texto_recomendador",
    ]

    df = df[columnas_finales].copy()

    # Regeneramos el ID para que sea consecutivo después de limpiar
    df["id"] = range(1, len(df) + 1)

    # Creamos las carpetas de salida si no existen
    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)

    # Guardamos CSV limpio
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    # Guardamos Excel limpio
    df.to_excel(OUTPUT_XLSX, index=False)

    print("Limpieza completada correctamente.")
    print(f"Archivo CSV generado: {OUTPUT_CSV}")
    print(f"Archivo Excel generado: {OUTPUT_XLSX}")
    print(f"Filas finales del dataset limpio: {len(df)}")


# ------------------------------------------------------------
# 8. Punto de entrada del script
# ------------------------------------------------------------

if __name__ == "__main__":
    main()