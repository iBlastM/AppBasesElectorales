from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from .perfiles import PerfilFormato, normalizar_clave


ALIASES_ENCABEZADO = {
    "seccion": ["SECCION", "SECCIÓN", "SECCI_N", "SECC", "SECCION_ELECTORAL", "NUM_SECCION"],
    "lista": ["LISTA_NOMINAL", "LISTA_NOMINAL_CASILLA", "LISTADO_NOMINAL", "LN"],
    "votos": ["TOTAL_VOTOS", "VOTOS_EMITIDOS", "TOTAL_VOTACION", "VOTACION_TOTAL", "VOTOS_TOTALES"],
    "nulos": ["NULOS", "NUM_VOTOS_NULOS", "VOTOS_NULOS", "VOTO_NULO"],
    "municipio": ["MUNICIPIO", "MUNICIPIO_LOCAL", "NOMBRE_MUNICIPIO", "NOM_MUNICIPIO"],
}


@dataclass(frozen=True)
class MetadataPerfil:
    fila_encabezado: int
    hoja: str
    filas_leidas: int
    encoding: str | None = None


def leer_tabla_perfil(ruta: Path, perfil: PerfilFormato | None = None) -> tuple[pd.DataFrame, MetadataPerfil]:
    """Lee una tabla electoral aunque tenga portada, varias hojas o CSV con preámbulo.

    ``perfil`` sólo aporta aliases y señales adicionales para favorecer una hoja; la
    detección de SECCION y de los encabezados básicos no depende del estado ni año.
    """
    extension = ruta.suffix.lower()
    if extension == ".csv":
        return _leer_csv(ruta, perfil)
    if extension in {".xlsx", ".xlsm"}:
        return _leer_excel(ruta, perfil)
    raise ValueError("El archivo origen debe ser .xlsx, .xlsm o .csv.")


def _leer_csv(ruta: Path, perfil: PerfilFormato | None) -> tuple[pd.DataFrame, MetadataPerfil]:
    ultimo_error: Exception | None = None
    for encoding in ("utf-8-sig", "cp1252", "latin1"):
        try:
            bruto = _leer_csv_sin_encabezado(ruta, encoding)
            fila = _detectar_encabezado_dataframe(bruto, "CSV", perfil)
            df = _dataframe_desde_fila_encabezado(bruto, fila)
            df = _limpiar_dataframe(df, perfil)
            return df, MetadataPerfil(fila_encabezado=fila, hoja="CSV", filas_leidas=len(df), encoding=encoding)
        except (UnicodeDecodeError, csv.Error, ValueError) as exc:
            ultimo_error = exc
    raise ValueError(f"No se detectó una tabla con columna SECCION en el CSV: {ultimo_error}")


def _leer_csv_sin_encabezado(ruta: Path, encoding: str) -> pd.DataFrame:
    """Lee CSV con preámbulos de longitud variable sin asumir su primera fila.

    Pandas infiere el número de columnas a partir de la primera línea; eso falla en
    exportaciones que anteponen títulos de una sola celda. ``csv.reader`` conserva
    todas las filas y DataFrame rellena las celdas faltantes de forma segura.
    """
    with ruta.open("r", encoding=encoding, newline="") as archivo:
        muestra = archivo.read(65_536)
        archivo.seek(0)
        delimitadores = ";,\t|"
        try:
            dialecto = csv.Sniffer().sniff(muestra, delimiters=delimitadores)
            lector = csv.reader(archivo, dialecto)
        except csv.Error:
            delimitador = max(delimitadores, key=muestra.count)
            lector = csv.reader(archivo, delimiter=delimitador)
        filas = list(lector)
    if not filas:
        raise ValueError("El CSV está vacío.")
    return pd.DataFrame(filas)


def _leer_excel(ruta: Path, perfil: PerfilFormato | None) -> tuple[pd.DataFrame, MetadataPerfil]:
    fila, hoja = _detectar_tabla_excel(ruta, perfil)
    df = pd.read_excel(ruta, sheet_name=hoja, header=fila - 1)
    df = _limpiar_dataframe(df, perfil)
    return df, MetadataPerfil(fila_encabezado=fila, hoja=hoja, filas_leidas=len(df))


def _detectar_tabla_excel(ruta: Path, perfil: PerfilFormato | None) -> tuple[int, str]:
    wb = load_workbook(ruta, read_only=True, data_only=True)
    mejor: tuple[int, int, str] | None = None
    try:
        for ws in wb.worksheets:
            for numero_fila, row in enumerate(ws.iter_rows(values_only=True), start=1):
                valores = [normalizar_clave(valor) for valor in row if valor is not None and str(valor).strip()]
                puntaje = _puntuar_encabezado(valores, ws.title, perfil)
                if puntaje <= 0:
                    continue
                candidato = (puntaje, numero_fila, ws.title)
                if mejor is None or candidato[0] > mejor[0] or (candidato[0] == mejor[0] and candidato[1] < mejor[1]):
                    mejor = candidato
                # Un encabezado con SECCION y un conjunto amplio de columnas no
                # mejora materialmente al recorrer miles de filas de datos.
                if puntaje >= 50:
                    break
    finally:
        wb.close()

    if mejor is None:
        raise ValueError("No se detectó una tabla principal con columna SECCION en ninguna hoja.")
    _, fila, hoja = mejor
    return fila, hoja


def _detectar_encabezado_dataframe(bruto: pd.DataFrame, hoja: str, perfil: PerfilFormato | None) -> int:
    mejor: tuple[int, int] | None = None
    for indice, row in bruto.iterrows():
        valores = [normalizar_clave(valor) for valor in row.tolist() if pd.notna(valor) and str(valor).strip()]
        puntaje = _puntuar_encabezado(valores, hoja, perfil)
        if puntaje <= 0:
            continue
        candidato = (puntaje, indice + 1)
        if mejor is None or candidato[0] > mejor[0] or (candidato[0] == mejor[0] and candidato[1] < mejor[1]):
            mejor = candidato
        if puntaje >= 50:
            break
    if mejor is None:
        raise ValueError("No se detectó una fila de encabezados con columna SECCION.")
    return mejor[1]


def _dataframe_desde_fila_encabezado(bruto: pd.DataFrame, fila: int) -> pd.DataFrame:
    encabezados = [str(valor).strip() if pd.notna(valor) else "" for valor in bruto.iloc[fila - 1].tolist()]
    datos = bruto.iloc[fila:].copy()
    datos.columns = encabezados
    return datos


def _puntuar_encabezado(valores: list[str], hoja: str, perfil: PerfilFormato | None) -> int:
    conjunto = set(valores)
    aliases = {clave: list(valores_alias) for clave, valores_alias in ALIASES_ENCABEZADO.items()}
    if perfil is not None:
        for clave, valores_alias in perfil.aliases_columnas.items():
            aliases.setdefault(clave, [])
            aliases[clave].extend(valores_alias)

    aliases_normalizados = {
        clave: {normalizar_clave(alias) for alias in valores_alias}
        for clave, valores_alias in aliases.items()
    }
    if not conjunto & aliases_normalizados["seccion"]:
        return 0

    # SECCION es indispensable. Los demás campos distinguen encabezados reales de
    # títulos, notas o tablas auxiliares que sólo mencionan la palabra "sección".
    puntaje = 30
    # Un encabezado tabular suele contener varias columnas, aun cuando el estado
    # use nombres de métricas distintos a los aliases conocidos.
    puntaje += min(len(conjunto), 20)
    for clave in ("lista", "votos", "nulos", "municipio"):
        if conjunto & aliases_normalizados.get(clave, set()):
            puntaje += 15

    if perfil is not None:
        for partido in perfil.partidos_salida:
            aliases_partido = perfil.aliases_columnas.get(partido, [partido])
            if conjunto & {normalizar_clave(alias) for alias in aliases_partido}:
                puntaje += 2

    hoja_norm = normalizar_clave(hoja)
    if hoja_norm in {"SECCION", "SECCIONES", "DATOS"} or hoja_norm.endswith("_SECCION"):
        puntaje += 5
    if "CASILLA" in hoja_norm:
        puntaje += 2
    return puntaje


def _limpiar_dataframe(df: pd.DataFrame, perfil: PerfilFormato | None) -> pd.DataFrame:
    df = df.dropna(axis=1, how="all").dropna(how="all").copy()
    df.columns = [str(col).strip() for col in df.columns]

    aliases_seccion = (perfil.aliases_columnas.get("seccion", []) if perfil is not None else []) + ALIASES_ENCABEZADO["seccion"]
    seccion_col = _resolver_columna(df, aliases_seccion)
    if seccion_col is None:
        raise ValueError("La tabla detectada no contiene una columna equivalente a SECCION.")
    if seccion_col != "SECCION":
        df = df.rename(columns={seccion_col: "SECCION"})

    df["SECCION"] = pd.to_numeric(df["SECCION"], errors="coerce")
    df = df.dropna(subset=["SECCION"]).copy()
    df["SECCION"] = df["SECCION"].astype(int)
    return df.reset_index(drop=True)


def _resolver_columna(df: pd.DataFrame, aliases: list[str]) -> str | None:
    indice = {normalizar_clave(col): col for col in df.columns}
    for alias in aliases:
        col = indice.get(normalizar_clave(alias))
        if col is not None:
            return col
    return None
