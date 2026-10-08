from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from factory_toto.config import SAMPLE_CSV


def generate_sample_plant(
    days: int = 21,
    step_minutes: int = 15,
    seed: int = 7,
) -> pd.DataFrame:
    """Synthetic extrusion line with shifts, weekends, and a developing bearing issue."""
    rng = np.random.default_rng(seed)
    periods = days * 24 * 60 // step_minutes
    index = pd.date_range("2026-08-27 00:00:00", periods=periods, freq=f"{step_minutes}min")
    t = np.arange(periods)
    hours = (index.hour + index.minute / 60.0).to_numpy(dtype=np.float64)
    weekday = index.dayofweek.to_numpy()

    shift = np.where((hours >= 6) & (hours < 14), 1.00, 0.0)
    shift = np.where((hours >= 14) & (hours < 22), 0.94, shift)
    shift = np.where((hours >= 22) | (hours < 6), 0.78, shift)
    weekend = np.where(weekday >= 5, 0.62, 1.0)
    load = shift * weekend

    # Planned 90-minute changeover every Wednesday around 10:00.
    changeover = (
        (index.dayofweek == 2)
        & (hours >= 10)
        & (hours < 11.5)
    ).astype(float)
    load = load * (1.0 - 0.85 * changeover)

    ambient = 24 + 6 * np.sin(2 * np.pi * (hours - 14) / 24) + rng.normal(0, 0.4, periods)
    line_speed = 42 * load + 4 * np.sin(2 * np.pi * t / (24 * 4)) + rng.normal(0, 0.7, periods)
    line_speed = np.clip(line_speed, 8, 52)

    oven = 198 + 8 * load + 1.5 * np.sin(2 * np.pi * hours / 24) + rng.normal(0, 0.8, periods)
    # Temperature excursion on day 17 (controller drift).
    drift_start = 16 * 24 * 60 // step_minutes
    drift_len = 10 * 60 // step_minutes
    oven[drift_start : drift_start + drift_len] += np.linspace(0, 18, drift_len)

    vibration = 1.6 + 0.9 * (line_speed / 42) + 0.15 * np.sin(2 * np.pi * t / 32)
    vibration += rng.normal(0, 0.08, periods)
    # Developing motor bearing — vibration ramps in the last 4 days.
    ramp_start = periods - (4 * 24 * 60 // step_minutes)
    vibration[ramp_start:] += np.linspace(0, 2.8, periods - ramp_start)
    vibration = np.clip(vibration, 0.8, 8.0)

    power = 410 + 7.8 * line_speed + 0.9 * (oven - 198) + rng.normal(0, 8, periods)
    output = 8.4 * line_speed * (1 - 0.015 * np.maximum(oven - 210, 0)) + rng.normal(0, 6, periods)
    output = np.clip(output, 40, 480)
    scrap = 0.7 + 0.35 * (vibration - 1.6) + 0.08 * np.maximum(oven - 210, 0)
    scrap += rng.normal(0, 0.08, periods)
    scrap = np.clip(scrap, 0.2, 8.0)

    # Random missing telemetry (~1.5%).
    frame = pd.DataFrame(
        {
            "output_units_per_hour": output,
            "line_speed_m_min": line_speed,
            "oven_temp_c": oven,
            "motor_vibration_mm_s": vibration,
            "power_kw": power,
            "scrap_rate_pct": scrap,
            "ambient_temp_c": ambient,
        },
        index=index,
    )
    for col in frame.columns:
        drop = rng.choice(periods, size=max(1, periods // 70), replace=False)
        frame.iloc[drop, frame.columns.get_loc(col)] = np.nan

    frame.index.name = "timestamp"
    return frame.reset_index()


def write_sample_csv(path: Path | None = None) -> Path:
    dest = path or SAMPLE_CSV
    dest.parent.mkdir(parents=True, exist_ok=True)
    df = generate_sample_plant()
    df.to_csv(dest, index=False)
    return dest
