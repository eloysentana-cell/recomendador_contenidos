# Recomendador de contenidos para emprendedores

Repositorio del proyecto para el trabajo final del curso ANBAN 2026 para construir un recomendador documental orientado a perfiles emprendedores. El sistema trabaja con documentos publicos de CEEI Elche y CEEI Valencia, crea un corpus consolidado, caracteriza perfiles de usuarios y genera recomendaciones mediante enfoques content-based.

El proyecto esta pensado para avanzar por fases reproducibles:

1. Captacion documental y trazabilidad de fuentes.
2. Consolidacion del corpus textual.
3. Caracterizacion semantica de perfiles emprendedores.
4. Linea base de recomendacion con TF-IDF.
5. Generacion de embeddings locales de documentos.
6. Comparacion posterior entre TF-IDF y embeddings.

No se usa OpenAI ni APIs externas para generar embeddings. Los embeddings actuales se calculan en local con Sentence Transformers.

## Estado Actual

Estado funcional del repositorio:

| Bloque | Estado | Salidas principales |
|---|---|---|
| Scraping CEEI Elche | Completado | `documentos_ceei_elche_PDF/`, `documentos_ceei_elche/` |
| Scraping CEEI Valencia | Completado | `documentos_ceei_valencia/`, `data/processed/documentos_ceei_valencia.json` |
| Fichas HTML Valencia a TXT | Completado | `data/raw/ceei_valencia/txt/`, `data/processed/documentos_ceei_valencia_texto.json` |
| Corpus recomendador | Completado | `data/processed/corpus_recomendador.csv`, `outputs/corpus_recomendador.xlsx` |
| Validacion del corpus | Completado | `outputs/informe_validacion_corpus_recomendador.txt` |
| Caracterizacion de perfiles/documentos | Completado | `outputs/perfiles_caracterizados.*`, `outputs/documentos_caracterizados_muestra.*` |
| Recomendador TF-IDF | Completado como linea base | `outputs/recomendaciones_tfidf_explicadas.xlsx` |
| Embeddings de documentos | Completado | `data/embeddings/document_embeddings.*`, `outputs/document_embeddings_*` |

Ultimos valores de referencia:

```text
Corpus consolidado: 423 documentos
Documentos utiles >= 300 caracteres: 413
CEEI Elche: 260 documentos en corpus
CEEI Valencia: 163 documentos en corpus
Embeddings generados: 413 documentos
Dimension embedding: 384
Modelo embedding: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

## Estructura Recomendada Del Proyecto

La estructura actual se mantiene deliberadamente simple para que los scripts sigan ejecutandose desde la raiz del repositorio.

```text
.
|-- README.md
|-- requirements.txt
|-- build_corpus_recomendador.py
|-- validate_corpus_recomendador.py
|-- build_characterization_tables.py
|-- build_document_embeddings.py
|-- build_profile_queries.py
|-- recommender_tfidf.py
|-- explain_tfidf_recommendations.py
|-- evaluate_tfidf_recommender.py
|-- run_pipeline.py
|-- extraer_valencia_texto_html.py
|-- diagnostico_proyecto.py
|-- data/
|   |-- raw/
|   |   `-- ceei_valencia/txt/            # fichas HTML convertidas a TXT
|   |-- processed/
|   |   |-- corpus_recomendador.csv       # corpus principal actual
|   |   |-- documentos_ceei_valencia.json
|   |   |-- documentos_ceei_valencia_texto.json
|   |   `-- profile_queries.csv
|   |-- perfiles/
|   |   |-- catalogo_perfiles.md
|   |   `-- perfiles_emprendedores.json
|   `-- embeddings/
|       |-- document_embeddings.csv
|       `-- document_embeddings.parquet
|-- documentos_ceei_elche/
|-- documentos_ceei_elche_PDF/
|-- documentos_ceei_valencia/
|-- scraping_valencia/
`-- outputs/
    |-- informes, excels y resultados generados
    `-- recomendaciones_tfidf_explicadas.xlsx
```

Nota: los scripts antiguos de exploracion (`scraper.py`, `scraper_multinivel.py`, `scraper_playwright.py`, `2_scraper_ceei_seguro.py`, etc.) se conservan como trazabilidad metodologica. El flujo actual de trabajo usa los scripts indicados en las secciones siguientes.

## Instalacion

Desde PowerShell, en la raiz del repositorio:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Si el entorno virtual no existe:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Dependencias principales:

```text
pandas
openpyxl
requests
beautifulsoup4
pypdf
scikit-learn
sentence-transformers
torch
pyarrow
scrapy/playwright en fases de scraping exploratorio
```

## Flujo Principal Reproducible

Ejecutar desde la raiz del repositorio.

### 1. Diagnostico Del Proyecto

```powershell
.\.venv\Scripts\python.exe diagnostico_proyecto.py
```

Genera:

```text
outputs/informe_diagnostico_proyecto.txt
```

Sirve para comprobar carpetas, datos procesados, conteos basicos y estado Git.

### 2. Extraccion De Fichas HTML De Valencia

```powershell
.\.venv\Scripts\python.exe extraer_valencia_texto_html.py
```

Entrada:

```text
data/processed/documentos_ceei_valencia.json
```

Salidas:

```text
data/raw/ceei_valencia/txt/
data/processed/documentos_ceei_valencia_texto.json
outputs/informe_extraccion_valencia_texto.txt
```

Esta fase convierte las fichas HTML de Valencia no descargables como PDF en TXT utiles para el corpus.

### 3. Construccion Del Corpus Recomendador

```powershell
.\.venv\Scripts\python.exe build_corpus_recomendador.py
```

Salidas:

```text
data/processed/corpus_recomendador.csv
outputs/corpus_recomendador.xlsx
outputs/informe_corpus_recomendador.txt
```

Columnas principales del corpus:

```text
id_documento
titulo
fuente
seccion
tipo_archivo
ruta_local
url_origen
texto
num_caracteres
estado_extraccion
texto_recomendador
```

### 4. Validacion Del Corpus

```powershell
.\.venv\Scripts\python.exe validate_corpus_recomendador.py
```

Salida:

```text
outputs/informe_validacion_corpus_recomendador.txt
```

Comprueba columnas, documentos utiles, documentos vacios/cortos y duplicados.

### 5. Caracterizacion De Perfiles Y Muestra De Documentos

```powershell
.\.venv\Scripts\python.exe build_characterization_tables.py
```

Salidas:

```text
outputs/perfiles_caracterizados.csv
outputs/perfiles_caracterizados.xlsx
outputs/documentos_caracterizados_muestra.csv
outputs/documentos_caracterizados_muestra.xlsx
outputs/informe_caracterizacion.txt
```

### 6. Recomendador TF-IDF

```powershell
.\.venv\Scripts\python.exe run_pipeline.py
```

Ejecuta:

```text
build_profile_queries.py
validate_corpus.py
recommender_tfidf.py
explain_tfidf_recommendations.py
evaluate_tfidf_recommender.py
```

Salidas principales:

```text
outputs/recomendaciones_tfidf.csv
outputs/recomendaciones_tfidf.xlsx
outputs/recomendaciones_tfidf_explicadas.csv
outputs/recomendaciones_tfidf_explicadas.xlsx
outputs/evaluacion_tfidf.csv
outputs/evaluacion_tfidf.xlsx
outputs/informe_evaluacion_tfidf.txt
```

### 7. Embeddings Locales De Documentos

```powershell
.\.venv\Scripts\python.exe build_document_embeddings.py
```

Modelo usado:

```text
sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

Entradas:

```text
data/processed/corpus_recomendador.csv
```

Salidas:

```text
data/embeddings/document_embeddings.csv
data/embeddings/document_embeddings.parquet
outputs/informe_document_embeddings.txt
outputs/document_embeddings_resumen_por_fuente.csv
outputs/document_embeddings_resumen_por_fuente.xlsx
outputs/document_embeddings_muestra.csv
outputs/document_embeddings_muestra.xlsx
```

La tabla principal de embeddings incluye:

```text
id_documento
titulo
fuente
seccion
tipo_archivo
ruta_local
url_origen
num_caracteres
estado_extraccion
texto_embedding_muestra
modelo_embedding
dimension_embedding
embedding_preview
embedding
```

`embedding` contiene el vector completo serializado como JSON string. `embedding_preview` contiene solo las primeras 8 dimensiones para inspeccion humana.

## Perfiles Emprendedores

Los perfiles estan en:

```text
data/perfiles/catalogo_perfiles.md
data/perfiles/perfiles_emprendedores.json
```

Cada perfil define:

```text
id
nombre
fase_emprendedora
nivel_madurez
perfil_funcional
necesidades_prioritarias
intenciones_busqueda
palabras_clave_semanticas
descripcion_embedding
```

La clave `descripcion_embedding` es texto semantico, no un vector. Sirve como entrada para TF-IDF o para una futura comparacion con embeddings de perfiles.

Perfiles actuales:

```text
perfil_001_investigador_ebt_ebc
perfil_002_ceo_scaling_internacional
perfil_003_consultor_silver
perfil_004_mentor_negocios_tradicionales
perfil_005_emprendedora_rural_agroalimentaria
perfil_006_fundador_cooperativa_impacto
perfil_007_estudiante_presemilla
perfil_008_autoempleo_necesidad
```

## Fuentes Documentales

### CEEI Elche

Documentos principales:

```text
documentos_ceei_elche_PDF/
|-- Fichas/
|-- Infografias/
|-- Informes_y_Publicaciones/
|-- Modelos_de_Negocio/
|-- Modelos_de_Negocio_texto/
`-- INDEX_DOCUMENTOS.csv
```

Conteo de referencia:

```text
Fichas: 121 PDF
Infografias: 48 PDF
Informes_y_Publicaciones: 27 PDF
Modelos_de_Negocio: 5 PDF
Modelos_de_Negocio_texto: 40 TXT
```

### CEEI Valencia

Indice principal:

```text
data/processed/documentos_ceei_valencia.json
```

Conteo de referencia:

```text
163 registros detectados
30 PDFs descargados
133 fichas HTML aprovechadas como TXT
```

Documentos descargados:

```text
documentos_ceei_valencia/
```

Fichas HTML convertidas:

```text
data/raw/ceei_valencia/txt/
```

## Criterios Metodologicos

El recomendador actual es content-based:

```text
perfil emprendedor -> texto descriptivo -> vector TF-IDF
documento -> texto_recomendador -> vector TF-IDF
comparacion -> similitud coseno
```

Se evita collaborative filtering porque no hay historico real de usuarios, clics, valoraciones o interacciones. Simular ese historico reduciria la solidez metodologica del TFM.

Los embeddings locales se usan como segunda representacion semantica de documentos. La comparacion futura puede valorar si los embeddings mejoran la linea base TF-IDF.

## Archivos Que Conviene Revisar

Para seguimiento del proyecto:

```text
README.md
data/perfiles/perfiles_emprendedores.json
data/processed/corpus_recomendador.csv
outputs/informe_validacion_corpus_recomendador.txt
outputs/recomendaciones_tfidf_explicadas.xlsx
outputs/informe_document_embeddings.txt
outputs/document_embeddings_resumen_por_fuente.xlsx
outputs/document_embeddings_muestra.xlsx
```

Para revisar calidad del corpus:

```text
outputs/informe_corpus_recomendador.txt
outputs/informe_validacion_corpus_recomendador.txt
outputs/documentos_caracterizados_muestra.xlsx
```

Para revisar recomendaciones:

```text
outputs/recomendaciones_tfidf_explicadas.xlsx
outputs/informe_evaluacion_tfidf.txt
```

## Mantenimiento De Git

Comandos habituales:

```powershell
git status --short
git add README.md requirements.txt build_document_embeddings.py data/embeddings outputs
git commit -m "Actualiza documentacion y resultados del recomendador"
git push origin main
```

Antes de subir, comprobar que no se estan incluyendo archivos temporales de Excel:

```text
~$*.xlsx
```

La carpeta `.venv/`, caches de Python y archivos temporales locales no deben subirse al repositorio.

## Siguiente Paso Recomendado

El siguiente paso tecnico es generar embeddings tambien para los perfiles emprendedores y construir una comparacion directa:

```text
perfil_embedding vs document_embedding
```

Despues se podran comparar:

```text
1. Ranking TF-IDF
2. Ranking por embeddings locales
3. Coincidencias entre ambos
4. Explicabilidad y utilidad por perfil emprendedor
```

Esto permitiria defender una evolucion natural desde una linea base explicable hacia una aproximacion semantica mas avanzada.
