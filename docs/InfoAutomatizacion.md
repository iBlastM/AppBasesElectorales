**Plantilla Electoral**

Las sábanas electorales son bases de datos construidas a partir de los
CÓMPUTOS de los resultados electorales de las diferentes elecciones que
se realizan en los diferentes órdenes de gobierno.

Para los cargos Federales los cómputos se buscan en la página oficial
del INE
([[https://computos2024.ine.mx/presidencia/nacional/candidatura]{.underline}](https://computos2024.ine.mx/presidencia/nacional/candidatura));
y para los cargos Estatales la información se extrae de las páginas
locales del INE de cada estado.

![](media/image2.png){width="4.119792213473316in"
height="1.786155949256343in"}

- 1\. [Bloque Geográfico]{.underline}

Este bloque contiene la información de ubicación de la delimitación
electoral de donde se están extrayendo los datos.

- **CVE_ENTIDAD**: Clave estado-asignada por el INEGI

- **ENTIDAD:** Nombre estado

- **CVE_MUN**: Clave municipio-asignada por el INEGI

- **MUNICIPIO**: Nombre municipio

- **DF**: Distrito federal

- **DL**: Distrito local

- **SECCIÓN**: Sección electoral

- **Casillas:** en algunos cómputos la información viene desagregada
  hasta casilla (indicada por numeros) y tipo de casillas (indicadas por
  letras)

![](media/image1.png){width="3.244792213473316in"
height="3.519773622047244in"}

- 2[. Bloque de participación]{.underline}

Este apartado tiene los datos generales de cada una de las casillas/
secciones/ distritos locales/ distritos federales y en función de esta
información se calcula la participación y abstención.

- **Lista nominal:** Número de personas que cuenta con INE vigente
  registrada en esa delimitación electoral (Credencial/documento
  obligatorio para emitir el voto)

- **Votos emitidos:** Número de personas que acudieron el día de las
  votaciones y emitieron su voto

- **Participación:** Porcentaje de personas que emitieron su voto (Votos
  emitidos/lista nominal)

- **Abstención:** Porcentaje de personas que no votaron (1-Porcentaje de
  personas que emitieron su voto)

<!-- -->

- 3\. [Bloque Top 3 ganadores]{.underline}

En este bloque se desagrega la información del TOP 3 ganadores, se
calcula el porcentaje de votos con el que ganó el antes mencionado y se
calcula la diferencia en voto y porcentajes de diferencia con el segundo
o tercer lugar.

- **1ER_LUGAR:** Partido político con la mayor cantidad de votos
  registrados

- **1ERO_VOTOS:** Número de votos al partido político con la mayor
  cantidad de votos

- **PCN:** Porcentaje de votos que recibió el primer lugar (1ERO
  VOTOS/VOTOS EMITIDOS)

- **DIF_VOTOS_2DO:** Número de votos por los que le ganó al segundo
  lugar (1ERO VOTOS-2DO VOTOS)

- **DIF_PCN_2DO:** Porcentaje de votos por los que se le ganó al segundo
  lugar (DIF VOTOS 2DO/VOTOS EMITIDOS)

- **2DO_LUGAR:** Segundo partido político con mayor cantidad de votos
  registrados

- **2DO_VOTOS:** Número de votos registrados al segundo partido político
  con mayor cantidad de votos

- **PCN:** Porcentaje de votos que recibió el segundo lugar (2DO
  VOTOS/VOTOS EMITIDOS)

- **DIF_VOTOS_3RO:** Número de votos por los que se le ganó al tercer
  lugar (2DO VOTOS-3ER VOTOS)

- **DIF_PCN_3RO:** Porcentaje de votos por los que se le ganó al tercer
  lugar (DIF VOTOS 3ER/VOTOS EMITIDOS)

- **3ER_LUGAR:** Tercer partido político con mayor cantidad de votos
  registrados

- **3RO_VOTOS:** Número de votos registrados al tercer partido político
  con mayor cantidad de votos

- **PCN:** Porcentaje de votos que recibió el tercer lugar (3ER
  VOTOS/VOTOS EMITIDOS)

<!-- -->

- 4\. Bloque Partido Político más votado

  - **1PP_MV:** Partido político con mayor cantidad de votos, esta
    columna tiene una fórmula que identifica la celda con la cantidad
    más alta del BLOQUE 5, de la misma fila y devuelve el encabezado de
    esa columna

  - **VOTOS:** Número de votos recibidos para el partido político más
    votado

  - **PCN:** Porcentaje de votos recibidos al partido político más
    votado (VOTOS/VOTOS EMITIDOS)

  - **DIF_2DO**: Diferencia de votos con el segundo partido político más
    votado (VOTOS - VOTOS 2)

  - **PCN:** Porcentaje de la diferencia de votos con el segundo partido
    político en función de los votos emitidos (DIF 2DO/VOTOS EMITIDOS)

  - **2PP_MV:** Segundo partido político con mayor cantidad de votos,
    esta columna tiene una fórmula que identifica la celda con la
    segunda cantidad más alta del BLOQUE 5, de la misma fila y devuelve
    el encabezado de esa columna

  - **VOTOS:** Número de votos recibidos para el segundo partido
    político más votado

  - **PCN:** Porcentaje de votos recibidos al segundo partido político
    más votado (VOTOS 2/VOTOS EMITIDOS)

  - **DIF_3RO:** Diferencia de votos con el tercer partido político más
    votado (VOTOS 2 -VOTOS 3)

  - **PCN:** Porcentaje de la diferencia de votos con el tercer puesto
    (DIF_3RO/VOTOS EMITIDOS)

  - **3PP_MV:** Tercer partido político con mayor cantidad de votos,
    esta columna tiene una fórmula que identifica la celda con la
    tercera cantidad más alta del BLOQUE 5, de la misma fila y devuelve
    el encabezado de esa columna

  - **VOTOS:** Número de votos recibidos al tercer tercer partido
    político más votado

  - **PCN:** Porcentaje de votos recibidos para el tercer partido
    político más votado (VOTOS 3/VOTOS EMITIDOS)

- 5[. Partidos políticos y coaliciones]{.underline}

En este apartado se desagregan los votos recibidos a cada uno de los
partidos políticos y coaliciones que se registran a la jornada
electoral.

- **PARTIDO:** Número de votos por partido político y/o coalición (N
  número de partido y coaliciones / N número de columnas)

- **PCN:** Porcentaje en función de los votos emitidos (N número de
  partido y coaliciones / N número de columnas)

- **NULOS:** Votos nulos

- **PCN:** Porcentaje en función de los votos emitidos

<!-- -->

- 6[. Validación]{.underline}

Finalmente, se realizan cálculos para validar que los datos sean los
correctos.

- **TOT_VOTOS:** Suma del total de votos registrados en el BLOQUE 5
  -Sólo votos-; el resultado debe ser el mismo que los -votos emitidos-,
  considerando los -votos nulos-

- VALIDACION: Suma de los porcentajes del BLOQUE 5 -sólo porcentaje-; el
  resultado debe ser igual a %100, considerando el porcentaje de los
  votos nulos
