"""Convierte perfiles emprendedores JSON en consultas textuales largas."""

from pathlib import Path
import json

import pandas as pd


ROOT = Path(__file__).resolve().parent
PROFILES_PATH = ROOT / "data" / "perfiles" / "perfiles_emprendedores.json"
OUTPUT_PATH = ROOT / "data" / "processed" / "profile_queries.csv"

TEXT_PRIORITY_FIELDS = [
    "nombre_perfil",
    "nombre",
    "fase_emprendedora",
    "perfil_funcional",
    "necesidades_prioritarias",
    "intenciones_busqueda",
    "palabras_clave_semanticas",
    "descripcion_embedding",
]


def clean(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def flatten_value(value: object) -> str:
    """Convierte listas y diccionarios del perfil en texto sin inventar campos."""
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(clean(item) for item in value if clean(item))
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            item_text = flatten_value(item)
            if item_text:
                parts.append(f"{key}: {item_text}")
        return " ".join(parts)
    return clean(value)


def profile_text(profile: dict) -> str:
    parts = []
    used_fields = set()

    for field in TEXT_PRIORITY_FIELDS:
        if field in profile:
            text = flatten_value(profile[field])
            if text:
                parts.append(text)
                used_fields.add(field)

    # Incluye campos equivalentes no previstos, respetando la estructura real.
    for field, value in profile.items():
        if field in used_fields or field == "id":
            continue
        text = flatten_value(value)
        if text:
            parts.append(text)

    return clean(" ".join(parts))


def main() -> None:
    if not PROFILES_PATH.exists():
        raise FileNotFoundError(f"No existe {PROFILES_PATH.relative_to(ROOT).as_posix()}")

    profiles = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    if not isinstance(profiles, list):
        raise ValueError("El JSON de perfiles debe contener una lista.")

    records = []
    for index, profile in enumerate(profiles, start=1):
        if not isinstance(profile, dict):
            continue

        profile_id = clean(profile.get("id")) or f"perfil_{index:03d}"
        profile_name = clean(profile.get("nombre_perfil")) or clean(profile.get("nombre")) or profile_id
        text = profile_text(profile)

        records.append(
            {
                "id_perfil": profile_id,
                "nombre_perfil": profile_name,
                "texto_perfil": text,
                "num_caracteres": len(text),
            }
        )

    df = pd.DataFrame(records)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print(f"Numero de perfiles: {len(df)}")
    print("\nNombres de perfiles:")
    for name in df["nombre_perfil"].tolist():
        print(f"- {name}")
    print(f"\nLongitud media del texto de perfil: {df['num_caracteres'].mean():.2f}")
    print(f"CSV generado: {OUTPUT_PATH.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
