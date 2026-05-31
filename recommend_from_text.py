"""Recomienda perfiles y documentos desde una consulta libre."""

from __future__ import annotations

import io
import json
import os
import sys
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
DOCUMENT_EMBEDDINGS = ROOT / "data" / "embeddings" / "document_embeddings.parquet"
PROFILE_EMBEDDINGS = ROOT / "data" / "embeddings" / "profile_embeddings.parquet"
DOCUMENT_EMBEDDINGS_CSV = ROOT / "data" / "embeddings" / "document_embeddings.csv"
PROFILE_EMBEDDINGS_CSV = ROOT / "data" / "embeddings" / "profile_embeddings.csv"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_QUERY = (
    "Soy una emprendedora rural que quiere montar una pequena empresa "
    "agroalimentaria con impacto territorial y necesito ayudas publicas"
)

_DOCS: pd.DataFrame | None = None
_PROFILES: pd.DataFrame | None = None
_DOC_VECTORS: np.ndarray | None = None
_PROFILE_VECTORS: np.ndarray | None = None


class SafeTextIO(io.StringIO):
    """Salida en memoria cuyo flush nunca rompe Streamlit en Windows."""

    def flush(self) -> None:
        try:
            super().flush()
        except OSError:
            pass

    def isatty(self) -> bool:
        return False


@contextmanager
def safe_model_io():
    """Evita que tqdm/transformers escriban en streams problematicos."""
    safe_stdout = SafeTextIO()
    safe_stderr = SafeTextIO()
    old_stdout, old_stderr = sys.stdout, sys.stderr
    old_dunder_stdout = getattr(sys, "__stdout__", None)
    old_dunder_stderr = getattr(sys, "__stderr__", None)

    sys.stdout = safe_stdout
    sys.stderr = safe_stderr
    sys.__stdout__ = safe_stdout
    sys.__stderr__ = safe_stderr
    try:
        yield
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        if old_dunder_stdout is not None:
            sys.__stdout__ = old_dunder_stdout
        if old_dunder_stderr is not None:
            sys.__stderr__ = old_dunder_stderr


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def parse_vector(value: object) -> np.ndarray:
    try:
        if isinstance(value, str):
            return np.array(json.loads(value), dtype=np.float32)
        if isinstance(value, list):
            return np.array(value, dtype=np.float32)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(
            "No se pudo convertir un embedding desde JSON string. "
            "Comprueba las columnas embedding en data/embeddings/."
        ) from exc
    raise ValueError(
        "Embedding con formato no reconocido. Se esperaba JSON string o lista numerica."
    )


def vector_preview(vector: np.ndarray, n: int = 8) -> str:
    return json.dumps([round(float(value), 4) for value in vector[:n]], ensure_ascii=False)


def clean(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).split()).strip()


def load_embedding_table(parquet_path: Path, csv_path: Path) -> pd.DataFrame:
    """Carga una tabla de embeddings desde Parquet y usa CSV como fallback."""
    if parquet_path.exists():
        return pd.read_parquet(parquet_path)
    if csv_path.exists():
        return pd.read_csv(csv_path)
    raise FileNotFoundError(
        f"No existe {rel(parquet_path)} ni su fallback {rel(csv_path)}"
    )


@lru_cache(maxsize=1)
def load_model():
    """Carga el modelo local con cache y sin barras de progreso en Streamlit."""
    with safe_model_io():
        from transformers.utils import logging as transformers_logging
        import tqdm.auto
        import tqdm.asyncio
        import tqdm.std

        def silent_status_printer(_file):
            return lambda *_args, **_kwargs: None

        transformers_logging.disable_progress_bar()
        transformers_logging.set_verbosity_error()
        tqdm.auto.tqdm.status_printer = staticmethod(silent_status_printer)
        tqdm.asyncio.tqdm.status_printer = staticmethod(silent_status_printer)
        tqdm.std.tqdm.status_printer = staticmethod(silent_status_printer)

        from sentence_transformers import SentenceTransformer

        try:
            return SentenceTransformer(MODEL_NAME, local_files_only=True)
        except Exception:
            return SentenceTransformer(MODEL_NAME)


def load_tables() -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray]:
    global _DOCS, _PROFILES, _DOC_VECTORS, _PROFILE_VECTORS

    if _DOCS is not None and _PROFILES is not None and _DOC_VECTORS is not None and _PROFILE_VECTORS is not None:
        return _DOCS, _PROFILES, _DOC_VECTORS, _PROFILE_VECTORS

    _DOCS = load_embedding_table(DOCUMENT_EMBEDDINGS, DOCUMENT_EMBEDDINGS_CSV)
    _PROFILES = load_embedding_table(PROFILE_EMBEDDINGS, PROFILE_EMBEDDINGS_CSV)
    _DOC_VECTORS = np.vstack([parse_vector(value) for value in _DOCS["embedding"]])
    _PROFILE_VECTORS = np.vstack([parse_vector(value) for value in _PROFILES["embedding"]])
    return _DOCS, _PROFILES, _DOC_VECTORS, _PROFILE_VECTORS


def encode_query(query_text: str) -> np.ndarray | None:
    query_text = str(query_text or "").strip()
    if not query_text:
        return None

    model = load_model()
    with safe_model_io():
        vector = model.encode(
            [query_text],
            normalize_embeddings=True,
            show_progress_bar=False,
        )[0]
    return np.array(vector, dtype=np.float32)


def recommend_profiles(query_text: str, top_k: int = 3) -> pd.DataFrame:
    """Devuelve los perfiles predefinidos mas parecidos al texto libre."""
    query_text = str(query_text or "").strip()
    if not query_text:
        return pd.DataFrame()

    _, profiles, _, profile_vectors = load_tables()
    query_vector = encode_query(query_text)
    if query_vector is None:
        return pd.DataFrame()

    scores = profile_vectors @ query_vector
    ordered = np.argsort(scores)[::-1][:top_k]
    query_preview = vector_preview(query_vector)

    rows: list[dict[str, Any]] = []
    for rank, idx in enumerate(ordered, start=1):
        profile = profiles.iloc[int(idx)]
        rows.append(
            {
                "rank": rank,
                "id_perfil": clean(profile.get("id_perfil")),
                "nombre_perfil": clean(profile.get("nombre_perfil")),
                "score_similitud": round(float(scores[idx]), 6),
                "embedding_query_preview": query_preview,
                "embedding_perfil_preview": clean(profile.get("embedding_preview")),
            }
        )

    return pd.DataFrame(rows)


def recommend_documents(query_text: str, top_k: int = 10) -> pd.DataFrame:
    """Devuelve documentos recomendados para un texto libre."""
    query_text = str(query_text or "").strip()
    if not query_text:
        return pd.DataFrame()

    docs, _, doc_vectors, _ = load_tables()
    query_vector = encode_query(query_text)
    if query_vector is None:
        return pd.DataFrame()

    scores = doc_vectors @ query_vector
    ordered = np.argsort(scores)[::-1][:top_k]
    query_preview = vector_preview(query_vector)

    rows: list[dict[str, Any]] = []
    for rank, idx in enumerate(ordered, start=1):
        doc = docs.iloc[int(idx)]
        rows.append(
            {
                "rank": rank,
                "id_documento": clean(doc.get("id_documento")),
                "titulo": clean(doc.get("titulo")),
                "fuente": clean(doc.get("fuente")),
                "seccion": clean(doc.get("seccion")),
                "tipo_archivo": clean(doc.get("tipo_archivo")),
                "score_similitud": round(float(scores[idx]), 6),
                "ruta_local": clean(doc.get("ruta_local")),
                "url_origen": clean(doc.get("url_origen")),
                "texto_muestra": clean(doc.get("texto_embedding_muestra")),
                "embedding_query_preview": query_preview,
                "embedding_documento_preview": clean(doc.get("embedding_preview")),
            }
        )

    return pd.DataFrame(rows)


def recommend(query_text: str, top_k: int = 10) -> pd.DataFrame:
    """Alias conservado por compatibilidad con versiones anteriores."""
    return recommend_documents(query_text, top_k=top_k)


def main() -> None:
    query = DEFAULT_QUERY
    print("Consulta de ejemplo:")
    print(query)

    profiles_df = recommend_profiles(query, top_k=3)
    docs_df = recommend_documents(query, top_k=10)

    print("\nPerfiles mas parecidos:")
    print(profiles_df[["rank", "nombre_perfil", "score_similitud"]].to_string(index=False))

    print("\nDocumentos recomendados:")
    print(
        docs_df[
            ["rank", "titulo", "fuente", "seccion", "tipo_archivo", "score_similitud"]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
