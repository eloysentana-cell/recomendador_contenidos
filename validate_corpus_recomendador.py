"""Valida el corpus consolidado del recomendador."""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
CORPUS_PATH = ROOT / "data" / "processed" / "corpus_recomendador.csv"
REPORT_PATH = ROOT / "outputs" / "informe_validacion_corpus_recomendador.txt"

REQUIRED_COLUMNS = [
    "id_documento",
    "titulo",
    "fuente",
    "seccion",
    "tipo_archivo",
    "ruta_local",
    "url_origen",
    "texto",
    "num_caracteres",
    "estado_extraccion",
    "texto_recomendador",
]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def table_or_none(df: pd.DataFrame) -> str:
    return df.to_string(index=False) if not df.empty else "Ninguno"


def main() -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not CORPUS_PATH.exists():
        raise FileNotFoundError(f"No existe {rel(CORPUS_PATH)}")
    if CORPUS_PATH.stat().st_size == 0:
        raise ValueError(f"{rel(CORPUS_PATH)} esta vacio.")

    df = pd.read_csv(CORPUS_PATH)
    if df.empty:
        raise ValueError("El corpus tiene cabecera pero no contiene filas.")

    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas obligatorias: {', '.join(missing)}")

    df = df.copy()
    df["num_caracteres"] = pd.to_numeric(df["num_caracteres"], errors="coerce").fillna(0).astype(int)

    useful_docs = int((df["num_caracteres"] >= 300).sum())
    if useful_docs == 0:
        raise ValueError("No hay documentos con texto util de al menos 300 caracteres.")

    zero_docs = df.loc[df["num_caracteres"] == 0, ["id_documento", "titulo", "fuente", "ruta_local"]]
    short_docs = df.loc[df["num_caracteres"] < 300, ["id_documento", "titulo", "fuente", "num_caracteres"]]
    dup_routes = df.loc[df["ruta_local"].duplicated(keep=False), ["id_documento", "ruta_local"]]
    dup_titles = df.loc[df["titulo"].duplicated(keep=False), ["id_documento", "titulo", "fuente", "seccion"]]
    preview = df[
        ["id_documento", "titulo", "fuente", "seccion", "tipo_archivo", "num_caracteres"]
    ].head(10)

    lines = [
        "Informe de validacion del corpus recomendador",
        "=" * 47,
        f"Archivo: {rel(CORPUS_PATH)}",
        f"Tamano bytes: {CORPUS_PATH.stat().st_size}",
        f"Numero total de documentos: {len(df)}",
        f"Documentos con texto util >= 300: {useful_docs}",
        "",
        "Conteo por fuente:",
        df["fuente"].value_counts(dropna=False).to_string(),
        "",
        "Conteo por tipo_archivo:",
        df["tipo_archivo"].value_counts(dropna=False).to_string(),
        "",
        "Conteo por seccion:",
        df["seccion"].value_counts(dropna=False).to_string(),
        "",
        "Conteo por estado_extraccion:",
        df["estado_extraccion"].value_counts(dropna=False).to_string(),
        "",
        f"Documentos con num_caracteres == 0: {len(zero_docs)}",
        table_or_none(zero_docs),
        "",
        f"Documentos con num_caracteres < 300: {len(short_docs)}",
        table_or_none(short_docs),
        "",
        f"Duplicados por ruta_local: {len(dup_routes)}",
        table_or_none(dup_routes),
        "",
        f"Duplicados por titulo: {len(dup_titles)}",
        table_or_none(dup_titles),
        "",
        "Primeras 10 filas:",
        preview.to_string(index=False),
    ]

    report = "\n".join(lines)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nInforme generado: {rel(REPORT_PATH)}")


if __name__ == "__main__":
    main()
