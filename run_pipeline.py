"""Ejecuta el pipeline completo del recomendador TF-IDF por fases."""

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
]


def main() -> None:
    for phase in PHASES:
        print("\n" + "=" * 70)
        print(f"Ejecutando fase: {phase}")
        print("=" * 70)

        result = subprocess.run([sys.executable, phase], cwd=ROOT)
        if result.returncode != 0:
            raise SystemExit(f"La fase {phase} ha fallado. Pipeline detenido.")

    print("\nPipeline completado correctamente.")
    print("\nArchivos generados:")
    for file_name in GENERATED_FILES:
        path = ROOT / file_name
        status = "OK" if path.exists() else "NO ENCONTRADO"
        print(f"- {file_name}: {status}")


if __name__ == "__main__":
    main()
