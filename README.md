# Recomendador de contenidos para emprendedores

Repositorio del trabajo final del curso de ANBAN 2026 para construir un recomendador documental orientado a perfiles emprendedores. El sistema trabaja con documentos publicos de CEEI Elche y CEEI Valencia, crea un corpus consolidado, caracteriza perfiles de usuarios y genera recomendaciones mediante enfoques content-based.

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
| Scraping CEEI Elche | Completado | `data/raw/ceei_elche/pdf/`, `data/raw/ceei_elche/original/` |
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
|-- build_profile_embeddings.py
|-- recommend_embeddings_by_profile.py
|-- compare_tfidf_vs_embeddings.py
|-- recommend_from_text.py
|-- recommend_from_text_worker.py
|-- build_profile_queries.py
|-- recommender_tfidf.py
|-- explain_tfidf_recommendations.py
|-- evaluate_tfidf_recommender.py
|-- run_pipeline.py
|-- extraer_valencia_texto_html.py
|-- diagnostico_proyecto.py
|-- web_app/
|   `-- app.py
|-- data/
|   |-- raw/
|   |   |-- ceei_elche/
|   |   |   |-- pdf/                       # PDFs y TXT extraidos de CEEI Elche
|   |   |   `-- original/                  # documentos originales descargados
|   |   `-- ceei_valencia/txt/             # fichas HTML convertidas a TXT
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

### 2. Extraccion De Documentos De Elche

La captacion de CEEI Elche se hizo antes que Valencia y combina dos tecnicas:

```text
1. Descarga web con requests + BeautifulSoup:
   se recorren listados de recursos, se detectan enlaces a fichas y se descargan PDFs reales.

2. Extraccion HTML a TXT:
   en Modelos de Negocio, cuando la ficha no ofrece PDF descargable, se aprovecha el HTML como texto util.
```

Scripts relacionados:

```powershell
.\.venv\Scripts\python.exe 2_scraper_ceei_seguro.py
.\.venv\Scripts\python.exe extraer_modelos_negocio_texto.py
.\.venv\Scripts\python.exe build_corpus.py
```

Salidas principales:

```text
data/raw/ceei_elche/pdf/
data/raw/ceei_elche/original/
data/raw/ceei_elche/pdf/INDEX_DOCUMENTOS.csv
data/raw/ceei_elche/pdf/Modelos_de_Negocio_texto/INDEX_MODELOS_TEXTO.csv
data/processed/corpus_documental.csv
outputs/corpus_documental.xlsx
```

En esta fase se usaron cabeceras de navegador, paginacion controlada, pausas entre peticiones e indices CSV para mantener trazabilidad de titulo, seccion, URL y ruta local. La extraccion textual posterior de PDFs se hace con `pypdf`; los TXT procedentes de HTML se limpian con reglas simples de normalizacion de espacios y ruido.

### 3. Extraccion De Fichas HTML De Valencia

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

Esta fase parte del indice generado por el spider de Valencia y trabaja solo sobre registros con `estado == "no_disponible"`. La tecnica usada es distinta a Elche: no intenta forzar la descarga cuando la URL devuelve HTML, sino que visita `url_pagina`, elimina bloques no utiles (`script`, `style`, `nav`, `footer`, `header`, formularios, iframes), prioriza selectores de contenido (`article`, `main`, `div.contenido`, `div.detalle`, `div.ficha`) y guarda la ficha como TXT si supera el umbral minimo de calidad.

### 4. Construccion Del Corpus Recomendador

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

### 5. Validacion Del Corpus

```powershell
.\.venv\Scripts\python.exe validate_corpus_recomendador.py
```

Salida:

```text
outputs/informe_validacion_corpus_recomendador.txt
```

Comprueba columnas, documentos utiles, documentos vacios/cortos y duplicados.

### 6. Caracterizacion De Perfiles Y Muestra De Documentos

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

### 7. Recomendador TF-IDF

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

### 8. Embeddings Locales De Documentos

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

### 9. Recomendacion Semantica Y Comparacion

```powershell
.\.venv\Scripts\python.exe build_profile_embeddings.py
.\.venv\Scripts\python.exe recommend_embeddings_by_profile.py
.\.venv\Scripts\python.exe compare_tfidf_vs_embeddings.py
.\.venv\Scripts\python.exe recommend_from_text.py
```

Salidas principales:

```text
data/embeddings/profile_embeddings.csv
data/embeddings/profile_embeddings.parquet
outputs/recomendaciones_embeddings_perfiles.csv
outputs/recomendaciones_embeddings_perfiles.xlsx
outputs/comparacion_tfidf_embeddings.csv
outputs/comparacion_tfidf_embeddings.xlsx
outputs/informe_comparacion_tfidf_embeddings.txt
```

### 10. Demostrador Web Local

Instalar dependencia web:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-web.txt
```

Ejecutar:

```powershell
.\.venv\Scripts\python.exe -m streamlit run web_app/app.py --server.port 8501 --server.fileWatcherType none --browser.gatherUsageStats false
```

La web permite escribir una necesidad emprendedora en lenguaje natural, comparar ese texto contra perfiles predefinidos y recomendar documentos del corpus usando embeddings locales. En Windows, la interfaz Streamlit delega el calculo en `recommend_from_text_worker.py` para evitar problemas de salida de consola durante la carga del modelo `SentenceTransformer` y preservar correctamente la codificacion UTF-8.

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

Tecnica usada:

```text
1. Scraping HTML con requests + BeautifulSoup sobre listados de recursos.
2. Deteccion de enlaces de ficha y enlaces de descarga.
3. Descarga directa de PDFs cuando existe documento descargable real.
4. Guardado de originales y PDFs procesables en data/raw/ceei_elche/.
5. Extraccion de texto con pypdf para PDFs y lectura directa para TXT.
6. Conversion de fichas HTML sin PDF de Modelos de Negocio a TXT.
```

La estrategia de Elche prioriza el documento descargable. Cuando el recurso existe como PDF, se conserva como archivo documental. Cuando una ficha no ofrece PDF util, se aprovecha el contenido HTML como texto limpio para no perder informacion relevante para el corpus.

Documentos principales:

```text
data/raw/ceei_elche/pdf/
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

Tecnica usada:

```text
1. Spider de Scrapy para detectar fichas y registrar metadatos.
2. Intento de descarga de PDF desde la URL de descarga.
3. Clasificacion de registros como descargado o no_disponible.
4. Recuperacion posterior de fichas no_disponible mediante requests + BeautifulSoup.
5. Limpieza de HTML y conversion a TXT cuando la ficha supera el umbral minimo de texto.
```

La estrategia de Valencia parte de un indice estructurado en JSON. Los PDFs validos se mantienen como documentos descargados; las fichas cuya descarga devolvia HTML se incorporan como TXT para aprovechar contenido que de otra forma quedaria fuera del corpus.

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

Se evita collaborative filtering porque no hay historico real de usuarios, clics, valoraciones o interacciones. Simular ese historico reduciria la solidez metodologica del trabajo final del curso de ANBAN 2026.

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

Tras incorporar embeddings de perfiles, ranking semantico y demostrador web, el siguiente paso recomendable es preparar una evaluacion cualitativa:

```text
1. Revisar recomendaciones con personas emprendedoras o expertos.
2. Recoger valoraciones de utilidad por perfil.
3. Comparar la percepcion humana con los rankings TF-IDF y embeddings.
4. Ajustar perfiles, textos de consulta y criterios de interpretacion.
```

Esto permitiria pasar de una validacion tecnica reproducible a una evaluacion de utilidad percibida, sin simular historicos de usuarios que el proyecto todavia no tiene.

## Embeddings, Comparacion Semantica Y Demostrador Web

El proyecto incorpora dos aproximaciones complementarias para recomendar contenidos:

```text
1. TF-IDF como linea base explicable.
2. Embeddings locales como representacion semantica.
```

### Embeddings De Documentos

Los embeddings de documentos se generan con:

```powershell
.\.venv\Scripts\python.exe build_document_embeddings.py
```

Configuracion:

```text
Modelo: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
Dimension: 384
Documentos vectorizados: 413
```

Salidas:

```text
data/embeddings/document_embeddings.csv
data/embeddings/document_embeddings.parquet
outputs/informe_document_embeddings.txt
```

### Embeddings De Perfiles

Los embeddings de perfiles se generan con:

```powershell
.\.venv\Scripts\python.exe build_profile_embeddings.py
```

El script usa los 8 perfiles definidos en:

```text
data/perfiles/perfiles_emprendedores.json
```

Utiliza el mismo modelo multilingue y la misma dimension vectorial que los documentos. Esto permite comparar directamente:

```text
profile_embedding vs document_embedding
```

Salidas:

```text
data/embeddings/profile_embeddings.csv
data/embeddings/profile_embeddings.parquet
outputs/informe_profile_embeddings.txt
outputs/profile_embeddings_muestra.csv
outputs/profile_embeddings_muestra.xlsx
```

### Ranking Por Embeddings

El ranking semantico por perfiles se calcula con:

```powershell
.\.venv\Scripts\python.exe recommend_embeddings_by_profile.py
```

Para cada perfil emprendedor, el script compara su embedding contra todos los embeddings de documentos mediante producto escalar, equivalente a similitud coseno al estar normalizados.

Salidas:

```text
outputs/recomendaciones_embeddings_perfiles.csv
outputs/recomendaciones_embeddings_perfiles.xlsx
outputs/informe_recomendaciones_embeddings.txt
```

### Comparacion TF-IDF Vs Embeddings

La comparacion de rankings se genera con:

```powershell
.\.venv\Scripts\python.exe compare_tfidf_vs_embeddings.py
```

Compara el top 10 de TF-IDF contra el top 10 de embeddings para cada perfil, calcula coincidencias, porcentaje de solapamiento y documentos exclusivos de cada metodo.

Salidas:

```text
outputs/comparacion_tfidf_embeddings.csv
outputs/comparacion_tfidf_embeddings.xlsx
outputs/informe_comparacion_tfidf_embeddings.txt
```

Interpretacion academica:

```text
TF-IDF aporta una linea base explicable basada en coincidencias lexicas.
Los embeddings capturan similitud semantica mas alla de coincidencias literales.
La comparacion de ambos rankings permite evaluar si la representacion semantica mejora o complementa la linea base.
No hay evaluacion con usuarios reales todavia.
```

### Recomendacion Desde Texto Libre

El script:

```powershell
.\.venv\Scripts\python.exe recommend_from_text.py
```

permite probar por consola una consulta libre como:

```text
Soy una emprendedora rural que quiere montar una pequena empresa agroalimentaria con impacto territorial y necesito ayudas publicas
```

Internamente compara el texto del usuario contra:

```text
1. Perfiles emprendedores predefinidos.
2. Documentos vectorizados del corpus.
```

### Demostrador Web

La web local esta en:

```text
web_app/app.py
recommend_from_text_worker.py
```

Instalacion de dependencia web:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-web.txt
```

Ejecucion:

```powershell
.\.venv\Scripts\python.exe -m streamlit run web_app/app.py --server.port 8501 --server.fileWatcherType none --browser.gatherUsageStats false
```

La interfaz permite introducir una descripcion libre del perfil o necesidad emprendedora, seleccionar el numero de documentos, ver perfiles similares, recomendaciones documentales, scores de similitud y previews de embeddings. Por legibilidad no muestra los vectores completos salvo indicacion explicita; los embeddings completos estan almacenados en `data/embeddings/`.

Arquitectura de ejecucion:

```text
web_app/app.py -> recommend_from_text_worker.py -> recommend_from_text.py -> embeddings locales
```

Esta separacion evita que Streamlit cargue directamente el modelo de Sentence Transformers. El worker devuelve JSON normalizado para que los textos con tildes se muestren correctamente en Windows.

### Comandos De La Fase Semantica

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-web.txt
.\.venv\Scripts\python.exe build_profile_embeddings.py
.\.venv\Scripts\python.exe recommend_embeddings_by_profile.py
.\.venv\Scripts\python.exe compare_tfidf_vs_embeddings.py
.\.venv\Scripts\python.exe recommend_from_text.py
.\.venv\Scripts\python.exe -m streamlit run web_app/app.py --server.port 8501 --server.fileWatcherType none --browser.gatherUsageStats false
```
