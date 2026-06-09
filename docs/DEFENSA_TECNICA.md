# Defensa tecnica del sistema recomendador

## 1. Hipotesis defendible

La hipotesis del proyecto es que es viable construir un recomendador de contenidos para emprendedores basado en tecnicas de procesamiento de lenguaje natural y similitud semantica, sin depender de historicos reales de usuarios.

Formulacion recomendada para la presentacion:

> Es posible construir un sistema recomendador content-based para perfiles emprendedores que, a partir de un corpus documental publico y perfiles textuales estructurados, genere recomendaciones utiles mediante TF-IDF, embeddings y similitud coseno, sin necesidad inicial de filtrado colaborativo.

Esta formulacion es mas solida que decir simplemente que el recomendador funciona, porque explica que se evalua la viabilidad tecnica del enfoque y no un producto comercial final.

## 2. Estado tecnico del repositorio

El proyecto contiene ya una arquitectura funcional por fases:

1. Captacion documental de CEEI Elche.
2. Captacion documental de CEEI Valencia.
3. Conversion de fichas HTML a TXT cuando no hay PDF descargable.
4. Construccion de corpus documental unificado.
5. Validacion del corpus.
6. Caracterizacion de perfiles emprendedores.
7. Recomendador TF-IDF como linea base explicable.
8. Generacion de embeddings locales de documentos.
9. Generacion de embeddings locales de perfiles.
10. Ranking semantico mediante similitud coseno.
11. Comparacion TF-IDF frente a embeddings.
12. Demostrador web local con Streamlit.

Valores de referencia documentados en el README:

```text
Corpus consolidado: 423 documentos
Documentos utiles >= 300 caracteres: 413
CEEI Elche: 260 documentos en corpus
CEEI Valencia: 163 documentos en corpus
Embeddings generados: 413 documentos
Dimension embedding: 384
Modelo embedding: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

## 3. Arquitectura conceptual

```text
Fuentes documentales publicas
        |
        v
Scraping y extraccion de texto
        |
        v
Corpus documental consolidado
        |
        +-------------------------+
        |                         |
        v                         v
Representacion TF-IDF      Embeddings semanticos
        |                         |
        v                         v
Similitud coseno           Similitud coseno
        |                         |
        +------------+------------+
                     v
          Ranking de recomendaciones
                     |
                     v
          Demostrador web local
```

## 4. Por que content-based y no collaborative filtering

Se ha elegido un sistema content-based porque el proyecto no dispone de usuarios reales, historicos de clics, valoraciones, descargas o interacciones.

El filtrado colaborativo necesita una matriz usuario-item suficientemente rica. En este proyecto esa matriz no existe. Simularla seria metodologicamente debil, porque se estaria evaluando un comportamiento de usuario inventado.

Por tanto, la decision correcta es usar el contenido documental como fuente principal de informacion.

Respuesta para la tutora:

> He descartado collaborative filtering en esta fase porque no hay historico real de interacciones. El proyecto parte de documentos y perfiles, no de usuarios activos. Por eso la aproximacion content-based es mas coherente, reproducible y defendible.

## 5. Por que TF-IDF

TF-IDF se utiliza como linea base porque es simple, rapido e interpretable.

Permite explicar por que un documento aparece recomendado: existe coincidencia entre terminos relevantes del perfil y terminos relevantes del documento.

Fortalezas:

- Bajo coste computacional.
- Alta explicabilidad.
- Facil reproduccion.
- Buena linea base academica.

Limitaciones:

- Depende de coincidencias lexicas.
- No capta bien sinonimos.
- Penaliza documentos relevantes que usan vocabulario distinto al perfil.

Respuesta para la tutora:

> He usado TF-IDF como baseline explicable. No pretende ser la solucion final mas avanzada, sino un punto de comparacion robusto para evaluar si los embeddings aportan mejora semantica.

## 6. Por que embeddings

Los embeddings convierten textos en vectores densos. A diferencia de TF-IDF, no se limitan a contar palabras. Buscan representar significado.

Esto permite que una consulta sobre `empresa rural agroalimentaria` pueda acercarse a documentos que hablen de `desarrollo territorial`, `economia circular`, `GAL`, `cohesion territorial` o `autoempleo rural`, aunque no coincidan literalmente todas las palabras.

Respuesta para la tutora:

> Los embeddings se incorporan para superar la limitacion lexica de TF-IDF. TF-IDF compara vocabulario; los embeddings comparan representaciones semanticas.

## 7. Modelo utilizado y justificacion

Modelo usado:

```text
sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

Justificacion:

1. Es multilingue, adecuado para corpus en espanol y potencialmente valenciano u otros idiomas.
2. Genera vectores de 384 dimensiones, lo que permite trabajar en local con un coste razonable.
3. Esta orientado a tareas de sentence similarity y semantic search.
4. Permite ejecutar el sistema sin enviar datos a APIs externas.
5. Encaja con el tamano actual del proyecto: 413 documentos vectorizados, 8 perfiles y una web local de demostracion.

Decision defendible:

> No he elegido un modelo mas grande porque el objetivo del proyecto no es maximizar rendimiento bruto, sino construir una prueba funcional, reproducible y ejecutable en local. Un modelo ligero reduce dependencias, coste computacional y complejidad de despliegue.

Riesgo:

- Puede perder matices frente a modelos mas grandes.
- El limite de entrada del modelo obliga a recortar textos largos.
- No se ha realizado todavia una evaluacion humana sistematica.

## 8. Por que similitud coseno

La similitud coseno mide el angulo entre vectores. Es adecuada cuando interesa comparar orientacion semantica mas que magnitud.

En el repositorio, los embeddings se generan normalizados. Por eso el producto escalar entre vectores normalizados es equivalente a similitud coseno.

Respuesta para la tutora:

> Uso similitud coseno porque es una metrica estandar en recuperacion semantica. Como los vectores estan normalizados, el producto escalar implementado equivale a calcular la similitud coseno.

## 9. Por que Streamlit para la web local

La web local se ha desarrollado con Streamlit.

Justificacion:

- Permite crear un demostrador rapido sin desarrollar una arquitectura frontend/backend completa.
- Es suficiente para probar consultas libres, perfiles similares y documentos recomendados.
- Reduce complejidad tecnica respecto a React + API.
- Es adecuado para una prueba de concepto academica.

Respuesta para la tutora:

> He usado Streamlit porque en esta fase necesitaba validar el recomendador, no construir un producto frontend completo. Si el proyecto escalara, una evolucion razonable seria separar backend FastAPI y frontend React.

## 10. Riesgos y limitaciones

1. No hay validacion con usuarios reales.
2. No hay feedback loop todavia.
3. El corpus depende de la calidad de las fuentes captadas.
4. Los perfiles emprendedores son predefinidos y pueden no cubrir casos atipicos.
5. Los documentos largos se recortan para generar embeddings.
6. No se usa todavia una base de datos vectorial.
7. La comparacion TF-IDF vs embeddings mide solapamiento de rankings, pero no necesariamente utilidad percibida.

## 11. Escalabilidad futura

Mejoras futuras defendibles:

1. Feedback loop con valoraciones de usuarios.
2. Evaluacion cualitativa con expertos o emprendedores reales.
3. Base de datos vectorial: FAISS, Chroma o Qdrant.
4. Sistema hibrido TF-IDF + embeddings.
5. Deteccion de perfiles atipicos.
6. Re-ranking con un LLM si se dispone de recursos.
7. API backend con FastAPI.
8. Frontend React para uso real.
9. Dockerizacion para reproducibilidad y despliegue.

## 12. Preguntas dificiles y respuestas

### Por que no RAG?

Porque el objetivo actual es recomendar documentos, no responder preguntas sobre ellos. RAG podria ser una fase futura para generar explicaciones conversacionales sobre las recomendaciones.

### Por que no usar directamente ChatGPT?

Porque se busca un sistema reproducible, trazable y ejecutable en local. El sistema actual genera rankings a partir de vectores y similitud, no respuestas opacas de un LLM.

### Como sabes que recomienda bien?

Ahora mismo hay validacion tecnica: corpus, rankings, scores, comparacion TF-IDF/embeddings y demostrador funcional. Falta la validacion de utilidad con usuarios o expertos, que es precisamente la mejora futura principal.

### Que harias si el perfil del usuario es muy atipico?

Compararia la consulta contra los perfiles predefinidos y analizaria si todos los scores son bajos. Si ocurre, el sistema deberia marcar el caso como atipico, evitar una recomendacion demasiado segura y proponer exploracion documental o crear un nuevo perfil.

### Que aporta el proyecto aunque no sea perfecto?

Aporta una arquitectura completa y reproducible: captacion documental, corpus, perfiles, baseline TF-IDF, embeddings, comparacion y demostrador web. Es una prueba de viabilidad tecnica del recomendador.