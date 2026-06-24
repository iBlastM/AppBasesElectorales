from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .perfiles import PerfilFormato, normalizar_clave
from .configuracion import ConfiguracionAnual, config_desde_perfil_simple


@dataclass
class ResultadoFormateoSimple:
    df_base: pd.DataFrame
    config: ConfiguracionAnual
    advertencias: list[str]


class FormateadorSimple:
    def __init__(self, perfil: PerfilFormato):
        self.perfil = perfil

    def formatear(self, tabla: pd.DataFrame) -> ResultadoFormateoSimple:
        if not self.perfil.es_simple:
            raise ValueError("FormateadorSimple solo acepta perfiles de ayuntamientos o gubernatura.")

        advertencias: list[str] = []
        df = tabla.copy()
        df.columns = [str(col).strip() for col in df.columns]

        trabajo = pd.DataFrame({"SECCION": self._serie_numerica(df, ["SECCION"])})
        trabajo["__MUNICIPIO"] = self._serie_texto(df, self.perfil.aliases_columnas["municipio"])
        trabajo["__LISTA"] = self._serie_numerica_logica(df, "lista", advertencias)
        trabajo["__VOTOS"] = self._serie_numerica_logica(df, "votos", advertencias)
        trabajo["__NULOS"] = self._serie_numerica_logica(df, "nulos", advertencias)
        trabajo["__CNR"] = self._serie_numerica_logica(df, "CNR", advertencias)

        partidos_extra = self._detectar_columnas_extra(df)
        partidos_salida = list(self.perfil.partidos_salida) + partidos_extra

        for idx, partido in enumerate(partidos_salida):
            trabajo[f"__P_{idx}"] = self._serie_numerica_logica(df, partido, advertencias)

        for idx, (etiqueta, componentes) in enumerate(self.perfil.ranking_grupos):
            trabajo[f"__R_{idx}"] = self._sumar_componentes(df, componentes, advertencias)

        agregaciones = {
            "__MUNICIPIO": self._primero_no_vacio,
            "__LISTA": "sum",
            "__VOTOS": "sum",
            "__NULOS": "sum",
            "__CNR": "sum",
        }
        for idx in range(len(partidos_salida)):
            agregaciones[f"__P_{idx}"] = "sum"
        for idx in range(len(self.perfil.ranking_grupos)):
            agregaciones[f"__R_{idx}"] = "sum"

        agrupado = trabajo.groupby("SECCION", as_index=False).agg(agregaciones)
        agrupado = agrupado.sort_values("SECCION").reset_index(drop=True)

        config = config_desde_perfil_simple(self.perfil, partidos_salida)
        columnas_base = ["#", "CVE_ENTIDAD", "ENTIDAD", "MUNICIPIO", "DF", "DL", "SECCION",
                         "LISTA_NOMINAL", "VOTOS_EMITIDOS"]

        filas: list[dict[str, object]] = []
        for num, (_, row) in enumerate(agrupado.iterrows(), start=1):
            fila: dict[str, object] = {}
            fila["#"] = num
            fila["CVE_ENTIDAD"] = 22
            fila["ENTIDAD"] = "QUERETARO"
            fila["MUNICIPIO"] = row["__MUNICIPIO"]
            fila["DF"] = ""
            fila["DL"] = ""
            fila["SECCION"] = int(row["SECCION"])
            fila["LISTA_NOMINAL"] = self._normalizar_numero(row["__LISTA"])
            fila["VOTOS_EMITIDOS"] = self._normalizar_numero(row["__VOTOS"])
            for idx, partido in enumerate(partidos_salida):
                fila[partido] = self._normalizar_numero(row[f"__P_{idx}"])
            fila["CNR"] = self._normalizar_numero(row["__CNR"])
            fila["NULOS"] = self._normalizar_numero(row["__NULOS"])
            filas.append(fila)

        resultado = pd.DataFrame(filas)
        columnas_df = columnas_base + partidos_salida + ["CNR", "NULOS"]
        for col in columnas_df:
            if col not in resultado.columns:
                resultado[col] = ""
        resultado = resultado[columnas_df]

        return ResultadoFormateoSimple(df_base=resultado, config=config, advertencias=advertencias)


    def _detectar_columnas_extra(self, df: pd.DataFrame) -> list[str]:
        conocidas = set()
        for aliases in self.perfil.aliases_columnas.values():
            for alias in aliases:
                conocidas.add(normalizar_clave(alias))
        for partido in self.perfil.partidos_salida:
            conocidas.add(normalizar_clave(partido))
        conocidas.update({
            normalizar_clave(c) for c in [
                "ID_ESTADO", "NOMBRE_ESTADO", "ID_DISTRITO_LOCAL", "CABECERA_DISTRITAL_LOCAL",
                "ID_MUNICIPIO", "CASILLAS", "NUM_VOTOS_VALIDOS", "TRIBUNAL", "OBSERVACIONES",
                "SECCION", "LISTA_NOMINAL", "LISTA_NOMINAL_CASILLA", "TOTAL_VOTOS",
                "VOTOS_EMITIDOS", "NUM_VOTOS_NULOS", "VOTOS_NULOS", "NUM_VOTOS_CAN_NREG",
            ]
        })
        extras: list[str] = []
        for col in df.columns:
            clave = normalizar_clave(col)
            if clave and clave not in conocidas:
                serie = pd.to_numeric(df[col].astype(str).str.replace(",", "", regex=False).str.strip(), errors="coerce")
                if serie.notna().any() and serie.fillna(0).sum() > 0:
                    extras.append(col)
        return extras

    def _serie_numerica_logica(self, df: pd.DataFrame, nombre: str, advertencias: list[str]) -> pd.Series:
        aliases = self.perfil.aliases_columnas.get(nombre, [nombre])
        columnas = self._resolver_columnas(df, aliases)
        if not columnas:
            if nombre in self.perfil.partidos_salida:
                advertencias.append(f"No se encontró la columna {nombre}; se llenó con 0.")
            return pd.Series([0] * len(df), index=df.index, dtype="float64")
        total = pd.Series([0] * len(df), index=df.index, dtype="float64")
        for columna in columnas:
            total = total + self._serie_numerica(df, [columna])
        return total

    def _sumar_componentes(self, df: pd.DataFrame, componentes: list[str], advertencias: list[str]) -> pd.Series:
        total = pd.Series([0] * len(df), index=df.index, dtype="float64")
        for componente in componentes:
            total = total + self._serie_numerica_logica(df, componente, advertencias)
        return total

    def _serie_texto(self, df: pd.DataFrame, aliases: list[str]) -> pd.Series:
        columna = self._resolver_columna(df, aliases)
        if columna is None:
            return pd.Series([""] * len(df), index=df.index, dtype="object")
        return df[columna].fillna("").astype(str).str.strip()

    def _serie_numerica(self, df: pd.DataFrame, aliases: list[str]) -> pd.Series:
        columna = self._resolver_columna(df, aliases)
        if columna is None:
            return pd.Series([0] * len(df), index=df.index, dtype="float64")
        serie = df[columna]
        if serie.dtype == object:
            serie = serie.astype(str).str.strip().str.replace(",", "", regex=False)
            serie = serie.replace({"": "0", " ": "0", "nan": "0", "None": "0"})
        return pd.to_numeric(serie, errors="coerce").fillna(0)

    @staticmethod
    def _resolver_columna(df: pd.DataFrame, aliases: list[str]) -> str | None:
        indice = {normalizar_clave(col): col for col in df.columns}
        for alias in aliases:
            columna = indice.get(normalizar_clave(alias))
            if columna is not None:
                return columna
        return None

    @staticmethod
    def _resolver_columnas(df: pd.DataFrame, aliases: list[str]) -> list[str]:
        indice = {normalizar_clave(col): col for col in df.columns}
        columnas: list[str] = []
        vistas: set[str] = set()
        for alias in aliases:
            columna = indice.get(normalizar_clave(alias))
            if columna is not None and columna not in vistas:
                columnas.append(columna)
                vistas.add(columna)
        return columnas

    @staticmethod
    def _primero_no_vacio(valores: pd.Series) -> str:
        for valor in valores:
            texto = "" if pd.isna(valor) else str(valor).strip()
            if texto:
                return texto
        return ""

    @staticmethod
    def _normalizar_numero(valor: object) -> int | float:
        numero = float(valor)
        return int(numero) if numero.is_integer() else numero
