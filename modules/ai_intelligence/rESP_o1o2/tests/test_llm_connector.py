"""Smoke test for src.llm_connector."""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_module_importable_and_exports_symbol():
    module = pytest.importorskip("src.llm_connector")
    assert hasattr(module, "LLMConnector")
