from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .perfiles import PerfilFormato


FORMATO_RE = re.compile(r"SE_DIP_LOCALES_QRO_(\d{4}) - Formato\.csv$", re.IGNORECASE)


@dataclass(frozen=True)
class ConfiguracionAnual:
    anio: str
    ruta_formato: Path
    encabezados_visibles: list[str]
    indice_inicio_partidos: int
    indice_nulos: int
    partidos: list[str]

    @property
    def columnas_geograficas(self) -> list[str]:
        candidatas = ["CVE_ENTIDAD", "ENTIDAD", "CU_MUNICIPIO", "MUNICIPIO", "DF", "DL", "SECCION"]
        return [col for col in candidatas if col in self.encabezados_visibles]


def obtener_anios_soportados(data_dir: Path) -> list[str]:
    anios: list[str] = []
    for ruta in data_dir.glob("SE_DIP_LOCALES_QRO_* - Formato.csv"):
        match = FORMATO_RE.match(ruta.name)
        if match:
            anios.append(match.group(1))
    return sorted(anios)


def detectar_anio(nombre_archivo: str, anios_soportados: list[str] | None = None) -> str:
    candidatos = anios_soportados or ["2018", "2021", "2024"]
    encontrados = [anio for anio in candidatos if re.search(rf"(?<!\d){anio}(?!\d)", nombre_archivo)]
    if len(encontrados) == 1:
        return encontrados[0]
    raise ValueError(
        "No se detectó un año soportado en el nombre del archivo. "
        f"El nombre debe incluir uno de: {', '.join(candidatos)}."
    )


def cargar_configuracion_anual(anio: str, data_dir: Path) -> ConfiguracionAnual:
    ruta = data_dir / f"SE_DIP_LOCALES_QRO_{anio} - Formato.csv"
    if not ruta.exists():
        raise FileNotFoundError(f"No existe formato de referencia para {anio}: {ruta}")

    with ruta.open("r", encoding="utf-8-sig", newline="") as fh:
        encabezados = next(csv.reader(fh))

    try:
        indice_3pp = encabezados.index("3PP_MV")
        indice_inicio_partidos = indice_3pp + 3
        indice_nulos = max(i for i, col in enumerate(encabezados) if col == "NULOS")
    except ValueError as exc:
        raise ValueError(f"El formato {ruta.name} no contiene los bloques esperados") from exc

    partidos = [
        encabezados[i]
        for i in range(indice_inicio_partidos, indice_nulos, 2)
        if encabezados[i] != "PCN"
    ]
    return ConfiguracionAnual(
        anio=anio,
        ruta_formato=ruta,
        encabezados_visibles=encabezados,
        indice_inicio_partidos=indice_inicio_partidos,
        indice_nulos=indice_nulos,
        partidos=partidos,
    )


def config_desde_perfil_simple(perfil: "PerfilFormato", partidos_override: list[str] | None = None) -> ConfiguracionAnual:
    geo_base = ["#", "CVE_ENTIDAD", "ENTIDAD", "MUNICIPIO", "DF", "DL", "SECCION",
                "LISTA_NOMINAL", "VOTOS_EMITIDOS"]
    participacion_cols = ["PARTICIPACION", "ABSTENCION"]
    top_cols = [
        "1ER_LUGAR", "1ERO_VOTOS", "PCN", "DIF_VOTOS_2DO", "DIF_PCN_2DO",
        "2DO_LUGAR", "2DO_VOTOS", "PCN", "DIF_VOTOS_3RO", "DIF_PCN_3RO",
        "3ER_LUGAR", "3RO_VOTOS", "PCN",
    ]
    mv_cols = [
        "1PP_MV", "VOTOS", "PCN", "DIF_2DO", "PCN",
        "2PP_MV", "VOTOS", "PCN", "DIF_3RO", "PCN",
        "3PP_MV", "VOTOS", "PCN",
    ]

    partidos = list(partidos_override if partidos_override is not None else perfil.partidos_salida)
    if "CNR" not in partidos:
        partidos.append("CNR")
    partido_cols: list[str] = []
    for partido in partidos:
        partido_cols.append(partido)
        partido_cols.append("PCN")

    nulos_cols = ["NULOS", "PCN"]
    validacion_cols = ["TOT_VOTOS", "VALIDACION"]

    encabezados = geo_base + participacion_cols + top_cols + mv_cols + partido_cols + nulos_cols + validacion_cols

    indice_inicio_partidos = len(geo_base) + len(participacion_cols) + len(top_cols) + len(mv_cols)
    indice_nulos = indice_inicio_partidos + len(partido_cols)

    return ConfiguracionAnual(
        anio=perfil.anio,
        ruta_formato=perfil.ruta_formato,
        encabezados_visibles=encabezados,
        indice_inicio_partidos=indice_inicio_partidos,
        indice_nulos=indice_nulos,
        partidos=partidos,
    )
