"""Worker JSON para ejecutar recomendaciones fuera del proceso Streamlit."""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata

from recommend_from_text import MODEL_NAME, recommend_documents, recommend_profiles


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Devuelve recomendaciones en JSON.")
    parser.add_argument("--query", required=True, help="Texto libre de consulta.")
    parser.add_argument("--top-k", type=int, default=10, help="Numero de documentos.")
    return parser.parse_args()


def normalize_for_json(value):
    """Normaliza textos para visualizacion web sin cambiar los embeddings."""
    if isinstance(value, str):
        return unicodedata.normalize("NFKC", value)
    if isinstance(value, list):
        return [normalize_for_json(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_for_json(item) for key, item in value.items()}
    return value


def main() -> None:
    args = parse_args()
    query = str(args.query or "").strip()
    if not query:
        payload = {
            "model_name": MODEL_NAME,
            "profiles": [],
            "documents": [],
            "error": "",
        }
        print(json.dumps(normalize_for_json(payload), ensure_ascii=True))
        return

    profiles_df = recommend_profiles(query, top_k=3)
    documents_df = recommend_documents(query, top_k=args.top_k)
    payload = {
        "model_name": MODEL_NAME,
        "profiles": profiles_df.to_dict(orient="records"),
        "documents": documents_df.to_dict(orient="records"),
        "error": "",
    }
    print(json.dumps(normalize_for_json(payload), ensure_ascii=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        payload = {
            "model_name": MODEL_NAME,
            "profiles": [],
            "documents": [],
            "error": str(exc),
        }
        print(json.dumps(normalize_for_json(payload), ensure_ascii=True))
        sys.exit(1)
