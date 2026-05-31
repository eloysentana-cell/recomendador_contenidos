"""
Construye un corpus documental consolidado y trazable para el recomendador.

Integra documentos de CEEI Elche, PDFs de CEEI Valencia y TXT extraidos de
fichas HTML de CEEI Valencia. No borra fuentes, conserva texto completo en CSV
y genera un informe legible de la construccion.
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
REPORT_PATH = OUTPUTS / "informe_corpus_recomendador.txt"
EXCEL_CELL_LIMIT = 32767

DOCUMENT_DIRS = [
    ROOT / "data" / "raw" / "ceei_elche" / "pdf",
    ROOT / "data" / "raw" / "ceei_elche" / "original",
    ROOT / "documentos_ceei_valencia",
    ROOT / "data" / "raw" / "ceei_valencia" / "pdf",
    ROOT / "data" / "raw" / "ceei_valencia" / "txt",
]

SKIP_DIRS = {".git", ".venv", "__pycache__", "outputs"}
ILLEGAL_EXCEL_CHARS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")
URL_PATTERN = re.compile(r"https?://[^\s\)\]\}<>\"']+")


def clean_text(value: object) -> str:
    """Limpia texto para CSV/Excel sin modificar archivos fuente."""
    if value is None:
        return ""
    text = str(value)
    text = ILLEGAL_EXCEL_CHARS.sub(" ", text)
    text = text.replace("\r", " ").replace("\n", " ")
    return " ".join(text.split()).strip()


def relative_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def discover_files() -> list[Path]:
    """Recorre fuentes conocidas y devuelve PDFs/TXT candidatos."""
    files: list[Path] = []
    for base_dir in DOCUMENT_DIRS:
        if not base_dir.exists():
            continue
        for path in base_dir.rglob("*"):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.is_file() and path.suffix.lower() in {".pdf", ".txt"}:
                files.append(path)
    return sorted(set(files), key=lambda item: relative_path(item).lower())


def infer_source(path: Path) -> str:
    normalized = relative_path(path).lower()
    if "ceei_valencia" in normalized or "documentos_ceei_valencia" in normalized:
        return "CEEI Valencia"
    if "ceei_elche" in normalized or "documentos_ceei_elche" in normalized:
        return "CEEI Elche"
    return "Desconocida"


def infer_section(path: Path) -> str:
    normalized = relative_path(path).lower()
    if "data/raw/ceei_valencia/txt" in normalized:
        return "Ficha_HTML"
    if "documentos_ceei_valencia" in normalized or "data/raw/ceei_valencia/pdf" in normalized:
        return "Documento_PDF"

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


def extract_pdf_text(path: Path) -> tuple[str, str]:
    """Extrae texto de PDF con pypdf y devuelve texto, mensaje_error."""
    chunks: list[str] = []
    try:
        reader = PdfReader(str(path))
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                chunks.append(page_text)
    except Exception as exc:
        return "", str(exc)
    return clean_text(" ".join(chunks)), ""


def extract_txt_text(path: Path) -> tuple[str, str]:
    """Lee TXT con UTF-8 y fallback latin-1."""
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return clean_text(path.read_text(encoding=encoding)), ""
        except UnicodeDecodeError:
            continue
        except Exception as exc:
            return "", str(exc)
    return "", "No se pudo decodificar el TXT con utf-8, utf-8-sig ni latin-1"


def first_url_from_text_file(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

    for line in text.splitlines()[:30]:
        if line.startswith("URL_PAGINA:"):
            return clean_text(line.replace("URL_PAGINA:", "", 1))

    match = URL_PATTERN.search(text)
    return match.group(0) if match else ""


def load_metadata() -> tuple[dict[str, dict], dict[str, dict]]:
    """Carga metadatos por ruta local y por URL cuando existen indices."""
    by_path: dict[str, dict] = {}
    by_url: dict[str, dict] = {}

    valencia_json = DATA_PROCESSED / "documentos_ceei_valencia.json"
    if valencia_json.exists():
        try:
            for record in json.loads(valencia_json.read_text(encoding="utf-8")):
                route = clean_text(record.get("ruta_local", "")).replace("\\", "/")
                url = clean_text(record.get("url_pagina", "")) or clean_text(record.get("url_descarga", ""))
                if route:
                    by_path[route.lower()] = record
                    by_path[relative_path(ROOT / route).lower()] = record
                if url:
                    by_url[url.lower()] = record
        except Exception as exc:
            print(f"Aviso: no se pudo leer {relative_path(valencia_json)}: {exc}")

    valencia_texto_json = DATA_PROCESSED / "documentos_ceei_valencia_texto.json"
    if valencia_texto_json.exists():
        try:
            for record in json.loads(valencia_texto_json.read_text(encoding="utf-8")):
                route = clean_text(record.get("ruta_local", "")).replace("\\", "/")
                url = clean_text(record.get("url_pagina", ""))
                if route:
                    by_path[route.lower()] = record
                    by_path[relative_path(ROOT / route).lower()] = record
                if url:
                    by_url[url.lower()] = record
        except Exception as exc:
            print(f"Aviso: no se pudo leer {relative_path(valencia_texto_json)}: {exc}")

    for index_path in [
        ROOT / "data" / "raw" / "ceei_elche" / "pdf" / "INDEX_DOCUMENTOS.csv",
        ROOT / "data" / "raw" / "ceei_elche" / "original" / "INDEX_DOCUMENTOS.csv",
    ]:
        if not index_path.exists():
            continue
        try:
            df_index = pd.read_csv(index_path)
        except Exception as exc:
            print(f"Aviso: no se pudo leer {relative_path(index_path)}: {exc}")
            continue

        for _, row in df_index.iterrows():
            record = row.to_dict()
            for path_col in ("ruta_local", "ruta_archivo", "archivo", "filename"):
                if path_col in record and pd.notna(record[path_col]):
                    key = clean_text(record[path_col]).replace("\\", "/").lower()
                    if key:
                        by_path[key] = record
            for url_col in ("url", "url_origen", "url_descarga", "url_pagina"):
                if url_col in record and pd.notna(record[url_col]):
                    url = clean_text(record[url_col])
                    if url:
                        by_url[url.lower()] = record

    return by_path, by_url


def metadata_for_path(path: Path, by_path: dict[str, dict], by_url: dict[str, dict]) -> dict:
    candidates = [
        relative_path(path).lower(),
        path.as_posix().lower(),
        path.name.lower(),
    ]
    for candidate in candidates:
        if candidate in by_path:
            return by_path[candidate]

    if path.suffix.lower() == ".txt":
        url = first_url_from_text_file(path)
        if url and url.lower() in by_url:
            return by_url[url.lower()]

    return {}


def title_for(path: Path, metadata: dict) -> str:
    for key in ("titulo", "title", "nombre"):
        value = metadata.get(key)
        if value is not None and clean_text(value):
            return clean_text(value)
    return clean_text(path.stem)


def origin_url_for(path: Path, metadata: dict) -> str:
    for key in ("url_origen", "url_pagina", "url_descarga_original", "url_descarga", "url"):
        value = metadata.get(key)
        if value is not None and clean_text(value):
            return clean_text(value)
    if path.suffix.lower() == ".txt":
        return first_url_from_text_file(path)
    return ""


def extraction_state(num_chars: int, error: str) -> str:
    if error:
        return "Error"
    if num_chars == 0:
        return "Sin texto extraido"
    if num_chars < 300:
        return "Texto insuficiente"
    return "OK"


def recommender_text(record: dict) -> str:
    parts = [
        record["titulo"],
        record["fuente"],
        record["seccion"],
        record["tipo_archivo"],
        record["url_origen"],
        record["texto"],
    ]
    return clean_text(" ".join(part for part in parts if part))


def build_corpus() -> tuple[pd.DataFrame, list[str]]:
    files = discover_files()
    by_path, by_url = load_metadata()
    processed_paths = [relative_path(path) for path in files]
    records = []

    for index, path in enumerate(files, start=1):
        print(f"Procesando {index}/{len(files)}: {relative_path(path)}")
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            file_type = "pdf"
            text, error = extract_pdf_text(path)
        elif suffix == ".txt":
            file_type = "txt"
            text, error = extract_txt_text(path)
        else:
            continue

        metadata = metadata_for_path(path, by_path, by_url)
        record = {
            "id_documento": f"doc_{index:04d}",
            "titulo": title_for(path, metadata),
            "fuente": infer_source(path),
            "seccion": infer_section(path),
            "tipo_archivo": file_type,
            "ruta_local": relative_path(path),
            "url_origen": origin_url_for(path, metadata),
            "texto": text,
            "num_caracteres": len(text),
            "estado_extraccion": extraction_state(len(text), error),
        }
        record["texto_recomendador"] = recommender_text(record)
        records.append(record)

    return pd.DataFrame(records), processed_paths


def excel_safe(df: pd.DataFrame) -> pd.DataFrame:
    df_excel = df.copy()
    for column in df_excel.select_dtypes(include=["object", "str"]).columns:
        df_excel[column] = df_excel[column].map(
            lambda value: value[:EXCEL_CELL_LIMIT] if isinstance(value, str) else value
        )
    return df_excel


def value_counts_text(df: pd.DataFrame, column: str) -> str:
    if df.empty or column not in df.columns:
        return "Sin datos"
    return df[column].value_counts(dropna=False).to_string()


def build_report(df: pd.DataFrame, processed_paths: list[str]) -> str:
    total = len(df)
    with_text = int((df["num_caracteres"] > 0).sum()) if total else 0
    without_text = int((df["num_caracteres"] == 0).sum()) if total else 0
    insufficient = int(((df["num_caracteres"] > 0) & (df["num_caracteres"] < 300)).sum()) if total else 0

    lines = [
        "Informe del corpus recomendador",
        "=" * 34,
        f"Total documentos procesados: {total}",
        f"Documentos con texto: {with_text}",
        f"Documentos sin texto: {without_text}",
        f"Documentos con texto insuficiente: {insufficient}",
        "",
        "Documentos por fuente:",
        value_counts_text(df, "fuente"),
        "",
        "Documentos por seccion:",
        value_counts_text(df, "seccion"),
        "",
        "Documentos por tipo_archivo:",
        value_counts_text(df, "tipo_archivo"),
        "",
        "Documentos por estado_extraccion:",
        value_counts_text(df, "estado_extraccion"),
        "",
        "Rutas procesadas:",
    ]
    lines.extend(f"- {path}" for path in processed_paths)
    return "\n".join(lines)


def main() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    df, processed_paths = build_corpus()
    if df.empty:
        raise ValueError("No se ha encontrado ningun PDF o TXT para construir el corpus.")

    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    excel_safe(df).to_excel(OUTPUT_XLSX, index=False)

    report = build_report(df, processed_paths)
    REPORT_PATH.write_text(report, encoding="utf-8")

    print("\n" + report)
    print(f"\nCSV generado: {relative_path(OUTPUT_CSV)}")
    print(f"Excel generado: {relative_path(OUTPUT_XLSX)}")
    print(f"Informe generado: {relative_path(REPORT_PATH)}")


if __name__ == "__main__":
    main()
