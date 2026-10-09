"""Ensure the src-layout package is importable in tests."""

from pathlib import Path
import sys


SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_ROOT))
