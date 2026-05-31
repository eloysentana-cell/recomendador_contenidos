"""Genera embeddings locales de perfiles emprendedores.

Entrada:
- data/perfiles/perfiles_emprendedores.json

Salidas:
- data/embeddings/profile_embeddings.csv
- data/embeddings/profile_embeddings.parquet
- outputs/informe_profile_embeddings.txt
- outputs/profile_embeddings_muestra.csv
- outputs/profile_embeddings_muestra.xlsx

No usa OpenAI ni APIs externas. Usa Sentence Transformers en local.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).resolve().parent
INPUT_JSON = ROOT / "data" / "perfiles" / "perfiles_emprendedores.json"
EMBEDDINGS_DIR = ROOT / "data" / "embeddings"
OUTPUT_CSV = EMBEDDINGS_DIR / "profile_embeddings.csv"
OUTPUT_PARQUET = EMBEDDINGS_DIR / "profile_embeddings.parquet"
OUTPUTS_DIR = ROOT / "outputs"
OUTPUT_REPORT = OUTPUTS_DIR / "informe_profile_embeddings.txt"
OUTPUT_SAMPLE_CSV = OUTPUTS_DIR / "profile_embeddings_muestra.csv"
OUTPUT_SAMPLE_XLSX = OUTPUTS_DIR / "profile_embeddings_muestra.xlsx"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MAX_TEXT_CHARS = 3000
SAMPLE_TEXT_CHARS = 500
BATCH_SIZE = 8

TEXT_FIELDS = [
    "nombre",
    "fase_emprendedora",
    "nivel_madurez",
    "perfil_funcional",
    "necesidades_prioritarias",
    "intenciones_busqueda",
    "palabras_clave_semanticas",
    "descripcion_embedding",
]


def rel(path: Path) -> str:
    """Devuelve una ruta relativa al proyecto para mensajes e informes."""
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def value_to_text(value: Any) -> str:
    """Convierte listas y diccionarios a texto sin inventar campos."""
    if value is None:
        return ""
    if isinstance(value, list):
        return " | ".join(value_to_text(item) for item in value if value_to_text(item))
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            item_text = value_to_text(item)
            if item_text:
                parts.append(f"{key}: {item_text}")
        return " | ".join(parts)
    return " ".join(str(value).split()).strip()


def ensure_dirs() -> None:
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


def load_profiles() -> list[dict[str, Any]]:
    if not INPUT_JSON.exists():
        raise FileNotFoundError(f"No existe {rel(INPUT_JSON)}")

    profiles = json.loads(INPUT_JSON.read_text(encoding="utf-8"))
    if not isinstance(profiles, list) or not profiles:
        raise ValueError(f"El archivo {rel(INPUT_JSON)} no contiene una lista de perfiles.")

    return profiles


def build_text_embedding(profile: dict[str, Any]) -> str:
    parts = []
    for field in TEXT_FIELDS:
        text = value_to_text(profile.get(field))
        if text:
            parts.append(text)

    text = " | ".join(parts)
    text = " ".join(text.split())
    return text[:MAX_TEXT_CHARS]


def vector_to_json(vector: list[float]) -> str:
    return json.dumps([round(float(value), 8) for value in vector], ensure_ascii=False)


def vector_preview(vector: list[float], n: int = 8) -> str:
    return json.dumps([round(float(value), 4) for value in vector[:n]], ensure_ascii=False)


def generate_embeddings(texts: list[str]) -> tuple[list[list[float]], int]:
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


def build_table(profiles: list[dict[str, Any]], vectors: list[list[float]], dimension: int) -> pd.DataFrame:
    rows = []
    for profile, vector in zip(profiles, vectors):
        text_embedding = build_text_embedding(profile)
        rows.append(
            {
                "id_perfil": value_to_text(profile.get("id")),
                "nombre_perfil": value_to_text(profile.get("nombre")),
                "fase_emprendedora": value_to_text(profile.get("fase_emprendedora")),
                "texto_embedding": text_embedding,
                "texto_embedding_muestra": text_embedding[:SAMPLE_TEXT_CHARS],
                "modelo_embedding": MODEL_NAME,
                "dimension_embedding": dimension,
                "embedding_preview": vector_preview(vector),
                "embedding": vector_to_json(vector),
            }
        )

    df = pd.DataFrame(rows)
    if df["id_perfil"].eq("").any():
        raise ValueError("Hay perfiles sin id_perfil.")
    return df


def write_report(embeddings_df: pd.DataFrame, dimension: int) -> None:
    generated_files = [
        OUTPUT_CSV,
        OUTPUT_PARQUET,
        OUTPUT_REPORT,
        OUTPUT_SAMPLE_CSV,
        OUTPUT_SAMPLE_XLSX,
    ]
    lines = [
        "INFORME DE EMBEDDINGS DE PERFILES",
        "=" * 40,
        f"Fecha: {datetime.now().isoformat(timespec='seconds')}",
        f"Entrada: {rel(INPUT_JSON)}",
        f"Modelo: {MODEL_NAME}",
        f"Dimension: {dimension}",
        f"Perfiles procesados: {len(embeddings_df)}",
        f"Longitud maxima aplicada: {MAX_TEXT_CHARS} caracteres",
        "",
        "Archivos generados:",
        *[f"- {rel(path)}" for path in generated_files],
    ]
    OUTPUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ensure_dirs()
    profiles = load_profiles()
    texts = [build_text_embedding(profile) for profile in profiles]
    if any(not text for text in texts):
        raise ValueError("Hay perfiles sin texto suficiente para vectorizar.")

    vectors, dimension = generate_embeddings(texts)
    embeddings_df = build_table(profiles, vectors, dimension)

    embeddings_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    embeddings_df.to_parquet(OUTPUT_PARQUET, index=False)

    sample_columns = [column for column in embeddings_df.columns if column != "embedding"]
    sample_df = embeddings_df[sample_columns].copy()
    sample_df.to_csv(OUTPUT_SAMPLE_CSV, index=False, encoding="utf-8-sig")
    sample_df.to_excel(OUTPUT_SAMPLE_XLSX, index=False)

    write_report(embeddings_df, dimension)

    print("Embeddings de perfiles generados correctamente.")
    print(f"Perfiles procesados: {len(embeddings_df)}")
    print(f"Dimension: {dimension}")
    print(f"CSV: {rel(OUTPUT_CSV)}")
    print(f"Parquet: {rel(OUTPUT_PARQUET)}")
    print(f"Informe: {rel(OUTPUT_REPORT)}")


if __name__ == "__main__":
    main()
