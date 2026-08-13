"""
Data Pipeline Module Entry Point (`src/data/build_splits.py`)

Delegates to authoritative single splitter in `src/splits/build_splits.py`.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.splits.build_splits import build_family_disjoint_splits

if __name__ == "__main__":
    build_family_disjoint_splits(seed=42)
