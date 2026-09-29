"""Make `backend/` importable from eval scripts and define shared paths."""
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
DATA_DIR = EVAL_DIR / "data"
RESULTS_PATH = EVAL_DIR / "results.jsonl"
sys.path.insert(0, str(EVAL_DIR.parent / "backend"))
