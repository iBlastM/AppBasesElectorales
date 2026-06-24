from pathlib import Path

import pytest

from src.configuracion import (
    cargar_configuracion_anual,
    detectar_anio,
    obtener_anios_soportados,
)


def test_detectar_anio_desde_nombre():
    assert detectar_anio("CASILLAS_DIPUTADOS_LOCALES_2018.xlsx") == "2018"
    assert detectar_anio("computos-qro-2021-final.xlsx") == "2021"
    assert detectar_anio("SE_DIP_LOCALES_QRO_2024.xlsx") == "2024"


def test_rechaza_nombre_sin_anio_soportado():
    with pytest.raises(ValueError, match="No se detectó un año soportado"):
        detectar_anio("CASILLAS_DIPUTADOS_LOCALES.xlsx")


def test_obtener_anios_soportados(data_dir: Path):
    assert obtener_anios_soportados(data_dir) == ["2018", "2021", "2024"]


def test_cargar_configuracion_2018_preserva_encabezados_visibles(data_dir: Path):
    config = cargar_configuracion_anual("2018", data_dir)

    assert config.anio == "2018"
    assert config.ruta_formato.name == "SE_DIP_LOCALES_QRO_2018 - Formato.csv"
    assert config.encabezados_visibles[:8] == [
        "#",
        "CVE_ENTIDAD",
        "ENTIDAD",
        "CU_MUNICIPIO",
        "MUNICIPIO",
        "DF",
        "DL",
        "SECCION",
    ]
    assert config.encabezados_visibles.count("PCN") > 1
    assert "PAN" in config.partidos
    assert "MORENA-PT-PES" in config.partidos
    assert "NULOS" not in config.partidos
    assert config.indice_nulos > config.indice_inicio_partidos
