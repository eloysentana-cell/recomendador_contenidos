# TFM Recomendador Documental CEEI Elche

Este proyecto desarrolla un sistema de recomendación documental a partir de recursos públicos del CEEI Elche.

## Objetivo del proyecto

El objetivo es construir un flujo completo de trabajo en Python para:

1. Extraer recursos públicos mediante scraping.
2. Limpiar y depurar los datos obtenidos.
3. Clasificar los documentos por tipo y categoría.
4. Preparar un dataset limpio para un sistema de recomendación documental.
5. Construir un recomendador basado en técnicas de inteligencia artificial.

## Estado del proyecto

### Día 1: Scraping de recursos

Se crearon los primeros scripts de extracción de datos:

- `scraper.py`
- `scraper_multinivel.py`
- `scraper_playwright.py`

El scraper básico extrajo 67 recursos.

El scraper multinivel extrajo 140 recursos.

La vía de Playwright se descartó porque activaba verificaciones de Cloudflare.

El dataset principal seleccionado para continuar es:

```text
data/processed/documentos_ceei_multinivel.csv
