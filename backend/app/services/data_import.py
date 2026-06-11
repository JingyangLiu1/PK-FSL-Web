from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def excel_sheet_names(path: Path) -> list[str]:
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    return list(wb.sheetnames)


def load_excel_sheet(path: Path, sheet_name: str, header_row: int = 0, index_col: int | None = None) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet_name, header=header_row, index_col=index_col, engine="openpyxl")
    # normalize column names to str
    df.columns = [str(c).strip() for c in df.columns]
    return df


def describe_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    n_rows, n_cols = df.shape
    dtypes = {c: str(df[c].dtype) for c in df.columns}
    missing = {c: int(df[c].isna().sum()) for c in df.columns}

    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    desc = df[numeric_cols].describe().T if numeric_cols else pd.DataFrame()
    desc_dict = desc.reset_index().rename(columns={"index": "column"}).to_dict(orient="records") if not desc.empty else []

    outliers = detect_outliers_iqr(df)
    return {
        "shape": {"rows": n_rows, "cols": n_cols},
        "dtypes": dtypes,
        "missing": missing,
        "numeric_summary": desc_dict,
        "outliers_iqr": outliers,
    }


def detect_outliers_iqr(df: pd.DataFrame, k: float = 1.5) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        s = df[col].dropna()
        if len(s) < 8:
            continue
        q1 = s.quantile(0.25)
        q3 = s.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        low = q1 - k * iqr
        high = q3 + k * iqr
        mask = (df[col] < low) | (df[col] > high)
        n = int(mask.sum())
        if n > 0:
            out[col] = {"n": n, "low": float(low), "high": float(high)}
    return out


def apply_missing_outlier_strategies(
    df: pd.DataFrame,
    na_strategy: str = "keep",
    outlier_strategy: str = "keep",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    report: dict[str, Any] = {"na_strategy": na_strategy, "outlier_strategy": outlier_strategy}
    df2 = df.copy()

    # missing
    missing_before = int(df2.isna().sum().sum())
    if na_strategy == "drop":
        df2 = df2.dropna(axis=0)
    elif na_strategy in ("mean", "median"):
        for col in df2.columns:
            if not pd.api.types.is_numeric_dtype(df2[col]):
                continue
            if na_strategy == "mean":
                df2[col] = df2[col].fillna(df2[col].mean())
            else:
                df2[col] = df2[col].fillna(df2[col].median())
    missing_after = int(df2.isna().sum().sum())
    report["missing_before"] = missing_before
    report["missing_after"] = missing_after

    # outliers
    outliers = detect_outliers_iqr(df2)
    report["outliers_iqr"] = outliers
    if outlier_strategy == "clip_iqr":
        for col, info in outliers.items():
            df2[col] = df2[col].clip(lower=info["low"], upper=info["high"])
    elif outlier_strategy == "drop_iqr":
        masks = []
        for col, info in outliers.items():
            masks.append((df2[col] >= info["low"]) & (df2[col] <= info["high"]))
        if masks:
            keep = masks[0]
            for m in masks[1:]:
                keep = keep & m
            df2 = df2[keep].copy()
    report["rows_after"] = int(len(df2))
    return df2, report

