"""Contrato de salida del pipeline de extracción de entidades técnicas."""

from enum import Enum

from pydantic import BaseModel, Field


class NivelCriticidad(str, Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"


class ExtraccionTecnica(BaseModel):
    """Objeto validado que devuelve el pipeline."""

    tecnologias: list[str] = Field(
        ...,
        min_length=1,
        description="Tecnologías, frameworks, lenguajes o servicios mencionados.",
    )
    nivel_de_criticidad: NivelCriticidad = Field(
        ...,
        description="Impacto operativo: baja, media o alta.",
    )
    resumen_tecnico: str = Field(
        ...,
        min_length=12,
        description="Síntesis técnica de la arquitectura o del incidente.",
    )
