"""Run the measured-only local detector comparison from the repository root."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'backend')]
from research.guard_eval import main

if __name__ == '__main__':
    raise SystemExit(main())
