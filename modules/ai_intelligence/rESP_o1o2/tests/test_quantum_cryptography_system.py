"""Smoke test for src.quantum_cryptography_system."""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_module_importable_and_exports_symbol():
    module = pytest.importorskip("src.quantum_cryptography_system")
    assert hasattr(module, "QuantumCryptographicSystem")
