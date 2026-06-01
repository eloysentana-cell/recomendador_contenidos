"""Demostrador web local para recomendaciones semanticas."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import recommend_from_text as recommender  # noqa: E402


MODEL_NAME = recommender.MODEL_NAME
recommend_profiles = recommender.recommend_profiles
recommend_documents = getattr(recommender, "recommend_documents", recommender.recommend)


DEFAULT_QUERY = (
    "Soy una emprendedora rural que quiere montar una pequena empresa "
    "agroalimentaria con impacto territorial y necesito ayudas publicas"
)
WORKER_CACHE_VERSION = "utf8_v2"


@st.cache_data(show_spinner=False)
def load_document_embedding_map() -> dict[str, str]:
    parquet_path = ROOT / "data" / "embeddings" / "document_embeddings.parquet"
    csv_path = ROOT / "data" / "embeddings" / "document_embeddings.csv"
    if parquet_path.exists():
        df = pd.read_parquet(parquet_path, columns=["id_documento", "embedding"])
    else:
        df = pd.read_csv(csv_path, usecols=["id_documento", "embedding"])
    return dict(zip(df["id_documento"].astype(str), df["embedding"].astype(str)))


@st.cache_data(show_spinner=False)
def get_vector_dimension() -> str:
    parquet_path = ROOT / "data" / "embeddings" / "document_embeddings.parquet"
    csv_path = ROOT / "data" / "embeddings" / "document_embeddings.csv"
    if parquet_path.exists():
        df = pd.read_parquet(parquet_path, columns=["dimension_embedding"])
    elif csv_path.exists():
        df = pd.read_csv(csv_path, usecols=["dimension_embedding"])
    else:
        return "no disponible"
    if df.empty:
        return "no disponible"
    return str(df["dimension_embedding"].iloc[0])


def show_table(df: pd.DataFrame, columns: list[str]) -> None:
    existing = [column for column in columns if column in df.columns]
    if existing:
        st.dataframe(df[existing], use_container_width=True, hide_index=True)


@st.cache_data(show_spinner=False)
def run_recommendation_worker(
    query_text: str,
    top_k: int,
    cache_version: str = WORKER_CACHE_VERSION,
) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    """Ejecuta la recomendacion fuera del proceso Streamlit."""
    _ = cache_version
    command = [
        sys.executable,
        str(ROOT / "recommend_from_text_worker.py"),
        "--query",
        query_text,
        "--top-k",
        str(top_k),
    ]
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )

    output = result.stdout.strip()
    if not output:
        error = result.stderr.strip() or f"El worker termino con codigo {result.returncode}."
        return pd.DataFrame(), pd.DataFrame(), error

    try:
        payload = json.loads(output.splitlines()[-1])
    except json.JSONDecodeError as exc:
        detail = result.stderr.strip() or output[-1000:]
        return pd.DataFrame(), pd.DataFrame(), f"No se pudo leer la salida JSON: {exc}. {detail}"

    error = str(payload.get("error") or "")
    if result.returncode != 0 and not error:
        error = result.stderr.strip() or f"El worker termino con codigo {result.returncode}."

    profiles_df = pd.DataFrame(payload.get("profiles") or [])
    docs_df = pd.DataFrame(payload.get("documents") or [])
    return profiles_df, docs_df, error


st.set_page_config(
    page_title="Recomendador de contenidos para emprendedores",
    layout="wide",
)

st.title("Recomendador de contenidos para emprendedores")
st.write(
    "Describe tu perfil emprendedor o necesidad y el sistema recomendara documentos "
    "del corpus CEEI usando embeddings locales."
)

with st.sidebar:
    st.subheader("Informacion tecnica")
    st.write(f"Modelo usado: `{MODEL_NAME}`")
    st.write(f"Dimension del vector: `{get_vector_dimension()}`")
    st.caption("Los embeddings completos estan almacenados en data/embeddings/.")

query_text = st.text_area(
    "Describe tu perfil emprendedor o necesidad",
    value=DEFAULT_QUERY,
    height=140,
)
top_k = st.slider("Numero de documentos", min_value=3, max_value=20, value=10)
show_full_vectors = st.checkbox("Mostrar vectores completos", value=False)

if st.button("Recomendar documentos", type="primary"):
    query_text = query_text.strip()
    if not query_text:
        st.warning("Introduce una descripción del perfil emprendedor o necesidad.")
        st.stop()

    try:
        with st.spinner("Calculando recomendaciones..."):
            profiles_df, docs_df, worker_error = run_recommendation_worker(query_text, top_k)
    except Exception as exc:
        st.error(f"No se pudieron calcular las recomendaciones: {exc}")
        st.stop()

    if worker_error:
        st.error(f"No se pudieron calcular las recomendaciones: {worker_error}")
        st.stop()

    st.subheader("Perfiles predefinidos mas parecidos")
    if profiles_df.empty:
        st.warning("No se encontraron perfiles similares para la consulta.")
    else:
        show_table(profiles_df, ["rank", "nombre_perfil", "score_similitud"])

    st.subheader("Documentos recomendados")
    if docs_df.empty:
        st.warning("No se encontraron documentos recomendados para la consulta.")
    else:
        show_table(
            docs_df,
            [
                "rank",
                "titulo",
                "fuente",
                "seccion",
                "tipo_archivo",
                "score_similitud",
                "ruta_local",
                "url_origen",
            ],
        )

        st.subheader("Detalle de documentos")
        full_embedding_map = load_document_embedding_map() if show_full_vectors else {}
        for _, row in docs_df.iterrows():
            title = f"{row['rank']}. {row['titulo']} ({row['score_similitud']})"
            with st.expander(title):
                st.write(row.get("texto_muestra", ""))
                st.code(row.get("embedding_documento_preview", ""), language="json")
                if show_full_vectors:
                    st.code(full_embedding_map.get(str(row["id_documento"]), ""), language="json")

    st.subheader("Informacion tecnica de coincidencia")
    st.write(f"Modelo usado: `{MODEL_NAME}`")
    st.write(f"Dimension del vector: `{get_vector_dimension()}`")
    if not docs_df.empty:
        st.write("Embedding preview del texto introducido:")
        st.code(docs_df.iloc[0]["embedding_query_preview"], language="json")

    st.write("Perfiles con scores")
    if not profiles_df.empty:
        show_table(
            profiles_df,
            [
                "rank",
                "id_perfil",
                "nombre_perfil",
                "score_similitud",
                "embedding_query_preview",
                "embedding_perfil_preview",
            ],
        )

    st.write("Documentos con scores")
    if not docs_df.empty:
        show_table(
            docs_df,
            [
                "rank",
                "id_documento",
                "titulo",
                "score_similitud",
                "embedding_query_preview",
                "embedding_documento_preview",
            ],
        )

    st.info(
        "Por legibilidad se muestran previews de los vectores. Los embeddings completos "
        "estan almacenados en data/embeddings/."
    )
else:
    st.caption("Pulsa el boton para calcular recomendaciones con embeddings locales.")
