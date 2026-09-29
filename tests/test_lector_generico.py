from pathlib import Path

import pandas as pd
from openpyxl import Workbook

from src.formateador_simple import FormateadorSimple
from src.lector_origen import leer_tabla_principal
from src.lector_perfiles import leer_tabla_perfil
from src.perfiles import crear_perfil_generico, detectar_perfil


def _crear_excel_con_tabla_secundaria(ruta: Path) -> None:
    libro = Workbook()
    portada = libro.active
    portada.title = "Portada"
    portada.append(["Resultados electorales"])
    portada.append(["La tabla está en la siguiente hoja"])

    datos = libro.create_sheet("Resultados")
    datos.append(["Proceso electoral estatal"])
    datos.append(["Corte final"])
    datos.append([
        "Clave entidad", "Estado", "Clave municipio", "Municipio", "Sección",
        "Lista nominal", "Votos emitidos", "Votos nulos", "DF", "DL", "PAN", "MORENA",
    ])
    datos.append([11, "GUANAJUATO", 1, "ABASOLO", 101, 1000, 700, 12, 5, 9, 350, 338])
    datos.append([11, "GUANAJUATO", 1, "ABASOLO", 101, 200, 150, 3, 5, 9, 70, 77])
    libro.save(ruta)


def test_lector_generico_encuentra_hoja_secundaria_y_preserva_geografia(tmp_path: Path):
    ruta = tmp_path / "GTO_AY_2030.xlsx"
    _crear_excel_con_tabla_secundaria(ruta)
    perfil = crear_perfil_generico(ruta.name)

    tabla, meta = leer_tabla_perfil(ruta, perfil)
    resultado = FormateadorSimple(perfil).formatear(tabla).df_base

    assert meta.hoja == "Resultados"
    assert meta.fila_encabezado == 3
    assert list(tabla["SECCION"]) == [101, 101]
    fila = resultado.iloc[0]
    assert fila["CVE_ENTIDAD"] == 11
    assert fila["ENTIDAD"] == "GUANAJUATO"
    # El formato estándar no lleva clave municipal; sí el nombre en ayuntamientos ("AY").
    assert "CU_MUNICIPIO" not in resultado.columns
    assert fila["MUNICIPIO"] == "ABASOLO"
    assert fila["DF"] == 5
    assert fila["DL"] == 9
    assert fila["LISTA_NOMINAL"] == 1200
    assert fila["VOTOS_EMITIDOS"] == 850
    assert fila["PAN"] == 420
    assert fila["MORENA"] == 415


def test_lector_generico_detecta_csv_con_preambulo_y_cualquier_anio(tmp_path: Path):
    ruta = tmp_path / "GTO_AY_2027.csv"
    ruta.write_text(
        "Resultados preliminares\n"
        "Fuente;Instituto electoral\n"
        "ID_ESTADO;NOMBRE_ESTADO;SECCION;LISTA_NOMINAL;TOTAL_VOTOS;NULOS;PAN\n"
        "11;GUANAJUATO;101;1000;700;12;350\n",
        encoding="utf-8",
    )

    perfil = crear_perfil_generico(ruta.name)
    tabla, meta = leer_tabla_principal(ruta)
    resultado = FormateadorSimple(perfil).formatear(tabla).df_base

    assert perfil.anio == "2027"
    assert meta.hoja == "CSV"
    assert meta.fila_encabezado == 3
    assert tabla.loc[0, "SECCION"] == 101
    assert resultado.loc[0, "CVE_ENTIDAD"] == 11
    assert resultado.loc[0, "PAN"] == 350


def test_deteccion_heredada_reconoce_abreviatura_ayu(data_dir: Path):
    assert detectar_perfil("GTO_AYU_2018.xlsx", data_dir).id == "ayuntamientos_2018"


def test_lector_principal_admite_excel_en_hoja_secundaria(tmp_path: Path):
    ruta = tmp_path / "DIP_2030.xlsx"
    _crear_excel_con_tabla_secundaria(ruta)

    tabla, meta = leer_tabla_principal(ruta)

    assert meta.hoja == "Resultados"
    assert isinstance(tabla, pd.DataFrame)
    assert "SECCION" in tabla.columns
