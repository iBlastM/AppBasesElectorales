from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd
import streamlit as st

from src.cache_helpers import dataframe_a_csv
from src.entidades import ENTIDADES, abreviatura_entidad
from src.excel_writer import construir_dataframe_completo, escribir_xlsx
from src.lector_perfiles import leer_tabla_perfil, listar_hojas
from src.mapeo_columnas import (
    CAMPOS_CLAVE,
    CAMPOS_REQUERIDOS,
    ETIQUETAS,
    detectar_columnas_clave,
    detectar_partidos,
)
from src.perfiles import TIPOS_ELECCION, crear_perfil_generico
from src.sabana import formatear_sabana
from src.ui_textos import COLUMNAS_INDISPENSABLES, COLUMNAS_RECOMENDADAS, REQUISITOS_ARCHIVO

NOMBRES_ELECCION = {
    "ayuntamientos": "Ayuntamientos",
    "gubernatura": "Gubernatura",
    "diputaciones": "Diputaciones locales",
    "generico": "Otra / genérica",
}
PREFIJO_SALIDA = {
    "ayuntamientos": "AYUN",
    "gubernatura": "GUB",
    "diputaciones": "DIP_LOCALES",
    "generico": "ELECCION",
}
SIN_COLUMNA = ""


@st.cache_data(show_spinner=False)
def _hojas(contenido: bytes, sufijo: str) -> list[str]:
    ruta = _temporal(contenido, sufijo)
    try:
        return listar_hojas(ruta)
    finally:
        ruta.unlink(missing_ok=True)


@st.cache_data(show_spinner="Leyendo archivo...")
def _leer(contenido: bytes, sufijo: str, hoja: str | None, fila: int | None):
    ruta = _temporal(contenido, sufijo)
    try:
        return leer_tabla_perfil(ruta, None, hoja=hoja, fila_encabezado=fila)
    finally:
        ruta.unlink(missing_ok=True)


def _temporal(contenido: bytes, sufijo: str) -> Path:
    with NamedTemporaryFile(suffix=sufijo, delete=False) as tmp:
        tmp.write(contenido)
    return Path(tmp.name)


def _nombre_salida(eleccion: str, entidad: tuple[int, str] | None, anio: str) -> str:
    partes = ["SE", PREFIJO_SALIDA[eleccion], abreviatura_entidad(entidad), anio]
    return "_".join(p for p in partes if p)


def _encabezados_unicos(columnas) -> list[str]:
    """La vista previa necesita nombres únicos; los PCN repetidos se distinguen con espacios."""
    conteo: dict[str, int] = {}
    resultado = []
    for col in columnas:
        n = conteo.get(col, 0)
        conteo[col] = n + 1
        resultado.append(f"{col}{' ' * n}")
    return resultado


def _selector_columnas_clave(tabla: pd.DataFrame, token: str) -> dict[str, str | None]:
    """Muestra un selector por campo clave, precargado con la detección automática."""
    detectado = detectar_columnas_clave(tabla)
    columnas = [str(col) for col in tabla.columns]
    opciones = [SIN_COLUMNA] + columnas
    no_detectadas = [c.etiqueta for c in CAMPOS_CLAVE if c.requerido and not detectado.get(c.clave)]

    st.subheader("2. Columnas clave")
    st.caption(
        "Estas columnas alimentan PARTICIPACION, porcentajes (PCN), top 3, diferencias y VALIDACION. "
        "Se detectaron automáticamente; corrige cualquier selección si no es la adecuada."
    )
    if no_detectadas:
        st.warning("No se detectaron automáticamente: " + ", ".join(no_detectadas) + ". Selecciónalas en la lista.")

    mapeo: dict[str, str | None] = {}
    columnas_ui = st.columns(2)
    for indice, campo in enumerate(CAMPOS_CLAVE):
        valor = detectado.get(campo.clave)
        estado = "detectada" if valor else ("⚠️ requerida, no detectada" if campo.requerido else "no detectada, opcional")
        with columnas_ui[indice % 2]:
            seleccion = st.selectbox(
                f"{campo.etiqueta}{' *' if campo.requerido else ''} — {estado}",
                options=opciones,
                index=opciones.index(valor) if valor in opciones else 0,
                format_func=lambda v: "(sin columna)" if v == SIN_COLUMNA else v,
                help=campo.descripcion,
                key=f"clave_{campo.clave}_{token}",
            )
        mapeo[campo.clave] = seleccion or None
    return mapeo


def _selector_partidos(tabla: pd.DataFrame, mapeo: dict[str, str | None], token: str) -> list[str]:
    usadas = {col for col in mapeo.values() if col}
    columnas = [str(col) for col in tabla.columns if str(col) not in usadas]
    detectados = detectar_partidos(tabla, mapeo)
    firma = hashlib.sha1(repr(sorted((k, v or "") for k, v in mapeo.items())).encode()).hexdigest()[:8]

    st.subheader("3. Partidos, coaliciones y candidaturas")
    st.caption(
        "Una columna de votos por partido, coalición o candidatura independiente. "
        "Se excluyen porcentajes (P_PAN, PCN) y campos de casilla o actas. Puedes agregar o quitar columnas."
    )
    seleccion = st.multiselect(
        "Columnas de votos",
        options=columnas,
        default=[c for c in detectados if c in columnas],
        key=f"partidos_{token}_{firma}",
    )
    orden = {col: i for i, col in enumerate(columnas)}
    return sorted(seleccion, key=lambda c: orden[c])


st.set_page_config(page_title="Formateador Electoral", layout="wide")
st.title("Formateador de Bases Electorales")
st.write(
    "Sube el archivo de cómputos del instituto electoral de cualquier estado para generar la sábana "
    "estándar por sección: votos por partido con porcentaje, participación, top 3, diferencias y validación."
)

with st.expander("Columnas indispensables del archivo origen", expanded=False):
    st.markdown("**Requisitos del archivo**")
    for requisito in REQUISITOS_ARCHIVO:
        st.markdown(f"- {requisito}")
    st.markdown("**Columnas indispensables**")
    st.dataframe(COLUMNAS_INDISPENSABLES, width="stretch", hide_index=True)
    st.markdown("**Columnas recomendadas**")
    st.dataframe(COLUMNAS_RECOMENDADAS, width="stretch", hide_index=True)

archivo = st.file_uploader("Elige un archivo Excel o CSV", type=["xlsx", "xlsm", "csv"])

if archivo is None:
    st.info("A la espera de un archivo.")
    st.stop()

contenido = archivo.getvalue()
sufijo = Path(archivo.name).suffix.lower()
token = hashlib.sha1(contenido).hexdigest()[:12]
if st.session_state.get("_token") != token:
    for clave in ("_xlsx", "_csv", "_firma_salida"):
        st.session_state.pop(clave, None)
    st.session_state["_token"] = token

# 1. Datos de la elección (inferidos del nombre del archivo, editables)
auto = crear_perfil_generico(archivo.name)
st.subheader("1. Datos de la elección")
col_anio, col_eleccion, col_entidad = st.columns(3)
anio = col_anio.text_input("Año", value=auto.anio, key=f"anio_{token}").strip()
eleccion = col_eleccion.selectbox(
    "Tipo de elección",
    TIPOS_ELECCION,
    index=TIPOS_ELECCION.index(auto.eleccion),
    format_func=NOMBRES_ELECCION.get,
    key=f"eleccion_{token}",
)
opciones_entidad = [None] + [(clave, nombre) for clave, nombre, _ in ENTIDADES]
entidad = col_entidad.selectbox(
    "Entidad",
    opciones_entidad,
    index=opciones_entidad.index(auto.entidad) if auto.entidad in opciones_entidad else 0,
    format_func=lambda e: "(tomar de la columna del archivo)" if e is None else f"{e[0]:02d} - {e[1]}",
    help="Se usa para CVE_ENTIDAD y ENTIDAD cuando el archivo no trae esas columnas.",
    key=f"entidad_{token}",
)
perfil = crear_perfil_generico(archivo.name, anio=anio, eleccion=eleccion, entidad=entidad)

with st.expander("Opciones de lectura (hoja y fila de encabezados)"):
    hojas = _hojas(contenido, sufijo) if sufijo in {".xlsx", ".xlsm"} else []
    hoja_sel = None
    if hojas:
        hoja_sel = st.selectbox(
            "Hoja", [None] + hojas, format_func=lambda h: "Automática" if h is None else h, key=f"hoja_{token}"
        )
    fila_sel = st.number_input(
        "Fila de encabezados (0 = automática)", min_value=0, step=1, value=0, key=f"fila_{token}"
    )

try:
    tabla, meta = _leer(contenido, sufijo, hoja_sel, int(fila_sel) or None)
except Exception as exc:
    st.error(f"No se pudo leer el archivo: {exc}")
    st.stop()

st.caption(f"Hoja: {meta.hoja} · Fila de encabezados: {meta.fila_encabezado} · Filas leídas: {len(tabla):,}")
with st.expander("Vista previa de la tabla detectada"):
    st.dataframe(tabla.head(10), width="stretch")

mapeo = _selector_columnas_clave(tabla, token)
faltantes = [campo for campo in CAMPOS_REQUERIDOS if not mapeo.get(campo)]
if faltantes:
    st.error("Selecciona las columnas requeridas: " + ", ".join(ETIQUETAS[c] for c in faltantes) + ".")
    st.stop()

partidos = _selector_partidos(tabla, mapeo, token)
incluir_municipio = st.checkbox(
    "Incluir columna MUNICIPIO en la salida",
    value=eleccion == "ayuntamientos",
    help="El formato estándar la incluye sólo en ayuntamientos.",
    key=f"municipio_{token}_{eleccion}",
)

try:
    resultado = formatear_sabana(tabla, perfil, mapeo=mapeo, partidos=partidos, incluir_municipio=incluir_municipio)
except Exception as exc:
    st.error(str(exc))
    st.stop()

df_base = resultado.df_base
total = df_base[resultado.config.partidos + ["NULOS"]].sum(axis=1)
validas = int((total == df_base["VOTOS_EMITIDOS"]).sum())

st.subheader("4. Resultado")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Filas origen", f"{len(tabla):,}")
m2.metric("Secciones", f"{len(df_base):,}")
m3.metric("Partidos / candidaturas", len(resultado.partidos))
m4.metric("Secciones con VALIDACION = 100%", f"{validas:,} de {len(df_base):,}")

if resultado.advertencias:
    with st.expander(f"{len(resultado.advertencias)} advertencia(s)", expanded=validas < len(df_base)):
        for aviso in resultado.advertencias:
            st.warning(aviso)

with st.expander("Vista previa de la sábana (primeras 20 secciones)", expanded=True):
    vista = construir_dataframe_completo(df_base.head(20), resultado.config)
    st.dataframe(vista.set_axis(_encabezados_unicos(vista.columns), axis=1), width="stretch", hide_index=True)

nombre = _nombre_salida(eleccion, entidad, anio)
firma_salida = (token, repr(mapeo), tuple(partidos), incluir_municipio, anio, eleccion, entidad)
if st.button("Generar archivos", type="primary"):
    with st.spinner("Generando Excel con fórmulas..."):
        st.session_state["_xlsx"] = escribir_xlsx(df_base, resultado.config)
        st.session_state["_csv"] = dataframe_a_csv(construir_dataframe_completo(df_base, resultado.config))
        st.session_state["_firma_salida"] = firma_salida

if st.session_state.get("_firma_salida") == firma_salida:
    col_xlsx, col_csv = st.columns(2)
    col_xlsx.download_button(
        "Descargar Excel (.xlsx)",
        data=st.session_state["_xlsx"],
        file_name=f"{nombre}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )
    col_csv.download_button(
        "Descargar CSV (.csv)",
        data=st.session_state["_csv"],
        file_name=f"{nombre}.csv",
        mime="text/csv",
        width="stretch",
    )
elif "_firma_salida" in st.session_state:
    st.info("La configuración cambió; vuelve a generar los archivos.")
