# Recomendador de contenidos para emprendedores

Este repositorio contiene la construccion inicial de un sistema recomendador documental para perfiles de emprendedores. El trabajo se organiza en etapas, empezando por la captacion y preparacion de documentos publicos de CEEI Elche y CEEI Valencia.

La idea del proyecto es sencilla y defendible para el TFM:

1. Captar documentos publicos de interes para emprendedores.
2. Ordenarlos y dejar trazabilidad de su origen.
3. Preparar perfiles de emprendedores en formato estructurado.
4. Construir un primer recomendador content-based con TF-IDF y similitud coseno.
5. Comparar despues con embeddings, sin usar collaborative filtering hasta disponer de historico de usuarios.

## Estructura del repositorio

```text
.
|-- 2_scraper_ceei_seguro.py
|-- extraer_modelos_negocio_texto.py
|-- build_corpus.py
|-- text_processing.py
|-- scraper.py
|-- scraper_multinivel.py
|-- scraper_playwright.py
|-- documentos_ceei_elche/
|-- documentos_ceei_elche_PDF/
|   |-- Fichas/
|   |-- Infografias/
|   |-- Informes_y_Publicaciones/
|   |-- Modelos_de_Negocio/
|   |-- Modelos_de_Negocio_texto/
|   `-- INDEX_DOCUMENTOS.csv
|-- documentos_ceei_valencia/
|-- scraping_valencia/
|   |-- scrapy.cfg
|   `-- scraping_valencia/
|       `-- spiders/
|           `-- ceei_valencia.py
|-- data/
|   |-- perfiles/
|   |   |-- catalogo_perfiles.md
|   |   `-- perfiles_emprendedores.json
|   `-- processed/
|       |-- corpus_documental.csv
|       |-- documentos_ceei_valencia.json
|       `-- enlaces_ceei_valencia.json
|-- outputs/
|-- requirements.txt
`-- README.md
```

## Entorno de trabajo

El proyecto se ha trabajado en Windows con PowerShell y un entorno virtual de Python.

Activacion habitual del entorno:

```powershell
.\.venv\Scripts\activate
```

Ejecucion de scripts desde la raiz del repositorio:

```powershell
.\.venv\Scripts\python.exe 2_scraper_ceei_seguro.py
```

Ejecucion del spider de Valencia desde su proyecto Scrapy:

```powershell
cd scraping_valencia
..\.venv\Scripts\python.exe -m scrapy crawl ceei_valencia
```

Si el entorno virtual esta en otra ruta, usar la ruta completa al ejecutable de Python del entorno.

## Etapa 1: Scraping y corpus documental

La primera etapa del TFM se centra en construir una base documental util. Todo el scraping realizado hasta ahora pertenece a esta misma etapa, aunque se hayan probado varias tecnicas.

### 1.1 Exploracion inicial

Se crearon varios scripts para entender la estructura de EmprenemJunts y validar como localizar recursos:

```text
scraper.py
scraper_multinivel.py
scraper_playwright.py
```

El aprendizaje de esta fase fue:

- Las paginas de listado contienen enlaces a fichas internas.
- Las fichas internas suelen tener URLs con el patron `?op=13&n=...`.
- El documento real no siempre esta enlazado directamente como `.pdf`; a menudo aparece detras de rutas tipo `contando2.php`.
- Playwright se probo, pero se descarto como via principal porque podia activar controles o verificaciones de la web. Para este caso se priorizo un scraping mas simple, reproducible y explicable.

### 1.2 Scraping de CEEI Elche

Para CEEI Elche se trabajo principalmente con:

```text
2_scraper_ceei_seguro.py
```

Este script usa:

- `requests` para descargar HTML y archivos.
- `BeautifulSoup` para analizar las paginas.
- `csv` para mantener indices.
- `os` y rutas locales para organizar carpetas.
- `time.sleep` para introducir pausas entre peticiones.

El scraper recorre secciones configuradas como:

```text
Fichas
Modelos_de_Negocio
Infografias
Informes_y_Publicaciones
Manuales
```

Cada seccion tiene una URL base y una carpeta local asociada. La salida principal de esta parte queda en:

```text
documentos_ceei_elche_PDF/
```

con subcarpetas por tipo de contenido:

```text
documentos_ceei_elche_PDF/
|-- Fichas/
|-- Infografias/
|-- Informes_y_Publicaciones/
|-- Modelos_de_Negocio/
`-- INDEX_DOCUMENTOS.csv
```

El indice `INDEX_DOCUMENTOS.csv` permite:

- Saber que documentos se han descargado.
- Conservar la URL de origen.
- Evitar duplicados entre ejecuciones.
- Reanudar el proceso sin empezar desde cero.

### 1.3 Paginacion y segundo nivel

El scraper de Elche no se queda en la pagina de listado. Primero extrae fichas y luego entra en cada ficha para buscar el archivo real.

La paginacion se controla con parametros como:

```text
empieza=15
cuantos=15
```

El segundo nivel se reconoce mediante:

```text
?op=13&n=...
```

Dentro de cada ficha se busca el enlace de descarga real. En muchos casos el enlace no termina en `.pdf`, sino que pasa por:

```text
contando2.php
```

Esta decision es importante para el TFM: se documenta que el scraping no solo descarga enlaces visibles, sino que resuelve la ficha intermedia antes de localizar el documento.

### 1.4 Validacion de PDFs

Antes de guardar un archivo, el scraper comprueba que realmente sea un PDF.

Criterios usados:

- Cabecera magica del archivo: `%PDF`.
- Tipo de contenido HTTP compatible con PDF.
- Descarte de respuestas HTML guardadas por error.

Esto evita contaminar el corpus con paginas HTML renombradas como PDF.

### 1.5 Extraccion de paginas sin PDF

En la seccion de modelos de negocio se detecto un caso especial: muchas fichas no ofrecian PDF descargable, pero si contenian texto util en HTML.

Para aprovechar ese contenido se creo:

```text
extraer_modelos_negocio_texto.py
```

La salida se guarda en:

```text
documentos_ceei_elche_PDF/Modelos_de_Negocio_texto/
```

Cada `.txt` conserva:

- Titulo.
- URL de origen.
- Texto limpio extraido de la pagina.

Esto permite ampliar el corpus sin forzar a que todo tenga que ser PDF.

### 1.6 Resultado de CEEI Elche

Estado del corpus de Elche preparado en esta etapa:

```text
PDFs:
  Fichas:                    121
  Infografias:                48
  Informes_y_Publicaciones:   27
  Modelos_de_Negocio:          5

Textos extraidos:
  Modelos_de_Negocio_texto:   40
```

Total aproximado:

```text
201 PDFs + 40 TXT
```

### 1.7 Scraping de CEEI Valencia con Scrapy

Para CEEI Valencia se creo un proyecto Scrapy independiente:

```text
scraping_valencia/
```

El spider principal es:

```text
scraping_valencia/scraping_valencia/spiders/ceei_valencia.py
```

Se eligio Scrapy porque permite dejar un flujo mas formal para:

- Separar el spider del resto de scripts.
- Exportar resultados directamente a JSON.
- Controlar concurrencia y pausas.
- Ejecutar primero en modo listado y despues en modo descarga.

Las paginas de partida fueron:

```text
https://ceeivalencia.emprenemjunts.es/?op=130&id=73
https://ceeivalencia.emprenemjunts.es/?op=35&quebusco=20&bbtipoagru=657
https://ceeivalencia.emprenemjunts.es/?op=35&quebusco=20&bbtipoagru=994
```

En estas paginas los documentos tambien aparecen en segundo nivel. El spider entra en las fichas `op=13&n=...` y desde ahi localiza el enlace real de descarga.

### 1.8 Decision metodologica: comparacion de alternativas de scraping

Se mantienen dos herramientas distintas porque el proyecto tambien busca probar y comparar alternativas de captacion documental. La finalidad no es declarar que una herramienta sea siempre mejor que otra, sino observar como se comportan dos aproximaciones razonables sobre fuentes documentales similares dentro del ecosistema EmprenemJunts.

Para CEEI Elche se conserva el scraper basado en `requests` y `BeautifulSoup`. Este enfoque es mas directo, facil de auditar y adecuado para una web cuya estructura ya habia sido explorada. Permite controlar manualmente las secciones, la paginacion mediante parametros como `empieza` y `cuantos`, la entrada en fichas `op=13&n=...` y la descarga final mediante enlaces como `contando2.php`.

Para CEEI Valencia se utiliza un spider Scrapy. Este enfoque permite disponer de un flujo mas formal y reutilizable: separacion entre listado, analisis de la ficha y descarga; exportacion directa a JSON; control de concurrencia; validacion de tipos de archivo; y ejecucion diferenciada entre modo listado y modo descarga.

Comparacion sintetica:

| Aspecto | Scraper de CEEI Elche | Spider de CEEI Valencia |
|---|---|---|
| Tecnologia | `requests` + `BeautifulSoup` | `Scrapy` |
| Archivo principal | `2_scraper_ceei_seguro.py` | `scraping_valencia/scraping_valencia/spiders/ceei_valencia.py` |
| Enfoque | Script secuencial | Spider/crawler estructurado |
| Flujo de trabajo | Funciones manuales y `main()` | Metodos `parse`, `parse_recurso` y `guardar_documento` |
| Descarga opcional | Descarga directa con limites configurados | Modo listado y modo descarga con `descargar=si` |
| Control de secciones | Manual, mediante lista de secciones | Mediante URLs iniciales del spider |
| Paginacion | Control explicito con `empieza` y `cuantos` | Recorrido de enlaces desde paginas iniciales |
| Metadatos | Indice CSV mas simple | JSON con metadatos mas completos |
| Formatos previstos | Principalmente PDF y TXT extraido de HTML | PDF y otros formatos detectables por extension o `content_type` |
| Reutilizacion | Media | Alta |
| Facilidad de auditoria | Alta, por ser un script directo | Media, por la arquitectura Scrapy |
| Escalabilidad | Menor | Mayor |
| Utilidad en el TFM | Permite documentar una fase exploratoria controlada | Permite comparar con una solucion mas formal de crawling |

La diferencia principal es, por tanto, de arquitectura:

```text
CEEI Elche     -> scraper secuencial con requests + BeautifulSoup
CEEI Valencia  -> spider Scrapy con flujo de crawling mas estructurado
```

La decision metodologica es mantener ambas aproximaciones para poder comparar resultados, trazabilidad, facilidad de ejecucion, riqueza de metadatos y mantenibilidad. En ambos casos se aplican criterios comunes de calidad: conservacion de URLs de origen, pausas entre peticiones, validacion del archivo descargado, evitacion de duplicados y conservacion de metadatos.

### 1.9 Modo listado y modo descarga

El spider de Valencia puede ejecutarse de dos formas.

Primero, modo listado:

```powershell
cd scraping_valencia
..\.venv\Scripts\python.exe -m scrapy crawl ceei_valencia -O ..\data\processed\enlaces_ceei_valencia.json
```

Este modo no descarga archivos. Sirve para revisar que documentos se han localizado antes de guardar nada en disco.

Despues, modo descarga:

```powershell
cd scraping_valencia
..\.venv\Scripts\python.exe -m scrapy crawl ceei_valencia -a descargar=si -O ..\data\processed\documentos_ceei_valencia.json
```

Este modo descarga los documentos validos en:

```text
documentos_ceei_valencia/
```

y genera un indice JSON con metadatos.

### 1.10 Campos del indice de Valencia

El archivo:

```text
data/processed/documentos_ceei_valencia.json
```

incluye campos como:

```text
titulo
categoria
url_listado
url_pagina
url_descarga
ruta_local
tipo_archivo
tamano_bytes
content_type
estado
```

El campo `estado` permite distinguir:

- `descargado`: archivo real guardado correctamente.
- `no_disponible`: enlace detectado, pero sin documento valido descargable.

Esto mantiene trazabilidad incluso cuando la web muestra una ficha pero no entrega un PDF real.

### 1.11 Limpieza de imagenes

Durante la descarga de Valencia se detecto un archivo de imagen `.jpg`. Como el objetivo inmediato es construir un corpus documental textual, se elimino la imagen y se retiro su registro del indice de documentos descargados.

Resultado final de Valencia:

```text
documentos_ceei_valencia/: 30 PDFs
data/processed/documentos_ceei_valencia.json: 163 registros
```

Desglose del JSON:

```text
30 registros con estado descargado y tipo pdf
133 registros con estado no_disponible y tipo pdf
0 imagenes
```

### 1.12 Criterios de calidad aplicados al scraping

En toda la etapa de scraping se han aplicado criterios pensados para que el proceso sea defendible:

- Separacion entre exploracion, descarga y procesado posterior.
- Conservacion de URLs de origen.
- Indices CSV o JSON para trazabilidad.
- Pausas entre peticiones para no saturar el servidor.
- Validacion de tipos de archivo antes de guardar.
- Evitacion de duplicados.
- Limpieza de archivos no utiles para el corpus textual.
- Uso de nombres de archivo compatibles con Windows.

## Etapa 2: Perfiles de emprendedores

Ademas del corpus documental, se preparo una primera base de perfiles de emprendedores.

Archivo original:

```text
data/perfiles/catalogo_perfiles.md
```

Archivo estructurado:

```text
data/perfiles/perfiles_emprendedores.json
```

Cada perfil incluye:

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

La clave `descripcion_embedding` no contiene embeddings reales. Es una descripcion textual optimizada para alimentar despues TF-IDF o modelos de embeddings.

Esta decision mantiene el sistema simple y explicable:

- Primero se representa cada perfil con texto descriptivo.
- Despues se comparara ese texto con los documentos.
- No se usan APIs ni modelos externos en esta etapa.

## Etapa 3: Corpus procesado

El repositorio ya contiene datos procesados en:

```text
data/processed/
```

Entre ellos:

```text
corpus_documental.csv
documentos_ceei.csv
documentos_ceei_limpio.csv
documentos_ceei_multinivel.csv
documentos_ceei_playwright.csv
documentos_ceei_valencia.json
enlaces_ceei_valencia.json
```

El archivo mas relevante ahora mismo es:

```text
data/processed/corpus_documental.csv
```

Se genera con:

```text
build_corpus.py
```

Este script:

1. Recorre documentos PDF y TXT.
2. Extrae texto de los PDFs con `pypdf`.
3. Lee los TXT generados desde paginas sin PDF.
4. Limpia texto.
5. Extrae URLs y correos detectados.
6. Crea el campo `texto_recomendador`.
7. Guarda CSV y Excel.

Salidas principales:

```text
data/processed/corpus_documental.csv
outputs/corpus_documental.xlsx
```

El CSV conserva el texto completo. El Excel recorta celdas largas para respetar el limite de 32.767 caracteres por celda.

## Estado actual del proyecto

El estado actual puede resumirse asi:

```text
1. Scraping de CEEI Elche completado.
2. Extraccion adicional de textos HTML de modelos de negocio completada.
3. Scraping de CEEI Valencia completado.
4. Corpus documental inicial generado.
5. Perfiles de emprendedores creados en JSON.
6. Proyecto preparado para iniciar el primer recomendador TF-IDF.
```

Todavia no se ha construido el recomendador final. El siguiente paso tecnico es consolidar un corpus unico y ejecutar una primera recomendacion content-based.

## Siguiente paso tecnico

El siguiente paso recomendado es construir una version inicial del recomendador basada en:

- `TF-IDF` para representar documentos y perfiles.
- `cosine similarity` para medir proximidad entre perfiles y documentos.
- Resultados explicables, mostrando que terminos conectan cada perfil con cada documento recomendado.

La primera salida esperada deberia ser:

```text
outputs/recomendaciones_tfidf.csv
outputs/recomendaciones_tfidf.xlsx
```

## Enfoque metodologico del recomendador

La recomendacion sera inicialmente content-based:

```text
perfil emprendedor -> texto descriptivo -> vector TF-IDF
recurso documental -> texto del documento -> vector TF-IDF
comparacion -> similitud coseno
```

No se usara collaborative filtering en esta fase porque no existe todavia historico de usuarios, interacciones, valoraciones ni comportamiento de navegacion.

La comparacion posterior con embeddings permitira valorar si una representacion semantica mas avanzada mejora las recomendaciones frente a la linea base TF-IDF.
