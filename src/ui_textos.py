REQUISITOS_ARCHIVO = [
    "El archivo debe estar en formato .xlsx o .csv, según el tipo de base origen.",
    "El nombre del archivo debe incluir el año de la elección: 2018, 2021 o 2024.",
    "La tabla principal puede iniciar en cualquier fila, siempre que conserve encabezados claros.",
    "Para ayuntamientos y gubernatura, la app detecta la hoja más compatible con el formato esperado.",
    "Para diputaciones locales, las columnas DF y DL no son necesarias en el origen; la app las asigna con el catálogo del año detectado.",
]


COLUMNAS_INDISPENSABLES = [
    {
        "campo": "SECCION",
        "nombres_aceptados": "SECCION, Seccion, SECCIÓN",
        "contenido": "Número de sección electoral. Debe ser numérico; si viene como 0001 se convierte a 1.",
    },
    {
        "campo": "LISTA_NOMINAL_CASILLA / LISTA_NOMINAL",
        "nombres_aceptados": "LISTA_NOMINAL_CASILLA, LISTA_NOMINAL, Lista Nominal",
        "contenido": "Cantidad de personas en lista nominal. Debe ser numérica; si hay varias casillas, se suma por sección.",
    },
    {
        "campo": "TOTAL_VOTOS / VOTOS_EMITIDOS",
        "nombres_aceptados": "TOTAL_VOTOS, VOTOS_EMITIDOS, Votos Emitidos",
        "contenido": "Total de votos emitidos. Debe ser numérico; se usa para calcular participación y porcentajes.",
    },
    {
        "campo": "NUM_VOTOS_NULOS / VOTOS_NULOS / NULOS",
        "nombres_aceptados": "NUM_VOTOS_NULOS, VOTOS_NULOS, NULOS, Nulos",
        "contenido": "Votos nulos. Debe ser numérico y se suma por sección.",
    },
    {
        "campo": "MUNICIPIO",
        "nombres_aceptados": "MUNICIPIO, MUNICIPIO_LOCAL",
        "contenido": "Nombre del municipio. Se usa para los formatos de ayuntamientos y gubernatura.",
    },
    {
        "campo": "Partidos y coaliciones",
        "nombres_aceptados": "Columnas del formato del año, por ejemplo PAN, PRI, MORENA, MC, PT, PAN_QI o PAN-PRI.",
        "contenido": "Votos por partido, coalición o candidatura. Deben ser numéricos; las columnas ausentes se llenan con 0.",
    },
]


COLUMNAS_RECOMENDADAS = [
    {
        "campo": "ID_ESTADO",
        "contenido": "Clave de entidad. Si existe, se usa para llenar CVE_ENTIDAD en formatos que la requieren.",
    },
    {
        "campo": "NOMBRE_ESTADO",
        "contenido": "Nombre de la entidad. Si existe, se usa para llenar ENTIDAD en formatos que la requieren.",
    },
    {
        "campo": "ID_MUNICIPIO_LOCAL / ID_MUNICIPIO",
        "contenido": "Clave de municipio. Si el formato anual la requiere, se usa para CU_MUNICIPIO.",
    },
    {
        "campo": "MUNICIPIO_LOCAL / MUNICIPIO",
        "contenido": "Nombre de municipio. Si el formato anual lo requiere, se usa para MUNICIPIO.",
    },
]
