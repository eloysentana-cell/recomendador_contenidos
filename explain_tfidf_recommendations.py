"""Explica recomendaciones TF-IDF mediante terminos compartidos relevantes."""

from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer


ROOT = Path(__file__).resolve().parent
CORPUS_PATH = ROOT / "data" / "processed" / "corpus_recomendador.csv"
PROFILES_PATH = ROOT / "data" / "processed" / "profile_queries.csv"
RECOMMENDATIONS_PATH = ROOT / "outputs" / "recomendaciones_tfidf.csv"
OUTPUT_CSV = ROOT / "outputs" / "recomendaciones_tfidf_explicadas.csv"
OUTPUT_XLSX = ROOT / "outputs" / "recomendaciones_tfidf_explicadas.xlsx"


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def clean(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).split()).strip()


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    for path in [CORPUS_PATH, PROFILES_PATH, RECOMMENDATIONS_PATH]:
        if not path.exists():
            raise FileNotFoundError(f"No existe {rel(path)}")

    docs = pd.read_csv(CORPUS_PATH)
    profiles = pd.read_csv(PROFILES_PATH)
    recommendations = pd.read_csv(RECOMMENDATIONS_PATH)

    docs = docs.copy()
    docs["num_caracteres"] = pd.to_numeric(docs["num_caracteres"], errors="coerce").fillna(0)
    docs["texto_modelo"] = (
        docs["titulo"].map(clean)
        + " "
        + docs["seccion"].map(clean)
        + " "
        + docs["texto"].map(clean)
    ).map(clean)
    docs = docs.loc[docs["num_caracteres"] > 300].reset_index(drop=True)

    profiles = profiles.copy()
    profiles["texto_perfil"] = profiles["texto_perfil"].map(clean)
    return docs, profiles, recommendations


def build_vectorizer(texts: list[str]) -> tuple[TfidfVectorizer, object]:
    try:
        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words=None,
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.85,
        )
        matrix = vectorizer.fit_transform(texts)
    except ValueError:
        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words=None,
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.85,
        )
        matrix = vectorizer.fit_transform(texts)
    return vectorizer, matrix


def top_shared_terms(profile_vector, doc_vector, feature_names, top_n: int = 12) -> str:
    """Selecciona terminos con peso TF-IDF en perfil y documento."""
    shared = profile_vector.multiply(doc_vector)
    if shared.nnz == 0:
        return ""

    coo = shared.tocoo()
    ranked = sorted(zip(coo.col, coo.data), key=lambda item: item[1], reverse=True)
    terms = [feature_names[index] for index, _ in ranked[:top_n]]
    return "; ".join(terms)


def main() -> None:
    docs, profiles, recommendations = load_data()

    doc_texts = docs["texto_modelo"].tolist()
    profile_texts = profiles["texto_perfil"].tolist()
    vectorizer, matrix = build_vectorizer(doc_texts + profile_texts)
    feature_names = vectorizer.get_feature_names_out()

    doc_matrix = matrix[: len(docs)]
    profile_matrix = matrix[len(docs) :]

    doc_index = {row["id_documento"]: idx for idx, row in docs.iterrows()}
    profile_index = {row["id_perfil"]: idx for idx, row in profiles.iterrows()}

    explanations = []
    for _, row in recommendations.iterrows():
        doc_idx = doc_index.get(row["id_documento"])
        profile_idx = profile_index.get(row["id_perfil"])
        if doc_idx is None or profile_idx is None:
            explanations.append("")
            continue
        explanations.append(
            top_shared_terms(profile_matrix[profile_idx], doc_matrix[doc_idx], feature_names)
        )

    explained = recommendations.copy()
    explained["terminos_explicativos"] = explanations

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    explained.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    explained.to_excel(OUTPUT_XLSX, index=False)

    print(f"Recomendaciones explicadas: {len(explained)}")
    print(f"CSV generado: {rel(OUTPUT_CSV)}")
    print(f"Excel generado: {rel(OUTPUT_XLSX)}")


if __name__ == "__main__":
    main()
