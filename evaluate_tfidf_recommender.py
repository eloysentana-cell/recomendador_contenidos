"""Genera metricas tecnicas descriptivas del recomendador TF-IDF."""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
INPUT_PATH = ROOT / "outputs" / "recomendaciones_tfidf_explicadas.csv"
OUTPUT_CSV = ROOT / "outputs" / "evaluacion_tfidf.csv"
OUTPUT_XLSX = ROOT / "outputs" / "evaluacion_tfidf.xlsx"
REPORT_PATH = ROOT / "outputs" / "informe_evaluacion_tfidf.txt"


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"No existe {rel(INPUT_PATH)}")

    recommendations = pd.read_csv(INPUT_PATH)
    required = [
        "id_perfil",
        "nombre_perfil",
        "rank",
        "id_documento",
        "fuente",
        "seccion",
        "score_similitud",
    ]
    missing = [column for column in required if column not in recommendations.columns]
    if missing:
        raise ValueError(f"Faltan columnas: {', '.join(missing)}")

    grouped = recommendations.groupby(["id_perfil", "nombre_perfil"], dropna=False)
    evaluation = grouped.agg(
        score_medio=("score_similitud", "mean"),
        score_maximo=("score_similitud", "max"),
        score_minimo_top10=("score_similitud", "min"),
        diversidad_fuentes=("fuente", "nunique"),
        diversidad_secciones=("seccion", "nunique"),
        total_recomendaciones=("id_documento", "count"),
    ).reset_index()

    repeated_docs = recommendations.groupby("id_documento")["id_perfil"].nunique()
    repeated_docs = repeated_docs[repeated_docs > 1].sort_values(ascending=False)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    evaluation.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    evaluation.to_excel(OUTPUT_XLSX, index=False)

    report_lines = [
        "Informe de evaluacion tecnica del recomendador TF-IDF",
        "=" * 55,
        "",
        "Importante:",
        "- Esto no es una evaluacion con usuarios reales.",
        "- Es una evaluacion tecnica y exploratoria.",
        "- Sirve como linea base antes de comparar con embeddings.",
        "",
        f"Perfiles evaluados: {evaluation['id_perfil'].nunique()}",
        f"Recomendaciones analizadas: {len(recommendations)}",
        f"Documentos repetidos entre perfiles: {len(repeated_docs)}",
        "",
        "Metricas por perfil:",
        evaluation.to_string(index=False),
        "",
        "Documentos repetidos entre perfiles:",
        repeated_docs.to_string() if not repeated_docs.empty else "Ninguno",
    ]
    REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")

    print("\n".join(report_lines))
    print(f"\nCSV generado: {rel(OUTPUT_CSV)}")
    print(f"Excel generado: {rel(OUTPUT_XLSX)}")
    print(f"Informe generado: {rel(REPORT_PATH)}")


if __name__ == "__main__":
    main()
