from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import IO

import numpy as np
import pandas as pd


from factory_toto.config import ID_COLUMNS

TIMESTAMP_CANDIDATES = (
    "timestamp",
    "time",
    "datetime",
    "date",
    "ts",
    "recorded_at",
)


def load_table(source: str | Path | IO[bytes] | bytes, filename: str = "") -> pd.DataFrame:
    name = filename.lower() if filename else str(source).lower()
    if isinstance(source, (str, Path)):
        path = Path(source)
        if path.suffix.lower() in {".xlsx", ".xls"}:
            df = pd.read_excel(path)
        else:
            df = pd.read_csv(path)
    else:
        raw = source if isinstance(source, bytes) else source.read()
        bio = BytesIO(raw)
        if name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(bio)
        else:
            df = pd.read_csv(bio)
    return df


def detect_timestamp_column(df: pd.DataFrame) -> str:
    lower = {c.lower().strip(): c for c in df.columns}
    for key in TIMESTAMP_CANDIDATES:
        if key in lower:
            return lower[key]
    for col in df.columns:
        if np.issubdtype(df[col].dtype, np.datetime64):
            return col
        parsed = pd.to_datetime(df[col], errors="coerce")
        if parsed.notna().mean() > 0.9:
            return col
    raise ValueError(
        "No timestamp column found. Rename your time column to 'timestamp' "
        "or include a datetime column."
    )


def prepare_plant_frame(
    df: pd.DataFrame,
    timestamp_col: str | None = None,
    value_cols: list[str] | None = None,
    tank_id: str | None = None,
) -> pd.DataFrame:
    work = df.copy()
    work.columns = [str(c).strip() for c in work.columns]
    if tank_id is not None and "tank_id" in work.columns:
        work = work[work["tank_id"].astype(str) == str(tank_id)]
        if work.empty:
            raise ValueError(f"No rows for tank {tank_id}.")
    ts_col = timestamp_col or detect_timestamp_column(work)
    work[ts_col] = pd.to_datetime(work[ts_col], errors="coerce")
    work = work.dropna(subset=[ts_col]).sort_values(ts_col)
    work = work.drop_duplicates(subset=[ts_col], keep="last")
    work = work.set_index(ts_col)

    numeric = work.select_dtypes(include=["number"]).copy()
    drop_ids = [c for c in numeric.columns if c.lower() in ID_COLUMNS]
    if drop_ids:
        numeric = numeric.drop(columns=drop_ids)
    if value_cols:
        missing = [c for c in value_cols if c not in numeric.columns]
        if missing:
            raise ValueError(f"Selected columns are not numeric: {missing}")
        numeric = numeric[value_cols]
    if numeric.empty:
        raise ValueError("No numeric sensor columns found.")

    numeric = numeric.replace([np.inf, -np.inf], np.nan)
    freq = pd.infer_freq(numeric.index)
    if freq:
        numeric = numeric.asfreq(freq)
    return numeric


def infer_step(index: pd.DatetimeIndex) -> pd.Timedelta:
    if len(index) < 2:
        return pd.Timedelta(minutes=15)
    diffs = pd.Series(index).diff().dropna()
    if diffs.empty:
        return pd.Timedelta(minutes=15)
    return pd.to_timedelta(diffs.median())


def to_model_arrays(
    frame: pd.DataFrame,
    context_length: int,
) -> tuple[np.ndarray, np.ndarray, pd.DatetimeIndex]:
    if frame.empty:
        raise ValueError("Time series is empty.")
    ctx = frame.tail(context_length)
    values = ctx.to_numpy(dtype=np.float32).T  # (n_var, time)
    mask = np.isfinite(values)
    values = np.nan_to_num(values, nan=0.0)
    return values, mask, ctx.index
