from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
DATA_DIR = PROJECT_ROOT / "data"

DEFAULT_MODEL_ID = "Datadog/Toto-2.0-22m"
DEFAULT_MODEL_DIR = MODELS_DIR / "Toto-2.0-22m"
SAMPLE_CSV = DATA_DIR / "sample_plant.csv"
SWEET_CSV = DATA_DIR / "corn_sweet_ferment.csv"
REALTIME_DB = DATA_DIR / "realtime_corn.db"
ID_COLUMNS = ("tank_id", "batch_id", "stage", "line_id", "process")

# Toto quantile head: 0.1 ... 0.9
QUANTILE_LEVELS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
MEDIAN_INDEX = 4
P10_INDEX = 0
P90_INDEX = 8

DEFAULT_CONTEXT = 512
DEFAULT_HORIZON = 96

# Typical plant-floor limits for the bundled sample line.
DEFAULT_THRESHOLDS = {
    "output_units_per_hour": {"warn": 190, "crit": 140, "mode": "low"},
    "line_speed_m_min": {"warn": 28, "crit": 22, "mode": "low"},
    "oven_temp_c": {"warn": 215, "crit": 228, "mode": "high"},
    "motor_vibration_mm_s": {"warn": 4.2, "crit": 5.5, "mode": "high"},
    "power_kw": {"warn": 780, "crit": 860, "mode": "high"},
    "scrap_rate_pct": {"warn": 2.4, "crit": 3.8, "mode": "high"},
    "brix_pct": {"warn": 36, "crit": 30, "mode": "low"},
    "sweetness_index": {"warn": 28, "crit": 22, "mode": "low"},
    "fructose_pct": {"warn": 28, "crit": 20, "mode": "low"},
    "fermenter_temp_c": {"warn": 64, "crit": 67, "mode": "high"},
    "ph": {"warn": 6.8, "crit": 6.3, "mode": "low"},
    "lactic_acid_pct": {"warn": 0.45, "crit": 0.7, "mode": "high"},
    "residual_starch_pct": {"warn": 8, "crit": 12, "mode": "high"},
    "color_icums": {"warn": 45, "crit": 60, "mode": "high"},
}

COLUMN_LABELS = {
    "output_units_per_hour": "Output (units/h)",
    "line_speed_m_min": "Line speed (m/min)",
    "oven_temp_c": "Oven temperature (°C)",
    "motor_vibration_mm_s": "Motor vibration (mm/s)",
    "power_kw": "Power (kW)",
    "scrap_rate_pct": "Scrap rate (%)",
    "ambient_temp_c": "Ambient temperature (°C)",
    "brix_pct": "Sweet degree (Brix %)",
    "sweetness_index": "Sweetness index",
    "fructose_pct": "Fructose (%)",
    "glucose_pct": "Glucose (%)",
    "dextrose_equivalent": "Dextrose equivalent",
    "fermenter_temp_c": "Fermenter temperature (°C)",
    "ph": "pH",
    "dissolved_oxygen_ppm": "Dissolved oxygen (ppm)",
    "agitator_rpm": "Agitator (rpm)",
    "fermentation_hour": "Fermentation hour",
    "enzyme_activity_u": "Enzyme activity",
    "residual_starch_pct": "Residual starch (%)",
    "lactic_acid_pct": "Lactic acid (%)",
    "corn_solids_pct": "Corn solids (%)",
    "mash_flow_m3h": "Mash flow (m³/h)",
    "steep_so2_ppm": "Steep SO2 (ppm)",
    "slurry_density_sg": "Slurry density (SG)",
    "color_icums": "Color (ICUMSA)",
    "ash_pct": "Ash (%)",
    "filter_pressure_kpa": "Filter pressure (kPa)",
    "steam_kpa": "Steam (kPa)",
    "cooling_water_temp_c": "Cooling water (°C)",
}
