"""Live corn fermenter: SQLite store + one-step physics for real-time ticks."""

from __future__ import annotations

import sqlite3
from datetime import datetime

import numpy as np
import pandas as pd

from factory_toto.config import DATA_DIR
from factory_toto.sweet_corn import DEFAULT_SWEET_COLUMNS, _ph_efficiency, _temp_efficiency

REALTIME_DB = DATA_DIR / "realtime_corn.db"

BATCH_H = 48.0
FILL_H = 2.0
CONVERT_H = 42.0
EMPTY_H = 2.0
STARCH0 = 28.0
LIVE_COLUMNS = list(DEFAULT_SWEET_COLUMNS)
META_COLUMNS = ["timestamp", "tank_id", "batch_id", "stage", "plant_hour"]


def _connect(path=REALTIME_DB) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetry (
            timestamp TEXT NOT NULL,
            tank_id TEXT NOT NULL,
            batch_id TEXT,
            stage TEXT,
            plant_hour REAL,
            brix_pct REAL,
            sweetness_index REAL,
            fructose_pct REAL,
            glucose_pct REAL,
            dextrose_equivalent REAL,
            fermenter_temp_c REAL,
            ph REAL,
            dissolved_oxygen_ppm REAL,
            agitator_rpm REAL,
            fermentation_hour REAL,
            enzyme_activity_u REAL,
            residual_starch_pct REAL,
            lactic_acid_pct REAL,
            corn_solids_pct REAL,
            mash_flow_m3h REAL,
            power_kw REAL,
            PRIMARY KEY (timestamp, tank_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS forecasts (
            issued_at TEXT NOT NULL,
            target_time TEXT NOT NULL,
            tank_id TEXT NOT NULL,
            column_name TEXT NOT NULL,
            step INTEGER NOT NULL,
            median REAL,
            p10 REAL,
            p90 REAL,
            PRIMARY KEY (tank_id, column_name, target_time, step)
        )
        """
    )
    conn.commit()
    return conn


def count_rows(tank_id: str = "F-1") -> int:
    with _connect() as conn:
        cur = conn.execute("SELECT COUNT(*) FROM telemetry WHERE tank_id = ?", (tank_id,))
        return int(cur.fetchone()[0])


def reset_db() -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM telemetry")
        conn.execute("DELETE FROM forecasts")
        conn.commit()


def read_history(tank_id: str = "F-1", limit: int = 800) -> pd.DataFrame:
    with _connect() as conn:
        df = pd.read_sql_query(
            """
            SELECT * FROM telemetry
            WHERE tank_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            conn,
            params=(tank_id, limit),
        )
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp").reset_index(drop=True)


def insert_rows(df: pd.DataFrame) -> None:
    if df.empty:
        return
    work = df.copy()
    work["timestamp"] = pd.to_datetime(work["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    cols = [c for c in META_COLUMNS + LIVE_COLUMNS if c in work.columns]
    placeholders = ", ".join("?" for _ in cols)
    col_sql = ", ".join(cols)
    sql = f"INSERT OR REPLACE INTO telemetry ({col_sql}) VALUES ({placeholders})"
    records = []
    for row in work[cols].itertuples(index=False, name=None):
        cleaned = []
        for value in row:
            if value is None or (isinstance(value, float) and np.isnan(value)) or pd.isna(value):
                cleaned.append(None)
            elif isinstance(value, (np.floating,)):
                cleaned.append(float(value))
            elif isinstance(value, (np.integer,)):
                cleaned.append(int(value))
            else:
                cleaned.append(value)
        records.append(cleaned)
    with _connect() as conn:
        conn.executemany(sql, records)
        conn.commit()


def simulate_row(plant_h: float, ts: pd.Timestamp, tank_id: str, rng: np.random.Generator) -> dict:
    batch_pos = float(np.mod(plant_h, BATCH_H))
    batch_no = int(plant_h // BATCH_H) + 1
    fill = batch_pos < FILL_H
    convert = (batch_pos >= FILL_H) & (batch_pos < FILL_H + CONVERT_H)
    empty = (batch_pos >= FILL_H + CONVERT_H) & (batch_pos < FILL_H + CONVERT_H + EMPTY_H)
    ferm_h = float(np.clip(batch_pos - FILL_H, 0, CONVERT_H)) if convert else 0.0
    progress = float(np.clip(ferm_h / CONVERT_H, 0, 1))
    clock_h = ts.hour + ts.minute / 60.0

    ambient = 24 + 6 * np.sin(2 * np.pi * (clock_h - 14) / 24) + rng.normal(0, 0.35)
    mash_flow = float(np.clip(38 + rng.normal(0, 1.2) if fill else 4 + rng.normal(0, 0.4), 0, 48))
    corn_solids = 32 + 1.5 * np.sin(2 * np.pi * plant_h / 24) + rng.normal(0, 0.25) if (convert or fill) else 8.0
    temp = 59.5 + 1.4 * np.sin(2 * np.pi * plant_h / 12) + rng.normal(0, 0.25)
    if not convert and not fill:
        temp = 35 + rng.normal(0, 1.0)
    ph = 7.55 - 0.55 * progress + rng.normal(0, 0.04)
    if not convert and not fill:
        ph = 9.2 + rng.normal(0, 0.15)
    do = 1.8 - 0.7 * progress + rng.normal(0, 0.08) if convert else 6.5
    rpm = 48 + 4 * np.sin(2 * np.pi * plant_h / 6) + rng.normal(0, 0.8) if convert else 12
    enzyme = 92 * float(_temp_efficiency(np.array([temp]))[0]) * float(_ph_efficiency(np.array([ph]))[0]) if convert else 8
    enzyme = float(np.clip(enzyme + rng.normal(0, 1.4), 0, 110))
    residual = STARCH0 * np.exp(-2.4 * progress * (enzyme / 90.0)) + rng.normal(0, 0.15) if convert else 2.0
    residual = float(np.clip(residual, 0.2, 30))
    de = float(np.clip(18 + 72 * (1 - residual / STARCH0) + rng.normal(0, 0.6), 15, 98))
    k = 0.085 * (enzyme / 90.0)
    fructose = 42.0 * (1.0 - np.exp(-k * ferm_h)) if convert else 0.8
    fructose = float(np.clip(fructose + rng.normal(0, 0.25), 0.2, 48))
    glucose = float(np.clip(96 - fructose - 0.35 * residual + rng.normal(0, 0.3), 40, 98))
    lactic = float(np.clip(0.04 + 0.35 * progress * max(7.2 - ph, 0) + rng.normal(0, 0.01), 0.02, 1.4))
    brix = 41.5 + 3.2 * progress - 0.08 * residual + rng.normal(0, 0.12) if convert else 6.5
    brix = float(np.clip(brix, 4, 48))
    sweetness = float(np.clip(brix * (0.72 + 0.55 * (fructose / 42.0)) + rng.normal(0, 0.08), 3, 55))
    power = float(np.clip(180 + 3.1 * rpm + rng.normal(0, 6), 80, 520))
    if fill:
        stage = "fill"
    elif convert:
        stage = "ferment"
    elif empty:
        stage = "empty"
    else:
        stage = "cip"
    return {
        "timestamp": ts,
        "tank_id": tank_id,
        "batch_id": f"B{batch_no:04d}",
        "stage": stage,
        "plant_hour": float(plant_h),
        "brix_pct": brix,
        "sweetness_index": sweetness,
        "fructose_pct": fructose,
        "glucose_pct": glucose,
        "dextrose_equivalent": de,
        "fermenter_temp_c": float(temp),
        "ph": float(ph),
        "dissolved_oxygen_ppm": float(np.clip(do, 0.1, 8)),
        "agitator_rpm": float(np.clip(rpm, 5, 70)),
        "fermentation_hour": ferm_h,
        "enzyme_activity_u": enzyme,
        "residual_starch_pct": residual,
        "lactic_acid_pct": lactic,
        "corn_solids_pct": float(np.clip(corn_solids, 4, 40)),
        "mash_flow_m3h": mash_flow,
        "power_kw": power,
    }


def seed_history(tank_id: str = "F-1", n: int = 360, step_minutes: int = 5, seed: int = 11) -> pd.DataFrame:
    with _connect() as conn:
        conn.execute("DELETE FROM telemetry WHERE tank_id = ?", (tank_id,))
        conn.execute("DELETE FROM forecasts WHERE tank_id = ?", (tank_id,))
        conn.commit()
    rng = np.random.default_rng(seed)
    now = pd.Timestamp(datetime.now()).floor("s")
    start_plant = 10.0
    rows = []
    for i in range(n):
        plant_h = start_plant + i * (step_minutes / 60.0)
        ts = now - pd.Timedelta(minutes=step_minutes * (n - 1 - i))
        rows.append(simulate_row(plant_h, ts, tank_id, rng))
    df = pd.DataFrame(rows)
    insert_rows(df)
    return df


def append_tick(tank_id: str = "F-1", step_minutes: int = 5, seed: int = 11) -> pd.DataFrame:
    hist = read_history(tank_id, limit=2)
    rng = np.random.default_rng(seed + int(datetime.now().timestamp()) % 10_000)
    if hist.empty:
        return seed_history(tank_id=tank_id, step_minutes=step_minutes, seed=seed)
    last = hist.iloc[-1]
    ts = pd.Timestamp(last["timestamp"]) + pd.Timedelta(minutes=step_minutes)
    plant_h = float(last["plant_hour"]) + step_minutes / 60.0
    row = simulate_row(plant_h, ts, tank_id, rng)
    insert_rows(pd.DataFrame([row]))
    return read_history(tank_id, limit=800)


def save_forecast(
    tank_id: str,
    columns: list[str],
    future_index,
    median: np.ndarray,
    p10: np.ndarray,
    p90: np.ndarray,
    issued_at=None,
) -> None:
    if not columns or future_index is None or len(future_index) == 0:
        return
    issued = pd.Timestamp(issued_at or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    records = []
    for i, col in enumerate(columns):
        for step, ts in enumerate(future_index, start=1):
            records.append(
                (
                    issued,
                    pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M:%S"),
                    tank_id,
                    str(col),
                    int(step),
                    float(median[i, step - 1]),
                    float(p10[i, step - 1]),
                    float(p90[i, step - 1]),
                )
            )
    sql = """
        INSERT OR REPLACE INTO forecasts
        (issued_at, target_time, tank_id, column_name, step, median, p10, p90)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    with _connect() as conn:
        conn.executemany(sql, records)
        conn.commit()


def count_past_predictions(
    column_name: str,
    tank_id: str = "F-1",
    until=None,
) -> int:
    until_s = pd.Timestamp(until or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    with _connect() as conn:
        cur = conn.execute(
            """
            SELECT COUNT(DISTINCT target_time)
            FROM forecasts
            WHERE tank_id = ? AND column_name = ? AND target_time <= ?
            """,
            (tank_id, column_name, until_s),
        )
        return int(cur.fetchone()[0])


def read_prediction_history(
    column_name: str,
    tank_id: str = "F-1",
    until=None,
    limit: int = 400,
) -> pd.DataFrame:
    until_s = pd.Timestamp(until or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    with _connect() as conn:
        df = pd.read_sql_query(
            """
            SELECT f.target_time AS timestamp, f.median, f.p10, f.p90, f.step, f.issued_at
            FROM forecasts f
            INNER JOIN (
                SELECT target_time, MIN(step) AS min_step
                FROM forecasts
                WHERE tank_id = ? AND column_name = ? AND target_time <= ?
                GROUP BY target_time
            ) best
              ON f.target_time = best.target_time AND f.step = best.min_step
            WHERE f.tank_id = ? AND f.column_name = ? AND f.target_time <= ?
            ORDER BY f.target_time DESC
            LIMIT ?
            """,
            conn,
            params=(tank_id, column_name, until_s, tank_id, column_name, until_s, limit),
        )
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp").reset_index(drop=True)
