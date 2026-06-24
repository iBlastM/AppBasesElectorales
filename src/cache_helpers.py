from __future__ import annotations

from io import BytesIO
from typing import Callable, TypeVar

import pandas as pd
from openpyxl import load_workbook

try:
    import streamlit as st
except Exception:
    st = None


F = TypeVar("F", bound=Callable)


def _cache_data(func: F) -> F:
    if st is None:
        return func
    return st.cache_data(show_spinner=False)(func)


@_cache_data
def cargar_excel_desde_bytes(data: bytes) -> bytes:
    load_workbook(BytesIO(data), read_only=True, data_only=True)
    return data


@_cache_data
def dataframe_a_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
