from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

import streamlit as st

from src.cache_helpers import cargar_excel_desde_bytes, dataframe_a_csv
from src.catalogos import construir_catalogo_dfdl
from src.configuracion import cargar_configuracion_anual
from src.excel_writer import escribir_xlsx
from src.formateador import FormateadorElectoral
from src.formateador_simple import FormateadorSimple
from src.lector_origen import leer_tabla_principal
from src.lector_perfiles import leer_tabla_perfil
from src.perfiles import detectar_perfil
from src.ui_textos import COLUMNAS_INDISPENSABLES, COLUMNAS_RECOMENDADAS, REQUISITOS_ARCHIVO


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


st.set_page_config(page_title="Formateador Electoral", layout="wide")
st.title("Formateador de Bases Electorales")
st.write("Sube un archivo de cómputos electorales para generar la sábana formateada.")

st.info("El nombre del archivo debe incluir el año soportado: 2018, 2021 o 2024.")

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
        perfil = detectar_perfil(archivo.name, DATA_DIR)
        anio = perfil.anio
        contenido = archivo.getvalue()

        if archivo.name.lower().endswith(".xlsx"):
            contenido = cargar_excel_desde_bytes(contenido)

        with NamedTemporaryFile(suffix=Path(archivo.name).suffix, delete=False) as tmp:
            tmp.write(contenido)
            ruta_tmp = Path(tmp.name)

        if perfil.es_simple:
            tabla, meta = leer_tabla_perfil(ruta_tmp, perfil)
            resultado = FormateadorSimple(perfil).formatear(tabla)
            generar_xlsx = lambda: escribir_xlsx(resultado.df_base, resultado.config)
        else:
            if not archivo.name.lower().endswith(".xlsx"):
                raise ValueError("Los formatos de diputaciones locales se procesan desde archivos .xlsx.")
            config = cargar_configuracion_anual(anio, DATA_DIR)
            catalogo = construir_catalogo_dfdl(config)
            tabla, meta = leer_tabla_principal(ruta_tmp, config)
            resultado = FormateadorElectoral(config, catalogo).formatear(tabla)
            generar_xlsx = lambda: escribir_xlsx(resultado.df_base, config)

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
                csv = dataframe_a_csv(resultado.df_base)
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
        - El nombre debe incluir `2018`, `2021` o `2024`.
        - Para ayuntamientos y gubernatura se detecta la hoja más compatible con el formato esperado.
        - Para diputaciones locales se conserva el flujo original de Excel con fórmulas.
        - La tabla principal puede iniciar en cualquier fila; la app detecta los encabezados.
        - La salida principal es Excel.
        """
    )
    st.caption("v2024.06.24")
