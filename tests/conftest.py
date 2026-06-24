from pathlib import Path

import pytest


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def data_dir(project_root: Path) -> Path:
    return project_root / "data"


@pytest.fixture
def formato_2018(data_dir: Path) -> Path:
    return data_dir / "SE_DIP_LOCALES_QRO_2018 - Formato.csv"


@pytest.fixture
def origen_2018(data_dir: Path) -> Path:
    return data_dir / "CASILLAS_DIPUTADOS_LOCALES.xlsx"
