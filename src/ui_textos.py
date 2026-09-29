REQUISITOS_ARCHIVO = [
    "El archivo debe estar en formato .xlsx, .xlsm o .csv, tal como lo publica el instituto electoral de cualquier estado.",
    "El año, el tipo de elección y la entidad se infieren del nombre del archivo; si no se detectan, se capturan en pantalla.",
    "La tabla principal puede iniciar en cualquier fila: la app detecta la hoja más compatible y la fila de encabezados "
    "(también pueden indicarse manualmente).",
    "Puede venir por casilla o por sección; la salida siempre tiene una fila por sección.",
    "Si alguna columna clave no se detecta, se elige manualmente entre las columnas del archivo.",
    "Las columnas DF y DL son opcionales: se conservan si el origen las incluye y quedan vacías si no están disponibles.",
]


COLUMNAS_INDISPENSABLES = [
    {
        "campo": "SECCION",
        "nombres_aceptados": "SECCION, Sección, SECC, ID_SECCION",
        "contenido": "Clave de sección electoral. Las filas sin sección numérica (totales, notas) se omiten.",
    },
    {
        "campo": "LISTA_NOMINAL_CASILLA / LISTA_NOMINAL",
        "nombres_aceptados": "LISTA_NOMINAL, LISTA_NOMINAL_CASILLA, LISTADO_NOMINAL, LN",
        "contenido": "Electores en lista nominal. Se suma por sección; se usa para PARTICIPACION y ABSTENCION.",
    },
    {
        "campo": "TOTAL_VOTOS / VOTOS_EMITIDOS",
        "nombres_aceptados": "TOTAL_VOTOS, VOTOS_EMITIDOS, TOTAL_VOTACION, TOTAL",
        "contenido": "Total de votos emitidos. Base de todos los porcentajes (PCN) y de VALIDACION.",
    },
    {
        "campo": "NUM_VOTOS_NULOS / VOTOS_NULOS / NULOS",
        "nombres_aceptados": "NUM_VOTOS_NULOS, VOTOS_NULOS, NULOS, NULO",
        "contenido": "Votos nulos. Se suman por sección y forman parte de TOT_VOTOS.",
    },
    {
        "campo": "Partidos y coaliciones",
        "nombres_aceptados": "Una columna por partido, coalición o candidatura independiente (PAN, PAN_PRI, CAND_IND_1, CI_1...).",
        "contenido": "Votos enteros. Se detectan automáticamente; los porcentajes (P_PAN, PCN) se excluyen. "
        "La selección se puede ajustar.",
    },
    {
        "campo": "MUNICIPIO",
        "nombres_aceptados": "MUNICIPIO, MUNICIPIO_LOCAL, NOMBRE_MUNICIPIO, NOM_MUN",
        "contenido": "Nombre del municipio. Obligatorio en la salida de ayuntamientos; si el archivo lo nombra de otra "
        "forma (p. ej. UBICACION) se selecciona manualmente.",
    },
]


COLUMNAS_RECOMENDADAS = [
    {
        "campo": "Candidaturas no registradas (CNR)",
        "contenido": "NUM_VOTOS_CAN_NREG, NO_REGISTRADOS, NOREG... Si no existe se llena con 0.",
    },
    {
        "campo": "CVE_ENTIDAD / ENTIDAD",
        "contenido": "ID_ESTADO / NOMBRE_ESTADO. Si no existen se usa la entidad seleccionada en pantalla.",
    },
    {
        "campo": "DF / DL",
        "contenido": "Distrito federal y local (ID_DISTRITO_LOCAL, DISTRITO_FEDERAL...). Si no existen quedan vacíos.",
    },
]
