"""Genera tablas de caracterizacion de perfiles y documentos para revision."""

from pathlib import Path
import json

import pandas as pd


ROOT = Path(__file__).resolve().parent
PROFILES_PATH = ROOT / "data" / "perfiles" / "perfiles_emprendedores.json"
CORPUS_PATH = ROOT / "data" / "processed" / "corpus_recomendador.csv"
OUTPUTS = ROOT / "outputs"

PROFILES_CSV = OUTPUTS / "perfiles_caracterizados.csv"
PROFILES_XLSX = OUTPUTS / "perfiles_caracterizados.xlsx"
DOCS_CSV = OUTPUTS / "documentos_caracterizados_muestra.csv"
DOCS_XLSX = OUTPUTS / "documentos_caracterizados_muestra.xlsx"
REPORT_PATH = OUTPUTS / "informe_caracterizacion.txt"


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def clean(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def flatten(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " | ".join(clean(item) for item in value if clean(item))
    if isinstance(value, dict):
        return " | ".join(f"{key}: {flatten(item)}" for key, item in value.items() if flatten(item))
    return clean(value)


def build_profile_text(profile: dict) -> str:
    fields = [
        "nombre",
        "fase_emprendedora",
        "perfil_funcional",
        "necesidades_prioritarias",
        "intenciones_busqueda",
        "palabras_clave_semanticas",
        "descripcion_embedding",
    ]
    return clean(" ".join(flatten(profile.get(field)) for field in fields if flatten(profile.get(field))))


def build_profiles_table() -> pd.DataFrame:
    profiles = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    if not isinstance(profiles, list):
        raise ValueError("data/perfiles/perfiles_emprendedores.json debe contener una lista.")

    records = []
    for index, profile in enumerate(profiles, start=1):
        records.append(
            {
                "id_perfil": clean(profile.get("id")) or f"perfil_{index:03d}",
                "nombre_perfil": clean(profile.get("nombre")),
                "fase_emprendedora": clean(profile.get("fase_emprendedora")),
                "necesidades_resumen": flatten(profile.get("necesidades_prioritarias")),
                "intenciones_resumen": flatten(profile.get("intenciones_busqueda")),
                "palabras_clave": flatten(profile.get("palabras_clave_semanticas")),
                "texto_caracterizacion": build_profile_text(profile),
            }
        )
    return pd.DataFrame(records)


def sample_documents(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["num_caracteres"] = pd.to_numeric(df["num_caracteres"], errors="coerce").fillna(0).astype(int)

    useful = df.loc[df["num_caracteres"] >= 300]
    insufficient = df.loc[df["num_caracteres"] < 300]

    samples = []
    for source in ["CEEI Elche", "CEEI Valencia"]:
        source_docs = useful.loc[useful["fuente"] == source].sort_values(
            ["seccion", "titulo"], kind="stable"
        )
        samples.append(source_docs.head(20))

    if not insufficient.empty:
        samples.append(insufficient.head(10))

    sample = pd.concat(samples, ignore_index=True).drop_duplicates("id_documento")
    sample["texto_caracterizacion_muestra"] = sample["texto_recomendador"].fillna("").map(
        lambda value: clean(value)[:1000]
    )

    columns = [
        "id_documento",
        "titulo",
        "fuente",
        "seccion",
        "tipo_archivo",
        "num_caracteres",
        "estado_extraccion",
        "texto_caracterizacion_muestra",
    ]
    return sample[columns]


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    if not PROFILES_PATH.exists():
        raise FileNotFoundError(f"No existe {rel(PROFILES_PATH)}")
    if not CORPUS_PATH.exists():
        raise FileNotFoundError(f"No existe {rel(CORPUS_PATH)}")

    profiles_df = build_profiles_table()
    corpus_df = pd.read_csv(CORPUS_PATH)
    docs_sample = sample_documents(corpus_df)

    profiles_df.to_csv(PROFILES_CSV, index=False, encoding="utf-8-sig")
    profiles_df.to_excel(PROFILES_XLSX, index=False)
    docs_sample.to_csv(DOCS_CSV, index=False, encoding="utf-8-sig")
    docs_sample.to_excel(DOCS_XLSX, index=False)

    lines = [
        "Informe de caracterizacion",
        "=" * 28,
        f"Numero de perfiles: {len(profiles_df)}",
        f"Numero total de documentos: {len(corpus_df)}",
        "",
        "Documentos por fuente:",
        corpus_df["fuente"].value_counts(dropna=False).to_string(),
        "",
        "Documentos por estado_extraccion:",
        corpus_df["estado_extraccion"].value_counts(dropna=False).to_string(),
        "",
        "Archivos generados:",
        f"- {rel(PROFILES_CSV)}",
        f"- {rel(PROFILES_XLSX)}",
        f"- {rel(DOCS_CSV)}",
        f"- {rel(DOCS_XLSX)}",
        f"- {rel(REPORT_PATH)}",
    ]
    report = "\n".join(lines)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
