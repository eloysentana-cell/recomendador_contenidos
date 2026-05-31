"""Genera recomendaciones content-based con TF-IDF y similitud coseno."""

from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


ROOT = Path(__file__).resolve().parent
CORPUS_PATH = ROOT / "data" / "processed" / "corpus_recomendador.csv"
PROFILES_PATH = ROOT / "data" / "processed" / "profile_queries.csv"
OUTPUT_CSV = ROOT / "outputs" / "recomendaciones_tfidf.csv"
OUTPUT_XLSX = ROOT / "outputs" / "recomendaciones_tfidf.xlsx"
TOP_N = 10


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def clean(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).split()).strip()


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"No existe {rel(path)}")


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    require_file(CORPUS_PATH)
    require_file(PROFILES_PATH)

    docs = pd.read_csv(CORPUS_PATH)
    profiles = pd.read_csv(PROFILES_PATH)

    required_docs = [
        "id_documento",
        "titulo",
        "fuente",
        "seccion",
        "tipo_archivo",
        "ruta_local",
        "texto",
        "num_caracteres",
    ]
    required_profiles = ["id_perfil", "nombre_perfil", "texto_perfil"]

    missing_docs = [column for column in required_docs if column not in docs.columns]
    missing_profiles = [column for column in required_profiles if column not in profiles.columns]
    if missing_docs:
        raise ValueError(f"Faltan columnas en corpus: {', '.join(missing_docs)}")
    if missing_profiles:
        raise ValueError(f"Faltan columnas en perfiles: {', '.join(missing_profiles)}")

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
    profiles = profiles.loc[profiles["texto_perfil"] != ""].reset_index(drop=True)

    if docs.empty:
        raise ValueError("No hay documentos con num_caracteres > 300.")
    if profiles.empty:
        raise ValueError("No hay perfiles con texto_perfil.")

    return docs, profiles


def build_vectorizer(texts: list[str]) -> tuple[TfidfVectorizer, object]:
    """Aplica min_df=2 y cae a min_df=1 si el vocabulario queda vacio."""
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


def recommend(docs: pd.DataFrame, profiles: pd.DataFrame) -> pd.DataFrame:
    doc_texts = docs["texto_modelo"].tolist()
    profile_texts = profiles["texto_perfil"].tolist()
    all_texts = doc_texts + profile_texts

    _, matrix = build_vectorizer(all_texts)
    doc_matrix = matrix[: len(docs)]
    profile_matrix = matrix[len(docs) :]
    similarity = cosine_similarity(profile_matrix, doc_matrix)

    records = []
    for profile_idx, profile in profiles.iterrows():
        scores = similarity[profile_idx]
        ordered_doc_indices = scores.argsort()[::-1][:TOP_N]

        print(f"\nTop 5 para {profile['nombre_perfil']}:")
        for rank, doc_idx in enumerate(ordered_doc_indices, start=1):
            doc = docs.iloc[doc_idx]
            score = float(scores[doc_idx])
            if rank <= 5:
                print(f"{rank}. {doc['titulo']} ({doc['fuente']}, {doc['seccion']}) - {score:.4f}")

            records.append(
                {
                    "id_perfil": profile["id_perfil"],
                    "nombre_perfil": profile["nombre_perfil"],
                    "rank": rank,
                    "id_documento": doc["id_documento"],
                    "titulo": doc["titulo"],
                    "fuente": doc["fuente"],
                    "seccion": doc["seccion"],
                    "tipo_archivo": doc["tipo_archivo"],
                    "score_similitud": round(score, 6),
                    "ruta_local": doc["ruta_local"],
                }
            )

    return pd.DataFrame(records)


def main() -> None:
    docs, profiles = load_inputs()
    print(f"Documentos candidatos: {len(docs)}")
    print(f"Perfiles: {len(profiles)}")

    recommendations = recommend(docs, profiles)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    recommendations.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    recommendations.to_excel(OUTPUT_XLSX, index=False)

    print(f"\nCSV generado: {rel(OUTPUT_CSV)}")
    print(f"Excel generado: {rel(OUTPUT_XLSX)}")


if __name__ == "__main__":
    main()
