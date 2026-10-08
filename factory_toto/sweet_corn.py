"""Corn-to-sweet liquor line: steep, liquefy, saccharify, ferment/convert."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from factory_toto.config import DATA_DIR

SWEET_CSV = DATA_DIR / "corn_sweet_ferment.csv"

VARIABLE_GROUPS: dict[str, list[tuple[str, str]]] = {
    "Sweetness (what you usually predict)": [
        ("brix_pct", "Sweet degree, Brix %"),
        ("sweetness_index", "Relative sweetness vs sucrose"),
        ("fructose_pct", "Fructose % on dry solids"),
        ("glucose_pct", "Glucose % on dry solids"),
        ("dextrose_equivalent", "Dextrose equivalent (DE)"),
    ],
    "Fermentation / conversion tank": [
        ("fermenter_temp_c", "Fermenter temperature C"),
        ("ph", "pH"),
        ("dissolved_oxygen_ppm", "Dissolved oxygen ppm"),
        ("agitator_rpm", "Agitator rpm"),
        ("fermentation_hour", "Hours in this batch"),
        ("enzyme_activity_u", "Enzyme / isomerase activity"),
        ("residual_starch_pct", "Residual starch %"),
        ("lactic_acid_pct", "Lactic acid %"),
    ],
    "Corn mash and steep": [
        ("corn_solids_pct", "Corn solids %"),
        ("mash_flow_m3h", "Mash flow m3/h"),
        ("steep_so2_ppm", "Steep SO2 ppm"),
        ("slurry_density_sg", "Slurry density SG"),
    ],
    "Finish and utilities": [
        ("color_icums", "Color ICUMSA"),
        ("ash_pct", "Ash %"),
        ("filter_pressure_kpa", "Filter pressure kPa"),
        ("steam_kpa", "Steam kPa"),
        ("cooling_water_temp_c", "Cooling water C"),
        ("power_kw", "Power kW"),
        ("ambient_temp_c", "Ambient C"),
    ],
}

DEFAULT_SWEET_COLUMNS = [
    "brix_pct",
    "sweetness_index",
    "fructose_pct",
    "glucose_pct",
    "dextrose_equivalent",
    "fermenter_temp_c",
    "ph",
    "dissolved_oxygen_ppm",
    "agitator_rpm",
    "fermentation_hour",
    "enzyme_activity_u",
    "residual_starch_pct",
    "lactic_acid_pct",
    "corn_solids_pct",
    "mash_flow_m3h",
    "power_kw",
]


def all_variable_keys() -> list[str]:
    keys: list[str] = []
    for items in VARIABLE_GROUPS.values():
        keys.extend(col for col, _ in items)
    return keys


def _temp_efficiency(temp: np.ndarray) -> np.ndarray:
    # Glucose isomerase likes about 58-62 C.
    return np.clip(1.0 - ((temp - 60.0) / 12.0) ** 2, 0.35, 1.0)


def _ph_efficiency(ph: np.ndarray) -> np.ndarray:
    return np.clip(1.0 - ((ph - 7.5) / 1.4) ** 2, 0.40, 1.0)


def generate_sweet_corn(
    days: int = 21,
    step_minutes: int = 15,
    tanks: int = 1,
    seed: int = 11,
    columns: list[str] | None = None,
    missing_pct: float = 1.2,
) -> pd.DataFrame:
    """One or more fermenters converting corn starch liquor toward sweet fructose syrup."""
    rng = np.random.default_rng(seed)
    wanted = columns or DEFAULT_SWEET_COLUMNS
    wanted = [c for c in wanted if c in set(all_variable_keys())]
    if not wanted:
        wanted = list(DEFAULT_SWEET_COLUMNS)

    step_h = step_minutes / 60.0
    batch_h = 48.0
    fill_h, empty_h, cip_h = 2.0, 2.0, 2.0
    convert_h = batch_h - fill_h - empty_h - cip_h

    frames: list[pd.DataFrame] = []
    start = pd.Timestamp("2026-08-27 00:00:00")
    periods = days * 24 * 60 // step_minutes

    for tank_i in range(tanks):
        index = pd.date_range(start, periods=periods, freq=f"{step_minutes}min")
        hours = (index.hour + index.minute / 60.0).to_numpy(dtype=np.float64)
        t_abs = np.arange(periods) * step_h + tank_i * 8.0
        batch_pos = np.mod(t_abs, batch_h)
        batch_no = np.floor(t_abs / batch_h).astype(int) + 1

        fill = batch_pos < fill_h
        convert = (batch_pos >= fill_h) & (batch_pos < fill_h + convert_h)
        empty = (batch_pos >= fill_h + convert_h) & (batch_pos < fill_h + convert_h + empty_h)
        cip = ~(fill | convert | empty)
        ferm_h = np.clip(batch_pos - fill_h, 0, convert_h)
        ferm_h = np.where(convert, ferm_h, 0.0)
        progress = np.clip(ferm_h / convert_h, 0, 1)

        ambient = 24 + 6 * np.sin(2 * np.pi * (hours - 14) / 24) + rng.normal(0, 0.35, periods)
        steam = 420 + 40 * convert.astype(float) + rng.normal(0, 8, periods)
        cooling = 18 + 0.35 * (ambient - 24) + rng.normal(0, 0.4, periods)
        mash_flow = np.where(fill, 38 + rng.normal(0, 1.2, periods), 4 + rng.normal(0, 0.4, periods))
        mash_flow = np.clip(mash_flow, 0, 48)
        corn_solids = np.where(convert | fill, 32 + 1.5 * np.sin(2 * np.pi * t_abs / 24) + rng.normal(0, 0.25, periods), 8)
        so2 = np.where(fill, 1050 + rng.normal(0, 40, periods), 120 + rng.normal(0, 20, periods))
        density = 1.12 + 0.004 * (corn_solids - 32) + rng.normal(0, 0.002, periods)

        temp = 59.5 + 1.4 * np.sin(2 * np.pi * t_abs / 12) + rng.normal(0, 0.25, periods)
        # Cooling loss on one weekend — sweetness stalls.
        if tank_i == 0:
            hot = (index.dayofweek >= 5) & (index.day >= 12) & (index.day <= 13)
            temp = np.where(hot & convert, temp + 7.5, temp)
        temp = np.where(cip, 35 + rng.normal(0, 1.0, periods), temp)

        ph = 7.55 - 0.55 * progress + rng.normal(0, 0.04, periods)
        ph = np.where(cip, 9.2 + rng.normal(0, 0.15, periods), ph)
        do = np.where(convert, 1.8 - 0.7 * progress + rng.normal(0, 0.08, periods), 6.5)
        rpm = np.where(convert, 48 + 4 * np.sin(2 * np.pi * t_abs / 6) + rng.normal(0, 0.8, periods), 12)
        enzyme = np.where(convert, 92 * _temp_efficiency(temp) * _ph_efficiency(ph), 8)
        enzyme = np.clip(enzyme + rng.normal(0, 1.4, periods), 0, 110)

        starch0 = 28.0
        residual = starch0 * np.exp(-2.4 * progress * (enzyme / 90.0)) + rng.normal(0, 0.15, periods)
        residual = np.clip(np.where(convert, residual, 2.0), 0.2, 30)
        de = np.clip(18 + 72 * (1 - residual / starch0) + rng.normal(0, 0.6, periods), 15, 98)

        k = 0.085 * (enzyme / 90.0)
        fructose = 42.0 * (1.0 - np.exp(-k * ferm_h))
        fructose = np.where(convert, fructose, 0.8)
        fructose = np.clip(fructose + rng.normal(0, 0.25, periods), 0.2, 48)
        glucose = np.clip(96 - fructose - 0.35 * residual + rng.normal(0, 0.3, periods), 40, 98)
        lactic = np.clip(0.04 + 0.35 * progress * np.maximum(7.2 - ph, 0) + rng.normal(0, 0.01, periods), 0.02, 1.4)
        brix = np.where(convert, 41.5 + 3.2 * progress - 0.08 * residual + rng.normal(0, 0.12, periods), 6.5)
        brix = np.clip(brix, 4, 48)
        # Fructose is sweeter than glucose, so sweet degree rises faster than Brix alone.
        sweetness = brix * (0.72 + 0.55 * (fructose / 42.0))
        sweetness = np.clip(sweetness + rng.normal(0, 0.08, periods), 3, 55)

        color = np.where(convert, 18 + 22 * progress + 4 * np.maximum(temp - 62, 0) + rng.normal(0, 0.8, periods), 6)
        ash = 0.18 + 0.04 * (so2 / 1000) + rng.normal(0, 0.01, periods)
        filt_p = np.where(convert, 145 + 35 * progress + rng.normal(0, 4, periods), 40)
        power = 180 + 3.1 * rpm + 0.12 * steam + rng.normal(0, 6, periods)

        stage = np.where(fill, "fill", np.where(convert, "ferment", np.where(empty, "empty", "cip")))
        payload = {
            "timestamp": index,
            "tank_id": f"F-{tank_i + 1}",
            "batch_id": [f"B{int(n):04d}" for n in batch_no],
            "stage": stage,
            "brix_pct": brix,
            "sweetness_index": sweetness,
            "fructose_pct": fructose,
            "glucose_pct": glucose,
            "dextrose_equivalent": de,
            "fermenter_temp_c": temp,
            "ph": ph,
            "dissolved_oxygen_ppm": np.clip(do, 0.1, 8),
            "agitator_rpm": np.clip(rpm, 5, 70),
            "fermentation_hour": ferm_h,
            "enzyme_activity_u": enzyme,
            "residual_starch_pct": residual,
            "lactic_acid_pct": lactic,
            "corn_solids_pct": np.clip(corn_solids, 4, 40),
            "mash_flow_m3h": mash_flow,
            "steep_so2_ppm": np.clip(so2, 50, 1400),
            "slurry_density_sg": np.clip(density, 1.02, 1.25),
            "color_icums": np.clip(color, 3, 80),
            "ash_pct": np.clip(ash, 0.05, 0.6),
            "filter_pressure_kpa": np.clip(filt_p, 20, 280),
            "steam_kpa": np.clip(steam, 250, 560),
            "cooling_water_temp_c": cooling,
            "power_kw": np.clip(power, 80, 520),
            "ambient_temp_c": ambient,
        }
        keep = ["timestamp", "tank_id", "batch_id", "stage", *wanted]
        frame = pd.DataFrame({k: payload[k] for k in keep})
        num_cols = [c for c in wanted if c in frame.columns]
        if missing_pct > 0 and num_cols:
            n_drop = max(1, int(len(frame) * missing_pct / 100))
            for col in num_cols:
                drop = rng.choice(len(frame), size=min(n_drop, len(frame) // 8), replace=False)
                frame.loc[frame.index[drop], col] = np.nan
        frames.append(frame)

    out = pd.concat(frames, ignore_index=True)
    return out.sort_values(["timestamp", "tank_id"]).reset_index(drop=True)


def write_sweet_csv(
    path: Path | None = None,
    **kwargs,
) -> Path:
    dest = path or SWEET_CSV
    dest.parent.mkdir(parents=True, exist_ok=True)
    generate_sweet_corn(**kwargs).to_csv(dest, index=False)
    return dest
