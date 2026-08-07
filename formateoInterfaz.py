from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

import streamlit as st

from src.cache_helpers import cargar_excel_desde_bytes, dataframe_a_csv
from src.excel_writer import construir_dataframe_completo, escribir_xlsx
from src.formateador_simple import FormateadorSimple
from src.lector_perfiles import leer_tabla_perfil
from src.perfiles import crear_perfil_generico
from src.ui_textos import COLUMNAS_INDISPENSABLES, COLUMNAS_RECOMENDADAS, REQUISITOS_ARCHIVO


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


st.set_page_config(page_title="Formateador Electoral", layout="wide")
st.title("Formateador de Bases Electorales")
st.write("Sube un archivo de cómputos electorales para generar la sábana formateada.")

st.info("El nombre del archivo debe incluir un único año de cuatro dígitos. La tabla se detecta automáticamente en Excel o CSV.")

with st.expander("Columnas indispensables del archivo origen", expanded=True):
    st.markdown("**Requisitos del archivo**")
    for requisito in REQUISITOS_ARCHIVO:
        st.markdown(f"- {requisito}")

    st.markdown("**Columnas indispensables**")
    st.dataframe(COLUMNAS_INDISPENSABLES, use_container_width=True, hide_index=True)

    st.markdown("**Columnas recomendadas**")
    st.dataframe(COLUMNAS_RECOMENDADAS, use_container_width=True, hide_index=True)

archivo = st.file_uploader("Elige un archivo Excel o CSV", type=["xlsx", "csv"])

if archivo is None:
    st.info("A la espera de un archivo.")
else:
    try:
        perfil = crear_perfil_generico(archivo.name)
        anio = perfil.anio
        contenido = archivo.getvalue()

        if archivo.name.lower().endswith(".xlsx"):
            contenido = cargar_excel_desde_bytes(contenido)

        with NamedTemporaryFile(suffix=Path(archivo.name).suffix, delete=False) as tmp:
            tmp.write(contenido)
            ruta_tmp = Path(tmp.name)

        tabla, meta = leer_tabla_perfil(ruta_tmp, perfil)
        resultado = FormateadorSimple(perfil).formatear(tabla)
        generar_xlsx = lambda: escribir_xlsx(resultado.df_base, resultado.config)

        col_anio, col_perfil, col_fila, col_origen, col_salida = st.columns(5)
        col_anio.metric("Año detectado", anio)
        col_perfil.metric("Perfil", perfil.tipo.title())
        col_fila.metric("Fila de encabezado", meta.fila_encabezado)
        col_origen.metric("Filas origen", f"{len(tabla):,}")
        col_salida.metric("Secciones", f"{len(resultado.df_base):,}")
        st.caption(f"Hoja detectada: {meta.hoja}")

        with st.expander("Vista previa de tabla detectada", expanded=False):
            st.dataframe(tabla.head(10), use_container_width=True)

        if resultado.advertencias:
            with st.expander(f"{len(resultado.advertencias)} advertencia(s)", expanded=True):
                for aviso in resultado.advertencias:
                    st.warning(aviso)

        if st.button("Generar formato electoral", type="primary"):
            with st.spinner("Generando Excel formateado..."):
                xlsx = generar_xlsx()
                df_completo = construir_dataframe_completo(resultado.df_base, resultado.config)
                csv = dataframe_a_csv(df_completo)
            st.session_state["_xlsx_formato"] = xlsx
            st.session_state["_csv_base"] = csv
            st.session_state["_nombre_salida"] = f"base_electoral_formateada_{perfil.id}.xlsx"
            st.session_state["_nombre_csv"] = f"base_electoral_base_{perfil.id}.csv"

        if "_xlsx_formato" in st.session_state:
            st.subheader("Resultado")
            st.dataframe(resultado.df_base.head(10), use_container_width=True)
            st.download_button(
                "Descargar Excel formateado (.xlsx)",
                data=st.session_state["_xlsx_formato"],
                file_name=st.session_state["_nombre_salida"],
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
            st.download_button(
                "Descargar CSV base (.csv)",
                data=st.session_state["_csv_base"],
                file_name=st.session_state["_nombre_csv"],
                mime="text/csv",
                use_container_width=True,
            )

    except Exception as exc:
        st.error(str(exc))

with st.expander("Ayuda", expanded=False):
    st.markdown(
        """
        - El archivo debe ser `.xlsx` o `.csv`.
        - El nombre debe incluir un único año de cuatro dígitos; no se limita a años o entidades preconfigurados.
        - La app busca automáticamente la hoja y la fila de encabezados con una columna de sección.
        - Se admiten CSV con preámbulos y codificaciones UTF-8, Windows-1252 o Latin-1.
        - Las columnas geográficas disponibles (entidad y municipio) se conservan en la salida.
        - La salida principal es Excel.
        """
    )
