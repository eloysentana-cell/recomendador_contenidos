"""Ejecuta el pipeline completo del recomendador por fases."""

import argparse
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent

PHASES = [
    "build_corpus_recomendador.py",
    "validate_corpus.py",
    "build_profile_queries.py",
    "recommender_tfidf.py",
    "explain_tfidf_recommendations.py",
    "evaluate_tfidf_recommender.py",
]

SEMANTIC_PHASES = [
    "build_profile_embeddings.py",
    "recommend_embeddings_by_profile.py",
    "compare_tfidf_vs_embeddings.py",
]

GENERATED_FILES = [
    "data/processed/corpus_recomendador.csv",
    "outputs/corpus_recomendador.xlsx",
    "outputs/informe_validacion_corpus.txt",
    "data/processed/profile_queries.csv",
    "outputs/recomendaciones_tfidf.csv",
    "outputs/recomendaciones_tfidf.xlsx",
    "outputs/recomendaciones_tfidf_explicadas.csv",
    "outputs/recomendaciones_tfidf_explicadas.xlsx",
    "outputs/evaluacion_tfidf.csv",
    "outputs/evaluacion_tfidf.xlsx",
    "outputs/informe_evaluacion_tfidf.txt",
    "data/embeddings/document_embeddings.parquet",
    "data/embeddings/profile_embeddings.parquet",
    "outputs/recomendaciones_embeddings_perfiles.csv",
    "outputs/comparacion_tfidf_embeddings.csv",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ejecuta el pipeline del recomendador.")
    parser.add_argument(
        "--rebuild-embeddings",
        action="store_true",
        help="Regenera tambien data/embeddings/document_embeddings.parquet.",
    )
    return parser.parse_args()


def run_phase(phase: str) -> None:
    print("\n" + "=" * 70)
    print(f"Ejecutando fase: {phase}")
    print("=" * 70)

    result = subprocess.run([sys.executable, phase], cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(f"La fase {phase} ha fallado. Pipeline detenido.")


def main() -> None:
    args = parse_args()

    for phase in PHASES:
        run_phase(phase)

    document_embeddings = ROOT / "data" / "embeddings" / "document_embeddings.parquet"
    if args.rebuild_embeddings or not document_embeddings.exists():
        run_phase("build_document_embeddings.py")
    else:
        print("\n" + "=" * 70)
        print("Saltando fase: build_document_embeddings.py")
        print("=" * 70)
        print("Ya existe data/embeddings/document_embeddings.parquet.")
        print("Usa --rebuild-embeddings para regenerarlo.")

    for phase in SEMANTIC_PHASES:
        run_phase(phase)

    print("\nPipeline completado correctamente.")
    print("\nArchivos generados:")
    for file_name in GENERATED_FILES:
        path = ROOT / file_name
        status = "OK" if path.exists() else "NO ENCONTRADO"
        print(f"- {file_name}: {status}")


if __name__ == "__main__":
    main()
