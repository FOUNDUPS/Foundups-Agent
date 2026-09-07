"""Isolated source loading avoids starting unrelated legacy OpenClaw imports."""
import importlib
from pathlib import Path
import sys
import types
from contextlib import contextmanager
import sqlite3

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"
PACKAGE = "_reddog_public_boundary_tests"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(SRC)]
sys.modules[PACKAGE] = package
policy = importlib.import_module(PACKAGE + ".reddog_public_policy")
sessions = importlib.import_module(PACKAGE + ".reddog_public_session_gate")


@pytest.fixture
def store(tmp_path):
    path = tmp_path / "agentdb.sqlite"
    @contextmanager
    def connect():
        conn = sqlite3.connect(path, timeout=5)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    gate = sessions.PublicSessionGate(connect)
    gate.initialize()
    return gate, connect


@pytest.fixture
def api_module():
    return importlib.import_module(PACKAGE + ".reddog_public_http")
