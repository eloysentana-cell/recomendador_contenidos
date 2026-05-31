"""Demostrador web local para recomendaciones semanticas."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from recommend_from_text import MODEL_NAME, recommend, recommend_profiles  # noqa: E402


DEFAULT_QUERY = (
    "Soy una emprendedora rural que quiere montar una pequena empresa "
    "agroalimentaria con impacto territorial y necesito ayudas publicas"
)


@st.cache_data(show_spinner=False)
def load_document_embedding_map() -> dict[str, str]:
    embeddings_path = ROOT / "data" / "embeddings" / "document_embeddings.parquet"
    df = pd.read_parquet(embeddings_path, columns=["id_documento", "embedding"])
    return dict(zip(df["id_documento"].astype(str), df["embedding"].astype(str)))


def show_table(df: pd.DataFrame, columns: list[str]) -> None:
    existing = [column for column in columns if column in df.columns]
    st.dataframe(df[existing], use_container_width=True, hide_index=True)


st.set_page_config(
    page_title="Recomendador de contenidos para emprendedores",
    layout="wide",
)

st.title("Recomendador de contenidos para emprendedores")
st.write(
    "Describe tu perfil emprendedor o necesidad y el sistema recomendará documentos "
    "del corpus CEEI usando embeddings locales."
)

query_text = st.text_area(
    "Describe tu perfil emprendedor o necesidad",
    value=DEFAULT_QUERY,
    height=140,
)
top_k = st.slider("Numero de documentos", min_value=3, max_value=20, value=10)
show_full_vectors = st.checkbox("Mostrar vectores completos", value=False)

if st.button("Recomendar documentos", type="primary"):
    with st.spinner("Calculando similitudes semanticas..."):
        profiles_df = recommend_profiles(query_text, top_k=3)
        docs_df = recommend(query_text, top_k=top_k)

    st.subheader("Perfiles predefinidos mas parecidos")
    show_table(profiles_df, ["rank", "nombre_perfil", "score_similitud"])

    st.subheader("Documentos recomendados")
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
    st.write("Dimension del vector: `384`")
    if not docs_df.empty:
        st.write("Embedding preview del texto introducido:")
        st.code(docs_df.iloc[0]["embedding_query_preview"], language="json")

    st.write("Perfiles con scores")
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
    tech_columns = [
        "rank",
        "id_documento",
        "titulo",
        "score_similitud",
        "embedding_query_preview",
        "embedding_documento_preview",
    ]
    show_table(docs_df, tech_columns)

    st.info(
        "Por legibilidad se muestran previews de los vectores. Los embeddings completos "
        "estan almacenados en data/embeddings/."
    )
else:
    st.caption("Pulsa el boton para calcular recomendaciones con embeddings locales.")
