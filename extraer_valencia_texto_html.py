"""
Extrae texto HTML util de fichas no disponibles de CEEI Valencia.

El script aprovecha registros con estado "no_disponible" en el indice
data/processed/documentos_ceei_valencia.json. En lugar de intentar forzar la
descarga de un PDF, visita la ficha HTML, extrae texto limpio y guarda un TXT
si el contenido supera un umbral minimo.
"""

from pathlib import Path
from urllib.parse import parse_qs, urlparse
import json
import re
import time

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent
INPUT_JSON = ROOT / "data" / "processed" / "documentos_ceei_valencia.json"
TXT_DIR = ROOT / "data" / "raw" / "ceei_valencia" / "txt"
OUTPUT_JSON = ROOT / "data" / "processed" / "documentos_ceei_valencia_texto.json"
REPORT_PATH = ROOT / "outputs" / "informe_extraccion_valencia_texto.txt"

MIN_CHARS = 500
REQUEST_DELAY_SECONDS = 1.2
TIMEOUT_SECONDS = 30

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome Safari"
    )
}

REMOVE_SELECTORS = [
    "script",
    "style",
    "nav",
    "footer",
    "header",
    "form",
    "aside",
    "noscript",
    "iframe",
]

MAIN_SELECTORS = [
    "article",
    "main",
    "div.contenido",
    "div#contenido",
    "div.detalle",
    "div.ficha",
    "body",
]


def rel(path: Path) -> str:
    """Devuelve una ruta relativa al proyecto para indices e informes."""
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def clean_spaces(text: str) -> str:
    """Normaliza espacios horizontales sin unir lineas aun."""
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_extracted_text(text: str) -> str:
    """
    Limpia texto HTML.

    Elimina lineas vacias, lineas repetidas y lineas muy cortas que suelen ser
    ruido de navegacion, conservando contenido corto cuando aparece cerca de
    bloques utiles.
    """
    text = clean_spaces(text)
    raw_lines = [line.strip() for line in text.splitlines()]
    raw_lines = [line for line in raw_lines if line]

    kept_lines: list[str] = []
    seen: set[str] = set()

    for index, line in enumerate(raw_lines):
        normalized = re.sub(r"\s+", " ", line).strip()
        if not normalized:
            continue

        normalized_key = normalized.lower()
        if normalized_key in seen:
            continue

        previous_len = len(raw_lines[index - 1].strip()) if index > 0 else 0
        next_len = len(raw_lines[index + 1].strip()) if index + 1 < len(raw_lines) else 0
        near_content = previous_len >= 80 or next_len >= 80

        # Las lineas muy cortas aisladas suelen ser menus, botones o migas.
        if len(normalized) < 4 and not near_content:
            continue

        kept_lines.append(normalized)
        seen.add(normalized_key)

    return "\n".join(kept_lines).strip()


def safe_filename(title: str, page_url: str) -> str:
    """Crea un nombre de archivo seguro para Windows usando titulo e id n."""
    parsed = urlparse(page_url or "")
    query = parse_qs(parsed.query)
    identifier = ""
    if query.get("n"):
        identifier = query["n"][0]

    base = title or "documento_valencia"
    base = base.lower()
    base = re.sub(r"[^\w\s.-]", " ", base, flags=re.UNICODE)
    base = re.sub(r"\s+", "_", base).strip("._-")
    base = base[:120].strip("._-")

    if identifier:
        filename = f"{identifier}_{base}.txt"
    else:
        filename = f"{base}.txt"

    # Caracteres reservados en Windows.
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)
    return filename[:150] or "documento_valencia.txt"


def load_records() -> list[dict]:
    """Carga el indice JSON original de CEEI Valencia."""
    if not INPUT_JSON.exists():
        raise FileNotFoundError(f"No existe {rel(INPUT_JSON)}")

    with INPUT_JSON.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("El JSON de Valencia debe contener una lista de registros.")

    return data


def select_main_content(soup: BeautifulSoup):
    """Selecciona el bloque principal con fallback a body."""
    for selector in MAIN_SELECTORS:
        element = soup.select_one(selector)
        if element is not None:
            return element
    return soup


def extract_text_from_html(html: str) -> str:
    """Parsea HTML y extrae texto limpio de la ficha."""
    soup = BeautifulSoup(html, "html.parser")

    for selector in REMOVE_SELECTORS:
        for element in soup.select(selector):
            element.decompose()

    main_content = select_main_content(soup)
    text = main_content.get_text(separator="\n", strip=True)
    return clean_extracted_text(text)


def fetch_page(url: str) -> str:
    """Descarga una ficha HTML con requests."""
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()

    if not response.encoding:
        response.encoding = response.apparent_encoding

    return response.text


def build_txt_content(record: dict, extracted_text: str) -> str:
    """Construye el contenido final del TXT con metadatos trazables."""
    title = str(record.get("titulo") or "").strip()
    page_url = str(record.get("url_pagina") or "").strip()
    download_url = str(record.get("url_descarga") or "").strip()
    original_type = str(record.get("tipo_archivo") or "").strip()

    return "\n".join(
        [
            f"TITULO: {title}",
            f"URL_PAGINA: {page_url}",
            f"URL_DESCARGA_ORIGINAL: {download_url}",
            "FUENTE: CEEI Valencia",
            "ESTADO_ORIGINAL: no_disponible",
            f"TIPO_ORIGINAL: {original_type}",
            "",
            "TEXTO:",
            extracted_text,
            "",
        ]
    )


def process_record(record: dict) -> dict:
    """Procesa una ficha no_disponible y devuelve su registro de indice."""
    title = str(record.get("titulo") or "").strip()
    page_url = str(record.get("url_pagina") or "").strip()
    download_url = str(record.get("url_descarga") or "").strip()
    original_type = str(record.get("tipo_archivo") or "").strip()

    output_record = {
        "titulo": title,
        "url_pagina": page_url,
        "url_descarga_original": download_url,
        "ruta_local": "",
        "tipo_archivo": "txt",
        "num_caracteres": 0,
        "estado_extraccion": "",
        "fuente": "CEEI Valencia",
        "estado_original": str(record.get("estado") or "").strip(),
        "tipo_original": original_type,
        "mensaje_error": "",
    }

    if not page_url:
        output_record["estado_extraccion"] = "error"
        output_record["mensaje_error"] = "Registro sin url_pagina"
        return output_record

    try:
        html = fetch_page(page_url)
        extracted_text = extract_text_from_html(html)
        output_record["num_caracteres"] = len(extracted_text)

        if len(extracted_text) < MIN_CHARS:
            output_record["estado_extraccion"] = "texto_insuficiente"
            return output_record

        file_path = TXT_DIR / safe_filename(title, page_url)
        file_path.write_text(build_txt_content(record, extracted_text), encoding="utf-8")

        output_record["ruta_local"] = rel(file_path)
        output_record["estado_extraccion"] = "texto_extraido"
        return output_record

    except Exception as exc:
        output_record["estado_extraccion"] = "error"
        output_record["mensaje_error"] = str(exc)
        return output_record


def build_report(index_records: list[dict]) -> str:
    """Crea un informe legible de la extraccion."""
    total = len(index_records)
    extracted = sum(1 for record in index_records if record["estado_extraccion"] == "texto_extraido")
    insufficient = sum(
        1 for record in index_records if record["estado_extraccion"] == "texto_insuficiente"
    )
    errors = sum(1 for record in index_records if record["estado_extraccion"] == "error")

    lines = [
        "Informe de extraccion HTML de CEEI Valencia",
        "=" * 45,
        f"Registros no_disponible analizados: {total}",
        f"Textos extraidos utiles: {extracted}",
        f"Textos insuficientes: {insufficient}",
        f"Errores: {errors}",
        f"Carpeta de salida: {rel(TXT_DIR)}",
        f"JSON de salida: {rel(OUTPUT_JSON)}",
        f"Informe de salida: {rel(REPORT_PATH)}",
    ]

    if errors:
        lines.extend(["", "Errores detectados:"])
        for record in index_records:
            if record["estado_extraccion"] == "error":
                lines.append(f"- {record['titulo']} | {record['url_pagina']} | {record['mensaje_error']}")

    if insufficient:
        lines.extend(["", "Textos insuficientes:"])
        for record in index_records:
            if record["estado_extraccion"] == "texto_insuficiente":
                lines.append(
                    f"- {record['titulo']} | {record['num_caracteres']} caracteres | "
                    f"{record['url_pagina']}"
                )

    return "\n".join(lines)


def main() -> None:
    TXT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    records = load_records()
    pending_records = [
        record for record in records if str(record.get("estado") or "").strip() == "no_disponible"
    ]

    index_records: list[dict] = []

    for position, record in enumerate(pending_records, start=1):
        title = str(record.get("titulo") or "").strip()
        print(f"Procesando {position}/{len(pending_records)}: {title}")
        index_records.append(process_record(record))
        time.sleep(REQUEST_DELAY_SECONDS)

    with OUTPUT_JSON.open("w", encoding="utf-8") as file:
        json.dump(index_records, file, ensure_ascii=False, indent=2)

    report = build_report(index_records)
    REPORT_PATH.write_text(report, encoding="utf-8")

    print("\n" + report)


if __name__ == "__main__":
    main()
