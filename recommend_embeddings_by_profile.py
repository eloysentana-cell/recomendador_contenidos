"""Recomienda documentos por similitud semantica entre perfiles y documentos."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
PROFILE_EMBEDDINGS = ROOT / "data" / "embeddings" / "profile_embeddings.parquet"
DOCUMENT_EMBEDDINGS = ROOT / "data" / "embeddings" / "document_embeddings.parquet"
OUTPUT_CSV = ROOT / "outputs" / "recomendaciones_embeddings_perfiles.csv"
OUTPUT_XLSX = ROOT / "outputs" / "recomendaciones_embeddings_perfiles.xlsx"
OUTPUT_REPORT = ROOT / "outputs" / "informe_recomendaciones_embeddings.txt"
TOP_K = 10


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"No existe {rel(path)}")


def parse_vector(value: object) -> np.ndarray:
    if isinstance(value, str):
        return np.array(json.loads(value), dtype=np.float32)
    if isinstance(value, list):
        return np.array(value, dtype=np.float32)
    raise ValueError("Embedding con formato no reconocido.")


def load_embeddings() -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray]:
    require_file(PROFILE_EMBEDDINGS)
    require_file(DOCUMENT_EMBEDDINGS)

    profiles = pd.read_parquet(PROFILE_EMBEDDINGS)
    docs = pd.read_parquet(DOCUMENT_EMBEDDINGS)

    for name, df in [("perfiles", profiles), ("documentos", docs)]:
        if df.empty:
            raise ValueError(f"La tabla de {name} esta vacia.")
        if "embedding" not in df.columns:
            raise ValueError(f"Falta la columna embedding en {name}.")

    profile_vectors = np.vstack([parse_vector(value) for value in profiles["embedding"]])
    doc_vectors = np.vstack([parse_vector(value) for value in docs["embedding"]])

    if profile_vectors.shape[1] != doc_vectors.shape[1]:
        raise ValueError(
            "La dimension de perfiles y documentos no coincide: "
            f"{profile_vectors.shape[1]} vs {doc_vectors.shape[1]}"
        )

    return profiles, docs, profile_vectors, doc_vectors


def clean(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).split()).strip()


def build_recommendations(
    profiles: pd.DataFrame,
    docs: pd.DataFrame,
    profile_vectors: np.ndarray,
    doc_vectors: np.ndarray,
) -> pd.DataFrame:
    scores_matrix = profile_vectors @ doc_vectors.T
    records = []

    for profile_idx, profile in profiles.iterrows():
        scores = scores_matrix[profile_idx]
        ordered = np.argsort(scores)[::-1][:TOP_K]

        print(f"\nTop {TOP_K} embeddings para {profile['nombre_perfil']}:")
        for rank, doc_idx in enumerate(ordered, start=1):
            doc = docs.iloc[int(doc_idx)]
            score = round(float(scores[doc_idx]), 6)
            if rank <= 5:
                print(f"{rank}. {doc['titulo']} ({doc['fuente']}, {doc['seccion']}) - {score:.4f}")

            records.append(
                {
                    "id_perfil": clean(profile.get("id_perfil")),
                    "nombre_perfil": clean(profile.get("nombre_perfil")),
                    "rank": rank,
                    "id_documento": clean(doc.get("id_documento")),
                    "titulo": clean(doc.get("titulo")),
                    "fuente": clean(doc.get("fuente")),
                    "seccion": clean(doc.get("seccion")),
                    "tipo_archivo": clean(doc.get("tipo_archivo")),
                    "ruta_local": clean(doc.get("ruta_local")),
                    "url_origen": clean(doc.get("url_origen")),
                    "score_similitud": score,
                    "embedding_perfil_preview": clean(profile.get("embedding_preview")),
                    "embedding_documento_preview": clean(doc.get("embedding_preview")),
                    "texto_documento_muestra": clean(doc.get("texto_embedding_muestra")),
                }
            )

    return pd.DataFrame(records)


def write_report(recommendations: pd.DataFrame, profiles: pd.DataFrame, docs: pd.DataFrame) -> None:
    lines = [
        "INFORME DE RECOMENDACIONES POR EMBEDDINGS",
        "=" * 48,
        f"Fecha: {datetime.now().isoformat(timespec='seconds')}",
        f"Perfiles: {len(profiles)}",
        f"Documentos: {len(docs)}",
        f"Top por perfil: {TOP_K}",
        "",
        "Scores por perfil:",
    ]

    stats = (
        recommendations.groupby(["id_perfil", "nombre_perfil"], dropna=False)["score_similitud"]
        .agg(["max", "mean", "min"])
        .reset_index()
    )
    for _, row in stats.iterrows():
        lines.append(
            "- {nombre}: max={maximo:.6f}, medio={medio:.6f}, min={minimo:.6f}".format(
                nombre=row["nombre_perfil"],
                maximo=row["max"],
                medio=row["mean"],
                minimo=row["min"],
            )
        )

    repeated = Counter(recommendations["id_documento"])
    lines.extend(["", "Documentos mas repetidos entre perfiles:"])
    for doc_id, count in repeated.most_common(10):
        doc_title = recommendations.loc[recommendations["id_documento"] == doc_id, "titulo"].iloc[0]
        lines.append(f"- {doc_id} | {doc_title}: {count} apariciones")

    lines.extend(
        [
            "",
            "Archivos generados:",
            f"- {rel(OUTPUT_CSV)}",
            f"- {rel(OUTPUT_XLSX)}",
            f"- {rel(OUTPUT_REPORT)}",
        ]
    )
    OUTPUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    profiles, docs, profile_vectors, doc_vectors = load_embeddings()
    recommendations = build_recommendations(profiles, docs, profile_vectors, doc_vectors)

    recommendations.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    recommendations.to_excel(OUTPUT_XLSX, index=False)
    write_report(recommendations, profiles, docs)

    print("\nRecomendaciones por embeddings generadas correctamente.")
    print(f"Perfiles: {len(profiles)}")
    print(f"Documentos: {len(docs)}")
    print(f"CSV: {rel(OUTPUT_CSV)}")
    print(f"Excel: {rel(OUTPUT_XLSX)}")
    print(f"Informe: {rel(OUTPUT_REPORT)}")


if __name__ == "__main__":
    main()
