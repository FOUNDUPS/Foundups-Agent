"""
Integration Test: Command Rolodex WRE Connection Alignment

Verifies that JSON and SQLite rolodex metadata match actual serialized rows,
and that `wre_connected_count` derives from the same source as the per-row
`wre_connected` flag.

NOTE: These are integration tests over generated artifacts, not hermetic unit
tests. The JSON artifact is committed; the SQLite artifact is gitignored
(*.db) and only exists after a local `python holo_index.py --index-cli` run.
SQLite and cross-format tests skip gracefully when the .db is absent.

Worker CE — ROLODEX_WRE_CONNECTION_ALIGNMENT_PHASE1
"""

import json
import sqlite3
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
ROLODEX_JSON = REPO_ROOT / "holo_index" / "docs" / "command_rolodex.json"
ROLODEX_DB = REPO_ROOT / "holo_index" / "docs" / "command_rolodex.db"

_needs_json = pytest.mark.skipif(
    not ROLODEX_JSON.exists(),
    reason="command_rolodex.json not found — run: python holo_index.py --index-cli",
)
_needs_db = pytest.mark.skipif(
    not ROLODEX_DB.exists(),
    reason="command_rolodex.db not found (gitignored) — run: python holo_index.py --index-cli",
)


@pytest.fixture
def json_data():
    """Load JSON rolodex."""
    with open(ROLODEX_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sqlite_data():
    """Load SQLite rolodex metadata and row counts."""
    conn = sqlite3.connect(str(ROLODEX_DB))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT key, value FROM rolodex_metadata")
    meta = {row["key"]: row["value"] for row in cur.fetchall()}

    cur.execute("SELECT COUNT(*) FROM cli_commands")
    total_rows = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM cli_commands WHERE wre_connected = 1")
    connected_rows = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM cli_commands WHERE wre_connected = 0")
    orphan_rows = cur.fetchone()[0]

    conn.close()
    return {"meta": meta, "total_rows": total_rows, "connected_rows": connected_rows, "orphan_rows": orphan_rows}


@_needs_json
class TestJSONAlignment:
    """JSON metadata matches actual serialized command rows."""

    def test_wre_connected_count_matches_rows(self, json_data):
        meta_count = json_data["wre_connected_count"]
        actual = sum(1 for c in json_data["commands"] if c.get("wre_connected"))
        assert meta_count == actual, (
            f"JSON wre_connected_count ({meta_count}) != actual connected rows ({actual})"
        )

    def test_orphan_count_matches_rows(self, json_data):
        meta_count = json_data["orphan_count"]
        actual = sum(1 for c in json_data["commands"] if not c.get("wre_connected"))
        assert meta_count == actual, (
            f"JSON orphan_count ({meta_count}) != actual orphan rows ({actual})"
        )

    def test_total_equals_connected_plus_orphans(self, json_data):
        total = json_data["total_cli_entrypoints"]
        connected = json_data["wre_connected_count"]
        orphans = json_data["orphan_count"]
        assert total == connected + orphans, (
            f"JSON total ({total}) != connected ({connected}) + orphans ({orphans})"
        )

    def test_total_matches_command_list_length(self, json_data):
        meta_total = json_data["total_cli_entrypoints"]
        actual_total = len(json_data["commands"])
        assert meta_total == actual_total


@_needs_db
class TestSQLiteAlignment:
    """SQLite metadata matches actual row counts (requires local --index-cli run)."""

    def test_wre_connected_count_matches_rows(self, sqlite_data):
        meta_count = int(sqlite_data["meta"]["wre_connected_count"])
        actual = sqlite_data["connected_rows"]
        assert meta_count == actual, (
            f"SQLite wre_connected_count ({meta_count}) != actual connected rows ({actual})"
        )

    def test_orphan_count_matches_rows(self, sqlite_data):
        meta_count = int(sqlite_data["meta"]["orphan_count"])
        actual = sqlite_data["orphan_rows"]
        assert meta_count == actual, (
            f"SQLite orphan_count ({meta_count}) != actual orphan rows ({actual})"
        )

    def test_total_equals_connected_plus_orphans(self, sqlite_data):
        total = int(sqlite_data["meta"]["total_commands"])
        connected = int(sqlite_data["meta"]["wre_connected_count"])
        orphans = int(sqlite_data["meta"]["orphan_count"])
        assert total == connected + orphans

    def test_total_matches_row_count(self, sqlite_data):
        meta_total = int(sqlite_data["meta"]["total_commands"])
        actual_total = sqlite_data["total_rows"]
        assert meta_total == actual_total


@_needs_db
@_needs_json
class TestCrossFormatParity:
    """JSON and SQLite report the same counts (requires both artifacts)."""

    def test_connected_count_parity(self, json_data, sqlite_data):
        j = json_data["wre_connected_count"]
        s = int(sqlite_data["meta"]["wre_connected_count"])
        assert j == s, f"JSON connected ({j}) != SQLite connected ({s})"

    def test_orphan_count_parity(self, json_data, sqlite_data):
        j = json_data["orphan_count"]
        s = int(sqlite_data["meta"]["orphan_count"])
        assert j == s, f"JSON orphans ({j}) != SQLite orphans ({s})"

    def test_total_count_parity(self, json_data, sqlite_data):
        j = json_data["total_cli_entrypoints"]
        s = int(sqlite_data["meta"]["total_commands"])
        assert j == s, f"JSON total ({j}) != SQLite total ({s})"


@_needs_json
class TestWREConnectionSemantics:
    """wre_connected means: CLI entrypoint has a matching SKILLz.md in its directory tree."""

    def test_connected_commands_have_skillz_path(self, json_data):
        for cmd in json_data["commands"]:
            if cmd.get("wre_connected"):
                assert cmd.get("skillz_md_path"), (
                    f"Connected command {cmd['path']} has no skillz_md_path"
                )

    def test_orphan_commands_have_no_skillz_path(self, json_data):
        for cmd in json_data["commands"]:
            if not cmd.get("wre_connected"):
                assert not cmd.get("skillz_md_path"), (
                    f"Orphan command {cmd['path']} has skillz_md_path={cmd.get('skillz_md_path')}"
                )


@_needs_json
class TestOrphanClassification:
    """CF2: orphan_class field validates orphan categorization."""

    VALID_ORPHAN_CLASSES = {
        "connected",       # WRE-connected (has SKILLz.md)
        "candidate",       # Should be connected to WRE
        "false_positive",  # Should never be counted (__init__.py, archived)
        "developer_tool",  # Manual tools used during dev
        "research",        # Simulation/analysis tools
        "wre_internal",    # Part of WRE machinery (circular dependency risk)
        "trivial",         # <50 lines, simple launchers
        "unclassified",    # Not yet classified
    }

    def test_all_commands_have_orphan_class(self, json_data):
        """Every command must have an orphan_class field."""
        for cmd in json_data["commands"]:
            assert "orphan_class" in cmd, (
                f"Command {cmd['path']} missing orphan_class field"
            )

    def test_orphan_class_values_valid(self, json_data):
        """orphan_class must be one of the defined categories."""
        for cmd in json_data["commands"]:
            orphan_class = cmd.get("orphan_class", "unclassified")
            assert orphan_class in self.VALID_ORPHAN_CLASSES, (
                f"Command {cmd['path']} has invalid orphan_class: {orphan_class}"
            )

    def test_connected_commands_have_connected_class(self, json_data):
        """WRE-connected commands must have orphan_class='connected'."""
        for cmd in json_data["commands"]:
            if cmd.get("wre_connected"):
                assert cmd.get("orphan_class") == "connected", (
                    f"Connected command {cmd['path']} has orphan_class={cmd.get('orphan_class')}, expected 'connected'"
                )

    def test_orphans_not_marked_connected(self, json_data):
        """Orphan commands must not have orphan_class='connected'."""
        for cmd in json_data["commands"]:
            if not cmd.get("wre_connected"):
                assert cmd.get("orphan_class") != "connected", (
                    f"Orphan command {cmd['path']} incorrectly marked as orphan_class='connected'"
                )

    def test_no_init_files_in_rolodex(self, json_data):
        """CF2: __init__.py files should be excluded from rolodex."""
        for cmd in json_data["commands"]:
            assert not cmd["path"].endswith("__init__.py"), (
                f"False positive __init__.py included in rolodex: {cmd['path']}"
            )
