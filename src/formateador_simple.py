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
            raise ValueError("FormateadorSimple solo acepta perfiles simples o genéricos.")

        advertencias: list[str] = []
        df = tabla.copy()
        df.columns = [str(col).strip() for col in df.columns]

        trabajo = pd.DataFrame({"SECCION": self._serie_numerica(df, self.perfil.aliases_columnas["seccion"])})
        trabajo["__CVE_ENTIDAD"] = self._serie_texto(df, self.perfil.aliases_columnas.get("cve_entidad", []))
        trabajo["__ENTIDAD"] = self._serie_texto(df, self.perfil.aliases_columnas.get("entidad", []))
        trabajo["__CVE_MUNICIPIO"] = self._serie_texto(df, self.perfil.aliases_columnas.get("cve_municipio", []))
        trabajo["__MUNICIPIO"] = self._serie_texto(df, self.perfil.aliases_columnas["municipio"])
        trabajo["__DF"] = self._serie_texto(df, self.perfil.aliases_columnas.get("df", []))
        trabajo["__DL"] = self._serie_texto(df, self.perfil.aliases_columnas.get("dl", []))
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
            "__CVE_ENTIDAD": self._primero_no_vacio,
            "__ENTIDAD": self._primero_no_vacio,
            "__CVE_MUNICIPIO": self._primero_no_vacio,
            "__MUNICIPIO": self._primero_no_vacio,
            "__DF": self._primero_no_vacio,
            "__DL": self._primero_no_vacio,
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
        columnas_base = [
            "#", "CVE_ENTIDAD", "ENTIDAD", "CU_MUNICIPIO", "MUNICIPIO", "DF", "DL", "SECCION",
            "LISTA_NOMINAL", "VOTOS_EMITIDOS",
        ]

        filas: list[dict[str, object]] = []
        for num, (_, row) in enumerate(agrupado.iterrows(), start=1):
            fila: dict[str, object] = {}
            fila["#"] = num
            fila["CVE_ENTIDAD"] = self._geografia_o_predeterminado(row["__CVE_ENTIDAD"], 22)
            fila["ENTIDAD"] = self._geografia_o_predeterminado(row["__ENTIDAD"], "QUERETARO")
            fila["CU_MUNICIPIO"] = self._geografia_o_predeterminado(row["__CVE_MUNICIPIO"], "")
            fila["MUNICIPIO"] = self._geografia_o_predeterminado(row["__MUNICIPIO"], "")
            fila["DF"] = self._geografia_o_predeterminado(row["__DF"], "")
            fila["DL"] = self._geografia_o_predeterminado(row["__DL"], "")
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
                resultado[col] = 0
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
                "ID_ESTADO", "NOMBRE_ESTADO", "ID_ENTIDAD", "CLAVE_ENTIDAD", "ENTIDAD", "ESTADO",
                "ID_DISTRITO_LOCAL", "DISTRITO_LOCAL", "DISTRITO_FEDERAL", "CABECERA_DISTRITAL_LOCAL",
                "ID_MUNICIPIO", "ID_MUNICIPIO_LOCAL", "CVE_MUNICIPIO", "CLAVE_MUNICIPIO", "MUNICIPIO_LOCAL",
                "CASILLAS", "CASILLA", "TIPO_CASILLA", "TOTAL_VOTOS_VALIDOS", "NUM_VOTOS_VALIDOS",
                "NUMERO_VOTOS_VALIDOS", "TRIBUNAL", "OBSERVACIONES", "SECCION", "SECCIÓN", "SECC",
                "LISTA_NOMINAL", "LISTA_NOMINAL_CASILLA", "LISTADO_NOMINAL", "TOTAL_VOTOS", "VOTOS_EMITIDOS",
                "TOTAL_VOTACION", "VOTACION_TOTAL", "NUM_VOTOS_NULOS", "VOTOS_NULOS", "NUM_VOTOS_CAN_NREG",
                "ID_CASILLA", "EXT_CONTIGUA", "ID_TIPO_CANDIDATURA", "ESTATUS_ACTA", "ESTATUS_PAQUETE",
                "ID_INCIDENTE", "NUM_BOLETAS_RECIBIDAS", "NUM_BOLETAS_SOBRANTES", "NUM_ESCRITOS",
                "BOLETAS_OTRA_ELECCION",
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
        if not pd.api.types.is_numeric_dtype(serie):
            serie = serie.astype(str).str.strip().str.replace(",", "", regex=False)
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

    def _geografia_o_predeterminado(self, valor: object, predeterminado: object) -> object:
        texto = "" if pd.isna(valor) else str(valor).strip()
        if texto:
            try:
                numero = float(texto)
                if numero.is_integer():
                    return int(numero)
            except ValueError:
                pass
            return texto
        return "" if self.perfil.tipo == "generico" else predeterminado

    @staticmethod
    def _normalizar_numero(valor: object) -> int | float:
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            return 0
        return int(numero) if numero.is_integer() else numero
