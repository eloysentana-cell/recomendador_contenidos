"""Valida la calidad minima del corpus documental del recomendador."""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
CORPUS_PATH = ROOT / "data" / "processed" / "corpus_recomendador.csv"
REPORT_PATH = ROOT / "outputs" / "informe_validacion_corpus.txt"

REQUIRED_COLUMNS = [
    "id_documento",
    "titulo",
    "fuente",
    "seccion",
    "tipo_archivo",
    "ruta_local",
    "texto",
    "num_caracteres",
]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def build_report(df: pd.DataFrame) -> str:
    empty_docs = df.loc[df["num_caracteres"] == 0, ["id_documento", "titulo", "fuente", "seccion"]]
    short_docs = df.loc[
        (df["num_caracteres"] > 0) & (df["num_caracteres"] < 300),
        ["id_documento", "titulo", "fuente", "seccion", "num_caracteres"],
    ]
    duplicated_titles = df.loc[
        df["titulo"].duplicated(keep=False),
        ["id_documento", "titulo", "fuente", "seccion"],
    ].sort_values("titulo")

    lines = [
        "Informe de validacion del corpus",
        "=" * 35,
        f"Numero total de documentos: {len(df)}",
        "",
        "Documentos por fuente:",
        df["fuente"].value_counts(dropna=False).to_string(),
        "",
        "Documentos por seccion:",
        df["seccion"].value_counts(dropna=False).to_string(),
        "",
        "Documentos por tipo_archivo:",
        df["tipo_archivo"].value_counts(dropna=False).to_string(),
        "",
        f"Documentos vacios: {len(empty_docs)}",
        empty_docs.to_string(index=False) if not empty_docs.empty else "Ninguno",
        "",
        f"Documentos con menos de 300 caracteres: {len(short_docs)}",
        short_docs.to_string(index=False) if not short_docs.empty else "Ninguno",
        "",
        f"Documentos duplicados por titulo: {len(duplicated_titles)}",
        duplicated_titles.to_string(index=False) if not duplicated_titles.empty else "Ninguno",
        "",
        "Criterios minimos para continuar:",
        f"- Mas de 100 documentos: {'OK' if len(df) > 100 else 'NO'}",
        f"- Hay documentos de CEEI Elche: {'OK' if (df['fuente'] == 'CEEI Elche').any() else 'NO'}",
        f"- Hay documentos de CEEI Valencia: {'OK' if (df['fuente'] == 'CEEI Valencia').any() else 'NO'}",
        f"- Mayoria con texto: {'OK' if (df['num_caracteres'] > 0).mean() > 0.5 else 'NO'}",
        "- Documentos vacios identificados: OK",
    ]
    return "\n".join(lines)


def main() -> None:
    if not CORPUS_PATH.exists():
        raise FileNotFoundError(f"No existe {rel(CORPUS_PATH)}. Ejecuta primero build_corpus_recomendador.py")

    df = pd.read_csv(CORPUS_PATH)
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas obligatorias: {', '.join(missing)}")

    df = df.copy()
    df["num_caracteres"] = pd.to_numeric(df["num_caracteres"], errors="coerce").fillna(0).astype(int)

    report = build_report(df)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")

    print(report)
    print(f"\nInforme guardado en: {rel(REPORT_PATH)}")


if __name__ == "__main__":
    main()
