"""Run the explicitly authorized A-only R1 calibration; never pulls a model."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'backend')]
from research.r1_runner import main

if __name__ == '__main__':
    raise SystemExit(main())
