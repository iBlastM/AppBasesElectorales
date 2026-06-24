from pathlib import Path

from src.catalogos import construir_catalogo_dfdl
from src.configuracion import cargar_configuracion_anual
from src.formateador import FormateadorElectoral
from src.lector_origen import leer_tabla_principal


def test_formateador_agrega_2018_por_seccion(data_dir: Path, origen_2018: Path):
    config = cargar_configuracion_anual("2018", data_dir)
    catalogo = construir_catalogo_dfdl(config)
    tabla, _ = leer_tabla_principal(origen_2018, config)

    resultado = FormateadorElectoral(config, catalogo).formatear(tabla)

    assert len(resultado.df_base) == 860
    assert resultado.advertencias
    fila = resultado.df_base.loc[resultado.df_base["SECCION"] == 1].iloc[0]
    assert int(fila["CVE_ENTIDAD"]) == 22
    assert fila["ENTIDAD"] == "QUERÉTARO"
    assert int(fila["CU_MUNICIPIO"]) == 1
    assert fila["MUNICIPIO"] == "AMEALCO DE BONFIL"
    assert int(fila["DF"]) == 2
    assert int(fila["DL"]) == 8
    assert int(fila["LISTA_NOMINAL"]) == 1062
    assert int(fila["VOTOS_EMITIDOS"]) == 825
    assert int(fila["PAN"]) == 327
    assert int(fila["NULOS"]) == 24


def test_formateador_reporta_partidos_faltantes_como_cero(data_dir: Path, origen_2018: Path):
    config = cargar_configuracion_anual("2018", data_dir)
    catalogo = construir_catalogo_dfdl(config)
    tabla, _ = leer_tabla_principal(origen_2018, config)
    tabla = tabla.drop(columns=["PAN"])

    resultado = FormateadorElectoral(config, catalogo).formatear(tabla)

    assert "PAN" in resultado.df_base.columns
    assert resultado.df_base["PAN"].sum() == 0
    assert any("PAN" in aviso for aviso in resultado.advertencias)
