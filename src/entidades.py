"""Catálogo de entidades federativas (claves INEGI) y detección por nombre de archivo."""
from __future__ import annotations

from .perfiles import normalizar_clave

# (clave INEGI, nombre, abreviaturas usuales en nombres de archivo de los OPLE)
ENTIDADES: list[tuple[int, str, list[str]]] = [
    (1, "AGUASCALIENTES", ["AGS"]),
    (2, "BAJA CALIFORNIA", ["BC"]),
    (3, "BAJA CALIFORNIA SUR", ["BCS"]),
    (4, "CAMPECHE", ["CAMP", "CAM"]),
    (5, "COAHUILA", ["COAH"]),
    (6, "COLIMA", []),
    (7, "CHIAPAS", ["CHIS"]),
    (8, "CHIHUAHUA", ["CHIH"]),
    (9, "CIUDAD DE MEXICO", ["CDMX", "CMX"]),
    (10, "DURANGO", ["DGO"]),
    (11, "GUANAJUATO", ["GTO"]),
    (12, "GUERRERO", ["GRO"]),
    (13, "HIDALGO", ["HGO"]),
    (14, "JALISCO", ["JAL"]),
    (15, "MEXICO", ["EDOMEX", "MEX"]),
    (16, "MICHOACAN", ["MICH"]),
    (17, "MORELOS", []),
    (18, "NAYARIT", ["NAY"]),
    (19, "NUEVO LEON", ["NL"]),
    (20, "OAXACA", ["OAX"]),
    (21, "PUEBLA", ["PUE"]),
    (22, "QUERETARO", ["QRO"]),
    (23, "QUINTANA ROO", ["QROO"]),
    (24, "SAN LUIS POTOSI", ["SLP"]),
    (25, "SINALOA", []),
    (26, "SONORA", []),
    (27, "TABASCO", ["TAB"]),
    (28, "TAMAULIPAS", ["TAMPS", "TAMS"]),
    (29, "TLAXCALA", ["TLAX"]),
    (30, "VERACRUZ", ["VER"]),
    (31, "YUCATAN", ["YUC"]),
    (32, "ZACATECAS", ["ZAC"]),
]


def detectar_entidad(nombre_archivo: str) -> tuple[int, str] | None:
    """Detecta la entidad por abreviatura (token completo) o nombre en el archivo."""
    normalizado = normalizar_clave(nombre_archivo)
    tokens = set(normalizado.split("_"))
    envuelto = f"_{normalizado}_"
    for clave, nombre, abreviaturas in ENTIDADES:
        if any(abrev in tokens for abrev in abreviaturas):
            return clave, nombre
    # Nombres completos; los más largos primero para no confundir BAJA CALIFORNIA SUR.
    for clave, nombre, _ in sorted(ENTIDADES, key=lambda e: -len(e[1])):
        if f"_{normalizar_clave(nombre)}_" in envuelto:
            return clave, nombre
    return None



def abreviatura_entidad(entidad: tuple[int, str] | None) -> str:
    if not entidad:
        return ""
    for clave, nombre, abreviaturas in ENTIDADES:
        if clave == entidad[0]:
            return abreviaturas[0] if abreviaturas else normalizar_clave(nombre)[:5]
    return normalizar_clave(entidad[1])
