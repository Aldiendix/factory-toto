from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from factory_toto.sample import write_sample_csv
from factory_toto.sweet_corn import write_sweet_csv

if __name__ == "__main__":
    print(f"Wrote {write_sample_csv()}")
    print(f"Wrote {write_sweet_csv()}")
