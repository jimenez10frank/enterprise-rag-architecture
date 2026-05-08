"""CLI: run Ragas on ``data/golden/golden_set.jsonl``.

Usage:
    python scripts/eval.py [--skip-rerank] [--faithfulness-min 0.95]

Exits 0 when OPENAI_API_KEY is unset (skip). Exits 1 when mean Faithfulness
on answered rows is below ``--faithfulness-min``.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.eval.ragas_runner import main

if __name__ == "__main__":
    sys.exit(main())
