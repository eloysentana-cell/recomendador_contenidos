"""
Genera embeddings locales de documentos a partir del corpus consolidado.

Entrada:
- data/processed/corpus_recomendador.csv

Salidas:
- data/embeddings/document_embeddings.csv
- data/embeddings/document_embeddings.parquet
- outputs/informe_document_embeddings.txt
- outputs/document_embeddings_resumen_por_fuente.csv
- outputs/document_embeddings_resumen_por_fuente.xlsx
- outputs/document_embeddings_muestra.csv
- outputs/document_embeddings_muestra.xlsx

No usa OpenAI ni APIs externas. Usa Sentence Transformers en local.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parent

INPUT_CORPUS = PROJECT_ROOT / "data" / "processed" / "corpus_recomendador.csv"

EMBEDDINGS_DIR = PROJECT_ROOT / "data" / "embeddings"
OUTPUT_CSV = EMBEDDINGS_DIR / "document_embeddings.csv"
OUTPUT_PARQUET = EMBEDDINGS_DIR / "document_embeddings.parquet"

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
OUTPUT_REPORT = OUTPUTS_DIR / "informe_document_embeddings.txt"
OUTPUT_SUMMARY_CSV = OUTPUTS_DIR / "document_embeddings_resumen_por_fuente.csv"
OUTPUT_SUMMARY_XLSX = OUTPUTS_DIR / "document_embeddings_resumen_por_fuente.xlsx"
OUTPUT_SAMPLE_CSV = OUTPUTS_DIR / "document_embeddings_muestra.csv"
OUTPUT_SAMPLE_XLSX = OUTPUTS_DIR / "document_embeddings_muestra.xlsx"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

MAX_TEXT_CHARS = 5000
SAMPLE_TEXT_CHARS = 500
BATCH_SIZE = 32
MIN_CHARS = 300

BASE_COLUMNS = [
    "id_documento",
    "titulo",
    "fuente",
    "seccion",
    "tipo_archivo",
    "ruta_local",
    "url_origen",
    "texto",
    "num_caracteres",
    "estado_extraccion",
    "texto_recomendador",
]


def safe_str(value: Any) -> str:
    """Convierte valores nulos o no textuales en cadenas limpias."""
    if pd.isna(value):
        return ""
    return str(value).strip()


def ensure_output_dirs() -> None:
    """Crea las carpetas de salida necesarias."""
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


def load_corpus(path: Path) -> pd.DataFrame:
    """Carga el corpus consolidado y comprueba que exista y tenga filas."""
    if not path.exists():
        raise FileNotFoundError(f"No existe el corpus: {path}")

    if path.stat().st_size == 0:
        raise ValueError(f"El corpus existe pero esta vacio: {path}")

    df = pd.read_csv(path)

    if df.empty:
        raise ValueError(f"El corpus no contiene filas: {path}")

    return df


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Asegura columnas minimas y adapta nombres alternativos sin romper."""
    df = df.copy()

    if "id_documento" not in df.columns:
        if "id" in df.columns:
            df["id_documento"] = df["id"].apply(
                lambda x: f"doc_{int(x):06d}" if str(x).isdigit() else safe_str(x)
            )
        else:
            df["id_documento"] = [f"doc_{i:06d}" for i in range(1, len(df) + 1)]

    if "ruta_local" not in df.columns:
        df["ruta_local"] = df["ruta_archivo"] if "ruta_archivo" in df.columns else ""

    for column in ["titulo", "fuente", "seccion", "tipo_archivo", "url_origen", "estado_extraccion"]:
        if column not in df.columns:
            df[column] = ""

    if "texto" not in df.columns:
        df["texto"] = ""

    if "texto_recomendador" not in df.columns:
        df["texto_recomendador"] = df["texto"]

    if "num_caracteres" not in df.columns:
        df["num_caracteres"] = df["texto"].fillna("").astype(str).str.len()

    df["num_caracteres"] = pd.to_numeric(df["num_caracteres"], errors="coerce").fillna(0).astype(int)

    return df


def infer_source(row: pd.Series) -> str:
    """Infiere la fuente cuando no esta informada."""
    fuente = safe_str(row.get("fuente", ""))
    if fuente:
        return fuente

    ruta = safe_str(row.get("ruta_local", "")).lower()
    if "ceei_elche" in ruta or "documentos_ceei_elche" in ruta:
        return "CEEI Elche"
    if "ceei_valencia" in ruta or "documentos_ceei_valencia" in ruta:
        return "CEEI Valencia"
    return "Desconocida"


def build_text_embedding(row: pd.Series) -> str:
    """Construye el texto que se enviara al modelo local."""
    texto_base = safe_str(row.get("texto_recomendador", ""))
    if not texto_base:
        texto_base = safe_str(row.get("texto", ""))

    parts = [
        safe_str(row.get("titulo", "")),
        safe_str(row.get("fuente", "")),
        safe_str(row.get("seccion", "")),
        safe_str(row.get("tipo_archivo", "")),
        safe_str(row.get("url_origen", "")),
        texto_base,
    ]

    text = " | ".join([part for part in parts if part])
    text = " ".join(text.split())
    return text[:MAX_TEXT_CHARS]


def prepare_documents(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Filtra documentos con texto suficiente y prepara campos auxiliares."""
    df = ensure_columns(df)
    df["fuente"] = df.apply(infer_source, axis=1)

    total = len(df)
    df = df[df["num_caracteres"] >= MIN_CHARS].copy()
    discarded = total - len(df)

    if df.empty:
        raise ValueError(
            "No hay documentos con texto suficiente para generar embeddings. "
            f"Umbral actual: {MIN_CHARS} caracteres."
        )

    df["texto_embedding"] = df.apply(build_text_embedding, axis=1)
    df["texto_embedding_muestra"] = df["texto_embedding"].str[:SAMPLE_TEXT_CHARS]

    return df, discarded


def generate_embeddings(texts: list[str]) -> tuple[list[list[float]], int]:
    """Genera embeddings normalizados con Sentence Transformers."""
    model = SentenceTransformer(MODEL_NAME)
    vectors = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    vectors_list = vectors.tolist()
    dimension = len(vectors_list[0]) if vectors_list else 0
    return vectors_list, dimension


def vector_to_json(vector: list[float]) -> str:
    """Serializa el vector completo como JSON string."""
    return json.dumps([round(float(value), 8) for value in vector], ensure_ascii=False)


def vector_preview(vector: list[float], n: int = 8) -> str:
    """Serializa una vista corta del vector para inspeccion humana."""
    return json.dumps([round(float(value), 4) for value in vector[:n]], ensure_ascii=False)


def build_embeddings_table(df: pd.DataFrame, vectors: list[list[float]], dimension: int) -> pd.DataFrame:
    """Crea la tabla principal de embeddings."""
    return pd.DataFrame(
        {
            "id_documento": df["id_documento"].astype(str),
            "titulo": df["titulo"].astype(str),
            "fuente": df["fuente"].astype(str),
            "seccion": df["seccion"].astype(str),
            "tipo_archivo": df["tipo_archivo"].astype(str),
            "ruta_local": df["ruta_local"].astype(str),
            "url_origen": df["url_origen"].astype(str),
            "num_caracteres": df["num_caracteres"].astype(int),
            "estado_extraccion": df["estado_extraccion"].astype(str),
            "texto_embedding_muestra": df["texto_embedding_muestra"].astype(str),
            "modelo_embedding": MODEL_NAME,
            "dimension_embedding": dimension,
            "embedding_preview": [vector_preview(vector) for vector in vectors],
            "embedding": [vector_to_json(vector) for vector in vectors],
        }
    )


def build_summary_table(embeddings_df: pd.DataFrame) -> pd.DataFrame:
    """Agrupa documentos vectorizados por fuente, seccion y tipo."""
    grouped = (
        embeddings_df.groupby(["fuente", "seccion", "tipo_archivo"], dropna=False)
        .agg(
            documentos=("id_documento", "count"),
            caracteres_medios=("num_caracteres", "mean"),
            caracteres_minimos=("num_caracteres", "min"),
            caracteres_maximos=("num_caracteres", "max"),
            dimension_embedding=("dimension_embedding", "first"),
            modelo_embedding=("modelo_embedding", "first"),
        )
        .reset_index()
    )
    grouped["caracteres_medios"] = grouped["caracteres_medios"].round(2)
    return grouped


def build_sample_table(embeddings_df: pd.DataFrame) -> pd.DataFrame:
    """Crea una muestra de hasta 10 documentos por fuente principal."""
    samples = []
    for fuente in ["CEEI Elche", "CEEI Valencia"]:
        sample = (
            embeddings_df[embeddings_df["fuente"] == fuente]
            .sort_values("num_caracteres", ascending=False)
            .head(10)
        )
        samples.append(sample)

    if not samples:
        return pd.DataFrame()

    sample_df = pd.concat(samples, ignore_index=True)
    return sample_df[
        [
            "id_documento",
            "titulo",
            "fuente",
            "seccion",
            "tipo_archivo",
            "ruta_local",
            "url_origen",
            "num_caracteres",
            "estado_extraccion",
            "texto_embedding_muestra",
            "modelo_embedding",
            "dimension_embedding",
            "embedding_preview",
        ]
    ]


def save_outputs(embeddings_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Guarda la tabla principal, resumen agrupado y muestra."""
    ensure_output_dirs()

    embeddings_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    embeddings_df.to_parquet(OUTPUT_PARQUET, index=False)

    summary = build_summary_table(embeddings_df)
    summary.to_csv(OUTPUT_SUMMARY_CSV, index=False, encoding="utf-8-sig")
    summary.to_excel(OUTPUT_SUMMARY_XLSX, index=False)

    sample = build_sample_table(embeddings_df)
    sample.to_csv(OUTPUT_SAMPLE_CSV, index=False, encoding="utf-8-sig")
    sample.to_excel(OUTPUT_SAMPLE_XLSX, index=False)

    return summary, sample


def format_counter(series: pd.Series) -> str:
    """Formatea conteos para el informe."""
    if series.empty:
        return "- Sin datos"

    counts = series.fillna("").astype(str).value_counts()
    return "\n".join([f"- {name}: {count}" for name, count in counts.items()])


def write_report(
    corpus_df: pd.DataFrame,
    embeddings_df: pd.DataFrame,
    discarded: int,
    dimension: int,
) -> None:
    """Escribe el informe legible del proceso."""
    files = [
        OUTPUT_CSV,
        OUTPUT_PARQUET,
        OUTPUT_REPORT,
        OUTPUT_SUMMARY_CSV,
        OUTPUT_SUMMARY_XLSX,
        OUTPUT_SAMPLE_CSV,
        OUTPUT_SAMPLE_XLSX,
    ]

    report = f"""Informe de embeddings de documentos
Fecha: {datetime.now().isoformat(timespec="seconds")}

Entrada:
- Corpus: {INPUT_CORPUS}

Modelo:
- {MODEL_NAME}
- Dimension embedding: {dimension}
- Embeddings normalizados: si
- Batch size: {BATCH_SIZE}

Preparacion:
- Documentos totales en corpus: {len(corpus_df)}
- Umbral minimo de texto: {MIN_CHARS} caracteres
- Longitud maxima por documento: {MAX_TEXT_CHARS} caracteres
- Documentos vectorizados: {len(embeddings_df)}
- Documentos descartados por texto insuficiente: {discarded}

Numero de documentos por fuente:
{format_counter(embeddings_df["fuente"])}

Numero de documentos por seccion:
{format_counter(embeddings_df["seccion"])}

Archivos generados:
{chr(10).join([f"- {path}" for path in files])}
"""

    OUTPUT_REPORT.write_text(report, encoding="utf-8")


def main() -> None:
    ensure_output_dirs()

    print("Cargando corpus consolidado...")
    corpus_df = load_corpus(INPUT_CORPUS)
    print(f"Documentos en corpus: {len(corpus_df)}")

    print("Preparando textos para embeddings...")
    prepared_df, discarded = prepare_documents(corpus_df)
    print(f"Documentos preparados para embeddings: {len(prepared_df)}")
    print(f"Documentos descartados por texto insuficiente: {discarded}")

    print(f"Cargando modelo local: {MODEL_NAME}")
    vectors, dimension = generate_embeddings(prepared_df["texto_embedding"].tolist())
    print(f"Dimension del embedding: {dimension}")

    print("Construyendo tabla principal...")
    embeddings_df = build_embeddings_table(prepared_df, vectors, dimension)

    print("Guardando salidas...")
    summary_df, sample_df = save_outputs(embeddings_df)
    write_report(corpus_df, embeddings_df, discarded, dimension)

    print("\nProceso terminado.")
    print(f"Documentos vectorizados: {len(embeddings_df)}")
    print(f"Resumen agrupado: {len(summary_df)} filas")
    print(f"Muestra: {len(sample_df)} filas")
    print(f"CSV: {OUTPUT_CSV}")
    print(f"Parquet: {OUTPUT_PARQUET}")
    print(f"Informe: {OUTPUT_REPORT}")


if __name__ == "__main__":
    main()
