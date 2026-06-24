from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .configuracion import ConfiguracionAnual


@dataclass
class ResultadoFormateo:
    df_base: pd.DataFrame
    advertencias: list[str]


class FormateadorElectoral:
    ALIASES_PARTIDOS = {
        "CNR": ["CNR", "NO_REGISTRADOS", "CAND_NO_REGISTRADOS"],
    }

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

        agregaciones: dict[str, str] = {
            lista_col: "sum",
            total_col: "sum",
            nulos_col: "sum",
        }
        columnas_suma = [lista_col, total_col, nulos_col]
        renombres = {
            lista_col: "LISTA_NOMINAL",
            total_col: "VOTOS_EMITIDOS",
            nulos_col: "NULOS",
        }

        for partido in self.config.partidos:
            origen_partido = self._resolver_columna_partido(df, partido)
            if origen_partido is None:
                df[partido] = 0
                origen_partido = partido
                advertencias.append(f"No se encontró la columna {partido}; se llenó con 0.")
            columnas_suma.append(origen_partido)
            agregaciones[origen_partido] = "sum"
            renombres[origen_partido] = partido

        for col in columnas_suma:
            original = df[col]
            convertido = pd.to_numeric(original, errors="coerce")
            invalidos = int(convertido.isna().sum() - original.isna().sum())
            if invalidos > 0:
                advertencias.append(f"{invalidos} valor(es) no numérico(s) en {col}; se convirtieron a 0.")
            df[col] = convertido.fillna(0)

        for origen, destino in [
            ("ID_ESTADO", "CVE_ENTIDAD"),
            ("NOMBRE_ESTADO", "ENTIDAD"),
            ("ID_MUNICIPIO_LOCAL", "CU_MUNICIPIO"),
            ("MUNICIPIO_LOCAL", "MUNICIPIO"),
        ]:
            if origen in df.columns and destino in self.config.encabezados_visibles:
                agregaciones[origen] = "first"
                renombres[origen] = destino

        usadas = set(agregaciones) | {"SECCION"}
        extras = [col for col in df.columns if col not in usadas]
        if extras:
            muestra = ", ".join(extras[:8])
            sufijo = "..." if len(extras) > 8 else ""
            advertencias.append(f"{len(extras)} columna(s) del origen no se usaron: {muestra}{sufijo}")

        agrupado = df.groupby("SECCION", as_index=False).agg(agregaciones)
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
            advertencias.append(f"{sin_catalogo} sección(es) no tuvieron coincidencia en catálogo DF/DL.")

        resultado = resultado.sort_values("SECCION").reset_index(drop=True)
        resultado.insert(0, "#", range(1, len(resultado) + 1))

        columnas_base = self._columnas_base_en_orden()
        for col in columnas_base:
            if col not in resultado.columns:
                resultado[col] = ""
        return ResultadoFormateo(df_base=resultado[columnas_base], advertencias=advertencias)

    def _columnas_base_en_orden(self) -> list[str]:
        base = [
            "#",
            "CVE_ENTIDAD",
            "ENTIDAD",
            "CU_MUNICIPIO",
            "MUNICIPIO",
            "DF",
            "DL",
            "SECCION",
            "LISTA_NOMINAL",
            "VOTOS_EMITIDOS",
        ]
        columnas = [col for col in base if col in self.config.encabezados_visibles]
        columnas.extend(self.config.partidos)
        if "NULOS" in self.config.encabezados_visibles:
            columnas.append("NULOS")
        return columnas

    def _resolver_columna_partido(self, df: pd.DataFrame, partido: str) -> str | None:
        for candidato in self.ALIASES_PARTIDOS.get(partido, [partido]):
            if candidato in df.columns:
                return candidato
        return None

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
