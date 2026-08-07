from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .configuracion import ConfiguracionAnual
from .lector_perfiles import _detectar_tabla_excel, leer_tabla_perfil


@dataclass(frozen=True)
class MetadataOrigen:
    fila_encabezado: int
    hoja: str
    filas_leidas: int
    encoding: str | None = None


def detectar_fila_encabezado(ruta_origen: Path, config: ConfiguracionAnual | None = None) -> int:
    """Devuelve la fila de encabezado, sin asumir que la tabla está en la primera hoja.

    ``config`` se conserva por compatibilidad con el flujo histórico; la detección se
    fundamenta en columnas electorales comunes y no queda atada al formato de QRO.
    """
    if ruta_origen.suffix.lower() in {".xlsx", ".xlsm"}:
        fila, _ = _detectar_tabla_excel(ruta_origen, None)
        return fila
    _, meta = leer_tabla_perfil(ruta_origen, None)
    return meta.fila_encabezado


def leer_tabla_principal(
    ruta_origen: Path,
    config: ConfiguracionAnual | None = None,
) -> tuple[pd.DataFrame, MetadataOrigen]:
    """Lee Excel o CSV y selecciona la tabla con encabezados electorales más compatibles."""
    df, meta = leer_tabla_perfil(ruta_origen, None)
    return df, MetadataOrigen(
        fila_encabezado=meta.fila_encabezado,
        hoja=meta.hoja,
        filas_leidas=meta.filas_leidas,
        encoding=meta.encoding,
    )
