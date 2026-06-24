from pathlib import Path

import pandas as pd

from src.configuracion import cargar_configuracion_anual
from src.lector_origen import detectar_fila_encabezado, leer_tabla_principal


def test_detecta_fila_20_en_excel_de_ejemplo(data_dir: Path, origen_2018: Path):
    config = cargar_configuracion_anual("2018", data_dir)
    fila = detectar_fila_encabezado(origen_2018, config)

    assert fila == 20


def test_lee_tabla_principal_desde_primera_hoja(data_dir: Path, origen_2018: Path):
    config = cargar_configuracion_anual("2018", data_dir)
    tabla, meta = leer_tabla_principal(origen_2018, config)

    assert meta.fila_encabezado == 20
    assert len(tabla) == 2648
    assert "SECCION" in tabla.columns
    assert "LISTA_NOMINAL_CASILLA" in tabla.columns
    assert "TOTAL_VOTOS" in tabla.columns
    assert "PAN" in tabla.columns
    assert pd.api.types.is_numeric_dtype(tabla["SECCION"])
