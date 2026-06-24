from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PerfilFormato:
    id: str
    tipo: str
    anio: str
    ruta_formato: Path
    encabezados_visibles: list[str]
    partidos_salida: list[str]
    aliases_columnas: dict[str, list[str]]
    ranking_grupos: list[tuple[str, list[str]]]
    ranking_referencia: dict[int, list[tuple[str, int | float]]]
    municipios_referencia: dict[int, str]

    @property
    def es_simple(self) -> bool:
        return self.tipo in {"ayuntamientos", "gubernatura"}


FORMATOS_SIMPLES = {
    "ayuntamientos_2018": ("ayuntamientos", "2018", "Ayuntamientos_2018.csv"),
    "ayuntamientos_2021": ("ayuntamientos", "2021", "Ayuntamientos_2021.csv"),
    "ayuntamientos_2024": ("ayuntamientos", "2024", "Ayuntamientos_2024.csv"),
    "gubernatura_2021": ("gubernatura", "2021", "Gubernatura_2021.csv"),
}

TOP_COLUMNS = {
    "ayuntamientos_2018": ["1ER_LUGAR", "1ERO_VOTOS", "2DO_LUGAR", "2DO_VOTOS", "3ER_LUGAR", "3RO_VOTOS"],
    "ayuntamientos_2021": ["1ER_LUGAR", "1ERO_VOTOS", "2DO_LUGAR", "2DO_VOTOS", "3ER_LUGAR", "3RO_VOTOS"],
    "ayuntamientos_2024": ["1er Lugar", "Votos", "2do Lugar", "Votos.1", "3er Lugar", "Votos.2"],
    "gubernatura_2021": ["1ER_LUGAR", "1ERO_VOTOS", "2DO_LUGAR", "2DO_VOTOS", "3ER_LUGAR", "3RO_VOTOS"],
}


def detectar_perfil(nombre_archivo: str, data_dir: Path) -> PerfilFormato:
    anio = _detectar_anio(nombre_archivo)
    nombre = _normalizar(nombre_archivo)

    if "GUBERNATURA" in nombre or re.search(r"\bGUB\b", nombre):
        perfil_id = f"gubernatura_{anio}"
    elif "AYUN" in nombre:
        perfil_id = f"ayuntamientos_{anio}"
    else:
        perfil_id = f"diputaciones_{anio}"

    return cargar_perfil(perfil_id, data_dir)


def cargar_perfil(perfil_id: str, data_dir: Path) -> PerfilFormato:
    if perfil_id.startswith("diputaciones_"):
        anio = perfil_id.rsplit("_", 1)[1]
        ruta = data_dir / f"SE_DIP_LOCALES_QRO_{anio} - Formato.csv"
        encabezados = _leer_encabezados(ruta)
        return PerfilFormato(
            id=perfil_id,
            tipo="diputaciones",
            anio=anio,
            ruta_formato=ruta,
            encabezados_visibles=encabezados,
            partidos_salida=[],
            aliases_columnas={},
            ranking_grupos=[],
            ranking_referencia={},
            municipios_referencia={},
        )

    if perfil_id not in FORMATOS_SIMPLES:
        soportados = ", ".join(sorted([*FORMATOS_SIMPLES, "diputaciones_2018", "diputaciones_2021", "diputaciones_2024"]))
        raise ValueError(f"Perfil no soportado: {perfil_id}. Perfiles disponibles: {soportados}.")

    tipo, anio, archivo = FORMATOS_SIMPLES[perfil_id]
    ruta = data_dir / archivo
    encabezados = _leer_encabezados(ruta)
    partidos_salida = _partidos_salida(perfil_id, encabezados)
    aliases = _aliases_base(perfil_id)
    ranking = _ranking_base(perfil_id)
    ranking = _agregar_ranking_de_formato(ruta, perfil_id, ranking, partidos_salida)
    ranking_referencia, municipios_referencia = _leer_referencia_geografica_y_ranking(ruta, perfil_id)

    return PerfilFormato(
        id=perfil_id,
        tipo=tipo,
        anio=anio,
        ruta_formato=ruta,
        encabezados_visibles=encabezados,
        partidos_salida=partidos_salida,
        aliases_columnas=aliases,
        ranking_grupos=ranking,
        ranking_referencia=ranking_referencia,
        municipios_referencia=municipios_referencia,
    )


def normalizar_clave(valor: object) -> str:
    texto = "" if valor is None else str(valor).strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(char for char in texto if not unicodedata.combining(char))
    texto = texto.upper()
    texto = re.sub(r"[^A-Z0-9]+", "_", texto)
    return re.sub(r"_+", "_", texto).strip("_")


def _normalizar(valor: str) -> str:
    return normalizar_clave(valor).replace("_", " ")


def _detectar_anio(nombre_archivo: str) -> str:
    encontrados = re.findall(r"(?<!\d)(2018|2021|2024)(?!\d)", nombre_archivo)
    unicos = sorted(set(encontrados))
    if len(unicos) == 1:
        return unicos[0]
    raise ValueError("El nombre del archivo debe incluir exactamente un año soportado: 2018, 2021 o 2024.")


def _leer_encabezados(ruta: Path) -> list[str]:
    if not ruta.exists():
        raise FileNotFoundError(f"No existe el formato de referencia: {ruta}")
    with ruta.open("r", encoding="utf-8-sig", newline="") as fh:
        return next(csv.reader(fh))


def _partidos_salida(perfil_id: str, encabezados: list[str]) -> list[str]:
    nulos = _columna_nulos(encabezados)
    inicio = max(encabezados.index(col) for col in TOP_COLUMNS[perfil_id]) + 1
    fin = encabezados.index(nulos)
    return encabezados[inicio:fin]


def _columna_nulos(encabezados: list[str]) -> str:
    for candidato in ("NULOS", "Nulos"):
        if candidato in encabezados:
            return candidato
    raise ValueError("El formato de referencia no contiene columna de votos nulos.")


def _aliases_base(perfil_id: str) -> dict[str, list[str]]:
    comunes = {
        "municipio": ["MUNICIPIO", "MUNICIPIO_LOCAL"],
        "seccion": ["SECCION", "Seccion", "SECCIÓN"],
        "lista": ["LISTA_NOMINAL", "LISTA_NOMINAL_CASILLA", "Lista Nominal"],
        "votos": ["TOTAL_VOTOS", "VOTOS_EMITIDOS", "Votos Emitidos"],
        "nulos": ["NUM_VOTOS_NULOS", "VOTOS_NULOS", "NULOS", "Nulos"],
        "CNR": ["CNR", "NUM_VOTOS_CAN_NREG", "NO_REGISTRADOS", "CAND_NO_REGISTRADOS"],
        "FXM": ["FXM", "FM", "FxM"],
        "FxM": ["FxM", "FM", "FXM"],
    }

    if perfil_id == "ayuntamientos_2018":
        comunes.update(
            {
                "PAN_PRD_MC": ["PAN_PRD_MC", "CC_PAN-PRD-MC"],
                "PAN_PRD": ["PAN_PRD", "P_PAN-PRD", "CC2_PAN-PRD"],
                "PAN_MC": ["PAN_MC", "P_PAN-MC", "CC3_PAN-MC"],
                "PRD_MC": ["PRD_MC", "P_PRD-MC"],
                "PRI_PVEM": ["PRI_PVEM", "PRI-PVEM", "CC4_PRI-PVEM"],
                "MORENA_PT_PES": ["MORENA_PT_PES", "MORENA-PT-PES"],
                "MORENA_PT": ["MORENA_PT", "P_MORENA-PT"],
                "MORENA_PES": ["MORENA_PES", "P_MORENA-PES"],
                "PT_PES": ["PT_PES", "P_PT-PES"],
            }
        )
    return comunes


def _ranking_base(perfil_id: str) -> list[tuple[str, list[str]]]:
    if perfil_id == "ayuntamientos_2018":
        return [
            ("PAN", ["PAN"]),
            ("PRI_PVEM", ["PRI", "PVEM", "PRI_PVEM"]),
            ("MORENA_PT_PES", ["MORENA", "PT", "ES", "MORENA_PT_PES", "MORENA_PT", "MORENA_PES", "PT_PES"]),
            ("PAN_PRD_MC", ["PAN_PRD_MC"]),
            ("PRI", ["PRI"]),
            ("PRD", ["PRD"]),
            ("MC", ["MC"]),
            ("NA", ["NA"]),
            ("PVEM", ["PVEM"]),
            ("ES", ["ES"]),
            ("MORENA", ["MORENA"]),
            ("PT", ["PT"]),
            ("CQ", ["CQ"]),
            ("QI", ["QI"]),
        ]
    if perfil_id == "ayuntamientos_2021":
        return [
            ("PAN_QI", ["PAN", "QI", "PAN_QI"]),
            ("PRI", ["PRI"]),
            ("PAN", ["PAN"]),
            ("MORENA", ["MORENA"]),
            ("PVEM", ["PVEM"]),
            ("PT_QI", ["PT_QI"]),
            ("PRI_PVEM", ["PRI_PVEM"]),
            ("PAN_PRD_QI", ["PAN_PRD_QI", "PAN_PRD", "PRD_QI"]),
            ("EMC", ["CI_8"]),
            ("GTM", ["CI_2"]),
            ("IVR", ["CI_4"]),
            ("JAML", ["CI_11"]),
            ("JECT", ["CI_10"]),
            ("SHU", ["CI_9"]),
            ("SMM", ["CI_3"]),
        ]
    if perfil_id == "ayuntamientos_2024":
        return [
            ("PAN-PRI", ["PAN", "PRI", "PAN-PRI"]),
            ("PAN-PRI-PRD", ["PAN-PRI-PRD"]),
            ("PVEM-MORENA-PT", ["PVEM", "MORENA", "PT", "PVEM-MORENA-PT", "PVEM-MORENA", "PVEM-PT", "MORENA-PT"]),
            ("MC", ["MC"]),
            ("PAN", ["PAN"]),
            ("PRI", ["PRI"]),
            ("PRD", ["PRD"]),
            ("MORENA", ["MORENA"]),
            ("PVEM", ["PVEM"]),
            ("PT", ["PT"]),
            ("PAN-PRD", ["PAN", "PRD", "PAN-PRD"]),
            ("PRI-PRD", ["PRI", "PRD", "PRI-PRD"]),
            ("PVEM-MORENA", ["PVEM", "MORENA", "PVEM-MORENA"]),
            ("PVEM-PT", ["PVEM", "PT", "PVEM-PT"]),
            ("MORENA-PT", ["MORENA", "PT", "MORENA-PT"]),
            ("QS", ["QS"]),
        ]
    if perfil_id == "gubernatura_2021":
        return [
            ("PAN", ["PAN"]),
            ("PRI", ["PRI"]),
            ("MORENA", ["MORENA"]),
            ("PVEM", ["PVEM"]),
            ("MC", ["MC"]),
            ("PT", ["PT"]),
            ("QI", ["QI"]),
            ("PAN_QI", ["PAN_QI"]),
            ("PRD", ["PRD"]),
            ("PES", ["PES"]),
            ("RSP", ["RSP"]),
            ("FxM", ["FM", "FxM", "FXM"]),
        ]
    return []


def _agregar_ranking_de_formato(
    ruta: Path,
    perfil_id: str,
    ranking: list[tuple[str, list[str]]],
    partidos_salida: list[str],
) -> list[tuple[str, list[str]]]:
    existentes = {normalizar_clave(nombre) for nombre, _ in ranking}
    resultado = list(ranking)

    for partido in partidos_salida:
        clave = normalizar_clave(partido)
        if clave not in existentes:
            resultado.append((partido, [partido]))
            existentes.add(clave)

    top_cols = TOP_COLUMNS[perfil_id][0::2]
    try:
        with ruta.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                for col in top_cols:
                    etiqueta = (row.get(col) or "").strip()
                    clave = normalizar_clave(etiqueta)
                    if etiqueta and clave not in existentes and clave not in {"NULOS", "NULOS"}:
                        resultado.append((etiqueta, [etiqueta]))
                        existentes.add(clave)
    except UnicodeDecodeError:
        pass

    if "NULOS" not in existentes:
        resultado.append(("NULOS", ["NULOS", "Nulos", "NUM_VOTOS_NULOS"]))
    return resultado


def _leer_referencia_geografica_y_ranking(
    ruta: Path,
    perfil_id: str,
) -> tuple[dict[int, list[tuple[str, int | float]]], dict[int, str]]:
    ranking: dict[int, list[tuple[str, int | float]]] = {}
    municipios: dict[int, str] = {}
    top_cols = TOP_COLUMNS[perfil_id]

    with ruta.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            seccion_val = _valor_por_clave(row, ["SECCION", "Seccion"])
            if seccion_val is None:
                continue
            try:
                seccion = int(float(str(seccion_val).replace(",", "")))
            except ValueError:
                continue
            municipio = _valor_por_clave(row, ["MUNICIPIO", "Municipio"])
            municipios[seccion] = str(municipio or "").strip()

            valores: list[tuple[str, int | float]] = []
            for idx in range(3):
                etiqueta = str(row.get(top_cols[idx * 2], "") or "").strip()
                votos = _numero_referencia(row.get(top_cols[idx * 2 + 1]))
                valores.append((etiqueta, votos))
            ranking[seccion] = valores
    return ranking, municipios


def _valor_por_clave(row: dict[str, str], aliases: list[str]) -> str | None:
    indice = {normalizar_clave(key): key for key in row}
    for alias in aliases:
        key = indice.get(normalizar_clave(alias))
        if key is not None:
            return row.get(key)
    return None


def _numero_referencia(valor: object) -> int | float:
    try:
        numero = float(str(valor or "0").replace(",", ""))
    except ValueError:
        return 0
    return int(numero) if numero.is_integer() else numero
