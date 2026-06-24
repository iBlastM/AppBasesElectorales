# Automatizacion de Bases Electorales - Diseno

## Objetivo

Construir una aplicacion en `AutomatizacionBasesElectorales` para convertir bases electorales origen en archivos formateados con la estructura de las sabanas electorales objetivo. La salida principal sera un archivo Excel `.xlsx` con todas las columnas en el orden del formato anual, formulas por fila en los campos calculados y estilos visuales por bloque.

El MVP debe funcionar con los ejemplos actuales de Queretaro para 2018, 2021 y 2024. El diseno debe dejar una base extensible para que despues se agreguen otros estados, anos o elecciones con partidos y coaliciones diferentes.

## Alcance Del MVP

- La interfaz sera una aplicacion Streamlit similar a `D:\Metrix\BaseProgramasSociales`.
- El usuario subira un archivo Excel origen.
- El archivo origen siempre se leera desde la primera hoja.
- El ano se detectara desde el nombre del archivo origen. El nombre debe contener `2018`, `2021` o `2024`.
- Si el ano no se detecta o no esta soportado, la aplicacion mostrara un error claro.
- Se generara un Excel `.xlsx` como descarga principal.
- Se podra ofrecer CSV como descarga secundaria.
- Los formatos anuales de referencia en `data/SE_DIP_LOCALES_QRO_<ano> - Formato.csv` definiran:
  - orden de columnas objetivo,
  - columnas geograficas disponibles,
  - lista de partidos, coaliciones y candidaturas,
  - catalogo auxiliar `SECCION -> DF/DL`.
- Si el origen trae columnas adicionales que no existan en el formato objetivo anual, se reportaran como advertencia y no se agregaran al archivo final del MVP.

## Fuera De Alcance Inicial

- Soporte completo para cualquier estado o eleccion sin configurar un formato de referencia.
- Copiar colores exactos desde los CSV de ejemplo, porque CSV no conserva estilos.
- Generar plantillas manuales por ano.
- Resolver cambios de nombres de columnas no observados en los ejemplos, salvo homologaciones basicas.

## Arquitectura

La estructura seguira el patron de `BaseProgramasSociales`:

```text
AutomatizacionBasesElectorales/
  formateoInterfaz.py
  requirements.txt
  src/
    __init__.py
    cache_helpers.py
    configuracion.py
    catalogos.py
    lector_origen.py
    formateador.py
    excel_writer.py
  tests/
    test_configuracion.py
    test_catalogos.py
    test_lector_origen.py
    test_formateador.py
    test_excel_writer.py
```

### Responsabilidades

- `formateoInterfaz.py`: app Streamlit principal. Carga archivo, muestra metricas, ejecuta formateo, muestra advertencias y expone descargas.
- `src/cache_helpers.py`: carga de bytes de Excel/CSV, conversiones a XLSX y CSV, funciones cacheables de Streamlit.
- `src/configuracion.py`: detecta ano desde nombre, lee formatos de referencia y deriva configuracion anual.
- `src/catalogos.py`: construye catalogos auxiliares por ano desde los CSV formateados.
- `src/lector_origen.py`: lee la primera hoja del Excel origen, detecta la fila de encabezado real y devuelve la tabla principal limpia.
- `src/formateador.py`: agrega casillas por seccion, une catalogos, prepara el modelo de salida y advertencias.
- `src/excel_writer.py`: escribe el workbook `.xlsx` con encabezados, formulas, formatos numericos, colores por bloque y anchos basicos.

## Flujo De Datos

1. El usuario sube el Excel origen.
2. La app detecta el ano desde el nombre del archivo.
3. `configuracion.py` carga la definicion anual usando el CSV de referencia correspondiente.
4. `catalogos.py` crea o carga el catalogo `SECCION -> DF/DL` para ese ano. Cuando existan `CU_MUNICIPIO` y `MUNICIPIO`, tambien se conservaran.
5. `lector_origen.py` abre la primera hoja y detecta la fila de encabezado.
6. `formateador.py` normaliza columnas y agrega por seccion.
7. `formateador.py` une la informacion de DF/DL desde el catalogo anual.
8. `excel_writer.py` genera el archivo `.xlsx` con columnas objetivo, formulas y estilos.
9. La app muestra una vista previa y permite descargar el resultado.

## Deteccion De La Tabla Principal

El origen siempre se leera desde la primera hoja, pero la tabla puede iniciar en cualquier fila. El lector escaneara filas hasta encontrar un encabezado valido.

Una fila sera considerada encabezado si cumple estas condiciones:

- contiene `SECCION`;
- contiene al menos una columna de lista nominal, como `LISTA_NOMINAL_CASILLA` o `LISTA_NOMINAL`;
- contiene al menos una columna de total de votos, como `TOTAL_VOTOS` o `VOTOS_EMITIDOS`;
- contiene al menos una columna de nulos, como `NUM_VOTOS_NULOS` o `VOTOS_NULOS`;
- contiene al menos dos columnas que coincidan con partidos/coaliciones del formato anual.

En el archivo de ejemplo, la fila detectada es la 20 y contiene encabezados como:

```text
ID_ESTADO, NOMBRE_ESTADO, ID_DISTRITO_LOCAL, ID_MUNICIPIO_LOCAL,
MUNICIPIO_LOCAL, SECCION, LISTA_NOMINAL_CASILLA, NUM_VOTOS_NULOS,
NO_REGISTRADOS, TOTAL_VOTOS, PAN, PRI, PRD, ...
```

Despues de detectar el encabezado, el lector descartara filas completamente vacias y filas sin `SECCION` numerica.

## Agregacion Por Seccion

El origen de ejemplo esta a nivel casilla y el formato objetivo esta a nivel seccion. La herramienta agregara por `SECCION`:

- `LISTA_NOMINAL`: suma de `LISTA_NOMINAL_CASILLA` por seccion.
- `VOTOS_EMITIDOS`: suma de `TOTAL_VOTOS` por seccion.
- `NULOS`: suma de `NUM_VOTOS_NULOS` por seccion.
- cada partido/coalicion: suma de su columna por seccion.
- `CVE_ENTIDAD`: primer valor no nulo de `ID_ESTADO` o columna equivalente.
- `ENTIDAD`: primer valor no nulo de `NOMBRE_ESTADO` o columna equivalente.
- `CU_MUNICIPIO`: primer valor no nulo de `ID_MUNICIPIO_LOCAL` o catalogo si existe en el formato anual.
- `MUNICIPIO`: primer valor no nulo de `MUNICIPIO_LOCAL` o catalogo si existe en el formato anual.

Para el MVP, esta agregacion debe reproducir para el archivo de ejemplo las mismas 860 secciones del formato 2018. Las diferencias por registros anulados o datos atipicos se reportaran como advertencias con conteos de filas afectadas y columnas involucradas.

## Catalogos Auxiliares DF/DL

Los catalogos se derivaran de los formatos anuales existentes:

- `SE_DIP_LOCALES_QRO_2018 - Formato.csv`
- `SE_DIP_LOCALES_QRO_2021 - Formato.csv`
- `SE_DIP_LOCALES_QRO_2024 - Formato.csv`

Para cada ano se extraeran columnas:

- siempre: `SECCION`, `DF`, `DL`;
- cuando existan: `CU_MUNICIPIO`, `MUNICIPIO`.

Si hay secciones repetidas, se deduplicaran siempre que `DF` y `DL` sean consistentes para la misma `SECCION`. Si una seccion tiene mas de un `DF` o `DL`, se detendra el proceso con una advertencia de catalogo ambiguo.

La inspeccion inicial confirmo:

- 2018: `SECCION -> DF/DL` unico.
- 2021: hay secciones repetidas, pero `SECCION -> DF/DL` es unico.
- 2024: `SECCION -> DF/DL` unico.

## Columnas Objetivo

El orden exacto de columnas vendra del CSV de formato anual. La herramienta respetara encabezados repetidos conceptualmente como `PCN` y `VOTOS` al escribir Excel.

Para procesamiento interno, pandas puede usar nombres desambiguados como `PCN.1`; al escribir XLSX se restauraran los encabezados visibles del formato original.

Las columnas objetivo se agrupan en bloques:

1. Geografico.
2. Participacion.
3. Top 3 ganadores.
4. Partido politico mas votado.
5. Partidos, coaliciones y candidaturas.
6. Validacion.

## Formulas Excel

La salida `.xlsx` incluira formulas por fila en columnas calculadas. Las columnas base se escribiran como valores.

Formulas esperadas:

- `PARTICIPACION`: `VOTOS_EMITIDOS / LISTA_NOMINAL`.
- `ABSTENCION`: `1 - PARTICIPACION`.
- porcentajes `PCN` de votos: votos de la columna correspondiente dividido entre `VOTOS_EMITIDOS`.
- `TOT_VOTOS`: suma del bloque de votos de partidos/coaliciones mas `NULOS`.
- `VALIDACION`: suma de porcentajes del bloque de partidos/coaliciones mas nulos.
- `1ER_LUGAR`, `2DO_LUGAR`, `3ER_LUGAR`: formulas sobre el bloque de votos de partidos, coaliciones y candidaturas para devolver encabezados de las columnas con mayor, segundo mayor y tercer mayor valor. `NULOS` no participa en el ranking.
- `1ERO_VOTOS`, `2DO_VOTOS`, `3RO_VOTOS`: formulas para devolver el primer, segundo y tercer mayor valor.
- diferencias de votos: resta entre posiciones consecutivas.
- diferencias porcentuales: diferencia de votos dividida entre `VOTOS_EMITIDOS`.
- `1PP_MV`, `2PP_MV`, `3PP_MV` y sus votos/porcentajes usaran el mismo bloque de partidos, coaliciones y candidaturas, excluyendo `NULOS`.

El escritor usara formulas compatibles con Excel moderno en espanol/ingles no dependientes del idioma cuando sea posible, usando nombres de funciones en ingles como espera el formato OOXML (`LARGE`, `INDEX`, `MATCH`, `SUM`).

## Estilos XLSX

Como los archivos de referencia son CSV y no conservan estilos reales, se recrearan estilos consistentes por bloque:

- encabezados congelados;
- filtros activados;
- color de relleno por bloque;
- negritas en encabezados;
- bordes ligeros;
- formato de miles en conteos de votos/lista nominal;
- formato porcentual en columnas `PCN`, `PARTICIPACION`, `ABSTENCION`, `DIF_PCN_*` y `VALIDACION`;
- ancho de columnas ajustado a encabezados y valores principales.

## Interfaz

La interfaz Streamlit tendra:

- titulo y descripcion breve;
- `file_uploader` para Excel `.xlsx`;
- mensaje indicando que el nombre del archivo debe contener el ano;
- metricas de carga:
  - ano detectado,
  - filas leidas,
  - fila de encabezado detectada,
  - secciones resultantes,
  - advertencias;
- vista previa del origen detectado;
- boton `Generar formato electoral`;
- vista previa del resultado;
- descarga principal `.xlsx`;
- descarga secundaria `.csv` cuando este disponible;
- expander de ayuda con requisitos del archivo origen.

## Advertencias Y Errores

Errores que detienen el proceso:

- no se detecta ano en el nombre;
- ano no soportado;
- no existe formato anual de referencia;
- no se detecta tabla principal en la primera hoja;
- falta `SECCION`;
- catalogo anual ambiguo para `SECCION -> DF/DL`.

Advertencias que permiten continuar:

- partido/coalicion del formato anual ausente en el origen: se llena con `0`;
- columna adicional del origen no usada en el formato anual;
- secciones del origen sin match en catalogo anual: `DF/DL` quedan vacios y se reportan;
- valores no numericos en columnas de votos: se convierten a `0` y se reporta el conteo.

## Pruebas

Las pruebas se escribiran antes de implementar cada componente.

Criterios minimos:

- detectar `2018`, `2021` y `2024` desde nombres de archivo;
- rechazar nombres sin ano soportado;
- derivar columnas objetivo y partidos desde cada CSV de referencia;
- construir catalogos `SECCION -> DF/DL` sin ambiguedad;
- detectar la fila 20 como encabezado en el Excel de ejemplo;
- agregar el origen de ejemplo por seccion y obtener 860 secciones para 2018;
- generar columnas en el mismo orden visible que el formato anual;
- escribir un `.xlsx` con formulas en columnas calculadas;
- verificar que el workbook generado contenga encabezados, formulas y estilos basicos.

## Criterios De Aceptacion

- Al subir un archivo origen cuyo nombre contiene `2018`, la app genera un `.xlsx` con 860 filas de datos para el ejemplo actual.
- El resultado contiene todas las columnas del formato anual 2018 en el mismo orden visible.
- Las columnas calculadas contienen formulas Excel.
- `DF` y `DL` se llenan desde el catalogo anual.
- Las columnas de partidos/coaliciones se llenan segun el formato anual.
- La app muestra advertencias claras cuando haya columnas faltantes, extras o secciones sin catalogo.
- La interfaz se parece en estructura y flujo a la de `BaseProgramasSociales`.
