"""Construcción de la base por sección para la sábana electoral estándar (cualquier estado)."""
from __future__ import annotations

import pandas as pd

from .configuracion import config_desde_perfil_simple
from .mapeo_columnas import (
    _VALORES_VACIOS,
    CAMPOS_CLAVE,
    CAMPOS_REQUERIDOS,
    ColumnasClaveFaltantes,
    detectar_columnas_clave,
    detectar_partidos,
    serie_numerica,
)
from .perfiles import PerfilFormato, normalizar_clave

# Encabezados que la sábana calcula o reserva; un partido no puede llamarse así.
ENCABEZADOS_RESERVADOS = {
    "#", "CVE_ENTIDAD", "ENTIDAD", "CU_MUNICIPIO", "MUNICIPIO", "DF", "DL", "SECCION", "LISTA_NOMINAL",
    "VOTOS_EMITIDOS", "PARTICIPACION", "ABSTENCION", "1ER_LUGAR", "1ERO_VOTOS", "PCN", "DIF_VOTOS_2DO",
    "DIF_PCN_2DO", "2DO_LUGAR", "2DO_VOTOS", "DIF_VOTOS_3RO", "DIF_PCN_3RO", "3ER_LUGAR", "3RO_VOTOS",
    "1PP_MV", "VOTOS", "DIF_2DO", "2PP_MV", "DIF_3RO", "3PP_MV", "CNR", "NULOS", "TOT_VOTOS", "VALIDACION",
}


def resolver_mapeo(
    tabla: pd.DataFrame,
    perfil: PerfilFormato,
    mapeo: dict[str, str | None] | None = None,
) -> dict[str, str | None]:
    """Combina la detección automática con las selecciones manuales.

    Una clave presente en ``mapeo`` tiene prioridad; con valor vacío o ``None``
    indica explícitamente que el origen no tiene esa columna.
    """
    resultado = detectar_columnas_clave(tabla, perfil.aliases_columnas or None)
    for campo, columna in (mapeo or {}).items():
        if campo in resultado:
            resultado[campo] = columna or None
    return resultado


def formatear_sabana(
    tabla: pd.DataFrame,
    perfil: PerfilFormato,
    mapeo: dict[str, str | None] | None = None,
    partidos: list[str] | None = None,
    incluir_municipio: bool | None = None,
):
    """Agrupa por sección y deja la base lista para ``escribir_xlsx``.

    Lanza ``ColumnasClaveFaltantes`` si falta alguna columna requerida.
    """
    from .formateador_simple import ResultadoFormateoSimple

    df = tabla.copy()
    df.columns = [str(col).strip() for col in df.columns]
    mapeo_final = resolver_mapeo(df, perfil, mapeo)

    inexistentes = [campo for campo, col in mapeo_final.items() if col and col not in df.columns]
    if inexistentes:
        raise ValueError(
            "Las columnas seleccionadas no existen en el origen: "
            + ", ".join(str(mapeo_final[c]) for c in inexistentes)
        )
    faltantes = [campo for campo in CAMPOS_REQUERIDOS if not mapeo_final.get(campo)]
    if faltantes:
        raise ColumnasClaveFaltantes(faltantes)

    advertencias: list[str] = []
    repetidas = _columnas_repetidas(mapeo_final)
    if repetidas:
        advertencias.append(f"La misma columna se asignó a varios campos: {', '.join(repetidas)}.")

    if partidos is None:
        partidos = detectar_partidos(df, mapeo_final)
    partidos = _validar_partidos(df, partidos, mapeo_final, advertencias)
    if not partidos:
        raise ValueError("No se detectaron columnas de votos por partido o candidatura. Selecciónalas manualmente.")

    # Filas sin sección numérica son totales, subtotales o notas al pie.
    seccion = serie_numerica(df[mapeo_final["seccion"]])
    sin_seccion = int(seccion.isna().sum())
    if sin_seccion:
        advertencias.append(f"Se omitieron {sin_seccion} fila(s) sin sección numérica (totales, notas o vacías).")
    df = df.loc[seccion.notna()].copy()
    if df.empty:
        raise ValueError(f"La columna de sección '{mapeo_final['seccion']}' no contiene valores numéricos.")

    trabajo = pd.DataFrame({"SECCION": seccion.loc[df.index].astype(int)}, index=df.index)
    for campo, destino in [("lista", "__LISTA"), ("votos", "__VOTOS"), ("nulos", "__NULOS"), ("CNR", "__CNR")]:
        trabajo[destino] = _numerica(df, mapeo_final.get(campo), advertencias)
    for idx, partido in enumerate(partidos):
        trabajo[f"__P_{idx}"] = _numerica(df, partido, advertencias)
    for campo in ("cve_entidad", "entidad", "municipio", "df", "dl"):
        trabajo[f"__{campo}"] = _texto(df, mapeo_final.get(campo))

    agregaciones: dict[str, object] = {col: "sum" for col in trabajo.columns if col.startswith(("__P_",))}
    agregaciones.update({"__LISTA": "sum", "__VOTOS": "sum", "__NULOS": "sum", "__CNR": "sum"})
    for campo in ("cve_entidad", "entidad", "municipio", "df", "dl"):
        agregaciones[f"__{campo}"] = _primero_no_vacio
    agrupado = trabajo.groupby("SECCION", as_index=False, sort=True).agg(agregaciones)

    config = config_desde_perfil_simple(perfil, partidos, incluir_municipio=incluir_municipio)
    cve_defecto, nombre_defecto = perfil.entidad if perfil.entidad else ("", "")

    salida = pd.DataFrame(
        {
            "#": range(1, len(agrupado) + 1),
            "CVE_ENTIDAD": [_geo(v, cve_defecto) for v in agrupado["__cve_entidad"]],
            "ENTIDAD": [_geo(v, nombre_defecto) for v in agrupado["__entidad"]],
            "MUNICIPIO": [_geo(v, "") for v in agrupado["__municipio"]],
            "DF": [_geo(v, "") for v in agrupado["__df"]],
            "DL": [_geo(v, "") for v in agrupado["__dl"]],
            "SECCION": agrupado["SECCION"].astype(int).tolist(),
            "LISTA_NOMINAL": [_entero(v) for v in agrupado["__LISTA"]],
            "VOTOS_EMITIDOS": [_entero(v) for v in agrupado["__VOTOS"]],
        }
    )
    for idx, partido in enumerate(partidos):
        salida[partido] = [_entero(v) for v in agrupado[f"__P_{idx}"]]
    salida["CNR"] = [_entero(v) for v in agrupado["__CNR"]]
    salida["NULOS"] = [_entero(v) for v in agrupado["__NULOS"]]

    geo = [col for col in config.encabezados_visibles[: config.encabezados_visibles.index("VOTOS_EMITIDOS") + 1]]
    salida = salida[geo + partidos + ["CNR", "NULOS"]]

    _advertir_validacion(salida, partidos, advertencias)
    for campo in CAMPOS_CLAVE:
        if not campo.requerido and not mapeo_final.get(campo.clave):
            if campo.clave in {"cve_entidad", "entidad"} and perfil.entidad:
                continue
            if campo.clave == "municipio" and "MUNICIPIO" not in geo:
                continue
            advertencias.append(f"No se encontró la columna '{campo.etiqueta}'; {campo.descripcion[0].lower()}{campo.descripcion[1:]}")

    return ResultadoFormateoSimple(
        df_base=salida.reset_index(drop=True),
        config=config,
        advertencias=advertencias,
        mapeo=mapeo_final,
        partidos=partidos,
    )


def _validar_partidos(
    df: pd.DataFrame, partidos: list[str], mapeo: dict[str, str | None], advertencias: list[str]
) -> list[str]:
    usadas = {col for col in mapeo.values() if col}
    resultado: list[str] = []
    vistos: set[str] = set()
    for partido in partidos:
        if partido not in df.columns:
            advertencias.append(f"La columna de partido '{partido}' no existe en el origen; se omitió.")
            continue
        if partido in usadas:
            advertencias.append(f"'{partido}' ya está asignada como columna clave; no se contó como partido.")
            continue
        if normalizar_clave(partido) in ENCABEZADOS_RESERVADOS or partido in ENCABEZADOS_RESERVADOS:
            advertencias.append(f"'{partido}' coincide con un encabezado calculado de la sábana; se omitió.")
            continue
        if partido in vistos:
            continue
        vistos.add(partido)
        resultado.append(partido)
    return resultado


def _advertir_validacion(salida: pd.DataFrame, partidos: list[str], advertencias: list[str]) -> None:
    total = salida[partidos + ["CNR", "NULOS"]].sum(axis=1)
    emitidos = salida["VOTOS_EMITIDOS"]
    distintas = salida.loc[total != emitidos, "SECCION"]
    if distintas.empty:
        return
    muestra = ", ".join(str(s) for s in distintas.head(8))
    sufijo = "..." if len(distintas) > 8 else ""
    advertencias.append(
        f"VALIDACION distinta de 100% en {len(distintas)} de {len(salida)} sección(es) "
        f"(TOT_VOTOS ≠ VOTOS_EMITIDOS): {muestra}{sufijo}. "
        "Revisa que las columnas de partidos, nulos, no registrados y total sean las correctas."
    )


def _columnas_repetidas(mapeo: dict[str, str | None]) -> list[str]:
    vistas: dict[str, int] = {}
    for col in mapeo.values():
        if col:
            vistas[col] = vistas.get(col, 0) + 1
    return [col for col, n in vistas.items() if n > 1]


def _numerica(df: pd.DataFrame, columna: str | None, advertencias: list[str]) -> pd.Series:
    if not columna:
        return pd.Series(0.0, index=df.index)
    original = df[columna]
    numeros = serie_numerica(original)
    texto = original.astype("string").fillna("").str.strip()
    invalidos = int((numeros.isna() & (texto != "") & ~texto.str.upper().isin(_VALORES_VACIOS)).sum())
    if invalidos:
        advertencias.append(f"{invalidos} valor(es) no numérico(s) en '{columna}' se tomaron como 0.")
    return numeros.fillna(0)


def _texto(df: pd.DataFrame, columna: str | None) -> pd.Series:
    if not columna:
        return pd.Series("", index=df.index, dtype="object")
    return df[columna].astype("string").fillna("").str.strip().astype(object)


def _primero_no_vacio(valores: pd.Series) -> str:
    for valor in valores:
        texto = "" if pd.isna(valor) else str(valor).strip()
        if texto:
            return texto
    return ""


def _geo(valor: object, predeterminado: object) -> object:
    texto = "" if valor is None or (isinstance(valor, float) and pd.isna(valor)) else str(valor).strip()
    if not texto:
        return predeterminado
    try:
        numero = float(texto)
    except ValueError:
        return texto
    return int(numero) if numero.is_integer() else numero


def _entero(valor: object) -> int | float:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return 0
    return int(numero) if numero.is_integer() else numero
