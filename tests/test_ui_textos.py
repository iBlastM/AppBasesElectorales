from src.ui_textos import COLUMNAS_INDISPENSABLES, REQUISITOS_ARCHIVO


def test_guia_explica_columnas_indispensables():
    nombres = {item["campo"] for item in COLUMNAS_INDISPENSABLES}

    assert "SECCION" in nombres
    assert "LISTA_NOMINAL_CASILLA / LISTA_NOMINAL" in nombres
    assert "TOTAL_VOTOS / VOTOS_EMITIDOS" in nombres
    assert "NUM_VOTOS_NULOS / VOTOS_NULOS / NULOS" in nombres
    assert "MUNICIPIO" in nombres
    assert "Partidos y coaliciones" in nombres


def test_guia_indica_requisitos_de_archivo_y_catalogo():
    texto = " ".join(REQUISITOS_ARCHIVO)

    assert ".xlsx" in texto
    assert ".csv" in texto
    assert "hoja más compatible" in texto
    assert "año" in texto
    assert "DF" in texto
    assert "DL" in texto
