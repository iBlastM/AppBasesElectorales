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
        raise ValueError(f"Catálogo ambiguo para SECCION -> DF/DL. Secciones: {muestra}")

    return catalogo.drop_duplicates(subset=["SECCION"]).sort_values("SECCION").reset_index(drop=True)
