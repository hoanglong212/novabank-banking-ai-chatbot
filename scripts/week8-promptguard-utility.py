"""Repeat the historical benign-only D evaluation with local Prompt Guard."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'backend')]
from research.promptguard_utility import main

if __name__ == '__main__':
    raise SystemExit(main())
