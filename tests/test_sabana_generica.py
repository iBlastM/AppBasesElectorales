from io import BytesIO

import pandas as pd
from openpyxl import load_workbook

from src.excel_writer import escribir_xlsx
from src.formateador_simple import FormateadorSimple
from src.perfiles import crear_perfil_generico


PREFIJO_SABANA_2024 = [
    "#", "CVE_ENTIDAD", "ENTIDAD", "DF", "DL", "SECCION", "LISTA_NOMINAL", "VOTOS_EMITIDOS",
    "PARTICIPACION", "ABSTENCION", "1ER_LUGAR", "1ERO_VOTOS", "PCN", "DIF_VOTOS_2DO",
    "DIF_PCN_2DO", "2DO_LUGAR", "2DO_VOTOS", "PCN", "DIF_VOTOS_3RO", "DIF_PCN_3RO",
    "3ER_LUGAR", "3RO_VOTOS", "PCN", "1PP_MV", "VOTOS", "PCN", "DIF_2DO", "PCN",
    "2PP_MV", "VOTOS", "PCN", "DIF_3RO", "PCN", "3PP_MV", "VOTOS", "PCN",
]


def test_generico_genera_sabana_2024_y_clasifica_metricas_indispensables():
    perfil = crear_perfil_generico("GTO_AYU_2018.xlsx")
    tabla = pd.DataFrame(
        {
            "ID_ESTADO": [11, 11],
            "NOMBRE_ESTADO": ["GUANAJUATO", "GUANAJUATO"],
            "DF": [5, 5],
            "DL": [7, 7],
            "SECCION": [101, 101],
            "LISTA_NOMINAL": [1000, 200],
            "TOTAL": [700, 150],
            "NULO": [12, 3],
            "NOREG": [4, 1],
            "PAN": [350, 70],
            "PRI": [334, 76],
        }
    )

    resultado = FormateadorSimple(perfil).formatear(tabla)
    fila = resultado.df_base.iloc[0]

    assert resultado.config.encabezados_visibles[: len(PREFIJO_SABANA_2024)] == PREFIJO_SABANA_2024
    assert "CU_MUNICIPIO" not in resultado.config.encabezados_visibles
    assert "MUNICIPIO" not in resultado.config.encabezados_visibles
    assert resultado.config.partidos == ["PAN", "PRI", "CNR"]
    assert fila["VOTOS_EMITIDOS"] == 850
    assert fila["NULOS"] == 15
    assert fila["CNR"] == 5
    assert fila["PAN"] == 420
    assert fila["PRI"] == 410

    libro = load_workbook(BytesIO(escribir_xlsx(resultado.df_base, resultado.config)), data_only=False)
    hoja = libro["Formato"]
    encabezados = [celda.value for celda in hoja[1]]
    assert encabezados == resultado.config.encabezados_visibles
    assert hoja["I2"].value == "=IFERROR(H2/G2,0)"
    assert hoja.cell(2, encabezados.index("TOT_VOTOS") + 1).value.startswith("=")
    assert hoja.cell(2, encabezados.index("VALIDACION") + 1).value.startswith("=")
