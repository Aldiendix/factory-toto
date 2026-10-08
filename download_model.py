"""Check that Toto-2.0-22m weights are already on this computer. No Hugging Face."""

from __future__ import annotations

import argparse
from pathlib import Path

from factory_toto.config import MODELS_DIR

TARGET = MODELS_DIR / "Toto-2.0-22m"


def _has_weights(target: Path) -> bool:
    if not (target / "config.json").exists():
        return False
    return bool(list(target.glob("*.safetensors")) or list(target.glob("*.bin")))


def download(dest: Path | None = None, force: bool = False) -> Path:
    target = dest or TARGET
    if _has_weights(target):
        print(f"Local weights ready at {target}. Offline. No Hugging Face.")
        return target
    raise FileNotFoundError(
        f"Toto weights not found at {target}. "
        "Copy models/Toto-2.0-22m (config.json + model.safetensors) from this repo. "
        "This app does not download from Hugging Face."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify local Toto weights (offline, no Hugging Face).")
    parser.add_argument("--force", action="store_true", help="Ignored. Weights are local-only.")
    args = parser.parse_args()
    download(force=args.force)
