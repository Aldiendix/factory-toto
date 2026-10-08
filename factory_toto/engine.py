from __future__ import annotations

import os
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from factory_toto.config import (
    DEFAULT_MODEL_DIR,
    MEDIAN_INDEX,
    P10_INDEX,
    P90_INDEX,
    QUANTILE_LEVELS,
    DEFAULT_THRESHOLDS,
)
from factory_toto.data import infer_step, to_model_arrays

# GluonTS (pulled in by Toto) prints this on first import. Harmless, not a login.
warnings.filterwarnings(
    "ignore",
    message="Using `json`-module for json-handling",
    category=UserWarning,
)
warnings.filterwarnings(
    "ignore",
    message="You are sending unauthenticated requests to the HF Hub",
    category=UserWarning,
)


@dataclass
class ForecastResult:
    columns: list[str]
    context_index: pd.DatetimeIndex
    future_index: pd.DatetimeIndex
    context: np.ndarray  # (n_var, context)
    quantiles: np.ndarray  # (9, n_var, horizon)
    device: str
    model_path: str

    @property
    def median(self) -> np.ndarray:
        return self.quantiles[MEDIAN_INDEX]

    @property
    def p10(self) -> np.ndarray:
        return self.quantiles[P10_INDEX]

    @property
    def p90(self) -> np.ndarray:
        return self.quantiles[P90_INDEX]


class TotoEngine:
    def __init__(self, model_dir: Path | None = None) -> None:
        self.model_dir = Path(model_dir or DEFAULT_MODEL_DIR)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None

    def ensure_weights(self) -> None:
        required = ["config.json"]
        if not self.model_dir.exists():
            raise FileNotFoundError(
                f"Local Toto weights not found at {self.model_dir}. "
                "Run: python download_model.py"
            )
        missing = [name for name in required if not (self.model_dir / name).exists()]
        weight_files = list(self.model_dir.glob("*.safetensors")) + list(
            self.model_dir.glob("*.bin")
        )
        if missing or not weight_files:
            raise FileNotFoundError(
                f"Incomplete Toto checkpoint in {self.model_dir}. "
                "Run: python download_model.py"
            )

    def load(self) -> None:
        if self.model is not None:
            return
        self.ensure_weights()
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
        from toto2 import Toto2Model

        self.model = Toto2Model.from_pretrained(
            str(self.model_dir),
            local_files_only=True,
            map_location=str(self.device),
        )
        self.model = self.model.to(self.device).eval()

    def forecast(
        self,
        frame: pd.DataFrame,
        horizon: int,
        context_length: int,
        columns: list[str] | None = None,
    ) -> ForecastResult:
        self.load()
        assert self.model is not None

        work = frame[columns] if columns else frame
        values, mask, ctx_index = to_model_arrays(work, context_length)
        model_values, model_mask = values, mask
        patch_size = int(getattr(self.model.config, "patch_size", 32))
        remainder = model_values.shape[-1] % patch_size
        if remainder:
            pad = patch_size - remainder
            model_values = np.pad(model_values, ((0, 0), (pad, 0)))
            model_mask = np.pad(model_mask, ((0, 0), (pad, 0)), constant_values=False)
        target = torch.from_numpy(model_values).unsqueeze(0).to(self.device)
        target_mask = torch.from_numpy(model_mask).unsqueeze(0).to(self.device)
        n_var = target.shape[1]
        series_ids = torch.zeros(1, n_var, dtype=torch.long, device=self.device)
        has_missing = not bool(model_mask.all())
        decode_block_size = None if horizon <= 512 else 768

        with torch.inference_mode():
            quantiles = self.model.forecast(
                {
                    "target": target,
                    "target_mask": target_mask,
                    "series_ids": series_ids,
                },
                horizon=int(horizon),
                decode_block_size=decode_block_size,
                has_missing_values=has_missing,
            )

        q = quantiles[:, 0].detach().cpu().numpy()  # (9, n_var, horizon)
        step = infer_step(ctx_index)
        last = ctx_index[-1]
        future = pd.date_range(last + step, periods=horizon, freq=step)
        return ForecastResult(
            columns=list(work.columns),
            context_index=ctx_index,
            future_index=future,
            context=values,
            quantiles=q,
            device=str(self.device),
            model_path=str(self.model_dir),
        )


def evaluate_alerts(
    result: ForecastResult,
    thresholds: dict | None = None,
) -> list[dict]:
    rules = thresholds or DEFAULT_THRESHOLDS
    alerts: list[dict] = []
    for i, col in enumerate(result.columns):
        rule = rules.get(col)
        if not rule:
            continue
        median = result.median[i]
        p90 = result.p90[i]
        p10 = result.p10[i]
        mode = rule.get("mode", "high")
        warn = float(rule["warn"])
        crit = float(rule["crit"])
        if mode == "high":
            crit_hit = float(np.max(p90)) >= crit or float(np.max(median)) >= crit
            warn_hit = float(np.max(p90)) >= warn or float(np.max(median)) >= warn
            peak = float(np.max(p90))
            when = result.future_index[int(np.argmax(p90))]
        else:
            crit_hit = float(np.min(p10)) <= crit or float(np.min(median)) <= crit
            warn_hit = float(np.min(p10)) <= warn or float(np.min(median)) <= warn
            peak = float(np.min(p10))
            when = result.future_index[int(np.argmin(p10))]
        if not warn_hit:
            continue
        alerts.append(
            {
                "column": col,
                "level": "critical" if crit_hit else "warning",
                "mode": mode,
                "value": peak,
                "when": when,
                "warn": warn,
                "crit": crit,
            }
        )
    order = {"critical": 0, "warning": 1}
    alerts.sort(key=lambda a: order[a["level"]])
    return alerts


def result_to_frame(result: ForecastResult) -> pd.DataFrame:
    rows = {"timestamp": result.future_index}
    for i, col in enumerate(result.columns):
        rows[f"{col}_p10"] = result.p10[i]
        rows[f"{col}_p50"] = result.median[i]
        rows[f"{col}_p90"] = result.p90[i]
    return pd.DataFrame(rows)


def latest_kpis(frame: pd.DataFrame) -> dict[str, float]:
    if frame.empty:
        return {}
    clean = frame.dropna(how="all")
    if clean.empty:
        return {}
    last = clean.iloc[-1]
    return {col: float(last[col]) for col in frame.columns if pd.notna(last[col])}
