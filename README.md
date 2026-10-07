# Pre-entrega 2: Pipeline de extracción de entidades técnicas

Pipeline que recibe un párrafo (arquitectura, log o incidente) y devuelve un objeto validado con LangChain LCEL.

## Requisitos

- Python **3.12**
- Una API key de OpenAI (`OPENAI_API_KEY`)

## Estructura

```
.
├── schemas.py        # ExtraccionTecnica (Pydantic)
├── chain.py          # ChatPromptTemplate + LCEL + with_retry
├── main.py           # Prueba asíncrona (caso claro y texto ambiguo)
├── requirements.txt
├── .env.example
└── README.md
```

## Instalación

Desde esta carpeta (`coderhouse-ai-engineering-pre-entrega-2`):

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

El `.env` ya queda con `LLM_PROVIDER=openai` y el modelo `gpt-4o-mini`. Solo falta pegar tu clave en `OPENAI_API_KEY`. El cliente que usa la cadena es `ChatOpenAI`.

## Cómo ejecutarlo

```bash
source .venv/bin/activate
python main.py
```

`main.py` llama a `process_text()` dos veces: una descripción de arquitectura y un texto ambiguo. Los logs muestran `finish_reason`, la validación y, si el JSON llega incompleto, el reintento.

## Cadena

```python
chain = prompt | model.with_structured_output(ExtraccionTecnica, include_raw=True) | validar
chain = chain.with_retry(stop_after_attempt=3)
```

`process_text(text)` ejecuta esa cadena con `.ainvoke()`. Antes de aceptar el objeto se mira `finish_reason`: si la generación se cortó por `length` o `max_tokens`, o si el JSON no cumple el esquema, se lanza un error controlado y `.with_retry()` reintenta hasta 3 veces.

## Salida esperada

```json
{
  "tecnologias": ["FastAPI", "Redis", "PostgreSQL"],
  "nivel_de_criticidad": "alta",
  "resumen_tecnico": "API con caché en Redis y persistencia en PostgreSQL; cuello de botella en conexiones concurrentes."
}
```

## Uso programático

```python
import asyncio
from dotenv import load_dotenv
from chain import process_text

load_dotenv()

async def demo():
    result = await process_text(
        "API en FastAPI con caché en Redis y datos en PostgreSQL. "
        "El pool de conexiones se agota bajo carga."
    )
    print(result.model_dump())

asyncio.run(demo())
```
