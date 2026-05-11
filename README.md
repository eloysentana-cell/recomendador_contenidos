# TFM Recomendador Documental CEEI Elche

Este repositorio contiene el trabajo inicial para construir un sistema de recomendacion documental a partir de recursos publicos del CEEI Elche y de la red EmprenemJunts.

El objetivo practico de esta fase ha sido crear una base documental descargable y ordenada: primero localizando recursos mediante scraping, despues descargando PDFs, y finalmente extrayendo texto de paginas que no tenian PDF disponible.

## Objetivo del Proyecto

El proyecto busca preparar un corpus documental que pueda alimentar despues un sistema de recomendacion. El flujo seguido hasta ahora es:

1. Explorar las paginas publicas de recursos del CEEI.
2. Extraer enlaces a documentos y fichas.
3. Descargar los documentos disponibles en PDF.
4. Clasificar los documentos por seccion.
5. Crear indices CSV para saber que se ha descargado.
6. Evitar duplicados entre ejecuciones.
7. Extraer texto de paginas utiles que no ofrecen PDF.
8. Versionar el codigo y los resultados en GitHub.

## Estructura Principal

```text
.
|-- scraper.py
|-- scraper_multinivel.py
|-- scraper_playwright.py
|-- 2_scraper_ceei_seguro.py
|-- extraer_modelos_negocio_texto.py
|-- documentos_ceei_elche/
|-- documentos_ceei_elche_PDF/
|   |-- Fichas/
|   |-- Infografias/
|   |-- Informes_y_Publicaciones/
|   |-- Modelos_de_Negocio/
|   |-- Modelos_de_Negocio_texto/
|   `-- INDEX_DOCUMENTOS.csv
|-- data/
|-- outputs/
|-- requirements.txt
`-- README.md
```

## Entorno de Trabajo

El proyecto se ha trabajado en Windows con PowerShell y un entorno virtual de Python.

Para ejecutar los scripts desde la raiz del proyecto:

```powershell
.\.venv\Scripts\python.exe 2_scraper_ceei_seguro.py
```

Y para el extractor de texto de modelos de negocio:

```powershell
.\.venv\Scripts\python.exe extraer_modelos_negocio_texto.py
```

Las dependencias principales usadas en esta fase son:

```python
import requests
from bs4 import BeautifulSoup
import csv
import os
import time
from urllib.parse import urljoin
```

`requests` descarga el HTML y los archivos. `BeautifulSoup` interpreta las paginas. `csv` permite mantener indices reutilizables. `os` organiza carpetas y rutas. `time` introduce pausas para no saturar el servidor.

## Fase 1: Scraping Inicial

Se crearon varios scripts de exploracion:

```text
scraper.py
scraper_multinivel.py
scraper_playwright.py
```

El primer enfoque (`scraper.py`) sirvio para validar que se podian localizar recursos publicos.

Despues se probo un scraper multinivel (`scraper_multinivel.py`) para recorrer mas enlaces y ampliar el numero de documentos detectados.

Tambien se probo Playwright:

```text
scraper_playwright.py
```

Esta via se descarto como metodo principal porque podia activar verificaciones de Cloudflare. Por eso se priorizo un enfoque con `requests` y `BeautifulSoup`, mas simple y estable para este caso.

Durante la depuracion se corrigio un error en `scraper_multinivel.py`:

```python
import pandas as pd
from urllib.parse import urljoin, urlparse, parse_qs
```

Habia quedado roto como `import pandas as` y `parse_qspd`, lo que impedia ejecutar el archivo correctamente.

## Fase 2: Renombrado de Archivos

Uno de los primeros scripts tenia espacios en el nombre:

```text
2 intento scrapping CEEI import requests.py
```

Se creo una version sin espacios:

```text
2_intento_scrapping_CEEI_import_requests.py
```

Esto facilita ejecutar scripts desde terminal y reduce errores al escribir rutas.

## Fase 3: Descarga Inicial de Documentos

El primer script de descarga usaba una carpeta simple:

```python
DOWNLOAD_FOLDER = "documentos_ceei_elche"
```

Eso guardaba archivos en:

```text
documentos_ceei_elche/
```

Posteriormente se creo un scraper mas seguro y estructurado:

```text
2_scraper_ceei_seguro.py
```

Este script guarda PDFs en:

```python
CARPETA_RAIZ = "documentos_ceei_elche_PDF"
INDEX_PATH = os.path.join(CARPETA_RAIZ, "INDEX_DOCUMENTOS.csv")
```

La carpeta final de PDFs queda asi:

```text
documentos_ceei_elche_PDF/
|-- Fichas/
|-- Infografias/
|-- Informes_y_Publicaciones/
|-- Modelos_de_Negocio/
-- INDEX_DOCUMENTOS.csv
```

## Fase 4: Configuracion de Secciones

El scraper define las secciones que se pueden recorrer:

```python
SECCIONES = [
    {
        "nombre": "Fichas",
        "url_base": "https://ceeielche.emprenemjunts.es/?op=35&buscar=1&quebusco=3&cuantos=15&bbtipofic=1&bgcarga=1&estado=3&bgcanal=-1",
    },
    {
        "nombre": "Modelos_de_Negocio",
        "url_base": "https://ceeielche.emprenemjunts.es/?op=35&quebusco=3&bgcanal=-1&bbtipofic=26&estado=3&orlis=1&fmto=3&buscar=1",
    },
    {
        "nombre": "Infografias",
        "url_base": "https://ceeielche.emprenemjunts.es/?op=35&quebusco=20&bbtipoagru=991",
    },
    {
        "nombre": "Informes_y_Publicaciones",
        "url_base": "https://ceeielche.emprenemjunts.es/?op=35&buscar=1&quebusco=20&bbtipoagru=667",
    },
    {
        "nombre": "Manuales",
        "url_base": "https://ceeielche.emprenemjunts.es/?op=35&quebusco=20&bbtipoagru=673",
    },
]
```

Cada seccion tiene un nombre local y una URL base. El nombre local se usa para crear subcarpetas. La URL base se usa como punto de partida para buscar fichas.

Para limitar una ejecucion a una seccion concreta se usa:

```python
SECCIONES_OBJETIVO = ["Modelos_de_Negocio"]
```

Si se quiere recorrer todo, se puede dejar vacio:

```python
SECCIONES_OBJETIVO = []
```

## Fase 5: Control de Limites

El script permite controlar cuantos documentos nuevos se intentan descargar:

```python
MAX_NUEVOS = 40
MAX_ENLACES_POR_SECCION = 200
```

`MAX_NUEVOS` indica cuantos PDFs nuevos se descargan como maximo en una ejecucion.

`MAX_ENLACES_POR_SECCION` indica cuantas fichas se exploran por seccion antes de parar.

Esto permitio hacer varias rondas:

```text
Primera ronda amplia: 95 documentos descargados.
Segunda ronda: 90 PDFs nuevos adicionales.
Tercera ronda en secciones distintas de Fichas: 17 PDFs nuevos.
```

## Fase 6: Limpieza de Nombres de Archivo

Los titulos de las paginas pueden contener signos no validos para nombres de archivo. Por eso se anadio:

```python
def limpiar_nombre_archivo(titulo):
    """Convierte un titulo web en un nombre de archivo valido para Windows."""
    nombre = "".join(c if c.isalnum() or c in " -_" else "_" for c in titulo)
    return nombre[:120].strip() or "documento"
```

Esta funcion conserva letras, numeros, espacios, guiones y guiones bajos. El resto lo cambia por `_`.

Tambien limita el nombre a 120 caracteres para evitar rutas demasiado largas en Windows.

## Fase 7: Creacion de Rutas

Cada PDF se guarda dentro de la seccion correspondiente:

```python
def ruta_pdf(titulo, seccion):
    nombre_limpio = limpiar_nombre_archivo(titulo)
    return os.path.join(CARPETA_RAIZ, seccion, f"{nombre_limpio}.pdf")
```

Por ejemplo, un documento de infografias se guarda en:

```text
documentos_ceei_elche_PDF/Infografias/nombre_del_documento.pdf
```

## Fase 8: Indice CSV y Reanudacion

Para poder ejecutar el scraper varias veces sin repetir trabajo, se creo un indice:

```text
documentos_ceei_elche_PDF/INDEX_DOCUMENTOS.csv
```

El codigo que lo carga es:

```python
def cargar_index_existente():
    """Carga el indice y crea claves por seccion para evitar duplicados."""
    if not os.path.exists(INDEX_PATH):
        return [], set()

    with open(INDEX_PATH, newline="", encoding="utf-8") as f:
        filas = list(csv.DictReader(f))

    claves = {
        (fila.get("seccion"), fila.get("url"))
        for fila in filas
        if fila.get("seccion") and fila.get("url")
    }
    return filas, claves
```

La clave usada es:

```python
(seccion, url)
```

Esto es importante porque una misma URL o contenido puede aparecer en varias secciones. Con esta clave se controla el duplicado dentro de cada seccion.

## Fase 9: Paginacion

El sitio lista documentos por paginas. Para recorrer varias paginas se usa el parametro `empieza`:

```python
def extraer_enlaces_paginados(url_base, max_total=MAX_ENLACES_POR_SECCION):
    """Recorre la paginacion y recoge enlaces a fichas de documentos."""
    enlaces = []
    pagina = 0
    cuantos = 15

    while len(enlaces) < max_total:
        url = (
            f"{url_base}&empieza={pagina * cuantos}&cuantos={cuantos}"
            if pagina > 0
            else url_base
        )
```

La primera pagina usa la URL original. Las siguientes anaden:

```text
&empieza=15&cuantos=15
&empieza=30&cuantos=15
&empieza=45&cuantos=15
```

Dentro de cada pagina se buscan enlaces a fichas:

```python
for a in soup.find_all("a", href=True):
    href = a["href"]
    titulo = a.get_text(strip=True)
    if "?op=13&n=" not in href or not titulo or len(titulo) <= 5:
        continue
```

El patron `?op=13&n=` identifica fichas de documentos dentro de EmprenemJunts.

## Fase 10: Localizacion del PDF Real

No basta con encontrar la ficha del documento. Hay que entrar en esa ficha y localizar el enlace de descarga real:

```python
def localizar_enlace_descarga(soup):
    """Encuentra el enlace interno que entrega el PDF real."""
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if "contando2.php" in href or href.endswith(".pdf"):
            return urljoin(BASE_URL, a["href"])
    return None
```

En muchas fichas el PDF aparece como:

```text
contando2.php?q=10&n=...
```

Por eso el scraper busca tanto `contando2.php` como enlaces directos terminados en `.pdf`.

## Fase 11: Validacion de PDFs

Antes de guardar un archivo se comprueba que realmente parece un PDF:

```python
def es_pdf_valido(response):
    """Comprueba el tipo MIME y la cabecera magica del archivo."""
    content_type = response.headers.get("content-type", "").lower()
    return "pdf" in content_type or response.content[:4] == b"%PDF"
```

Esto evita guardar paginas HTML con extension `.pdf` cuando el servidor no devuelve un documento real.

## Fase 12: Descarga del PDF

La descarga final se hace por bloques:

```python
with open(ruta, "wb") as f:
    for chunk in pdf_response.iter_content(8192):
        f.write(chunk)
```

Esto permite descargar archivos grandes sin cargar todo el contenido de golpe en memoria.

El flujo completo de una descarga es:

```python
def descargar_pdf(url_doc, titulo, seccion):
    ruta = ruta_pdf(titulo, seccion)
    if os.path.exists(ruta):
        print(f"      Ya existe: {os.path.basename(ruta)[:75]}...")
        return False

    response = requests.get(url_doc, headers=HEADERS, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    link_descarga = localizar_enlace_descarga(soup)
    if not link_descarga:
        return False
```

Primero calcula la ruta, despues evita repetir un archivo que ya existe, entra en la ficha, busca el enlace real y solo entonces descarga.

## Fase 13: Pausas Entre Peticiones

Para no saturar el servidor se anadieron pausas:

```python
time.sleep(1.5)
```

durante la paginacion, y:

```python
time.sleep(1.7)
```

entre descargas.

Estas pausas hacen el proceso mas lento, pero reducen el riesgo de bloqueos y son una practica mas respetuosa con el servidor.

## Fase 14: Resultado de PDFs

Despues de las rondas realizadas, el corpus de PDFs quedo organizado asi:

```text
documentos_ceei_elche_PDF/
|-- Fichas/                    121 PDFs
|-- Infografias/                48 PDFs
|-- Informes_y_Publicaciones/   27 PDFs
|-- Modelos_de_Negocio/          5 PDFs
-- INDEX_DOCUMENTOS.csv
```

Total fisico de PDFs:

```text
201 PDFs
```

El indice contiene un registro adicional respecto al total fisico porque se conserva la trazabilidad de las ejecuciones:

```text
INDEX_DOCUMENTOS.csv: 202 registros
```

## Fase 15: Caso Especial de Modelos de Negocio

Al intentar descargar 40 documentos mas de `Modelos_de_Negocio`, se detecto que la seccion tenia 49 entradas, pero solo 5 ofrecian PDF descargable.

Las 5 con PDF ya estaban guardadas en:

```text
documentos_ceei_elche_PDF/Modelos_de_Negocio/
```

Las otras 44 entradas eran paginas web sin enlace de PDF. Para aprovecharlas, se creo:

```text
extraer_modelos_negocio_texto.py
```

Este script no descarga PDFs. Extrae texto limpio desde las paginas web y lo guarda como `.txt`.

## Fase 16: Extraccion de Texto de Modelos de Negocio

La configuracion principal del extractor es:

```python
BASE_URL = "https://ceeielche.emprenemjunts.es"
URL_MODELOS = "https://ceeielche.emprenemjunts.es/?op=35&quebusco=3&bgcanal=-1&bbtipofic=26&estado=3&orlis=1&fmto=3&buscar=1"
CARPETA_SALIDA = os.path.join("documentos_ceei_elche_PDF", "Modelos_de_Negocio_texto")
INDEX_PATH = os.path.join(CARPETA_SALIDA, "INDEX_MODELOS_TEXTO.csv")
MAX_DOCUMENTOS = 40
```

La salida se guarda en:

```text
documentos_ceei_elche_PDF/Modelos_de_Negocio_texto/
```

El indice especifico se guarda en:

```text
documentos_ceei_elche_PDF/Modelos_de_Negocio_texto/INDEX_MODELOS_TEXTO.csv
```

## Fase 17: Deteccion de Paginas Sin PDF

El extractor evita procesar fichas que si tienen PDF, porque esas ya pertenecen al flujo principal:

```python
def tiene_pdf_descargable(soup):
    """Distingue fichas con PDF real de fichas que solo son pagina web."""
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if "contando2.php" in href or href.endswith(".pdf"):
            return True
    return False
```

Si una pagina tiene PDF, se salta. Si no tiene PDF, se extrae su texto.

## Fase 18: Limpieza de HTML y Extraccion de Texto

Para limpiar el contenido de una pagina:

```python
def extraer_texto_documento(soup):
    """Limpia HTML auxiliar y devuelve texto util para procesado posterior."""
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
```

Primero se eliminan scripts, estilos y bloques no utiles.

Despues se intenta recuperar el titulo:

```python
titulo = soup.find("h1")
partes = []
if titulo:
    partes.append(titulo.get_text(" ", strip=True))
```

Y finalmente se extraen lineas suficientemente informativas:

```python
for linea in texto.splitlines():
    linea = " ".join(linea.split())
    if len(linea) >= 25 and linea not in lineas:
        lineas.append(linea)
```

Se descartan lineas muy cortas y duplicadas para reducir ruido.

## Fase 19: Guardado de TXT

Cada documento de texto se guarda con titulo, URL y contenido:

```python
with open(ruta, "w", encoding="utf-8") as f:
    f.write(f"Titulo: {titulo}\n")
    f.write(f"URL: {url}\n\n")
    f.write(texto)
```

Esto facilita que mas adelante se pueda saber de donde procede cada texto.

Resultado obtenido:

```text
Modelos_de_Negocio_texto: 40 TXT
```

## Fase 20: Depuracion del Codigo

Se depuro el codigo para que fuera mas mantenible:

```text
2_scraper_ceei_seguro.py
extraer_modelos_negocio_texto.py
scraper_multinivel.py
```

Cambios principales:

- Se eliminaron salidas con caracteres problematicos para la consola de Windows.
- Se anadieron comentarios y docstrings.
- Se separaron responsabilidades en funciones.
- Se corrigieron imports rotos.
- Se anadio control de duplicados mediante CSV.
- Se anadio validacion de PDFs.
- Se anadio soporte para limitar secciones objetivo.

Tambien se actualizo `.gitignore` para evitar subir caches:

```gitignore
__pycache__/
*.py[cod]
```

## Fase 21: Validacion

Antes de hacer commit se valido que los scripts principales compilaban:

```powershell
.\.venv\Scripts\python.exe -m py_compile 2_scraper_ceei_seguro.py extraer_modelos_negocio_texto.py scraper_multinivel.py
```

Esta comprobacion no ejecuta el scraping, pero si detecta errores de sintaxis.

## Fase 22: Git, Commit y Sincronizacion

Se reviso el estado del repositorio:

```powershell
git status --short
```

Se anadieron al control de versiones:

```powershell
git add .gitignore scraper_multinivel.py 2_scraper_ceei_seguro.py extraer_modelos_negocio_texto.py documentos_ceei_elche documentos_ceei_elche_PDF
```

Se creo el commit:

```powershell
git commit -m "Add CEEI document scraping outputs"
```

Commit generado:

```text
16ec82f Add CEEI document scraping outputs
```

Y se sincronizo con GitHub:

```powershell
git push origin main
```

Repositorio remoto:

```text
https://github.com/eloysentana-cell/tfm-recomendador-ceei-elche.git
```

## Como Repetir el Proceso

Para descargar PDFs con la configuracion actual:

```powershell
.\.venv\Scripts\python.exe 2_scraper_ceei_seguro.py
```

Para cambiar la seccion objetivo, editar:

```python
SECCIONES_OBJETIVO = ["Modelos_de_Negocio"]
```

Ejemplos:

```python
SECCIONES_OBJETIVO = ["Infografias"]
SECCIONES_OBJETIVO = ["Informes_y_Publicaciones"]
SECCIONES_OBJETIVO = []
```

Para cambiar el numero de documentos nuevos:

```python
MAX_NUEVOS = 40
```

Para extraer texto de modelos de negocio sin PDF:

```powershell
.\.venv\Scripts\python.exe extraer_modelos_negocio_texto.py
```

## Estado Actual del Corpus

Resumen del material preparado:

```text
PDFs:
  Fichas:                    121
  Infografias:                 48
  Informes_y_Publicaciones:    27
  Modelos_de_Negocio:           5

Textos extraidos:
  Modelos_de_Negocio_texto:    40
```

Total aproximado:

```text
201 PDFs + 40 TXT
```

## Siguientes Pasos Recomendados

Los proximos pasos naturales del TFM serian:

1. Extraer texto de todos los PDFs.
2. Normalizar codificacion y limpiar caracteres corruptos en nombres o contenidos.
3. Crear un dataset unico con columnas como `titulo`, `seccion`, `tipo_archivo`, `ruta`, `url` y `texto`.
4. Aplicar tecnicas de embeddings o TF-IDF.
5. Construir un buscador semantico o recomendador documental.
6. Evaluar recomendaciones con consultas reales de usuarios emprendedores.

## Nota Sobre Codificacion

Algunos nombres de archivos descargados muestran caracteres mal codificados en consola de Windows. Los contenidos se han guardado en UTF-8 cuando el script escribe texto propio, pero los nombres proceden directamente de titulos web y de como PowerShell los representa.

Esto no impide usar los documentos, pero conviene normalizar nombres y metadatos en una fase posterior de limpieza.
