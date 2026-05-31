"""Diagnostica estructura, datos y estado Git del proyecto."""

from pathlib import Path
import json
import subprocess

from collections import Counter


ROOT = Path(__file__).resolve().parent
OUTPUT_PATH = ROOT / "outputs" / "informe_diagnostico_proyecto.txt"

PATHS_TO_CHECK = [
    "documentos_ceei_elche_PDF",
    "documentos_ceei_valencia",
    "data/raw/ceei_valencia/txt",
    "data/processed/documentos_ceei_valencia.json",
    "data/processed/documentos_ceei_valencia_texto.json",
    "data/processed/corpus_recomendador.csv",
    "data/processed/corpus_documental.csv",
    "outputs/informe_extraccion_valencia_texto.txt",
    "outputs/informe_corpus_recomendador.txt",
]

SIZE_PATHS = [
    "data/processed/corpus_recomendador.csv",
    "data/processed/corpus_documental.csv",
]

COUNT_DIRS = [
    "documentos_ceei_elche_PDF",
    "documentos_ceei_valencia",
    "data/raw/ceei_valencia/txt",
]


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def count_files(directory: Path, suffix: str) -> int:
    if not directory.exists():
        return 0
    return sum(1 for path in directory.rglob(f"*{suffix}") if path.is_file())


def load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def git_status() -> str:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return f"Error ejecutando git status: {result.stderr.strip()}"
    return result.stdout.strip() or "Sin cambios"


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = ["Informe de diagnostico del proyecto", "=" * 37, ""]

    lines.append("Archivos y carpetas existentes:")
    for item in PATHS_TO_CHECK:
        path = ROOT / item
        kind = "carpeta" if path.is_dir() else "archivo" if path.is_file() else "no existe"
        lines.append(f"- {item}: {kind}")

    lines.extend(["", "Tamano de archivos CSV:"])
    for item in SIZE_PATHS:
        path = ROOT / item
        size = path.stat().st_size if path.exists() else 0
        lines.append(f"- {item}: {size} bytes")

    lines.extend(["", "Conteo PDF/TXT por carpeta:"])
    for item in COUNT_DIRS:
        directory = ROOT / item
        lines.append(
            f"- {item}: PDF={count_files(directory, '.pdf')}, TXT={count_files(directory, '.txt')}"
        )

    valencia_texto = load_json(ROOT / "data/processed/documentos_ceei_valencia_texto.json")
    lines.extend(["", "documentos_ceei_valencia_texto.json:"])
    if isinstance(valencia_texto, list):
        states = Counter(record.get("estado_extraccion", "") for record in valencia_texto)
        lines.append(f"- total registros: {len(valencia_texto)}")
        lines.append(f"- conteo por estado_extraccion: {dict(states)}")
    else:
        lines.append("- no existe o no contiene una lista")

    valencia = load_json(ROOT / "data/processed/documentos_ceei_valencia.json")
    lines.extend(["", "documentos_ceei_valencia.json:"])
    if isinstance(valencia, list):
        states = Counter(record.get("estado", "") for record in valencia)
        types = Counter(record.get("tipo_archivo", "") for record in valencia)
        lines.append(f"- total registros: {len(valencia)}")
        lines.append(f"- conteo por estado: {dict(states)}")
        lines.append(f"- conteo por tipo_archivo: {dict(types)}")
    else:
        lines.append("- no existe o no contiene una lista")

    lines.extend(["", "Estado Git:", git_status()])

    report = "\n".join(lines)
    OUTPUT_PATH.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nInforme generado: {rel(OUTPUT_PATH)}")


if __name__ == "__main__":
    main()
