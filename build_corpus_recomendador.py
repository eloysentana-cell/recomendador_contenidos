"""
Construye un corpus documental unico para el recomendador.

El script recorre carpetas locales con documentos de CEEI Elche y CEEI
Valencia, extrae texto de PDF/TXT y genera una tabla reproducible para la
linea base TF-IDF.
"""

from pathlib import Path
import json
import re

import pandas as pd
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parent
DATA_PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
OUTPUT_CSV = DATA_PROCESSED / "corpus_recomendador.csv"
OUTPUT_XLSX = OUTPUTS / "corpus_recomendador.xlsx"
EXCEL_CELL_LIMIT = 32767

DOCUMENT_DIRS = [
    ROOT / "documentos_ceei_elche_PDF",
    ROOT / "documentos_ceei_valencia",
    ROOT / "documentos_ceei_elche",
    ROOT / "data" / "raw" / "ceei_valencia" / "txt",
]

SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "outputs",
}

ILLEGAL_EXCEL_CHARS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")


def clean_text(value: object) -> str:
    """Normaliza texto extraido para CSV/Excel sin alterar el documento fuente."""
    if value is None:
        return ""
    text = str(value)
    text = ILLEGAL_EXCEL_CHARS.sub(" ", text)
    return " ".join(text.replace("\r", " ").replace("\n", " ").split()).strip()


def relative_path(path: Path) -> str:
    """Devuelve rutas relativas al proyecto para evitar rutas absolutas."""
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def discover_files() -> list[Path]:
    """Localiza PDF y TXT dentro de las carpetas documentales conocidas."""
    files: list[Path] = []

    for base_dir in DOCUMENT_DIRS:
        if not base_dir.exists():
            continue

        for path in base_dir.rglob("*"):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.is_file() and path.suffix.lower() in {".pdf", ".txt"}:
                files.append(path)

    return sorted(set(files), key=lambda p: relative_path(p).lower())


def infer_source(path: Path) -> str:
    """Infiere la fuente documental a partir de la ruta local."""
    normalized = relative_path(path).lower()
    if "data/raw/ceei_valencia/txt" in normalized:
        return "CEEI Valencia"
    if "documentos_ceei_elche_pdf" in normalized or "documentos_ceei_elche" in normalized:
        return "CEEI Elche"
    if "documentos_ceei_valencia" in normalized:
        return "CEEI Valencia"
    return "Desconocida"


def infer_section(path: Path) -> str:
    """Usa la subcarpeta principal bajo la fuente como seccion documental."""
    if "data/raw/ceei_valencia/txt" in relative_path(path).lower():
        return "Fichas_HTML"

    for base_dir in DOCUMENT_DIRS:
        if not base_dir.exists():
            continue
        try:
            rel = path.relative_to(base_dir)
        except ValueError:
            continue

        if len(rel.parts) > 1:
            return rel.parts[0]
        return "General"

    return path.parent.name or "Sin seccion"


def extract_pdf_text(path: Path) -> str:
    """Extrae texto de un PDF; si falla o es escaneado, devuelve texto vacio."""
    chunks: list[str] = []
    try:
        reader = PdfReader(str(path))
        for page in reader.pages:
            text = page.extract_text()
            if text:
                chunks.append(text)
    except Exception as exc:
        print(f"Aviso: no se pudo extraer texto de {relative_path(path)}: {exc}")
    return clean_text(" ".join(chunks))


def extract_txt_text(path: Path) -> str:
    """Lee TXT intentando primero UTF-8 y despues latin-1."""
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return clean_text(path.read_text(encoding=encoding))
        except UnicodeDecodeError:
            continue
        except Exception as exc:
            print(f"Aviso: no se pudo leer {relative_path(path)}: {exc}")
            return ""
    return ""


def load_origin_urls() -> dict[str, str]:
    """Carga URLs de origen conocidas desde indices existentes si estan disponibles."""
    url_by_path: dict[str, str] = {}

    valencia_json = DATA_PROCESSED / "documentos_ceei_valencia.json"
    if valencia_json.exists():
        try:
            records = json.loads(valencia_json.read_text(encoding="utf-8"))
            for record in records:
                route = clean_text(record.get("ruta_local", ""))
                url = clean_text(record.get("url_descarga", "")) or clean_text(record.get("url_pagina", ""))
                if route and url:
                    url_by_path[Path(route).as_posix().lower()] = url
                    url_by_path[relative_path(ROOT / route).lower()] = url
        except Exception as exc:
            print(f"Aviso: no se pudo leer {relative_path(valencia_json)}: {exc}")

    for index_path in [
        ROOT / "documentos_ceei_elche_PDF" / "INDEX_DOCUMENTOS.csv",
        ROOT / "documentos_ceei_elche" / "INDEX_DOCUMENTOS.csv",
    ]:
        if not index_path.exists():
            continue
        try:
            df_index = pd.read_csv(index_path)
        except Exception as exc:
            print(f"Aviso: no se pudo leer {relative_path(index_path)}: {exc}")
            continue

        for _, row in df_index.iterrows():
            url = ""
            for url_col in ("url", "url_origen", "url_descarga", "url_pagina"):
                if url_col in row and pd.notna(row[url_col]):
                    url = clean_text(row[url_col])
                    if url:
                        break
            if not url:
                continue

            for path_col in ("ruta_local", "ruta_archivo", "archivo", "filename"):
                if path_col in row and pd.notna(row[path_col]):
                    key = clean_text(row[path_col]).replace("\\", "/").lower()
                    if key:
                        url_by_path[key] = url

    return url_by_path


def find_origin_url(path: Path, urls: dict[str, str]) -> str:
    """Busca URL por ruta relativa, absoluta o nombre de archivo."""
    if path.suffix.lower() == ".txt":
        header_url = extract_origin_url_from_txt(path)
        if header_url:
            return header_url

    candidates = [
        relative_path(path).lower(),
        path.as_posix().lower(),
        path.name.lower(),
    ]
    for candidate in candidates:
        if candidate in urls:
            return urls[candidate]
    return ""


def extract_origin_url_from_txt(path: Path) -> str:
    """Extrae URL_PAGINA de TXT generados a partir de fichas HTML."""
    try:
        with path.open("r", encoding="utf-8") as file:
            for _ in range(12):
                line = file.readline()
                if not line:
                    break
                if line.startswith("URL_PAGINA:"):
                    return line.replace("URL_PAGINA:", "", 1).strip()
    except Exception:
        return ""

    return ""


def build_corpus() -> pd.DataFrame:
    """Construye el DataFrame final de corpus documental."""
    files = discover_files()
    urls = load_origin_urls()
    records = []

    for index, path in enumerate(files, start=1):
        suffix = path.suffix.lower()
        print(f"Procesando {index}/{len(files)}: {relative_path(path)}")

        if suffix == ".pdf":
            file_type = "pdf"
            text = extract_pdf_text(path)
        elif suffix == ".txt":
            file_type = "txt"
            text = extract_txt_text(path)
        else:
            continue

        records.append(
            {
                "id_documento": f"doc_{index:04d}",
                "titulo": clean_text(path.stem),
                "fuente": infer_source(path),
                "seccion": infer_section(path),
                "tipo_archivo": file_type,
                "ruta_local": relative_path(path),
                "url_origen": find_origin_url(path, urls),
                "texto": text,
                "num_caracteres": len(text),
            }
        )

    return pd.DataFrame(records)


def excel_safe(df: pd.DataFrame) -> pd.DataFrame:
    """Recorta celdas de texto para respetar el limite de Excel."""
    df_excel = df.copy()
    for column in df_excel.select_dtypes(include=["object"]).columns:
        df_excel[column] = df_excel[column].map(
            lambda value: value[:EXCEL_CELL_LIMIT] if isinstance(value, str) else value
        )
    return df_excel


def print_report(df: pd.DataFrame) -> None:
    """Imprime un informe descriptivo del corpus generado."""
    total = len(df)
    with_text = int((df["num_caracteres"] > 0).sum()) if total else 0
    without_text = total - with_text
    avg_chars = float(df["num_caracteres"].mean()) if total else 0.0

    print("\nInforme del corpus")
    print(f"Total de documentos procesados: {total}")
    print(f"Documentos con texto: {with_text}")
    print(f"Documentos sin texto: {without_text}")
    print(f"Media de caracteres: {avg_chars:.2f}")

    print("\nDocumentos por fuente:")
    print(df["fuente"].value_counts(dropna=False).to_string())

    print("\nDocumentos por seccion:")
    print(df["seccion"].value_counts(dropna=False).to_string())

    empty_docs = df.loc[df["num_caracteres"] == 0, ["id_documento", "titulo", "ruta_local"]]
    print("\nDocumentos con num_caracteres = 0:")
    if empty_docs.empty:
        print("Ninguno")
    else:
        print(empty_docs.to_string(index=False))


def main() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    df = build_corpus()
    if df.empty:
        raise ValueError("No se encontraron documentos PDF o TXT para construir el corpus.")

    excluded_docs = df.loc[
        df["num_caracteres"] < 300,
        ["id_documento", "titulo", "ruta_local", "num_caracteres"],
    ]
    if not excluded_docs.empty:
        print("\nDocumentos con menos de 300 caracteres excluidos del corpus final:")
        print(excluded_docs.to_string(index=False))
        print(f"\nTotal excluidos: {len(excluded_docs)}")
        df = df.loc[df["num_caracteres"] >= 300].reset_index(drop=True)

    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    excel_safe(df).to_excel(OUTPUT_XLSX, index=False)

    print_report(df)
    print(f"\nCSV generado: {relative_path(OUTPUT_CSV)}")
    print(f"Excel generado: {relative_path(OUTPUT_XLSX)}")


if __name__ == "__main__":
    main()
