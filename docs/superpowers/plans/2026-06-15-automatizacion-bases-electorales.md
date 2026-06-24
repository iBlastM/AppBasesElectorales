# Automatizacion Bases Electorales Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. User instruction for this project: do not use any `git` command.

**Goal:** Build a Streamlit app that reads electoral Excel files, detects the real table in the first sheet, aggregates casilla-level data by section, maps annual `DF/DL`, and exports the annual target format as `.xlsx` with formulas and styles.

**Architecture:** Follow the existing `BaseProgramasSociales` style: a Streamlit entrypoint plus focused modules under `src/`. The pipeline is split into configuration discovery, annual catalogs, source table reading, section aggregation, and workbook writing.

**Tech Stack:** Python, pandas, openpyxl, Streamlit, pytest.

---

## File Structure

- Create `AutomatizacionBasesElectorales/requirements.txt`: runtime and test dependencies.
- Create `AutomatizacionBasesElectorales/formateoInterfaz.py`: Streamlit UI.
- Create `AutomatizacionBasesElectorales/src/__init__.py`: package marker.
- Create `AutomatizacionBasesElectorales/src/configuracion.py`: year detection, reference CSV parsing, target column metadata.
- Create `AutomatizacionBasesElectorales/src/catalogos.py`: annual `SECCION -> DF/DL` catalogs from reference formats.
- Create `AutomatizacionBasesElectorales/src/lector_origen.py`: first-sheet header detection and source table loading.
- Create `AutomatizacionBasesElectorales/src/formateador.py`: aggregation by section and target-row preparation.
- Create `AutomatizacionBasesElectorales/src/excel_writer.py`: `.xlsx` export with formulas, styles, and hidden helper sheet.
- Create `AutomatizacionBasesElectorales/src/cache_helpers.py`: cached loading and download helpers for Streamlit.
- Create `AutomatizacionBasesElectorales/tests/test_configuracion.py`
- Create `AutomatizacionBasesElectorales/tests/test_catalogos.py`
- Create `AutomatizacionBasesElectorales/tests/test_lector_origen.py`
- Create `AutomatizacionBasesElectorales/tests/test_formateador.py`
- Create `AutomatizacionBasesElectorales/tests/test_excel_writer.py`

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `src/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create dependency file**

Write `requirements.txt`:

```text
streamlit
pandas
openpyxl
pytest
```

- [ ] **Step 2: Create package marker**

Write `src/__init__.py` as an empty file.

- [ ] **Step 3: Create shared test fixtures**

Write `tests/conftest.py`:

```python
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
```

- [ ] **Step 4: Verify scaffold imports**

Run:

```powershell
python -m pytest -q
```

Expected: pytest runs with no collected tests or all scaffold-only tests pass.

---

## Task 2: Annual Configuration Discovery

**Files:**
- Create: `src/configuracion.py`
- Create: `tests/test_configuracion.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_configuracion.py`:

```python
from pathlib import Path

import pytest

from src.configuracion import (
    detectar_anio,
    cargar_configuracion_anual,
    obtener_anios_soportados,
)


def test_detectar_anio_desde_nombre():
    assert detectar_anio("CASILLAS_DIPUTADOS_LOCALES_2018.xlsx") == "2018"
    assert detectar_anio("computos-qro-2021-final.xlsx") == "2021"
    assert detectar_anio("SE_DIP_LOCALES_QRO_2024.xlsx") == "2024"


def test_rechaza_nombre_sin_anio_soportado():
    with pytest.raises(ValueError, match="No se detecto un ano soportado"):
        detectar_anio("CASILLAS_DIPUTADOS_LOCALES.xlsx")


def test_obtener_anios_soportados(data_dir: Path):
    assert obtener_anios_soportados(data_dir) == ["2018", "2021", "2024"]


def test_cargar_configuracion_2018_preserva_encabezados_visibles(data_dir: Path):
    config = cargar_configuracion_anual("2018", data_dir)

    assert config.anio == "2018"
    assert config.ruta_formato.name == "SE_DIP_LOCALES_QRO_2018 - Formato.csv"
    assert config.encabezados_visibles[:8] == [
        "#", "CVE_ENTIDAD", "ENTIDAD", "CU_MUNICIPIO",
        "MUNICIPIO", "DF", "DL", "SECCION",
    ]
    assert config.encabezados_visibles.count("PCN") > 1
    assert "PAN" in config.partidos
    assert "MORENA-PT-PES" in config.partidos
    assert "NULOS" not in config.partidos
    assert config.indice_nulos > config.indice_inicio_partidos
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
python -m pytest tests/test_configuracion.py -q
```

Expected: fails with `ModuleNotFoundError` or missing functions from `src.configuracion`.

- [ ] **Step 3: Implement configuration module**

Write `src/configuracion.py`:

```python
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path


FORMATO_RE = re.compile(r"SE_DIP_LOCALES_QRO_(\d{4}) - Formato\.csv$", re.IGNORECASE)


@dataclass(frozen=True)
class ConfiguracionAnual:
    anio: str
    ruta_formato: Path
    encabezados_visibles: list[str]
    indice_inicio_partidos: int
    indice_nulos: int
    partidos: list[str]

    @property
    def columnas_geograficas(self) -> list[str]:
        candidatas = ["CVE_ENTIDAD", "ENTIDAD", "CU_MUNICIPIO", "MUNICIPIO", "DF", "DL", "SECCION"]
        return [col for col in candidatas if col in self.encabezados_visibles]


def obtener_anios_soportados(data_dir: Path) -> list[str]:
    anios: list[str] = []
    for ruta in data_dir.glob("SE_DIP_LOCALES_QRO_* - Formato.csv"):
        match = FORMATO_RE.match(ruta.name)
        if match:
            anios.append(match.group(1))
    return sorted(anios)


def detectar_anio(nombre_archivo: str, anios_soportados: list[str] | None = None) -> str:
    candidatos = anios_soportados or ["2018", "2021", "2024"]
    encontrados = [anio for anio in candidatos if re.search(rf"(?<!\d){anio}(?!\d)", nombre_archivo)]
    if len(encontrados) == 1:
        return encontrados[0]
    raise ValueError(
        "No se detecto un ano soportado en el nombre del archivo. "
        f"El nombre debe incluir uno de: {', '.join(candidatos)}."
    )


def cargar_configuracion_anual(anio: str, data_dir: Path) -> ConfiguracionAnual:
    ruta = data_dir / f"SE_DIP_LOCALES_QRO_{anio} - Formato.csv"
    if not ruta.exists():
        raise FileNotFoundError(f"No existe formato de referencia para {anio}: {ruta}")

    with ruta.open("r", encoding="utf-8-sig", newline="") as fh:
        encabezados = next(csv.reader(fh))

    try:
        indice_3pp = encabezados.index("3PP_MV")
        indice_inicio_partidos = indice_3pp + 3
        indice_nulos = max(i for i, col in enumerate(encabezados) if col == "NULOS")
    except ValueError as exc:
        raise ValueError(f"El formato {ruta.name} no contiene los bloques esperados") from exc

    partidos = [
        encabezados[i]
        for i in range(indice_inicio_partidos, indice_nulos, 2)
        if encabezados[i] != "PCN"
    ]
    return ConfiguracionAnual(
        anio=anio,
        ruta_formato=ruta,
        encabezados_visibles=encabezados,
        indice_inicio_partidos=indice_inicio_partidos,
        indice_nulos=indice_nulos,
        partidos=partidos,
    )
```

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_configuracion.py -q
```

Expected: all tests pass.

---

## Task 3: Annual Catalogs

**Files:**
- Create: `src/catalogos.py`
- Create: `tests/test_catalogos.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_catalogos.py`:

```python
from pathlib import Path

import pandas as pd
import pytest

from src.catalogos import construir_catalogo_dfdl
from src.configuracion import cargar_configuracion_anual


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
    from src.configuracion import ConfiguracionAnual

    config = ConfiguracionAnual(
        anio="2099",
        ruta_formato=ruta,
        encabezados_visibles=["SECCION", "DF", "DL"],
        indice_inicio_partidos=0,
        indice_nulos=0,
        partidos=[],
    )

    with pytest.raises(ValueError, match="Catalogo ambiguo"):
        construir_catalogo_dfdl(config)
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
python -m pytest tests/test_catalogos.py -q
```

Expected: fails because `src.catalogos` does not exist.

- [ ] **Step 3: Implement catalog module**

Write `src/catalogos.py`:

```python
from __future__ import annotations

import pandas as pd

from .configuracion import ConfiguracionAnual


def construir_catalogo_dfdl(config: ConfiguracionAnual) -> pd.DataFrame:
    df = pd.read_csv(config.ruta_formato, encoding="utf-8-sig")
    requeridas = ["SECCION", "DF", "DL"]
    faltantes = [col for col in requeridas if col not in df.columns]
    if faltantes:
        raise ValueError(f"El formato {config.ruta_formato.name} no contiene: {', '.join(faltantes)}")

    columnas = [col for col in ["SECCION", "DF", "DL", "CU_MUNICIPIO", "MUNICIPIO"] if col in df.columns]
    catalogo = df[columnas].copy()
    catalogo["SECCION"] = pd.to_numeric(catalogo["SECCION"], errors="coerce")
    catalogo = catalogo.dropna(subset=["SECCION"])
    catalogo["SECCION"] = catalogo["SECCION"].astype(int)

    conteos = catalogo.groupby("SECCION")[["DF", "DL"]].nunique(dropna=False)
    ambiguas = conteos[(conteos["DF"] > 1) | (conteos["DL"] > 1)]
    if not ambiguas.empty:
        muestra = ", ".join(str(i) for i in ambiguas.index[:10])
        raise ValueError(f"Catalogo ambiguo para SECCION -> DF/DL. Secciones: {muestra}")

    return catalogo.drop_duplicates(subset=["SECCION"]).sort_values("SECCION").reset_index(drop=True)
```

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_catalogos.py -q
```

Expected: all tests pass.

---

## Task 4: Source Table Detection

**Files:**
- Create: `src/lector_origen.py`
- Create: `tests/test_lector_origen.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_lector_origen.py`:

```python
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
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
python -m pytest tests/test_lector_origen.py -q
```

Expected: fails because `src.lector_origen` does not exist.

- [ ] **Step 3: Implement first-sheet reader**

Write `src/lector_origen.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from .configuracion import ConfiguracionAnual


LISTA_NOMINAL_ALIASES = {"LISTA_NOMINAL_CASILLA", "LISTA_NOMINAL"}
TOTAL_VOTOS_ALIASES = {"TOTAL_VOTOS", "VOTOS_EMITIDOS"}
NULOS_ALIASES = {"NUM_VOTOS_NULOS", "VOTOS_NULOS", "NULOS"}


@dataclass(frozen=True)
class MetadataOrigen:
    fila_encabezado: int
    hoja: str
    filas_leidas: int


def _normalizar_columna(valor: object) -> str:
    return str(valor).strip().upper() if valor is not None else ""


def detectar_fila_encabezado(ruta_excel: Path, config: ConfiguracionAnual) -> int:
    wb = load_workbook(ruta_excel, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    partidos = {p.upper() for p in config.partidos}

    for numero_fila, row in enumerate(ws.iter_rows(values_only=True), start=1):
        valores = {_normalizar_columna(v) for v in row if v is not None}
        coincidencias_partidos = len(valores & partidos)
        if (
            "SECCION" in valores
            and valores & LISTA_NOMINAL_ALIASES
            and valores & TOTAL_VOTOS_ALIASES
            and valores & NULOS_ALIASES
            and coincidencias_partidos >= 2
        ):
            return numero_fila

    raise ValueError("No se detecto la tabla principal en la primera hoja.")


def leer_tabla_principal(ruta_excel: Path, config: ConfiguracionAnual) -> tuple[pd.DataFrame, MetadataOrigen]:
    fila_encabezado = detectar_fila_encabezado(ruta_excel, config)
    wb = load_workbook(ruta_excel, read_only=True, data_only=True)
    hoja = wb.sheetnames[0]

    df = pd.read_excel(ruta_excel, sheet_name=0, header=fila_encabezado - 1)
    df = df.dropna(axis=1, how="all")
    df.columns = [str(col).strip() for col in df.columns]

    if "SECCION" not in df.columns:
        raise ValueError("La tabla detectada no contiene SECCION.")

    df["SECCION"] = pd.to_numeric(df["SECCION"], errors="coerce")
    df = df.dropna(subset=["SECCION"]).copy()
    df["SECCION"] = df["SECCION"].astype(int)
    df = df.dropna(how="all")

    return df, MetadataOrigen(fila_encabezado=fila_encabezado, hoja=hoja, filas_leidas=len(df))
```

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_lector_origen.py -q
```

Expected: all tests pass.

---

## Task 5: Section Aggregation And Target Rows

**Files:**
- Create: `src/formateador.py`
- Create: `tests/test_formateador.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_formateador.py`:

```python
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
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
python -m pytest tests/test_formateador.py -q
```

Expected: fails because `src.formateador` does not exist.

- [ ] **Step 3: Implement aggregation**

Write `src/formateador.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .configuracion import ConfiguracionAnual


@dataclass
class ResultadoFormateo:
    df_base: pd.DataFrame
    advertencias: list[str]


class FormateadorElectoral:
    def __init__(self, config: ConfiguracionAnual, catalogo_dfdl: pd.DataFrame):
        self.config = config
        self.catalogo_dfdl = catalogo_dfdl.copy()

    def formatear(self, tabla: pd.DataFrame) -> ResultadoFormateo:
        advertencias: list[str] = []
        df = tabla.copy()
        df.columns = [str(col).strip() for col in df.columns]

        self._asegurar_columna(df, "SECCION")
        lista_col = self._primera_existente(df, ["LISTA_NOMINAL_CASILLA", "LISTA_NOMINAL"])
        total_col = self._primera_existente(df, ["TOTAL_VOTOS", "VOTOS_EMITIDOS"])
        nulos_col = self._primera_existente(df, ["NUM_VOTOS_NULOS", "VOTOS_NULOS", "NULOS"])

        columnas_suma = [lista_col, total_col, nulos_col]
        for partido in self.config.partidos:
            if partido not in df.columns:
                df[partido] = 0
                advertencias.append(f"No se encontro la columna {partido}; se lleno con 0.")
            columnas_suma.append(partido)

        for col in columnas_suma:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        agregaciones = {
            lista_col: "sum",
            total_col: "sum",
            nulos_col: "sum",
            **{partido: "sum" for partido in self.config.partidos},
        }

        for origen, destino in [
            ("ID_ESTADO", "CVE_ENTIDAD"),
            ("NOMBRE_ESTADO", "ENTIDAD"),
            ("ID_MUNICIPIO_LOCAL", "CU_MUNICIPIO"),
            ("MUNICIPIO_LOCAL", "MUNICIPIO"),
        ]:
            if origen in df.columns and destino in self.config.encabezados_visibles:
                agregaciones[origen] = "first"

        agrupado = df.groupby("SECCION", as_index=False).agg(agregaciones)
        renombres = {
            lista_col: "LISTA_NOMINAL",
            total_col: "VOTOS_EMITIDOS",
            nulos_col: "NULOS",
            "ID_ESTADO": "CVE_ENTIDAD",
            "NOMBRE_ESTADO": "ENTIDAD",
            "ID_MUNICIPIO_LOCAL": "CU_MUNICIPIO",
            "MUNICIPIO_LOCAL": "MUNICIPIO",
        }
        agrupado = agrupado.rename(columns=renombres)

        resultado = agrupado.merge(self.catalogo_dfdl, on="SECCION", how="left", suffixes=("", "_CAT"))
        for col in ["DF", "DL", "CU_MUNICIPIO", "MUNICIPIO"]:
            cat_col = f"{col}_CAT"
            if cat_col in resultado.columns:
                if col in resultado.columns:
                    resultado[col] = resultado[col].where(resultado[col].notna(), resultado[cat_col])
                else:
                    resultado[col] = resultado[cat_col]
                resultado = resultado.drop(columns=[cat_col])

        sin_catalogo = int(resultado["DF"].isna().sum()) if "DF" in resultado else len(resultado)
        if sin_catalogo:
            advertencias.append(f"{sin_catalogo} seccion(es) no tuvieron coincidencia en catalogo DF/DL.")

        resultado = resultado.sort_values("SECCION").reset_index(drop=True)
        resultado.insert(0, "#", range(1, len(resultado) + 1))

        columnas_base = self._columnas_base_en_orden()
        for col in columnas_base:
            if col not in resultado.columns:
                resultado[col] = ""
        return ResultadoFormateo(df_base=resultado[columnas_base], advertencias=advertencias)

    def _columnas_base_en_orden(self) -> list[str]:
        base = [
            "#", "CVE_ENTIDAD", "ENTIDAD", "CU_MUNICIPIO", "MUNICIPIO",
            "DF", "DL", "SECCION", "LISTA_NOMINAL", "VOTOS_EMITIDOS",
        ]
        columnas = [col for col in base if col in self.config.encabezados_visibles]
        columnas.extend(self.config.partidos)
        if "NULOS" in self.config.encabezados_visibles:
            columnas.append("NULOS")
        return columnas

    @staticmethod
    def _asegurar_columna(df: pd.DataFrame, columna: str) -> None:
        if columna not in df.columns:
            raise ValueError(f"Falta columna requerida: {columna}")

    @staticmethod
    def _primera_existente(df: pd.DataFrame, opciones: list[str]) -> str:
        for opcion in opciones:
            if opcion in df.columns:
                return opcion
        raise ValueError(f"Falta una de estas columnas requeridas: {', '.join(opciones)}")
```

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_formateador.py -q
```

Expected: all tests pass. If the first row differs because source annulment rows need filtering, add filtering in `FormateadorElectoral` for rows where `TOTAL_VOTOS` cannot be numeric and keep the test expectation fixed.

---

## Task 6: Excel Writer With Formulas And Styles

**Files:**
- Create: `src/excel_writer.py`
- Create: `tests/test_excel_writer.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_excel_writer.py`:

```python
from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook

from src.catalogos import construir_catalogo_dfdl
from src.configuracion import cargar_configuracion_anual
from src.excel_writer import escribir_xlsx
from src.formateador import FormateadorElectoral
from src.lector_origen import leer_tabla_principal


def _resultado_2018(data_dir: Path, origen_2018: Path):
    config = cargar_configuracion_anual("2018", data_dir)
    catalogo = construir_catalogo_dfdl(config)
    tabla, _ = leer_tabla_principal(origen_2018, config)
    resultado = FormateadorElectoral(config, catalogo).formatear(tabla)
    return config, resultado.df_base.head(3)


def test_escribe_encabezados_visibles_y_formulas(data_dir: Path, origen_2018: Path):
    config, df_base = _resultado_2018(data_dir, origen_2018)
    datos = escribir_xlsx(df_base, config)
    wb = load_workbook(BytesIO(datos), data_only=False)
    ws = wb["Formato"]

    encabezados = [ws.cell(1, col).value for col in range(1, len(config.encabezados_visibles) + 1)]
    assert encabezados == config.encabezados_visibles
    assert ws["K2"].value.startswith("=")
    assert ws["L2"].value.startswith("=")
    assert ws["M2"].value.startswith("=")
    assert ws["N2"].value.startswith("=")
    assert ws["CV2"].value.startswith("=")
    assert ws["CW2"].value.startswith("=")


def test_escribe_hoja_calculos_oculta(data_dir: Path, origen_2018: Path):
    config, df_base = _resultado_2018(data_dir, origen_2018)
    datos = escribir_xlsx(df_base, config)
    wb = load_workbook(BytesIO(datos), data_only=False)

    assert "_calculos" in wb.sheetnames
    assert wb["_calculos"].sheet_state == "hidden"
    assert wb["Formato"].freeze_panes == "A2"
    assert wb["Formato"].auto_filter.ref is not None
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
python -m pytest tests/test_excel_writer.py -q
```

Expected: fails because `src.excel_writer` does not exist.

- [ ] **Step 3: Implement Excel writer**

Write `src/excel_writer.py` with these core elements:

```python
from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .configuracion import ConfiguracionAnual


def escribir_xlsx(df_base: pd.DataFrame, config: ConfiguracionAnual) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Formato"
    calc = wb.create_sheet("_calculos")
    calc.sheet_state = "hidden"

    _escribir_encabezados(ws, config)
    _escribir_calculos(calc, df_base, config)
    _escribir_datos_y_formulas(ws, df_base, config)
    _aplicar_estilos(ws, config, len(df_base))

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _escribir_encabezados(ws, config: ConfiguracionAnual) -> None:
    for col_idx, header in enumerate(config.encabezados_visibles, start=1):
        ws.cell(1, col_idx, header)


def _escribir_calculos(calc, df_base: pd.DataFrame, config: ConfiguracionAnual) -> None:
    for idx, partido in enumerate(config.partidos, start=1):
        calc.cell(1, idx, partido)
    for row_idx, (_, row) in enumerate(df_base.iterrows(), start=2):
        for col_idx, partido in enumerate(config.partidos, start=1):
            calc.cell(row_idx, col_idx, _numero(row.get(partido, 0)))


def _escribir_datos_y_formulas(ws, df_base: pd.DataFrame, config: ConfiguracionAnual) -> None:
    posiciones = _posiciones(config)
    emitted_col = posiciones["VOTOS_EMITIDOS"]
    nominal_col = posiciones["LISTA_NOMINAL"]
    party_indices = list(range(config.indice_inicio_partidos + 1, config.indice_nulos + 1, 2))
    pcn_indices = [idx + 1 for idx in party_indices]
    nulos_col = config.indice_nulos + 1

    for excel_row, (_, row) in enumerate(df_base.iterrows(), start=2):
        for col_idx, header in enumerate(config.encabezados_visibles, start=1):
            cell = ws.cell(excel_row, col_idx)
            if header in df_base.columns and header not in {"PCN", "VOTOS"}:
                cell.value = _numero(row.get(header, ""))
            else:
                cell.value = _formula_para_columna(
                    header=header,
                    col_idx=col_idx,
                    row_idx=excel_row,
                    posiciones=posiciones,
                    party_indices=party_indices,
                    pcn_indices=pcn_indices,
                    emitted_col=emitted_col,
                    nominal_col=nominal_col,
                    nulos_col=nulos_col,
                    total_partidos=len(config.partidos),
                )


def _formula_para_columna(
    header: str,
    col_idx: int,
    row_idx: int,
    posiciones: dict[str, int],
    party_indices: list[int],
    pcn_indices: list[int],
    emitted_col: int,
    nominal_col: int,
    nulos_col: int,
    total_partidos: int,
) -> Any:
    col = get_column_letter(col_idx)
    emitted = f"{get_column_letter(emitted_col)}{row_idx}"
    nominal = f"{get_column_letter(nominal_col)}{row_idx}"
    calc_votes = f"_calculos!$A{row_idx}:${get_column_letter(total_partidos)}{row_idx}"
    calc_heads = f"_calculos!$A$1:${get_column_letter(total_partidos)}$1"

    top_map = {
        "1ER_LUGAR": 1, "2DO_LUGAR": 2, "3ER_LUGAR": 3,
        "1PP_MV": 1, "2PP_MV": 2, "3PP_MV": 3,
    }
    vote_map = {
        "1ERO_VOTOS": 1, "2DO_VOTOS": 2, "3RO_VOTOS": 3,
    }
    if header in top_map:
        n = top_map[header]
        return f'=IFERROR(INDEX({calc_heads},1,MATCH(LARGE({calc_votes},{n}),{calc_votes},0)),"")'
    if header in vote_map:
        return f"=IFERROR(LARGE({calc_votes},{vote_map[header]}),0)"
    if header == "PARTICIPACION":
        return f"=IFERROR({emitted}/{nominal},0)"
    if header == "ABSTENCION":
        return f"=IFERROR(1-{get_column_letter(posiciones['PARTICIPACION'])}{row_idx},0)"
    if header == "DIF_VOTOS_2DO":
        return f"=IFERROR({get_column_letter(posiciones['1ERO_VOTOS'])}{row_idx}-{get_column_letter(posiciones['2DO_VOTOS'])}{row_idx},0)"
    if header == "DIF_VOTOS_3RO":
        return f"=IFERROR({get_column_letter(posiciones['2DO_VOTOS'])}{row_idx}-{get_column_letter(posiciones['3RO_VOTOS'])}{row_idx},0)"
    if header == "DIF_PCN_2DO":
        return f"=IFERROR({get_column_letter(posiciones['DIF_VOTOS_2DO'])}{row_idx}/{emitted},0)"
    if header == "DIF_PCN_3RO":
        return f"=IFERROR({get_column_letter(posiciones['DIF_VOTOS_3RO'])}{row_idx}/{emitted},0)"
    if header == "DIF_2DO":
        return f"=IFERROR({get_column_letter(posiciones['VOTOS'])}{row_idx}-{get_column_letter(posiciones['VOTOS.1'])}{row_idx},0)"
    if header == "DIF_3RO":
        return f"=IFERROR({get_column_letter(posiciones['VOTOS.1'])}{row_idx}-{get_column_letter(posiciones['VOTOS.2'])}{row_idx},0)"
    if header == "TOT_VOTOS":
        votos = ",".join(f"{get_column_letter(i)}{row_idx}" for i in party_indices + [nulos_col])
        return f"=SUM({votos})"
    if header == "VALIDACION":
        pcns = ",".join(f"{get_column_letter(i)}{row_idx}" for i in pcn_indices + [nulos_col + 1])
        return f"=SUM({pcns})"
    if header == "PCN":
        vote_col = get_column_letter(col_idx - 1)
        return f"=IFERROR({vote_col}{row_idx}/{emitted},0)"
    if header == "VOTOS":
        ordinal = _ordinal_votos(col_idx, posiciones)
        return f"=IFERROR(LARGE({calc_votes},{ordinal}),0)"
    return ""


def _ordinal_votos(col_idx: int, posiciones: dict[str, int]) -> int:
    ordered = [posiciones["VOTOS"], posiciones["VOTOS.1"], posiciones["VOTOS.2"]]
    return ordered.index(col_idx) + 1 if col_idx in ordered else 1


def _posiciones(config: ConfiguracionAnual) -> dict[str, int]:
    posiciones: dict[str, int] = {}
    conteos: dict[str, int] = {}
    for idx, header in enumerate(config.encabezados_visibles, start=1):
        ocurrencia = conteos.get(header, 0)
        key = header if ocurrencia == 0 else f"{header}.{ocurrencia}"
        posiciones[key] = idx
        conteos[header] = ocurrencia + 1
    return posiciones


def _numero(value: Any) -> Any:
    if pd.isna(value):
        return ""
    if isinstance(value, str):
        return value
    try:
        if float(value).is_integer():
            return int(value)
    except (TypeError, ValueError):
        return value
    return value


def _aplicar_estilos(ws, config: ConfiguracionAnual, total_rows: int) -> None:
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(config.encabezados_visibles))}{max(total_rows + 1, 1)}"
    thin = Side(style="thin", color="D9D9D9")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    fills = {
        "geo": PatternFill("solid", fgColor="D9EAF7"),
        "participacion": PatternFill("solid", fgColor="E2F0D9"),
        "top": PatternFill("solid", fgColor="FFF2CC"),
        "partidos": PatternFill("solid", fgColor="FCE4D6"),
        "validacion": PatternFill("solid", fgColor="E4DFEC"),
    }
    for col_idx in range(1, len(config.encabezados_visibles) + 1):
        cell = ws.cell(1, col_idx)
        cell.font = Font(bold=True, color="000000")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border
        cell.fill = _fill_para_columna(col_idx, config, fills)
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max(len(str(cell.value)) + 2, 10), 22)

    percent_headers = {"PCN", "PARTICIPACION", "ABSTENCION", "DIF_PCN_2DO", "DIF_PCN_3RO", "VALIDACION"}
    for row in ws.iter_rows(min_row=2, max_row=total_rows + 1):
        for cell in row:
            header = ws.cell(1, cell.column).value
            cell.border = border
            if header in percent_headers:
                cell.number_format = "0.00%"
            elif header not in {"ENTIDAD", "MUNICIPIO", "1ER_LUGAR", "2DO_LUGAR", "3ER_LUGAR", "1PP_MV", "2PP_MV", "3PP_MV"}:
                cell.number_format = "#,##0"


def _fill_para_columna(col_idx: int, config: ConfiguracionAnual, fills: dict[str, PatternFill]) -> PatternFill:
    if col_idx <= 8:
        return fills["geo"]
    if col_idx <= 12:
        return fills["participacion"]
    if col_idx < config.indice_inicio_partidos + 1:
        return fills["top"]
    if col_idx <= config.indice_nulos + 2:
        return fills["partidos"]
    return fills["validacion"]
```

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_excel_writer.py -q
```

Expected: all tests pass. If formula cell addresses differ for 2024 because geographic columns are shorter, update tests to locate columns by header occurrence rather than hard-coded `K2`, `CV2`.

---

## Task 7: Streamlit Cache Helpers

**Files:**
- Create: `src/cache_helpers.py`
- Create: `tests/test_cache_helpers.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_cache_helpers.py`:

```python
from pathlib import Path

from src.cache_helpers import cargar_excel_desde_bytes


def test_cargar_excel_desde_bytes(origen_2018: Path):
    data = origen_2018.read_bytes()
    wb_bytes = cargar_excel_desde_bytes(data)

    assert wb_bytes[:2] == b"PK"
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
python -m pytest tests/test_cache_helpers.py -q
```

Expected: fails because `src.cache_helpers` does not exist.

- [ ] **Step 3: Implement helpers**

Write `src/cache_helpers.py`:

```python
from __future__ import annotations

from io import BytesIO

import pandas as pd
import streamlit as st
from openpyxl import load_workbook


@st.cache_data(show_spinner=False)
def cargar_excel_desde_bytes(data: bytes) -> bytes:
    load_workbook(BytesIO(data), read_only=True, data_only=True)
    return data


@st.cache_data(show_spinner=False)
def dataframe_a_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
```

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_cache_helpers.py -q
```

Expected: all tests pass.

---

## Task 8: Streamlit Interface

**Files:**
- Create: `formateoInterfaz.py`

- [ ] **Step 1: Implement UI**

Write `formateoInterfaz.py`:

```python
from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd
import streamlit as st

from src.cache_helpers import cargar_excel_desde_bytes, dataframe_a_csv
from src.catalogos import construir_catalogo_dfdl
from src.configuracion import cargar_configuracion_anual, detectar_anio, obtener_anios_soportados
from src.excel_writer import escribir_xlsx
from src.formateador import FormateadorElectoral
from src.lector_origen import leer_tabla_principal


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


st.set_page_config(page_title="Formateador Electoral", layout="wide")
st.title("Formateador de Bases Electorales")
st.write("Sube un Excel de computos electorales para generar la sabana formateada.")

st.info("El nombre del archivo debe incluir el ano soportado: 2018, 2021 o 2024.")

archivo = st.file_uploader("Elige un archivo Excel (.xlsx)", type=["xlsx"])

if archivo is None:
    st.info("A la espera de un archivo.")
else:
    try:
        anios = obtener_anios_soportados(DATA_DIR)
        anio = detectar_anio(archivo.name, anios)
        config = cargar_configuracion_anual(anio, DATA_DIR)
        catalogo = construir_catalogo_dfdl(config)
        contenido = cargar_excel_desde_bytes(archivo.getvalue())

        with NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp.write(contenido)
            ruta_tmp = Path(tmp.name)

        tabla, meta = leer_tabla_principal(ruta_tmp, config)
        resultado = FormateadorElectoral(config, catalogo).formatear(tabla)

        col_anio, col_fila, col_origen, col_salida = st.columns(4)
        col_anio.metric("Ano detectado", anio)
        col_fila.metric("Fila de encabezado", meta.fila_encabezado)
        col_origen.metric("Filas origen", f"{len(tabla):,}")
        col_salida.metric("Secciones", f"{len(resultado.df_base):,}")

        with st.expander("Vista previa de tabla detectada", expanded=False):
            st.dataframe(tabla.head(10), use_container_width=True)

        if resultado.advertencias:
            with st.expander(f"{len(resultado.advertencias)} advertencia(s)", expanded=True):
                for aviso in resultado.advertencias:
                    st.warning(aviso)

        if st.button("Generar formato electoral", type="primary"):
            with st.spinner("Generando Excel con formulas..."):
                xlsx = escribir_xlsx(resultado.df_base, config)
                csv = dataframe_a_csv(resultado.df_base)
            st.session_state["_xlsx_formato"] = xlsx
            st.session_state["_csv_base"] = csv
            st.session_state["_nombre_salida"] = f"base_electoral_formateada_{anio}.xlsx"

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
                file_name=f"base_electoral_base_{anio}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    except Exception as exc:
        st.error(str(exc))

with st.expander("Ayuda", expanded=False):
    st.markdown(
        """
        - El archivo debe ser `.xlsx`.
        - El nombre debe incluir `2018`, `2021` o `2024`.
        - Solo se lee la primera hoja.
        - La tabla principal puede iniciar en cualquier fila; la app detecta los encabezados.
        - La salida principal es Excel con formulas.
        """
    )
```

- [ ] **Step 2: Compile UI and modules**

Run:

```powershell
python -m py_compile formateoInterfaz.py src/configuracion.py src/catalogos.py src/lector_origen.py src/formateador.py src/excel_writer.py src/cache_helpers.py
```

Expected: exit code 0.

---

## Task 9: End-To-End Verification

**Files:**
- Modify tests only if real outputs reveal a mismatch in assumptions.

- [ ] **Step 1: Run full test suite**

Run:

```powershell
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Run an end-to-end generation smoke test**

Run:

```powershell
python -c "from pathlib import Path; from io import BytesIO; from openpyxl import load_workbook; from src.configuracion import cargar_configuracion_anual; from src.catalogos import construir_catalogo_dfdl; from src.lector_origen import leer_tabla_principal; from src.formateador import FormateadorElectoral; from src.excel_writer import escribir_xlsx; base=Path('data'); config=cargar_configuracion_anual('2018', base); catalogo=construir_catalogo_dfdl(config); tabla, meta=leer_tabla_principal(base/'CASILLAS_DIPUTADOS_LOCALES.xlsx', config); res=FormateadorElectoral(config, catalogo).formatear(tabla); data=escribir_xlsx(res.df_base, config); wb=load_workbook(BytesIO(data), data_only=False); ws=wb['Formato']; print('rows', len(res.df_base)); print('header_row', meta.fila_encabezado); print('sheets', wb.sheetnames); print('formula_K2', ws['K2'].value); print('formula_M2', ws['M2'].value)"
```

Expected output includes:

```text
rows 860
header_row 20
sheets ['Formato', '_calculos']
formula_K2 =
formula_M2 =
```

- [ ] **Step 3: Run Streamlit locally**

Run:

```powershell
streamlit run formateoInterfaz.py
```

Expected: local URL opens in terminal output, the app loads, and uploading a copied 2018 example with `2018` in the filename generates the `.xlsx` download.

---

## Plan Self-Review

- Spec coverage: covered year detection, first-sheet table detection, annual catalogs, aggregation, formulas, XLSX styling, Streamlit UI, warnings and verification.
- Placeholder scan: no deferred implementation tasks; each task names concrete files and expected commands.
- Type consistency: `ConfiguracionAnual`, `MetadataOrigen`, `ResultadoFormateo`, and function signatures are consistent across tasks.
- User constraint: no `git` commands appear in execution steps.
