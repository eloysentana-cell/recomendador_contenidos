"""
Genera la tabla de embeddings de documentos a partir del corpus consolidado.

Entrada:
- data/processed/corpus_recomendador.csv

Salidas:
- data/embeddings/document_embeddings.csv
- data/embeddings/document_embeddings.parquet
- outputs/informe_document_embeddings.txt

No usa APIs externas. Usa Sentence Transformers en local.
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

OUTPUT_DIR = PROJECT_ROOT / "data" / "embeddings"
OUTPUT_CSV = OUTPUT_DIR / "document_embeddings.csv"
OUTPUT_PARQUET = OUTPUT_DIR / "document_embeddings.parquet"

OUTPUT_REPORT = PROJECT_ROOT / "outputs" / "informe_document_embeddings.txt"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

MAX_TEXT_CHARS = 5000
BATCH_SIZE = 32
MIN_CHARS = 300


def safe_str(value: Any) -> str:
    """Convierte valores nulos o no textuales en cadenas limpias."""
    if pd.isna(value):
        return ""
    return str(value).strip()


def load_corpus(path: Path) -> pd.DataFrame:
    """Carga y valida el corpus consolidado."""
    if not path.exists():
        raise FileNotFoundError(f"No existe el corpus: {path}")

    if path.stat().st_size == 0:
        raise ValueError(
            f"El corpus existe pero esta vacio: {path}. "
            "Ejecuta primero build_corpus_recomendador.py."
        )

    df = pd.read_csv(path)

    if df.empty:
        raise ValueError(
            f"El corpus no contiene filas: {path}. "
            "Ejecuta primero build_corpus_recomendador.py."
        )

    return df


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Asegura columnas minimas, adaptandose a nombres alternativos."""
    df = df.copy()

    if "id_documento" not in df.columns:
        if "id" in df.columns:
            df["id_documento"] = df["id"].apply(
                lambda x: f"doc_{int(x):06d}" if str(x).isdigit() else str(x)
            )
        else:
            df["id_documento"] = [f"doc_{i:06d}" for i in range(1, len(df) + 1)]

    if "ruta_local" not in df.columns:
        if "ruta_archivo" in df.columns:
            df["ruta_local"] = df["ruta_archivo"]
        else:
            df["ruta_local"] = ""

    for col in ["titulo", "fuente", "seccion", "tipo_archivo", "url_origen", "estado_extraccion"]:
        if col not in df.columns:
            df[col] = ""

    if "texto_recomendador" not in df.columns:
        df["texto_recomendador"] = ""

    if "texto" not in df.columns:
        df["texto"] = ""

    if "num_caracteres" not in df.columns:
        base_text = df["texto"].fillna("").astype(str)
        df["num_caracteres"] = base_text.str.len()

    return df


def infer_source(row: pd.Series) -> str:
    """Infiere fuente si no esta informada."""
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
    """Construye el texto que se vectorizara."""
    parts = [
        safe_str(row.get("titulo", "")),
        safe_str(row.get("fuente", "")),
        safe_str(row.get("seccion", "")),
        safe_str(row.get("tipo_archivo", "")),
        safe_str(row.get("url_origen", "")),
        safe_str(row.get("texto_recomendador", "")),
    ]

    if not safe_str(row.get("texto_recomendador", "")):
        parts.append(safe_str(row.get("texto", "")))

    text = " | ".join([p for p in parts if p])
    text = " ".join(text.split())

    return text[:MAX_TEXT_CHARS]


def prepare_documents(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Prepara los documentos para embeddings y descarta textos insuficientes."""
    df = ensure_columns(df)

    df["fuente"] = df.apply(infer_source, axis=1)
    df["texto_embedding"] = df.apply(build_text_embedding, axis=1)
    df["num_caracteres_embedding"] = df["texto_embedding"].fillna("").astype(str).str.len()

    before = len(df)

    df = df[df["num_caracteres_embedding"] >= MIN_CHARS].copy()

    discarded = before - len(df)

    if df.empty:
        raise ValueError(
            "No hay documentos con texto suficiente para generar embeddings. "
            f"Umbral actual: {MIN_CHARS} caracteres."
        )

    return df, discarded


def generate_embeddings(texts: list[str]) -> tuple[list[list[float]], int]:
    """Genera embeddings normalizados."""
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
    return json.dumps([round(float(x), 8) for x in vector], ensure_ascii=False)


def vector_preview(vector: list[float], n: int = 8) -> str:
    """Devuelve una vista corta del vector para inspeccion humana."""
    return json.dumps([round(float(x), 4) for x in vector[:n]], ensure_ascii=False)


def save_outputs(df: pd.DataFrame, vectors: list[list[float]], dimension: int) -> pd.DataFrame:
    """Guarda CSV y Parquet."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)

    out = pd.DataFrame(
        {
            "id_documento": df["id_documento"].astype(str),
            "titulo": df["titulo"].astype(str),
            "fuente": df["fuente"].astype(str),
            "seccion": df["seccion"].astype(str),
            "tipo_archivo": df["tipo_archivo"].astype(str),
            "ruta_local": df["ruta_local"].astype(str),
            "url_origen": df["url_origen"].astype(str),
            "num_caracteres": df["num_caracteres"],
            "num_caracteres_embedding": df["num_caracteres_embedding"],
            "estado_extraccion": df["estado_extraccion"].astype(str),
            "texto_embedding": df["texto_embedding"].astype(str),
            "modelo_embedding": MODEL_NAME,
            "dimension_embedding": dimension,
            "embedding": [vector_to_json(v) for v in vectors],
            "embedding_preview": [vector_preview(v) for v in vectors],
        }
    )

    out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    out.to_parquet(OUTPUT_PARQUET, index=False)

    return out


def write_report(total_input: int, total_output: int, discarded: int, dimension: int) -> None:
    """Escribe informe de generacion."""
    report = f"""Informe de embeddings de documentos
Fecha: {datetime.now().isoformat(timespec="seconds")}

Entrada:
- Corpus: {INPUT_CORPUS}
- Documentos en corpus original: {total_input}

Modelo:
- {MODEL_NAME}
- Dimension embedding: {dimension}
- Embeddings normalizados: si
- Batch size: {BATCH_SIZE}

Preparacion:
- Longitud maxima por documento: {MAX_TEXT_CHARS} caracteres
- Umbral minimo de texto: {MIN_CHARS} caracteres
- Documentos descartados por texto insuficiente: {discarded}
- Documentos vectorizados: {total_output}

Salidas:
- {OUTPUT_CSV}
- {OUTPUT_PARQUET}
"""

    OUTPUT_REPORT.write_text(report, encoding="utf-8")


def main() -> None:
    print("Cargando corpus consolidado...")
    df = load_corpus(INPUT_CORPUS)

    print(f"Documentos en corpus: {len(df)}")

    print("Preparando textos de documentos...")
    prepared, discarded = prepare_documents(df)

    print(f"Documentos preparados para embeddings: {len(prepared)}")
    print(f"Documentos descartados: {discarded}")

    print(f"Cargando modelo: {MODEL_NAME}")
    vectors, dimension = generate_embeddings(prepared["texto_embedding"].tolist())

    print(f"Dimension del embedding: {dimension}")

    print("Guardando tabla de embeddings...")
    out = save_outputs(prepared, vectors, dimension)

    write_report(
        total_input=len(df),
        total_output=len(out),
        discarded=discarded,
        dimension=dimension,
    )

    print("\nProceso terminado.")
    print(f"CSV: {OUTPUT_CSV}")
    print(f"Parquet: {OUTPUT_PARQUET}")
    print(f"Informe: {OUTPUT_REPORT}")


if __name__ == "__main__":
    main()
