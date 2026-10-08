"""One-shot local inference check."""

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from factory_toto.config import SAMPLE_CSV
from factory_toto.data import load_table, prepare_plant_frame
from factory_toto.engine import TotoEngine
from factory_toto.sample import write_sample_csv


def main() -> None:
    if not SAMPLE_CSV.exists():
        write_sample_csv()
    frame = prepare_plant_frame(load_table(SAMPLE_CSV))
    engine = TotoEngine()
    t0 = time.time()
    result = engine.forecast(frame, horizon=32, context_length=256, columns=list(frame.columns)[:3])
    elapsed = time.time() - t0
    print(f"device={result.device}")
    print(f"model={result.model_path}")
    print(f"quantiles={result.quantiles.shape}")
    print(f"median_last={result.median[:, -1]}")
    print(f"elapsed_sec={elapsed:.1f}")


if __name__ == "__main__":
    main()
