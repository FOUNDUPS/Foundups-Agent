"""Isolated source loading avoids starting unrelated legacy OpenClaw imports."""
import importlib
import importlib.util
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
def database_store(tmp_path, monkeypatch):
    """Load unchanged DB source with an isolated singleton and temporary path."""
    path = SRC.parents[2] / "infrastructure" / "database" / "src" / "db_manager.py"
    spec = importlib.util.spec_from_file_location("_reddog_public_test_db", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv("FOUNDUPS_DB_ENGINE", "sqlite")
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "actual-agentdb.sqlite"))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    manager = module.DatabaseManager()
    gate = sessions.PublicSessionGate(manager.get_connection)
    gate.initialize()
    return gate, manager, module


@pytest.fixture
def api_module():
    return importlib.import_module(PACKAGE + ".reddog_public_http")
