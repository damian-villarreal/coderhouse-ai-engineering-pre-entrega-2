"""Cadena LCEL: prompt + LLM estructurado + validación + reintento."""

import logging
import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.exceptions import OutputParserException
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from schemas import ExtraccionTecnica

logger = logging.getLogger("pipeline")

# Cortes por límite de tokens: el objeto todavía no es confiable.
_INCOMPLETE_FINISH_REASONS = {"length", "max_tokens"}


class IncompleteExtractionError(Exception):
    """El modelo cortó la respuesta o devolvió un JSON inválido o incompleto."""


PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Sos un extractor de entidades técnicas. "
            "Analizá el texto y completá el esquema pedido.\n"
            "- tecnologias: cada tecnología, framework, lenguaje, base de datos "
            "o servicio que el texto mencione o implique de forma reconocible. "
            "La lista no puede quedar vacía.\n"
            "- nivel_de_criticidad: baja, media o alta, según el impacto operativo. "
            "Usá alta si hay caída, pérdida de datos o un cuello de botella que "
            "impide atender tráfico.\n"
            "- resumen_tecnico: una o dos oraciones, concretas, sin relleno.\n"
            "Si el texto es ambiguo, inferí solo lo que esté justificado y "
            "dejá esa incertidumbre explícita en el resumen.",
        ),
        ("human", "Texto a analizar:\n\n{texto}"),
    ]
)


def build_model():
    """ChatOpenAI o ChatAnthropic según LLM_PROVIDER (misma convención del módulo 1)."""
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    temperature = float(os.getenv("LLM_TEMPERATURE", "0"))
    max_tokens = int(os.getenv("LLM_MAX_TOKENS", "1024"))

    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("Falta OPENAI_API_KEY en el entorno (.env).")
        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=temperature,
            max_tokens=max_tokens,
        )

    if provider == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise ValueError("Falta ANTHROPIC_API_KEY en el entorno (.env).")
        return ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
            temperature=temperature,
            max_tokens=max_tokens,
        )

    raise ValueError(
        f"Proveedor no soportado: '{provider}'. Usa 'openai' o 'anthropic'."
    )


def _ensure_complete(payload: dict) -> ExtraccionTecnica:
    """Rechaza JSON mal formado y respuestas cortadas por finish_reason."""
    raw = payload.get("raw")
    parsed = payload.get("parsed")
    parsing_error = payload.get("parsing_error")

    metadata = getattr(raw, "response_metadata", None) or {}
    finish_reason = metadata.get("finish_reason") or metadata.get("stop_reason")
    logger.info("Validando salida | finish_reason=%s", finish_reason)

    if finish_reason in _INCOMPLETE_FINISH_REASONS:
        logger.warning(
            "Respuesta incompleta (finish_reason=%s). Se solicita reintento.",
            finish_reason,
        )
        raise IncompleteExtractionError(
            f"La generación se cortó por límite de tokens (finish_reason={finish_reason})."
        )

    if parsing_error is not None or parsed is None:
        logger.warning("JSON mal formado o incompleto: %s", parsing_error)
        raise IncompleteExtractionError(
            f"No se pudo validar la extracción: {parsing_error}"
        )

    if not isinstance(parsed, ExtraccionTecnica):
        parsed = ExtraccionTecnica.model_validate(parsed)

    logger.info(
        "Extracción válida | tecnologias=%s | criticidad=%s",
        parsed.tecnologias,
        parsed.nivel_de_criticidad.value,
    )
    return parsed


@lru_cache(maxsize=1)
def get_chain():
    """prompt | model.with_structured_output(Schema) | validación, con reintento."""
    load_dotenv()
    model = build_model()
    structured = model.with_structured_output(ExtraccionTecnica, include_raw=True)
    chain = PROMPT | structured | RunnableLambda(_ensure_complete)
    return chain.with_retry(
        retry_if_exception_type=(
            IncompleteExtractionError,
            ValidationError,
            OutputParserException,
        ),
        wait_exponential_jitter=True,
        stop_after_attempt=3,
    )


async def process_text(text: str) -> ExtraccionTecnica:
    """Ejecuta el pipeline de forma asíncrona y devuelve el objeto validado."""
    if not text or not text.strip():
        raise ValueError("El texto de entrada no puede estar vacío.")

    logger.info("process_text | caracteres=%d", len(text))
    try:
        result = await get_chain().ainvoke({"texto": text.strip()})
    except Exception:
        logger.exception("El pipeline falló después de los reintentos")
        raise

    logger.info("process_text completado")
    return result
