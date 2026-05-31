"""
recommend_tfidf.py

Primera version funcional del recomendador content-based del proyecto.

Objetivo:
- Leer el corpus documental ya procesado.
- Leer los perfiles emprendedores semanticos.
- Representar perfiles y documentos con TF-IDF.
- Calcular similitud coseno entre perfiles y documentos.
- Generar un ranking de documentos recomendados por perfil.

Entrada:
- data/processed/corpus_documental.csv
- data/perfiles/perfiles_emprendedores.json

Salida:
- outputs/recomendaciones_tfidf.csv
- outputs/recomendaciones_tfidf.xlsx
"""

import json
import os

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


RUTA_CORPUS = "data/processed/corpus_documental.csv"
RUTA_PERFILES = "data/perfiles/perfiles_emprendedores.json"
OUTPUT_CSV = "outputs/recomendaciones_tfidf.csv"
OUTPUT_XLSX = "outputs/recomendaciones_tfidf.xlsx"
TOP_N = 10


COLUMNAS_CORPUS_REQUERIDAS = [
    "id",
    "titulo",
    "ruta_archivo",
    "tipo_archivo",
    "seccion",
    "texto_recomendador",
]

COLUMNAS_PERFIL_REQUERIDAS = [
    "id",
    "nombre",
    "fase_emprendedora",
    "perfil_funcional",
    "descripcion_embedding",
]


def limpiar_texto(valor):
    """
    Convierte valores nulos en texto vacio y normaliza espacios.
    """

    if valor is None:
        return ""

    if pd.isna(valor):
        return ""

    return " ".join(str(valor).split()).strip()


def validar_columnas(df, columnas_requeridas, nombre_fuente):
    """
    Comprueba que una tabla contiene las columnas necesarias.
    """

    columnas_faltantes = [
        columna for columna in columnas_requeridas if columna not in df.columns
    ]

    if columnas_faltantes:
        columnas = ", ".join(columnas_faltantes)
        raise ValueError(f"Faltan columnas en {nombre_fuente}: {columnas}")


def cargar_corpus(ruta_corpus):
    """
    Carga el corpus documental y conserva solo documentos con texto util.
    """

    if not os.path.exists(ruta_corpus):
        raise FileNotFoundError(f"No existe el corpus documental: {ruta_corpus}")

    df = pd.read_csv(ruta_corpus)
    validar_columnas(df, COLUMNAS_CORPUS_REQUERIDAS, ruta_corpus)

    df = df.copy()
    df["texto_recomendador"] = df["texto_recomendador"].map(limpiar_texto)

    documentos_sin_texto = df["texto_recomendador"] == ""
    if documentos_sin_texto.any():
        total_sin_texto = int(documentos_sin_texto.sum())
        print(f"Aviso: se excluyen {total_sin_texto} documentos sin texto_recomendador.")
        df = df.loc[~documentos_sin_texto].copy()

    if len(df) == 0:
        raise ValueError("No hay documentos con texto_recomendador para recomendar.")

    return df


def cargar_perfiles(ruta_perfiles):
    """
    Carga los perfiles emprendedores desde JSON.
    """

    if not os.path.exists(ruta_perfiles):
        raise FileNotFoundError(f"No existe el archivo de perfiles: {ruta_perfiles}")

    with open(ruta_perfiles, "r", encoding="utf-8") as archivo:
        perfiles = json.load(archivo)

    if not isinstance(perfiles, list):
        raise ValueError("El archivo de perfiles debe contener una lista de perfiles.")

    df = pd.DataFrame(perfiles)
    validar_columnas(df, COLUMNAS_PERFIL_REQUERIDAS, ruta_perfiles)

    df = df.copy()
    df["descripcion_embedding"] = df["descripcion_embedding"].map(limpiar_texto)

    perfiles_sin_texto = df["descripcion_embedding"] == ""
    if perfiles_sin_texto.any():
        total_sin_texto = int(perfiles_sin_texto.sum())
        print(f"Aviso: se excluyen {total_sin_texto} perfiles sin descripcion_embedding.")
        df = df.loc[~perfiles_sin_texto].copy()

    if len(df) == 0:
        raise ValueError("No hay perfiles con descripcion_embedding para recomendar.")

    return df


def calcular_recomendaciones(df_corpus, df_perfiles, top_n):
    """
    Calcula el ranking de documentos mas similares para cada perfil.
    """

    textos_documentos = df_corpus["texto_recomendador"].tolist()
    textos_perfiles = df_perfiles["descripcion_embedding"].tolist()

    vectorizador = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        stop_words=None,
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.95,
    )

    matriz_documentos = vectorizador.fit_transform(textos_documentos)
    matriz_perfiles = vectorizador.transform(textos_perfiles)
    matriz_similitud = cosine_similarity(matriz_perfiles, matriz_documentos)

    registros = []

    for indice_perfil, perfil in df_perfiles.reset_index(drop=True).iterrows():
        similitudes = matriz_similitud[indice_perfil]
        indices_ordenados = similitudes.argsort()[::-1][:top_n]

        for posicion, indice_documento in enumerate(indices_ordenados, start=1):
            documento = df_corpus.iloc[indice_documento]
            score = float(similitudes[indice_documento])

            registros.append(
                {
                    "id_perfil": perfil["id"],
                    "nombre_perfil": perfil["nombre"],
                    "fase_emprendedora": perfil["fase_emprendedora"],
                    "ranking": posicion,
                    "score_tfidf_coseno": round(score, 6),
                    "id_documento": documento["id"],
                    "titulo_documento": documento["titulo"],
                    "seccion_documento": documento["seccion"],
                    "tipo_archivo": documento["tipo_archivo"],
                    "ruta_archivo": documento["ruta_archivo"],
                }
            )

    return pd.DataFrame(registros)


def guardar_recomendaciones(df_recomendaciones):
    """
    Guarda las recomendaciones en CSV y Excel.
    """

    os.makedirs("outputs", exist_ok=True)
    df_recomendaciones.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    df_recomendaciones.to_excel(OUTPUT_XLSX, index=False)


def main():
    """
    Ejecuta el pipeline completo de recomendacion TF-IDF.
    """

    print("Cargando corpus documental...")
    df_corpus = cargar_corpus(RUTA_CORPUS)
    print(f"Documentos disponibles: {len(df_corpus)}")

    print("\nCargando perfiles emprendedores...")
    df_perfiles = cargar_perfiles(RUTA_PERFILES)
    print(f"Perfiles disponibles: {len(df_perfiles)}")

    print("\nCalculando recomendaciones TF-IDF...")
    df_recomendaciones = calcular_recomendaciones(df_corpus, df_perfiles, TOP_N)

    guardar_recomendaciones(df_recomendaciones)

    print("\nRecomendaciones generadas correctamente.")
    print(f"Total recomendaciones: {len(df_recomendaciones)}")
    print(f"CSV generado: {OUTPUT_CSV}")
    print(f"Excel generado: {OUTPUT_XLSX}")

    print("\nVista previa:")
    columnas_preview = [
        "nombre_perfil",
        "ranking",
        "score_tfidf_coseno",
        "titulo_documento",
        "seccion_documento",
    ]
    print(df_recomendaciones[columnas_preview].head(20).to_string(index=False))


if __name__ == "__main__":
    main()
