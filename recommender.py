"""
Motor de recomendacion content-based para perfiles emprendedores.

Calcula similitud coseno con TF-IDF y aplica una politica de confianza para
evitar presentar como fiables perfiles que no encajan bien con el corpus.
"""

from __future__ import annotations

import csv
import json
import math
import os
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HIGH_CONFIDENCE_THRESHOLD = 0.70
MEDIUM_CONFIDENCE_THRESHOLD = 0.45
LOW_CONFIDENCE_THRESHOLD = 0.45

LOW_MATCH_STATUS = "low_match_profile"
OK_STATUS = "ok"
LOW_MATCH_MESSAGE = (
    "No se han encontrado documentos con una coincidencia suficientemente alta "
    "para este perfil."
)
LOW_MATCH_SUGGESTIONS = [
    "Amplía la descripción del perfil emprendedor.",
    "Incluye sector, fase del proyecto, necesidades concretas y objetivos.",
    "Explora contenidos generales del ecosistema emprendedor.",
]

DEFAULT_CORPUS_PATH = Path("data/processed/corpus_documental.csv")
DEFAULT_FEEDBACK_PATH = Path("data/feedback/low_match_profiles.csv")
TOKEN_PATTERN = re.compile(r"(?u)\b\w\w+\b")
MAX_VECTOR_TERMS = 20
SPANISH_STOPWORDS = {
    "a",
    "al",
    "algo",
    "algunas",
    "algunos",
    "ante",
    "antes",
    "aquel",
    "aquella",
    "aquellas",
    "aquello",
    "aquellos",
    "asi",
    "bajo",
    "cada",
    "como",
    "con",
    "contra",
    "cual",
    "cuando",
    "de",
    "del",
    "desde",
    "donde",
    "durante",
    "e",
    "el",
    "ella",
    "ellas",
    "ello",
    "ellos",
    "en",
    "entre",
    "era",
    "eran",
    "eres",
    "es",
    "esa",
    "esas",
    "ese",
    "eso",
    "esos",
    "esta",
    "estaba",
    "estaban",
    "estado",
    "estais",
    "estamos",
    "estan",
    "estar",
    "estas",
    "este",
    "esto",
    "estos",
    "estoy",
    "fue",
    "fueron",
    "ha",
    "habia",
    "han",
    "has",
    "hasta",
    "hay",
    "la",
    "las",
    "le",
    "les",
    "lo",
    "los",
    "mas",
    "me",
    "mi",
    "mis",
    "muy",
    "ni",
    "no",
    "nos",
    "nosotras",
    "nosotros",
    "o",
    "os",
    "otra",
    "otras",
    "otro",
    "otros",
    "para",
    "pero",
    "por",
    "porque",
    "que",
    "quien",
    "se",
    "ser",
    "si",
    "sin",
    "sobre",
    "sois",
    "somos",
    "son",
    "su",
    "sus",
    "te",
    "teneis",
    "tenemos",
    "tener",
    "tengo",
    "ti",
    "tu",
    "tus",
    "un",
    "una",
    "unas",
    "uno",
    "unos",
    "vosotras",
    "vosotros",
    "y",
    "ya",
    "yo",
}
csv.field_size_limit(sys.maxsize)


def classify_confidence(score: float) -> str:
    if score >= HIGH_CONFIDENCE_THRESHOLD:
        return "high_confidence"

    if score >= MEDIUM_CONFIDENCE_THRESHOLD:
        return "medium_confidence"

    return "low_confidence"


def load_corpus(corpus_path: str | os.PathLike[str] = DEFAULT_CORPUS_PATH) -> list[dict[str, str]]:
    path = Path(corpus_path)

    if not path.exists():
        raise FileNotFoundError(f"No se ha encontrado el corpus: {path}")

    with path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None or "texto_recomendador" not in reader.fieldnames:
            raise ValueError("El corpus debe incluir la columna texto_recomendador.")

        rows: list[dict[str, str]] = []
        for index, row in enumerate(reader, start=1):
            normalized = {key: str(value or "") for key, value in row.items()}
            normalized.setdefault("id", str(index))
            normalized.setdefault("titulo", "")
            normalized.setdefault("url_principal", "")
            normalized.setdefault("url", "")
            normalized["texto_recomendador"] = normalized.get("texto_recomendador", "")
            rows.append(normalized)

    return rows


def build_recommendations(
    profile_text: str,
    corpus: list[dict[str, str]],
    top_k: int = 5,
) -> tuple[list[dict[str, Any]], float, list[dict[str, float]]]:
    if len(corpus) == 0 or top_k <= 0:
        return [], 0.0, []

    profile_text = str(profile_text or "").strip()
    documents = [row.get("texto_recomendador", "") for row in corpus]

    if profile_text == "" or all(document.strip() == "" for document in documents):
        return [], 0.0, []

    scores, profile_vector, document_vectors = calculate_tfidf_cosine_scores(
        profile_text,
        documents,
    )
    ranked_positions = sorted(range(len(scores)), key=lambda index: scores[index], reverse=True)[:top_k]
    recommendations: list[dict[str, Any]] = []

    for position in ranked_positions:
        row = corpus[int(position)]
        score = float(scores[int(position)])
        recommendations.append(
            {
                "document_id": str(row.get("id", "")),
                "title": str(row.get("titulo", "")),
                "url": str(row.get("url_principal", "") or row.get("url", "")),
                "score": round(score, 4),
                "confidence_level": classify_confidence(score),
                "vector": serialize_vector(document_vectors[int(position)]),
            }
        )

    max_score = float(scores[ranked_positions[0]]) if len(ranked_positions) else 0.0
    return recommendations, round(max_score, 4), serialize_vector(profile_vector)


def calculate_tfidf_cosine_scores(
    profile_text: str,
    documents: list[str],
) -> tuple[list[float], dict[str, float], list[dict[str, float]]]:
    tokenized_texts = [tokenize(profile_text)] + [tokenize(document) for document in documents]
    document_frequencies: Counter[str] = Counter()

    for tokens in tokenized_texts:
        document_frequencies.update(set(tokens))

    total_texts = len(tokenized_texts)
    idf = {
        token: math.log((1 + total_texts) / (1 + frequency)) + 1
        for token, frequency in document_frequencies.items()
    }

    profile_vector = build_tfidf_vector(tokenized_texts[0], idf)
    document_vectors = [build_tfidf_vector(tokens, idf) for tokens in tokenized_texts[1:]]
    scores = [cosine(profile_vector, document_vector) for document_vector in document_vectors]

    return scores, profile_vector, document_vectors


def tokenize(text: str) -> list[str]:
    tokens = TOKEN_PATTERN.findall(str(text or "").lower())
    normalized_tokens = [normalize_token(token) for token in tokens]
    return [
        token
        for token in normalized_tokens
        if token and token not in SPANISH_STOPWORDS
    ]


def normalize_token(token: str) -> str:
    normalized = unicodedata.normalize("NFKD", token)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def build_tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    if not tokens:
        return {}

    counts = Counter(tokens)
    total = len(tokens)
    return {token: (count / total) * idf.get(token, 0.0) for token, count in counts.items()}


def serialize_vector(vector: dict[str, float], max_terms: int = MAX_VECTOR_TERMS) -> list[dict[str, float]]:
    sorted_terms = sorted(vector.items(), key=lambda item: item[1], reverse=True)[:max_terms]
    return [{"term": term, "weight": round(weight, 6)} for term, weight in sorted_terms]


def cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0

    shared_tokens = set(left).intersection(right)
    numerator = sum(left[token] * right[token] for token in shared_tokens)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))

    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0

    return numerator / (left_norm * right_norm)


def recommend_for_profile(
    profile_text: str,
    corpus_path: str | os.PathLike[str] = DEFAULT_CORPUS_PATH,
    top_k: int = 5,
    feedback_path: str | os.PathLike[str] = DEFAULT_FEEDBACK_PATH,
    log_low_match: bool = True,
) -> dict[str, Any]:
    corpus = load_corpus(corpus_path)
    recommendations, max_score, profile_vector = build_recommendations(
        profile_text,
        corpus,
        top_k=top_k,
    )

    if max_score < LOW_CONFIDENCE_THRESHOLD:
        exploratory_recommendations = [
            {**item, "recommendation_type": "exploratory"} for item in recommendations
        ]
        response = {
            "status": LOW_MATCH_STATUS,
            "max_score": max_score,
            "message": LOW_MATCH_MESSAGE,
            "suggestions": LOW_MATCH_SUGGESTIONS,
            "profile_vector": profile_vector,
            "recommendations": exploratory_recommendations,
        }

        if log_low_match:
            log_low_match_profile(
                profile_text=profile_text,
                max_score=max_score,
                recommendations=exploratory_recommendations,
                feedback_path=feedback_path,
            )

        return response

    return {
        "status": OK_STATUS,
        "max_score": max_score,
        "profile_vector": profile_vector,
        "recommendations": recommendations,
    }


def log_low_match_profile(
    profile_text: str,
    max_score: float,
    recommendations: list[dict[str, Any]],
    feedback_path: str | os.PathLike[str] = DEFAULT_FEEDBACK_PATH,
) -> None:
    path = Path(feedback_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "profile_text": str(profile_text or ""),
        "max_score": max_score,
        "status": LOW_MATCH_STATUS,
        "top_document_ids": json.dumps(
            [item.get("document_id", "") for item in recommendations],
            ensure_ascii=False,
        ),
        "top_scores": json.dumps(
            [item.get("score", 0.0) for item in recommendations],
            ensure_ascii=False,
        ),
    }
    file_exists = path.exists()

    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(row.keys()))

        if not file_exists:
            writer.writeheader()

        writer.writerow(row)


if __name__ == "__main__":
    example = "startup en fase de escalado internacional busca financiacion y softlanding"
    result = recommend_for_profile(example)
    print(json.dumps(result, ensure_ascii=False, indent=2))
