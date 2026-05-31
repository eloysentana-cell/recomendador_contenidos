"""Compara rankings TF-IDF frente a rankings por embeddings locales."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
TFIDF_EXPLAINED = ROOT / "outputs" / "recomendaciones_tfidf_explicadas.csv"
TFIDF_BASIC = ROOT / "outputs" / "recomendaciones_tfidf.csv"
EMBEDDINGS_RECS = ROOT / "outputs" / "recomendaciones_embeddings_perfiles.csv"
OUTPUT_CSV = ROOT / "outputs" / "comparacion_tfidf_embeddings.csv"
OUTPUT_XLSX = ROOT / "outputs" / "comparacion_tfidf_embeddings.xlsx"
OUTPUT_REPORT = ROOT / "outputs" / "informe_comparacion_tfidf_embeddings.txt"
TOP_K = 10


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def select_tfidf_path() -> Path:
    if TFIDF_EXPLAINED.exists():
        return TFIDF_EXPLAINED
    if TFIDF_BASIC.exists():
        return TFIDF_BASIC
    raise FileNotFoundError(
        f"No existe {rel(TFIDF_EXPLAINED)} ni {rel(TFIDF_BASIC)}"
    )


def clean(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).split()).strip()


def title_map(df: pd.DataFrame) -> dict[str, str]:
    return {
        clean(row["id_documento"]): clean(row.get("titulo", row["id_documento"]))
        for _, row in df.iterrows()
    }


def format_docs(doc_ids: list[str], titles: dict[str, str]) -> str:
    return " || ".join(f"{doc_id}: {titles.get(doc_id, doc_id)}" for doc_id in doc_ids)


def interpret(overlap: float) -> str:
    if overlap >= 0.6:
        return "Alta coincidencia entre metodos"
    if overlap >= 0.3:
        return "Coincidencia parcial"
    return "Baja coincidencia; embeddings aportan ranking diferenciado"


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, Path]:
    tfidf_path = select_tfidf_path()
    if not EMBEDDINGS_RECS.exists():
        raise FileNotFoundError(f"No existe {rel(EMBEDDINGS_RECS)}")

    tfidf = pd.read_csv(tfidf_path)
    embeddings = pd.read_csv(EMBEDDINGS_RECS)

    required = ["id_perfil", "nombre_perfil", "rank", "id_documento", "titulo"]
    for name, df in [("TF-IDF", tfidf), ("embeddings", embeddings)]:
        missing = [column for column in required if column not in df.columns]
        if missing:
            raise ValueError(f"Faltan columnas en {name}: {', '.join(missing)}")

    return tfidf, embeddings, tfidf_path


def compare_rankings(tfidf: pd.DataFrame, embeddings: pd.DataFrame) -> pd.DataFrame:
    all_titles = title_map(pd.concat([tfidf, embeddings], ignore_index=True))
    records = []

    profile_ids = sorted(set(tfidf["id_perfil"].astype(str)) | set(embeddings["id_perfil"].astype(str)))
    for profile_id in profile_ids:
        tfidf_profile = (
            tfidf[tfidf["id_perfil"].astype(str) == profile_id]
            .sort_values("rank")
            .head(TOP_K)
        )
        emb_profile = (
            embeddings[embeddings["id_perfil"].astype(str) == profile_id]
            .sort_values("rank")
            .head(TOP_K)
        )

        if tfidf_profile.empty and emb_profile.empty:
            continue

        profile_name = clean(
            (tfidf_profile if not tfidf_profile.empty else emb_profile)["nombre_perfil"].iloc[0]
        )
        tfidf_ids = [clean(value) for value in tfidf_profile["id_documento"].tolist()]
        emb_ids = [clean(value) for value in emb_profile["id_documento"].tolist()]
        common = [doc_id for doc_id in tfidf_ids if doc_id in set(emb_ids)]
        only_tfidf = [doc_id for doc_id in tfidf_ids if doc_id not in set(emb_ids)]
        only_embeddings = [doc_id for doc_id in emb_ids if doc_id not in set(tfidf_ids)]

        denominator = max(len(tfidf_ids), len(emb_ids), 1)
        overlap = round(len(common) / denominator, 4)

        records.append(
            {
                "id_perfil": profile_id,
                "nombre_perfil": profile_name,
                "total_tfidf_top10": len(tfidf_ids),
                "total_embeddings_top10": len(emb_ids),
                "coincidencias_top10": len(common),
                "porcentaje_solapamiento": overlap,
                "documentos_comunes": format_docs(common, all_titles),
                "documentos_solo_tfidf": format_docs(only_tfidf, all_titles),
                "documentos_solo_embeddings": format_docs(only_embeddings, all_titles),
                "interpretacion_breve": interpret(overlap),
            }
        )

    return pd.DataFrame(records)


def write_report(comparison: pd.DataFrame, tfidf_path: Path) -> None:
    mean_overlap = comparison["porcentaje_solapamiento"].mean() if not comparison.empty else 0
    max_rows = comparison.sort_values("porcentaje_solapamiento", ascending=False).head(3)
    min_rows = comparison.sort_values("porcentaje_solapamiento", ascending=True).head(3)

    lines = [
        "INFORME DE COMPARACION TF-IDF VS EMBEDDINGS",
        "=" * 48,
        f"Fecha: {datetime.now().isoformat(timespec='seconds')}",
        f"Entrada TF-IDF: {rel(tfidf_path)}",
        f"Entrada embeddings: {rel(EMBEDDINGS_RECS)}",
        f"Perfiles comparados: {len(comparison)}",
        f"Promedio de solapamiento top {TOP_K}: {mean_overlap:.4f}",
        "",
        "Perfiles con mayor coincidencia:",
    ]
    for _, row in max_rows.iterrows():
        lines.append(f"- {row['nombre_perfil']}: {row['porcentaje_solapamiento']:.4f}")

    lines.append("")
    lines.append("Perfiles con menor coincidencia:")
    for _, row in min_rows.iterrows():
        lines.append(f"- {row['nombre_perfil']}: {row['porcentaje_solapamiento']:.4f}")

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
    tfidf, embeddings, tfidf_path = load_inputs()
    comparison = compare_rankings(tfidf, embeddings)
    comparison.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    comparison.to_excel(OUTPUT_XLSX, index=False)
    write_report(comparison, tfidf_path)

    print("Comparacion TF-IDF vs embeddings generada correctamente.")
    print(f"Perfiles comparados: {len(comparison)}")
    if not comparison.empty:
        print(f"Solapamiento medio: {comparison['porcentaje_solapamiento'].mean():.4f}")
    print(f"CSV: {rel(OUTPUT_CSV)}")
    print(f"Excel: {rel(OUTPUT_XLSX)}")
    print(f"Informe: {rel(OUTPUT_REPORT)}")


if __name__ == "__main__":
    main()
