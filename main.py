"""Mini-script de prueba asíncrono del pipeline de extracción."""

import asyncio
import json
import logging

from dotenv import load_dotenv

from chain import process_text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

SAMPLES = [
    (
        "arquitectura",
        "El servicio de pagos expone una API en FastAPI, cachea sesiones en Redis "
        "y persiste las órdenes en PostgreSQL. Bajo carga el pool de conexiones "
        "se agota y las requests empiezan a fallar con 503.",
    ),
    (
        "texto ambiguo",
        "Ayer el sistema se puso lento. Creo que era el server de siempre, "
        "o capaz la base. No estoy seguro de qué componente falló.",
    ),
]


async def main() -> None:
    load_dotenv()
    for name, text in SAMPLES:
        print(f"\n=== {name} ===\n")
        result = await process_text(text)
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
