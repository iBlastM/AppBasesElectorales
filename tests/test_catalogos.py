from pathlib import Path

import pandas as pd
import pytest

from src.catalogos import construir_catalogo_dfdl
from src.configuracion import ConfiguracionAnual, cargar_configuracion_anual


def test_catalogo_2018_tiene_mapeo_unico(data_dir: Path):
    config = cargar_configuracion_anual("2018", data_dir)
    catalogo = construir_catalogo_dfdl(config)

    assert set(["SECCION", "DF", "DL"]).issubset(catalogo.columns)
    assert len(catalogo) == 860
    fila = catalogo.loc[catalogo["SECCION"] == 1].iloc[0]
    assert int(fila["DF"]) == 2
    assert int(fila["DL"]) == 8


def test_catalogo_2021_deduplica_secciones_repetidas(data_dir: Path):
    config = cargar_configuracion_anual("2021", data_dir)
    catalogo = construir_catalogo_dfdl(config)

    assert catalogo["SECCION"].is_unique
    assert len(catalogo) == 891


def test_catalogo_ambiguo_detiene_proceso(tmp_path: Path):
    ruta = tmp_path / "SE_DIP_LOCALES_QRO_2099 - Formato.csv"
    pd.DataFrame(
        [
            {"SECCION": 1, "DF": 1, "DL": 1},
            {"SECCION": 1, "DF": 2, "DL": 1},
        ]
    ).to_csv(ruta, index=False)

    config = ConfiguracionAnual(
        anio="2099",
        ruta_formato=ruta,
        encabezados_visibles=["SECCION", "DF", "DL"],
        indice_inicio_partidos=0,
        indice_nulos=0,
        partidos=[],
    )

    with pytest.raises(ValueError, match="Catálogo ambiguo"):
        construir_catalogo_dfdl(config)
