"""Recomienda perfiles y documentos desde una consulta libre."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from transformers.utils import logging as transformers_logging


os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TQDM_DISABLE"] = "1"
transformers_logging.disable_progress_bar()
transformers_logging.set_verbosity_error()


ROOT = Path(__file__).resolve().parent
DOCUMENT_EMBEDDINGS = ROOT / "data" / "embeddings" / "document_embeddings.parquet"
PROFILE_EMBEDDINGS = ROOT / "data" / "embeddings" / "profile_embeddings.parquet"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_QUERY = (
    "Soy una emprendedora rural que quiere montar una pequena empresa "
    "agroalimentaria con impacto territorial y necesito ayudas publicas"
)

_MODEL: SentenceTransformer | None = None
_DOCS: pd.DataFrame | None = None
_PROFILES: pd.DataFrame | None = None
_DOC_VECTORS: np.ndarray | None = None
_PROFILE_VECTORS: np.ndarray | None = None


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def parse_vector(value: object) -> np.ndarray:
    if isinstance(value, str):
        return np.array(json.loads(value), dtype=np.float32)
    if isinstance(value, list):
        return np.array(value, dtype=np.float32)
    raise ValueError("Embedding con formato no reconocido.")


def vector_preview(vector: np.ndarray, n: int = 8) -> str:
    return json.dumps([round(float(value), 4) for value in vector[:n]], ensure_ascii=False)


def clean(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).split()).strip()


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"No existe {rel(path)}")


def load_model() -> SentenceTransformer:
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer(MODEL_NAME)
    return _MODEL


def load_tables() -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray]:
    global _DOCS, _PROFILES, _DOC_VECTORS, _PROFILE_VECTORS

    if _DOCS is not None and _PROFILES is not None and _DOC_VECTORS is not None and _PROFILE_VECTORS is not None:
        return _DOCS, _PROFILES, _DOC_VECTORS, _PROFILE_VECTORS

    require_file(DOCUMENT_EMBEDDINGS)
    require_file(PROFILE_EMBEDDINGS)

    _DOCS = pd.read_parquet(DOCUMENT_EMBEDDINGS)
    _PROFILES = pd.read_parquet(PROFILE_EMBEDDINGS)
    _DOC_VECTORS = np.vstack([parse_vector(value) for value in _DOCS["embedding"]])
    _PROFILE_VECTORS = np.vstack([parse_vector(value) for value in _PROFILES["embedding"]])
    return _DOCS, _PROFILES, _DOC_VECTORS, _PROFILE_VECTORS


def encode_query(query_text: str) -> np.ndarray:
    query_text = clean(query_text)
    if not query_text:
        raise ValueError("query_text no puede estar vacio.")

    model = load_model()
    vector = model.encode(
        [query_text],
        normalize_embeddings=True,
        show_progress_bar=False,
    )[0]
    return np.array(vector, dtype=np.float32)


def recommend_profiles(query_text: str, top_k: int = 3) -> pd.DataFrame:
    """Devuelve los perfiles predefinidos mas parecidos al texto libre."""
    _, profiles, _, profile_vectors = load_tables()
    query_vector = encode_query(query_text)
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


def recommend(query_text: str, top_k: int = 10) -> pd.DataFrame:
    """Devuelve documentos recomendados para un texto libre."""
    docs, _, doc_vectors, _ = load_tables()
    query_vector = encode_query(query_text)
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


def main() -> None:
    query = DEFAULT_QUERY
    print("Consulta de ejemplo:")
    print(query)

    profiles_df = recommend_profiles(query, top_k=3)
    docs_df = recommend(query, top_k=10)

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
