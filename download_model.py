"""Download Datadog Toto 2.0 weights into ./models for fully local inference."""

from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import snapshot_download

from factory_toto.config import DEFAULT_MODEL_ID, MODELS_DIR


def _has_weights(target: Path) -> bool:
    if not (target / "config.json").exists():
        return False
    return bool(list(target.glob("*.safetensors")) or list(target.glob("*.bin")))


def download(model_id: str = DEFAULT_MODEL_ID, dest: Path | None = None, force: bool = False) -> Path:
    name = model_id.split("/")[-1]
    target = dest or (MODELS_DIR / name)
    target.mkdir(parents=True, exist_ok=True)
    if _has_weights(target) and not force:
        print(f"Local weights already present at {target}. Skipping download.")
        return target
    print(f"Downloading {model_id} -> {target}")
    snapshot_download(
        repo_id=model_id,
        local_dir=str(target),
    )
    print("Download complete. The app can now run offline.")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Toto weights for local use.")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_ID,
        help="Hugging Face repo id, e.g. Datadog/Toto-2.0-22m",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Download again even if local weights already exist.",
    )
    args = parser.parse_args()
    download(args.model, force=args.force)
