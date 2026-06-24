from pathlib import Path

from src.cache_helpers import cargar_excel_desde_bytes


def test_cargar_excel_desde_bytes(origen_2018: Path):
    data = origen_2018.read_bytes()
    wb_bytes = cargar_excel_desde_bytes(data)

    assert wb_bytes[:2] == b"PK"
