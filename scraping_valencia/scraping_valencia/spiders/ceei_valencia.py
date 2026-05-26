import re
from pathlib import Path
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import scrapy


class CeeiValenciaSpider(scrapy.Spider):
    name = "ceei_valencia"
    allowed_domains = [
        "ceeivalencia.emprenemjunts.es",
        "emprenemjunts.es",
        "www.emprenemjunts.es",
    ]
    start_urls = [
        "https://ceeivalencia.emprenemjunts.es/?op=130&id=73",
        "https://ceeivalencia.emprenemjunts.es/?op=35&quebusco=20&bbtipoagru=657",
        "https://ceeivalencia.emprenemjunts.es/?op=35&quebusco=20&bbtipoagru=994",
    ]

    custom_settings = {
        "DOWNLOAD_DELAY": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "FEED_EXPORT_ENCODING": "utf-8",
        "ROBOTSTXT_OBEY": False,
        "USER_AGENT": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0 Safari/537.36"
        ),
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        },
    }

    def __init__(self, descargar="no", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.descargar = descargar.lower() in {"si", "sí", "true", "1", "yes"}
        self.urls_descarga_vistas = set()

    def parse(self, response):
        """Localiza las páginas de recursos enlazadas desde la sección principal."""
        for link in response.css("a"):
            texto = self.limpiar_texto(" ".join(link.css("::text").getall()))
            href = link.css("::attr(href)").get()

            if not href:
                continue

            url = urljoin(response.url, href)

            if self.es_pagina_documento(url):
                yield response.follow(
                    url,
                    callback=self.parse_recurso,
                    meta={
                        "titulo_listado": texto,
                        "url_listado": response.url,
                    },
                )

    def parse_recurso(self, response):
        """Busca el enlace real de descarga dentro de cada página de recurso."""
        titulo_pagina = self.limpiar_texto(
            " ".join(
                response.css(
                    "h1::text, h2::text, .titulo::text, .title::text, title::text"
                ).getall()
            )
        )
        titulo = response.meta.get("titulo_listado") or titulo_pagina
        categoria = self.limpiar_texto(
            " ".join(response.css(".breadcrumb ::text, nav ::text").getall())
        )

        for link in response.css("a"):
            texto = self.limpiar_texto(" ".join(link.css("::text").getall()))
            href = link.css("::attr(href)").get()

            if href:
                url = urljoin(response.url, href)
            elif self.es_boton_descarga_sin_href(texto):
                url = self.url_descarga_desde_pagina(response.url)
            else:
                continue

            if self.es_documento(url) or self.es_descarga(url, texto):
                if url in self.urls_descarga_vistas:
                    continue
                self.urls_descarga_vistas.add(url)

                registro = {
                    "titulo": titulo or self.nombre_desde_url(url),
                    "categoria": categoria,
                    "url_pagina": response.url,
                    "url_listado": response.meta.get("url_listado", ""),
                    "url_descarga": url,
                    "texto_descarga": texto,
                    "tipo": self.detectar_tipo(url),
                }

                if not self.descargar:
                    yield registro
                    continue

                yield response.follow(
                    url,
                    callback=self.guardar_documento,
                    meta={
                        "titulo": registro["titulo"],
                        "categoria": categoria,
                        "url_listado": response.meta.get("url_listado", ""),
                        "url_pagina": response.url,
                        "texto_descarga": texto,
                    },
                )

    def guardar_documento(self, response):
        """Guarda el archivo en disco y devuelve un registro para el índice."""
        titulo = response.meta["titulo"]
        url_pagina = response.meta["url_pagina"]
        url_descarga = response.url

        extension = self.detectar_extension(response)
        identificador = self.extraer_identificador(url_descarga) or self.extraer_identificador(
            url_pagina
        )

        if not self.es_archivo_valido(response, extension):
            yield {
                "titulo": titulo,
                "categoria": response.meta.get("categoria", ""),
                "url_listado": response.meta.get("url_listado", ""),
                "url_pagina": url_pagina,
                "url_descarga": url_descarga,
                "ruta_local": "",
                "tipo_archivo": extension.replace(".", ""),
                "tamano_bytes": len(response.body),
                "content_type": response.headers.get(b"Content-Type", b"").decode(
                    "latin1", errors="ignore"
                ),
                "estado": "no_disponible",
            }
            return

        nombre_archivo = self.crear_nombre_archivo(titulo, identificador, extension)
        ruta_destino = self.carpeta_documentos() / nombre_archivo
        ruta_destino.write_bytes(response.body)

        yield {
            "titulo": titulo,
            "categoria": response.meta.get("categoria", ""),
            "url_listado": response.meta.get("url_listado", ""),
            "url_pagina": url_pagina,
            "url_descarga": url_descarga,
            "ruta_local": str(ruta_destino.relative_to(self.repo_root())),
            "tipo_archivo": extension.replace(".", ""),
            "tamano_bytes": len(response.body),
            "content_type": response.headers.get(b"Content-Type", b"").decode(
                "latin1", errors="ignore"
            ),
            "estado": "descargado",
        }

    def es_documento(self, url):
        url_lower = url.lower().split("?")[0]
        extensiones = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx")
        return url_lower.endswith(extensiones)

    def es_descarga(self, url, texto):
        texto = texto.lower()
        url_lower = url.lower()
        patrones_descarga = [
            "descargar",
            "descarga",
            "download",
            "contando2",
            "fichero",
            "documento",
        ]
        return any(patron in url_lower or patron in texto for patron in patrones_descarga)

    def es_boton_descarga_sin_href(self, texto):
        texto = texto.lower()
        return "descargar archivo" in texto or "descarga" in texto

    def url_descarga_desde_pagina(self, url_pagina):
        identificador = self.extraer_identificador(url_pagina)
        if not identificador:
            return url_pagina
        return urljoin(url_pagina, f"/contando2.php?q=10&n={identificador}")

    def es_pagina_documento(self, url):
        url_lower = url.lower()
        return "emprenemjunts.es" in url_lower and "op=13" in url_lower and "n=" in url_lower

    def detectar_tipo(self, url):
        url_lower = url.lower().split("?")[0]

        if url_lower.endswith(".pdf"):
            return "pdf"
        if url_lower.endswith((".doc", ".docx")):
            return "word"
        if url_lower.endswith((".xls", ".xlsx")):
            return "excel"
        if url_lower.endswith((".ppt", ".pptx")):
            return "presentacion"
        if "contando2" in url.lower() or "download" in url.lower():
            return "descarga"
        return "enlace"

    def limpiar_texto(self, texto):
        return " ".join(texto.split())

    def nombre_desde_url(self, url):
        return url.rstrip("/").split("/")[-1].replace("-", " ").replace("_", " ")

    def detectar_extension(self, response):
        content_disposition = response.headers.get(b"Content-Disposition", b"").decode(
            "latin1", errors="ignore"
        )
        match = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', content_disposition)
        if match:
            nombre = unquote(match.group(1))
            extension = Path(nombre).suffix.lower()
            if extension:
                return extension

        content_type = response.headers.get(b"Content-Type", b"").decode(
            "latin1", errors="ignore"
        ).lower()
        if "pdf" in content_type:
            return ".pdf"
        if "word" in content_type or "officedocument.wordprocessingml" in content_type:
            return ".docx"
        if "excel" in content_type or "spreadsheetml" in content_type:
            return ".xlsx"
        if "jpeg" in content_type or "jpg" in content_type:
            return ".jpg"
        if "png" in content_type:
            return ".png"

        texto_descarga = response.meta.get("texto_descarga", "").lower()
        match = re.search(r"\(\.([a-z0-9]+)", texto_descarga)
        if match:
            return f".{match.group(1)}"

        return ".bin"

    def es_archivo_valido(self, response, extension):
        content_type = response.headers.get(b"Content-Type", b"").decode(
            "latin1", errors="ignore"
        ).lower()

        if extension == ".pdf":
            return response.body.startswith(b"%PDF") or "application/pdf" in content_type
        if extension in {".jpg", ".jpeg"}:
            return response.body.startswith(b"\xff\xd8") or "image/jpeg" in content_type
        if extension == ".png":
            return response.body.startswith(b"\x89PNG") or "image/png" in content_type
        if extension in {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}:
            return len(response.body) > 1000 and "text/html" not in content_type

        return len(response.body) > 1000 and "text/html" not in content_type

    def extraer_identificador(self, url):
        query = parse_qs(urlparse(url).query)
        return (query.get("n") or query.get("id") or [""])[0]

    def crear_nombre_archivo(self, titulo, identificador, extension):
        base = self.slug(titulo)[:90] or "documento"
        if identificador:
            base = f"{identificador}_{base}"
        return f"{base}{extension}"

    def slug(self, texto):
        texto = texto.lower()
        reemplazos = {
            "á": "a",
            "é": "e",
            "í": "i",
            "ó": "o",
            "ú": "u",
            "ü": "u",
            "ñ": "n",
            "ç": "c",
        }
        for origen, destino in reemplazos.items():
            texto = texto.replace(origen, destino)
        texto = re.sub(r"[^a-z0-9]+", "_", texto)
        return texto.strip("_")

    def repo_root(self):
        return Path(__file__).resolve().parents[3]

    def carpeta_documentos(self):
        carpeta = self.repo_root() / "documentos_ceei_valencia"
        carpeta.mkdir(parents=True, exist_ok=True)
        return carpeta

