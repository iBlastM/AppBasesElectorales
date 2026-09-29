"""Detección de columnas clave y columnas de votos en tablas electorales de cualquier estado.

Las columnas clave son las que alimentan las columnas calculadas de la sábana
(participación, porcentajes, top 3, diferencias y validación). Si alguna no se
detecta, la interfaz permite elegirla manualmente entre las columnas del origen.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .perfiles import ALIASES_GENERICOS, normalizar_clave


@dataclass(frozen=True)
class CampoClave:
    clave: str
    etiqueta: str
    requerido: bool
    descripcion: str


# El orden define la prioridad al asignar columnas: una columna usada por un
# campo anterior no se propone para uno posterior.
CAMPOS_CLAVE: list[CampoClave] = [
    CampoClave("seccion", "Sección", True, "Clave de sección electoral; la salida tiene una fila por sección."),
    CampoClave("lista", "Lista nominal", True, "Electores en lista nominal; se usa para PARTICIPACION y ABSTENCION."),
    CampoClave("votos", "Votos emitidos (total)", True, "Total de votos; base de todos los porcentajes (PCN) y de VALIDACION."),
    CampoClave("nulos", "Votos nulos", True, "Votos nulos; forman parte de TOT_VOTOS."),
    CampoClave("CNR", "Candidaturas no registradas", False, "Si no existe se llena con 0."),
    CampoClave("cve_entidad", "Clave de entidad", False, "Si no existe se usa la entidad seleccionada."),
    CampoClave("entidad", "Entidad", False, "Si no existe se usa la entidad seleccionada."),
    CampoClave("municipio", "Municipio", False, "Se incluye en la salida de ayuntamientos."),
    CampoClave("df", "Distrito federal", False, "Si no existe la columna DF queda vacía."),
    CampoClave("dl", "Distrito local", False, "Si no existe la columna DL queda vacía."),
]

CAMPOS_REQUERIDOS = [campo.clave for campo in CAMPOS_CLAVE if campo.requerido]
ETIQUETAS = {campo.clave: campo.etiqueta for campo in CAMPOS_CLAVE}


class ColumnasClaveFaltantes(ValueError):
    """No se pudo determinar una o más columnas clave requeridas."""

    def __init__(self, faltantes: list[str]):
        self.faltantes = faltantes
        nombres = ", ".join(ETIQUETAS.get(campo, campo) for campo in faltantes)
        super().__init__(f"No se encontraron las columnas clave: {nombres}. Selecciónalas manualmente.")


def _empieza_con_prefijo_de_porcentaje(clave: str) -> bool:
    return clave.startswith(("P_", "PORC", "PCT", "PERCENT")) or clave.endswith(("_PCT", "_PORC", "_PORCENTAJE"))


def _regla_respaldo(campo: str, clave: str) -> bool:
    """Coincidencia aproximada cuando ningún alias exacto aparece en el origen."""
    if not clave or _empieza_con_prefijo_de_porcentaje(clave):
        return False
    tokens = clave.split("_")
    es_id = tokens[0] in {"ID", "CVE", "CLAVE", "CLV", "NUM", "NO", "CU", "COD", "CODIGO"}
    if campo == "seccion":
        return clave.startswith("SECC") and clave not in {"SECCIONES"}
    if campo == "lista":
        return "LISTA" in clave or "LISTADO" in clave or tokens[0] == "LN"
    if campo == "votos":
        if "VALID" in clave:
            return False
        return ("TOTAL" in clave and "VOT" in clave) or "EMITID" in clave
    if campo == "nulos":
        return "NULO" in clave
    if campo == "CNR":
        return "NO_REG" in clave or "NOREG" in clave or "NREG" in clave or "NO_REGIST" in clave
    if campo == "municipio":
        return "MUNICIPIO" in clave and not es_id and clave != "MUNICIPIOS"
    if campo == "entidad":
        return ("ESTADO" in clave or "ENTIDAD" in clave) and not es_id
    if campo == "cve_entidad":
        return es_id and ("ESTADO" in clave or "ENT" in tokens or "ENTIDAD" in clave or "EDO" in tokens)
    if campo == "df":
        return "FEDERAL" in clave or "DTTO_FED" in clave
    if campo == "dl":
        return (
            "DISTRITO" in clave
            and "FEDERAL" not in clave
            and not clave.startswith(("CABECERA", "CABEZERA"))
            and clave != "DISTRITOS_LOCALES"
        )
    return False


def detectar_columnas_clave(df: pd.DataFrame, aliases: dict[str, list[str]] | None = None) -> dict[str, str | None]:
    """Devuelve ``{campo: columna_origen | None}`` para cada campo de ``CAMPOS_CLAVE``.

    Se prefieren los aliases exactos (en orden) y después reglas aproximadas.
    Una misma columna nunca se asigna a dos campos.
    """
    aliases = aliases or ALIASES_GENERICOS
    columnas = [str(col) for col in df.columns]
    claves = {col: normalizar_clave(col) for col in columnas}
    indice: dict[str, str] = {}
    for col in columnas:
        indice.setdefault(claves[col], col)

    usadas: set[str] = set()
    resultado: dict[str, str | None] = {}
    for campo in CAMPOS_CLAVE:
        elegido: str | None = None
        for alias in aliases.get(campo.clave, []):
            col = indice.get(normalizar_clave(alias))
            if col is not None and col not in usadas:
                elegido = col
                break
        if elegido is None:
            for col in columnas:
                if col not in usadas and _regla_respaldo(campo.clave, claves[col]):
                    elegido = col
                    break
        resultado[campo.clave] = elegido
        if elegido is not None:
            usadas.add(elegido)
    return resultado


# Primer token de columnas que describen casilla, geografía, control de actas o
# totales; nunca son votos de un partido o candidatura.
_TOKENS_NO_PARTIDISTAS = {
    "ID", "IDCASILLA", "CVE", "CLAVE", "CLV", "CU", "COD", "CODIGO", "CASILLA", "CASILLAS", "UBICACION",
    "ESTATUS", "ACTA", "ACTAS", "PAQUETE", "BOLETAS", "BOLETA", "ESCRITOS", "INCIDENTE", "DISTRITO",
    "DISTRITOS", "MUNICIPIO", "MUNICIPIOS", "ENTIDAD", "ESTADO", "LISTA", "LISTADO", "TOTAL", "TOT",
    "NUM", "NUMERO", "NO", "OBSERVACIONES", "OBSERVACION", "TRIBUNAL", "TIPO", "EXT", "SECCION",
    "SECCIONES", "SECC", "CABECERA", "CABEZERA", "RUTA", "NOMBRE", "NOM", "LN", "FECHA", "HORA",
    "LOCALIDAD", "CONSECUTIVO", "REPRESENTANTES", "UNNAMED", "COLUMNA", "VOTOS", "VOTO", "VOTACION",
    "NULOS", "NULO", "PARTICIPACION", "ABSTENCION", "VALIDACION", "DIF", "SEXO", "APEP", "APEM",
    "CIRCUNSCRIPCION", "DEMARCACION", "CONTABILIZADA", "CONTABILIZADAS", "COTEJADA", "RECONTADA",
    "PCN", "PORCENTAJE", "PORC", "PCT", "ORDEN", "FOLIO", "MESA", "CNR", "NOREG", "NREG", "SUMA",
    "SUBTOTAL", "LUGAR", "GANADOR", "DF", "DL", "ESPERADAS", "COMPUTADAS", "ZONA", "ARE", "ZORE",
    "LATITUD", "LONGITUD", "DOMICILIO", "REFERENCIA", "CAPTURA", "SHA", "CODIGO_INTEGRIDAD", "AÑO",
    "ANIO", "ANO", "PROCESO", "ELECCION", "CARGO", "SEDE", "OBS", "JUSTIFICACION", "MECANISMOS",
    "TRASLADO", "RECUENTO", "COMPUTO", "PERSONAS", "REPRESENTANTE",
}
_PREFIJOS_NO_PARTIDISTAS = ("PORC", "PCT", "PERCENT", "1ER", "2DO", "3ER", "1PP", "2PP", "3PP", "LN_")
_VALORES_VACIOS = {"", "-", "–", "—", "N/A", "NA", "S/D", "SD", "NAN", "NONE"}


def es_porcentaje_de_otra_columna(columna: str, claves_origen: set[str]) -> bool:
    """``P_PAN`` es porcentaje si también existe ``PAN``.

    Algunos institutos (p. ej. Querétaro 2018) usan ``P_MORENA-PT`` para votos de
    una combinación de coalición sin columna homóloga; esos sí son votos.
    """
    clave = normalizar_clave(columna)
    return clave.startswith("P_") and clave[2:] in claves_origen


def es_nombre_no_partidista(columna: str, claves_origen: set[str] | None = None) -> bool:
    clave = normalizar_clave(columna)
    if not clave:
        return True
    if clave.startswith("P_"):
        # Sin contexto de columnas se asume porcentaje, que es lo más común.
        return claves_origen is None or es_porcentaje_de_otra_columna(columna, claves_origen)
    if clave.startswith(_PREFIJOS_NO_PARTIDISTAS) or _empieza_con_prefijo_de_porcentaje(clave):
        return True
    if "NO_REG" in clave or "NOREG" in clave:
        return True
    primer_token = clave.split("_")[0]
    return primer_token in _TOKENS_NO_PARTIDISTAS


def serie_numerica(serie: pd.Series) -> pd.Series:
    """Convierte a número tolerando comas de miles, espacios y guiones como vacío."""
    if pd.api.types.is_numeric_dtype(serie):
        return pd.to_numeric(serie, errors="coerce")
    texto = serie.astype("string").str.strip().str.replace(",", "", regex=False)
    texto = texto.mask(texto.str.upper().isin(_VALORES_VACIOS))
    return pd.to_numeric(texto, errors="coerce")


def es_columna_de_votos(serie: pd.Series) -> bool:
    """Votos: valores numéricos, enteros y no negativos (se toleran celdas vacías)."""
    numeros = serie_numerica(serie)
    no_vacios = serie.dropna()
    if not pd.api.types.is_numeric_dtype(serie):
        no_vacios = no_vacios[~no_vacios.astype(str).str.strip().str.upper().isin(_VALORES_VACIOS)]
    validos = numeros.dropna()
    if validos.empty or len(no_vacios) == 0:
        return False
    if len(validos) / len(no_vacios) < 0.95:
        return False
    return bool((validos >= 0).all() and (validos == validos.round()).all())


def columnas_candidatas_a_votos(df: pd.DataFrame, excluir: set[str] | None = None) -> list[str]:
    """Columnas numéricas enteras no negativas (para el selector manual de partidos)."""
    excluir = excluir or set()
    return [str(col) for col in df.columns if str(col) not in excluir and es_columna_de_votos(df[col])]


def detectar_partidos(df: pd.DataFrame, mapeo: dict[str, str | None] | None = None) -> list[str]:
    """Columnas de votos por partido, coalición o candidatura independiente, en orden de origen.

    Se excluyen las columnas clave ya asignadas, porcentajes (``P_PAN``, ``PCN``),
    campos de casilla/actas/geografía y columnas no numéricas.
    """
    usadas = {col for col in (mapeo or {}).values() if col}
    claves_origen = {normalizar_clave(col) for col in df.columns}
    partidos: list[str] = []
    for col in df.columns:
        nombre = str(col)
        if nombre in usadas or es_nombre_no_partidista(nombre, claves_origen):
            continue
        if es_columna_de_votos(df[col]):
            partidos.append(nombre)
    return partidos
