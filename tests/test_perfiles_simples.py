from pathlib import Path

import pandas as pd

from src.formateador_simple import FormateadorSimple
from src.lector_perfiles import leer_tabla_perfil
from src.perfiles import cargar_perfil, detectar_perfil


def _resultado(data_dir: Path, origen: str, perfil_id: str) -> pd.DataFrame:
    perfil = cargar_perfil(perfil_id, data_dir)
    tabla, _ = leer_tabla_perfil(data_dir / origen, perfil)
    return FormateadorSimple(perfil).formatear(tabla).df_base


def test_detecta_perfiles_por_nombre_de_archivo(data_dir: Path):
    assert detectar_perfil("Ayuntamientos 2018.xlsx", data_dir).id == "ayuntamientos_2018"
    assert detectar_perfil("Ayuntamiento 2021.xlsx", data_dir).id == "ayuntamientos_2021"
    assert detectar_perfil("QRO_AYUN_RESULTADOS_2024.csv", data_dir).id == "ayuntamientos_2024"
    assert detectar_perfil("2021_Gubernatura.xlsx", data_dir).id == "gubernatura_2021"
    assert detectar_perfil("CASILLAS_DIPUTADOS_LOCALES_2018.xlsx", data_dir).id == "diputaciones_2018"


def test_lector_elige_tabla_correcta_para_bases_nuevas(data_dir: Path):
    casos = [
        ("Ayuntamientos 2018.xlsx", "ayuntamientos_2018", "CASILLAS_AYUNTAMIENTOS", 23),
        ("Ayuntamiento 2021.xlsx", "ayuntamientos_2021", "Sección", 2),
        ("2021_Gubernatura.xlsx", "gubernatura_2021", "Sección", 2),
        ("QRO_AYUN_RESULTADOS_2024.csv", "ayuntamientos_2024", "CSV", 1),
    ]

    for archivo, perfil_id, hoja, fila in casos:
        perfil = cargar_perfil(perfil_id, data_dir)
        tabla, meta = leer_tabla_perfil(data_dir / archivo, perfil)

        assert meta.hoja == hoja
        assert meta.fila_encabezado == fila
        assert "SECCION" in {col.upper() for col in tabla.columns}


def test_formatea_ayuntamientos_2018(data_dir: Path):
    df = _resultado(data_dir, "Ayuntamientos 2018.xlsx", "ayuntamientos_2018")

    assert list(df.columns) == cargar_perfil("ayuntamientos_2018", data_dir).encabezados_visibles
    assert len(df) == 860
    fila = df.loc[df["SECCION"] == 1].iloc[0]
    assert fila["MUNICIPIO"] == "AMEALCO DE BONFIL"
    assert int(fila["LISTA_NOMINAL"]) == 1062
    assert int(fila["VOTOS_EMITIDOS"]) == 821
    assert fila["1ER_LUGAR"] == "PRI_PVEM"
    assert int(fila["1ERO_VOTOS"]) == 379
    assert fila["2DO_LUGAR"] == "PAN"
    assert int(fila["2DO_VOTOS"]) == 331
    assert int(fila["NULOS"]) == 19


def test_formatea_ayuntamientos_2021(data_dir: Path):
    df = _resultado(data_dir, "Ayuntamiento 2021.xlsx", "ayuntamientos_2021")

    assert list(df.columns) == cargar_perfil("ayuntamientos_2021", data_dir).encabezados_visibles
    assert len(df) == 891
    fila = df.loc[df["SECCION"] == 1].iloc[0]
    assert fila["1ER_LUGAR"] == "PRI"
    assert int(fila["1ERO_VOTOS"]) == 331
    assert fila["2DO_LUGAR"] == "PAN_QI"
    assert int(fila["2DO_VOTOS"]) == 241
    assert int(fila["FXM"]) == 5
    assert int(fila["NULOS"]) == 11


def test_formatea_ayuntamientos_2024_desde_csv_cp1252(data_dir: Path):
    df = _resultado(data_dir, "QRO_AYUN_RESULTADOS_2024.csv", "ayuntamientos_2024")

    assert list(df.columns) == cargar_perfil("ayuntamientos_2024", data_dir).encabezados_visibles
    assert len(df) == 953
    fila = df.loc[df["Seccion"] == 1].iloc[0]
    assert fila["Municipio"] == "Amealco de Bonfil"
    assert int(fila["Lista Nominal"]) == 1071
    assert int(fila["Votos Emitidos"]) == 769
    assert fila["1er Lugar"] == "MC"
    assert int(fila["Votos"]) == 363
    assert fila["2do Lugar"] == "PAN-PRI"
    assert int(fila["Votos.1"]) == 229
    assert int(fila["Nulos"]) == 31


def test_formatea_gubernatura_2021(data_dir: Path):
    df = _resultado(data_dir, "2021_Gubernatura.xlsx", "gubernatura_2021")

    assert list(df.columns) == cargar_perfil("gubernatura_2021", data_dir).encabezados_visibles
    assert len(df) == 892
    extranjero = df.loc[df["SECCION"] == 0].iloc[0]
    assert extranjero["MUNICIPIO"] == "VOTO EN EL EXTRANJERO"
    assert extranjero["1ER_LUGAR"] == "PAN"
    assert int(extranjero["1ERO_VOTOS"]) == 402
    fila = df.loc[df["SECCION"] == 1].iloc[0]
    assert fila["2DO_LUGAR"] == "PRI"
    assert int(fila["2DO_VOTOS"]) == 186
    assert int(fila["FxM"]) == 1
