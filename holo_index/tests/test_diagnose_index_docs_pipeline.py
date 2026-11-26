"""Focused truth-boundary tests for the read-only docs diagnostic."""

from __future__ import annotations

import hashlib
import os
import sqlite3
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from holo_index.scripts import diagnose_index_docs_pipeline as diagnostic
from holo_index.scripts import _navigation_docs_metadata_probe as metadata_probe


REPO_ROOT = Path(__file__).resolve().parents[2]


def _complete_model_snapshot(ssd_path: Path) -> Path:
    snapshot = (
        ssd_path
        / "models"
        / "models--sentence-transformers--all-MiniLM-L6-v2"
        / "snapshots"
        / "revision-one"
    )
    snapshot.mkdir(parents=True)
    for name in ("modules.json", "config.json", "model.safetensors", "tokenizer.json"):
        (snapshot / name).write_text(name, encoding="utf-8")
    return snapshot


def _metadata_columns(value: object) -> tuple[object, object, object, object]:
    if isinstance(value, bool):
        return None, None, None, value
    if isinstance(value, int):
        return None, value, None, None
    if isinstance(value, float):
        return None, None, value, None
    return value, None, None, None


def _write_navigation_docs_database(ssd_path: Path, paths: list[object]) -> Path:
    database = ssd_path / "vectors" / "chroma.sqlite3"
    database.parent.mkdir(parents=True)
    connection = sqlite3.connect(database)
    try:
        connection.executescript(
            """
            CREATE TABLE collections (id TEXT PRIMARY KEY, name TEXT NOT NULL);
            CREATE TABLE segments (
                id TEXT PRIMARY KEY, type TEXT NOT NULL,
                scope TEXT NOT NULL, collection TEXT NOT NULL
            );
            CREATE TABLE embeddings (
                id INTEGER PRIMARY KEY, segment_id TEXT NOT NULL,
                embedding_id TEXT NOT NULL, seq_id BLOB NOT NULL,
                created_at TIMESTAMP NOT NULL
            );
            CREATE TABLE embedding_metadata (
                id INTEGER NOT NULL, key TEXT NOT NULL,
                string_value TEXT, int_value INTEGER,
                float_value REAL, bool_value INTEGER,
                PRIMARY KEY (id, key)
            );
            """
        )
        connection.execute(
            "INSERT INTO collections(id, name) VALUES (?, ?)",
            ("collection-one", "navigation_docs"),
        )
        connection.execute(
            "INSERT INTO segments(id, type, scope, collection) VALUES (?, ?, ?, ?)",
            ("segment-one", "metadata", "METADATA", "collection-one"),
        )
        for index, path in enumerate(paths, start=1):
            connection.execute(
                "INSERT INTO embeddings VALUES (?, ?, ?, ?, ?)",
                (index, "segment-one", f"doc_{index}", b"1", "2026-08-16"),
            )
            connection.execute(
                "INSERT INTO embedding_metadata VALUES (?, ?, ?, ?, ?, ?)",
                (index, "path", *_metadata_columns(path)),
            )
        connection.commit()
    finally:
        connection.close()
    return database


def _commit_concurrent_doc(
    database: Path,
    commit_attempted: threading.Event,
    writer_finished: threading.Event,
    writer_errors: list[Exception],
) -> None:
    connection = sqlite3.connect(database, timeout=2.0)
    try:
        connection.execute(
            "INSERT INTO embeddings VALUES (?, ?, ?, ?, ?)",
            (3, "segment-one", "doc_3", b"1", "2026-08-16"),
        )
        connection.execute(
            "INSERT INTO embedding_metadata VALUES (?, ?, ?, ?, ?, ?)",
            (3, "path", "docs/concurrent.md", None, None, None),
        )
        commit_attempted.set()
        connection.commit()
    except Exception as error:
        writer_errors.append(error)
    finally:
        connection.close()
        writer_finished.set()


def _create_module_target(project_root: Path) -> tuple[str, str]:
    module = project_root / "modules" / "infrastructure" / "example"
    module.mkdir(parents=True)
    for name in ("README.md", "INTERFACE.md"):
        (module / name).write_text(f"# {name}\n", encoding="utf-8")
    return (
        "modules/infrastructure/example/README.md",
        "modules/infrastructure/example/INTERFACE.md",
    )


def _observe_paths(tmp_path: Path, paths: list[str]) -> dict[str, object]:
    _create_module_target(tmp_path)
    ssd_path = tmp_path / "ssd"
    _write_navigation_docs_database(ssd_path, paths)
    return diagnostic.observe_navigation_docs_collection_readonly(
        str(ssd_path), project_root=tmp_path
    )


def _run_git(repo_root: Path, *args: str) -> None:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert completed.returncode == 0


def test_help_exits_before_any_diagnostic_probe(monkeypatch, capsys) -> None:
    def unexpected_probe(_project_root: Path):
        raise AssertionError("diagnostic probe must not run for --help")

    monkeypatch.setattr(diagnostic, "_build_summary", unexpected_probe)

    with pytest.raises(SystemExit) as raised:
        diagnostic.main(["--help"])

    captured = capsys.readouterr()
    assert raised.value.code == 0
    assert "usage: diagnose_index_docs_pipeline.py" in captured.out
    assert "PRIMARY ROOT CAUSE" not in captured.out + captured.err


def test_real_main_help_subprocess_exits_without_probe() -> None:
    script = REPO_ROOT / "holo_index" / "scripts" / "diagnose_index_docs_pipeline.py"

    completed = subprocess.run(
        [sys.executable, "-B", str(script), "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert completed.returncode == 0
    assert "usage: diagnose_index_docs_pipeline.py" in completed.stdout
    assert "PRIMARY ROOT CAUSE" not in completed.stdout + completed.stderr


def test_h2_resolves_huggingface_snapshot_without_path_disclosure(
    tmp_path: Path,
) -> None:
    ssd_path = tmp_path / "secret-root-token" / "ssd"
    _complete_model_snapshot(ssd_path)

    report = diagnostic.probe_h2_embedding_model(str(ssd_path))

    assert report["cache_hit"] is True
    assert report["cache_layout"] == "huggingface_snapshot"
    assert report["h2_finding"] == "MODEL_CACHE_PRESENT"
    assert "secret-root-token" not in repr(report)


def test_h4_does_not_promote_policy_backup_exclusion_to_root_cause(
    tmp_path: Path,
) -> None:
    for target in diagnostic.TARGETS:
        path = tmp_path / target["rel_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# target\n", encoding="utf-8")
    backup = tmp_path / "docs" / "audit_backup" / "excluded.md"
    backup.parent.mkdir(parents=True)
    backup.write_text("# backup\n", encoding="utf-8")

    report = diagnostic.probe_h4_filter_targets(tmp_path)

    assert report["rejected_target_count"] == 0
    assert report["docs_tree_failing"] == 1
    assert report["failure_counts_by_clause"] == {"no_backup": 1}
    assert report["h4_finding"] == "TARGETS_ADMITTED_WITH_POLICY_EXCLUSIONS"


def test_readonly_metadata_probe_finds_absolute_tier0_path_break(
    tmp_path: Path,
) -> None:
    _create_module_target(tmp_path)
    secret_root = "C:/secret-authority-root-token"
    paths = [
        f"{secret_root}/modules/infrastructure/example/README.md",
        f"{secret_root}/modules/infrastructure/example/INTERFACE.md",
        f"{secret_root}/docs/audits/architecture/EXAMPLE.md",
    ]
    ssd_path = tmp_path / "ssd"
    database = _write_navigation_docs_database(ssd_path, paths)
    before = hashlib.sha256(database.read_bytes()).hexdigest()

    report = diagnostic.observe_navigation_docs_collection_readonly(
        str(ssd_path), project_root=tmp_path
    )

    after = hashlib.sha256(database.read_bytes()).hexdigest()
    assert before == after
    assert report["navigation_docs_total"] == 3
    assert report["all_paths_absolute"] is True
    assert report["absolute_tier0_rows"] == 2
    assert report["strict_tier0_relative_exact_rows"] == 0
    assert report["docs_audits_architecture_in_index"] == 1
    assert report["stored_checkout_root_count"] == 1
    assert report["stored_checkout_matches_diagnostic_root"] is False
    assert report["missing_required_tier0_rows"] == 2
    assert report["strict_tier0_contract_complete"] is False
    assert report["h7_finding"] == "TIER0_ABSOLUTE_PATH_ROWS"
    assert "secret-authority-root-token" not in repr(report)


def test_exact_tier0_pair_is_complete_and_case_sensitive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    readme, interface = _create_module_target(tmp_path)
    ssd_path = tmp_path / "ssd"
    database = _write_navigation_docs_database(ssd_path, [readme, interface])
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    monkeypatch.setattr(metadata_probe, "SQLITE_PATH_PAGE_ROWS", 1)

    report = diagnostic.observe_navigation_docs_collection_readonly(
        str(ssd_path), project_root=tmp_path
    )

    assert hashlib.sha256(database.read_bytes()).hexdigest() == before
    assert report["canonical_module_target_count"] == 1
    assert report["required_tier0_exact_row_count"] == 2
    assert report["strict_tier0_relative_exact_rows"] == 2
    assert report["strict_tier0_contract_complete"] is True
    assert report["h7_findings"] == ["TIER0_EXACT_CONTRACT_COMPLETE"]


def test_metadata_rows_and_total_share_one_delete_journal_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    readme, interface = _create_module_target(tmp_path)
    ssd_path = tmp_path / "ssd"
    database = _write_navigation_docs_database(ssd_path, [readme, interface])
    with sqlite3.connect(database) as inspection:
        assert inspection.execute("PRAGMA journal_mode").fetchone() == ("delete",)

    original_path_rows = metadata_probe._path_rows
    commit_attempted = threading.Event()
    writer_finished = threading.Event()
    writer_errors: list[Exception] = []

    writer_thread: threading.Thread | None = None

    def interleave_writer(connection: sqlite3.Connection, join: str) -> list[object]:
        nonlocal writer_thread
        paths = original_path_rows(connection, join)
        assert connection.in_transaction is True
        writer_thread = threading.Thread(
            target=_commit_concurrent_doc,
            args=(database, commit_attempted, writer_finished, writer_errors),
            daemon=True,
        )
        writer_thread.start()
        assert commit_attempted.wait(timeout=1.0)
        assert writer_finished.wait(timeout=0.1) is False
        return paths

    monkeypatch.setattr(metadata_probe, "_path_rows", interleave_writer)
    report = diagnostic.observe_navigation_docs_collection_readonly(
        str(ssd_path), project_root=tmp_path
    )

    assert writer_thread is not None
    writer_thread.join(timeout=2.0)
    assert writer_finished.is_set()
    assert writer_errors == []
    assert report["metadata_path_count"] == 2
    assert report["navigation_docs_total"] == 2
    with sqlite3.connect(database) as inspection:
        assert inspection.execute("SELECT COUNT(*) FROM embeddings").fetchone() == (3,)


@pytest.mark.parametrize("failure_phase", ["none", "setup", "read"])
def test_read_snapshot_always_rolls_back_and_closes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_phase: str
) -> None:
    readme, interface = _create_module_target(tmp_path)
    database = _write_navigation_docs_database(tmp_path / "ssd", [readme, interface])
    inner = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
    events: list[str] = []

    class TrackedConnection:
        def set_progress_handler(self, handler, interval: int) -> None:
            events.append("progress_off" if handler is None else "progress_on")
            if handler is not None and failure_phase == "setup":
                raise sqlite3.OperationalError("private setup detail")
            inner.set_progress_handler(handler, interval)

        def execute(self, statement: str, parameters=()):
            events.append("begin" if statement == "BEGIN" else "select")
            return inner.execute(statement, parameters)

        def rollback(self) -> None:
            events.append("rollback")
            inner.rollback()

        def close(self) -> None:
            events.append("close")
            inner.close()

    tracked = TrackedConnection()
    monkeypatch.setattr(metadata_probe, "_open_readonly_database", lambda _: tracked)
    if failure_phase == "read":
        def fail_paths(_connection, _join):
            raise sqlite3.OperationalError("private database detail")

        monkeypatch.setattr(metadata_probe, "_path_rows", fail_paths)
    if failure_phase != "none":
        with pytest.raises(metadata_probe._MetadataProbeFailure) as raised:
            metadata_probe._read_navigation_docs_metadata(database)
        assert raised.value.classification == "SQLITE_SCHEMA_OR_QUERY_FAILED"
        assert "private" not in str(raised.value)
    else:
        total, paths = metadata_probe._read_navigation_docs_metadata(database)
        assert total == 2
        assert paths == [readme, interface]

    if failure_phase == "setup":
        assert events[0] == "progress_on"
        assert "begin" not in events
    else:
        assert events[:2] == ["progress_on", "begin"]
    assert events[-3:] == ["progress_off", "rollback", "close"]


def test_live_repository_uses_exact_tracked_module_root_policy() -> None:
    required = metadata_probe._canonical_tier0_paths(REPO_ROOT)

    assert len(required) == 356
    assert "modules/economy/src/README.md" not in required
    assert "modules/foundups/docs/README.md" not in required
    assert (
        "modules/gamification/_archived_duplicates_per_wsp3/README.md"
        not in required
    )
    assert "modules/telemetry/feedback/README.md" not in required


def test_untracked_module_docs_cannot_change_canonical_target_count(
    tmp_path: Path,
) -> None:
    _run_git(tmp_path, "init", "-q")
    tracked = tmp_path / "modules" / "infrastructure" / "tracked"
    tracked.mkdir(parents=True)
    for name in ("README.md", "INTERFACE.md", "src/runtime.py"):
        path = tracked / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("tracked\n", encoding="utf-8")
    _run_git(tmp_path, "add", "--", "modules/infrastructure/tracked")
    untracked = tmp_path / "modules" / "infrastructure" / "untracked"
    untracked.mkdir(parents=True)
    for name in ("README.md", "INTERFACE.md"):
        (untracked / name).write_text("untracked\n", encoding="utf-8")

    required = metadata_probe._canonical_tier0_paths(tmp_path)

    assert required == [
        "modules/infrastructure/tracked/README.md",
        "modules/infrastructure/tracked/INTERFACE.md",
    ]


def test_fixture_root_policy_excludes_structural_buckets(tmp_path: Path) -> None:
    roots = (
        "modules/economy/src",
        "modules/foundups/docs",
        "modules/gamification/_archived_duplicates_per_wsp3",
        "modules/telemetry/feedback",
        "modules/infrastructure/real_module",
    )
    for root in roots:
        module = tmp_path / root
        module.mkdir(parents=True)
        for name in ("README.md", "INTERFACE.md"):
            (module / name).write_text("fixture\n", encoding="utf-8")

    required = metadata_probe._canonical_tier0_paths(tmp_path)

    assert required == [
        "modules/infrastructure/real_module/README.md",
        "modules/infrastructure/real_module/INTERFACE.md",
    ]


def test_missing_and_duplicate_exact_rows_are_rejected(tmp_path: Path) -> None:
    readme, interface = _create_module_target(tmp_path)
    missing = _observe_paths(tmp_path / "missing", [readme])
    duplicate = _observe_paths(tmp_path / "duplicate", [readme, readme, interface])

    assert missing["missing_required_tier0_rows"] == 1
    assert missing["h7_finding"] == "TIER0_EXACT_ROWS_MISSING"
    assert duplicate["duplicate_required_tier0_rows"] == 1
    assert duplicate["h7_finding"] == "TIER0_EXACT_ROWS_DUPLICATE"
    assert duplicate["strict_tier0_contract_complete"] is False


def test_mixed_absolute_and_relative_rows_are_rejected(tmp_path: Path) -> None:
    readme, interface = _create_module_target(tmp_path)
    absolute = f"C:/foreign-root/{readme}"
    ssd_path = tmp_path / "ssd"
    _write_navigation_docs_database(ssd_path, [readme, interface, absolute])

    report = diagnostic.observe_navigation_docs_collection_readonly(
        str(ssd_path), project_root=tmp_path
    )

    assert report["strict_tier0_relative_exact_rows"] == 2
    assert report["strict_tier0_contract_complete"] is False
    assert report["h7_finding"] == "TIER0_MIXED_ABSOLUTE_RELATIVE_PATHS"
    assert "TIER0_ABSOLUTE_PATH_ROWS" in report["h7_findings"]


@pytest.mark.parametrize(
    ("bad_readme", "classification"),
    [
        ("./modules/infrastructure/example/README.md", "TIER0_DOT_PREFIX_PATH"),
        ("../modules/infrastructure/example/README.md", "TIER0_PATH_TRAVERSAL"),
        ("modules\\infrastructure\\example\\README.md", "TIER0_BACKSLASH_PATH"),
        ("modules/infrastructure/example/readme.md", "TIER0_PATH_CASE_MISMATCH"),
        ("modules//infrastructure/example/README.md", "TIER0_MALFORMED_PATH"),
    ],
)
def test_malformed_tier0_rows_never_normalize_to_healthy(
    tmp_path: Path, bad_readme: str, classification: str
) -> None:
    _, interface = _create_module_target(tmp_path)
    ssd_path = tmp_path / "ssd"
    _write_navigation_docs_database(ssd_path, [bad_readme, interface])

    report = diagnostic.observe_navigation_docs_collection_readonly(
        str(ssd_path), project_root=tmp_path
    )

    assert report["strict_tier0_relative_exact_rows"] == 1
    assert report["missing_required_tier0_rows"] == 1
    assert report["strict_tier0_contract_complete"] is False
    assert classification in report["h7_findings"]


def test_nonstring_and_null_path_rows_are_counted_and_malformed(
    tmp_path: Path,
) -> None:
    readme, interface = _create_module_target(tmp_path)
    values: list[object] = [None, 7, 3.25, True, b"blob", "snowman-\u2603", readme, interface]
    ssd_path = tmp_path / "ssd"
    _write_navigation_docs_database(ssd_path, values)

    report = diagnostic.observe_navigation_docs_collection_readonly(
        str(ssd_path), project_root=tmp_path
    )

    assert report["metadata_path_count"] == len(values)
    assert report["h7_classification_counts"]["TIER0_MALFORMED_PATH"] == 5
    assert report["repository_relative_path_count"] == 3
    assert report["strict_tier0_contract_complete"] is False


@pytest.mark.parametrize("value", [None, 7, 3.25, b"blob"])
def test_every_path_storage_type_obeys_row_cap(
    tmp_path: Path, value: object
) -> None:
    _create_module_target(tmp_path)
    ssd_path = tmp_path / "ssd"
    _write_navigation_docs_database(
        ssd_path, [value] * (metadata_probe.SQLITE_MAX_PATH_ROWS + 1)
    )

    report = diagnostic.observe_navigation_docs_collection_readonly(
        str(ssd_path), project_root=tmp_path
    )

    assert report == {
        "navigation_docs_available": False,
        "error": "chroma_metadata_probe_overflow",
        "overflow_classification": "PATH_ROW_LIMIT_EXCEEDED",
    }


@pytest.mark.parametrize(
    ("limit_name", "limit_value", "overflow"),
    [
        ("SQLITE_MAX_PATH_ROWS", 1, "PATH_ROW_LIMIT_EXCEEDED"),
        ("SQLITE_MAX_PATH_BYTES", 8, "PATH_BYTE_LIMIT_EXCEEDED"),
        ("SQLITE_MAX_TOTAL_PATH_BYTES", 8, "TOTAL_PATH_BYTES_LIMIT_EXCEEDED"),
    ],
)
def test_sqlite_metadata_probe_fails_closed_at_explicit_bounds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    limit_name: str,
    limit_value: int,
    overflow: str,
) -> None:
    readme, interface = _create_module_target(tmp_path)
    ssd_path = tmp_path / "ssd"
    database = _write_navigation_docs_database(ssd_path, [readme, interface])
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    monkeypatch.setattr(metadata_probe, limit_name, limit_value)

    report = diagnostic.observe_navigation_docs_collection_readonly(
        str(ssd_path), project_root=tmp_path
    )

    assert report == {
        "navigation_docs_available": False,
        "error": "chroma_metadata_probe_overflow",
        "overflow_classification": overflow,
    }
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before


def test_missing_or_invalid_database_fails_closed_without_sensitive_detail(
    tmp_path: Path,
) -> None:
    missing_ssd = tmp_path / "missing-secret" / "ssd"
    missing = diagnostic.observe_navigation_docs_collection_readonly(str(missing_ssd))
    assert missing == {
        "navigation_docs_available": False,
        "error": "chroma_database_missing",
    }
    assert not (missing_ssd / "vectors" / "chroma.sqlite3").exists()

    invalid_ssd = tmp_path / "invalid-secret" / "ssd"
    database = invalid_ssd / "vectors" / "chroma.sqlite3"
    database.parent.mkdir(parents=True)
    database.write_bytes(b"not sqlite")
    invalid = diagnostic.observe_navigation_docs_collection_readonly(str(invalid_ssd))
    assert invalid == {
        "navigation_docs_available": False,
        "error": "chroma_readonly_metadata_probe_failed",
        "failure_classification": "SQLITE_CORRUPT_OR_INVALID",
    }
    assert "invalid-secret" not in repr(invalid)


def test_sqlite_progress_deadline_fails_with_stable_redacted_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    readme, interface = _create_module_target(tmp_path)
    ssd_path = tmp_path / "deadline-secret" / "ssd"
    _write_navigation_docs_database(ssd_path, [readme, interface])
    monkeypatch.setattr(metadata_probe, "SQLITE_PROGRESS_OPCODE_INTERVAL", 1)
    monkeypatch.setattr(metadata_probe, "SQLITE_MAX_QUERY_SECONDS", -1.0)

    report = diagnostic.observe_navigation_docs_collection_readonly(
        str(ssd_path), project_root=tmp_path
    )

    assert report == {
        "navigation_docs_available": False,
        "error": "chroma_readonly_metadata_probe_failed",
        "failure_classification": "SQLITE_TIME_LIMIT_EXCEEDED",
    }
    assert "deadline-secret" not in repr(report)


def test_sqlite_vm_step_budget_fails_with_stable_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    readme, interface = _create_module_target(tmp_path)
    ssd_path = tmp_path / "ssd"
    _write_navigation_docs_database(ssd_path, [readme, interface])
    monkeypatch.setattr(metadata_probe, "SQLITE_PROGRESS_OPCODE_INTERVAL", 1)
    monkeypatch.setattr(metadata_probe, "SQLITE_MAX_PROGRESS_CALLBACKS", 0)

    report = diagnostic.observe_navigation_docs_collection_readonly(
        str(ssd_path), project_root=tmp_path
    )

    assert report["failure_classification"] == "SQLITE_VM_STEP_LIMIT_EXCEEDED"


def test_locked_database_fails_with_stable_redacted_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    readme, interface = _create_module_target(tmp_path)
    ssd_path = tmp_path / "locked-secret" / "ssd"
    database = _write_navigation_docs_database(ssd_path, [readme, interface])
    monkeypatch.setattr(metadata_probe, "SQLITE_CONNECTION_TIMEOUT_SECONDS", 0.01)
    locker = sqlite3.connect(database)
    try:
        locker.execute("BEGIN EXCLUSIVE")
        report = diagnostic.observe_navigation_docs_collection_readonly(
            str(ssd_path), project_root=tmp_path
        )
    finally:
        locker.rollback()
        locker.close()

    assert report == {
        "navigation_docs_available": False,
        "error": "chroma_readonly_metadata_probe_failed",
        "failure_classification": "SQLITE_BUSY_OR_LOCKED",
    }
    assert "locked-secret" not in repr(report)


def test_symlink_database_path_is_rejected_before_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target_ssd = tmp_path / "target"
    target = _write_navigation_docs_database(target_ssd, [])
    linked_ssd = tmp_path / "linked"
    database = linked_ssd / "vectors" / "chroma.sqlite3"
    database.parent.mkdir(parents=True)
    try:
        database.symlink_to(target)
    except OSError:
        database.write_bytes(b"unopened")
        monkeypatch.setattr(
            metadata_probe, "_contains_link_component", lambda _: True
        )

    report = diagnostic.observe_navigation_docs_collection_readonly(str(linked_ssd))

    assert report == {
        "navigation_docs_available": False,
        "error": "chroma_readonly_metadata_probe_failed",
        "failure_classification": "SQLITE_LINK_COMPONENT_REJECTED",
    }


def test_link_component_guard_fails_closed_deterministically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ssd_path = tmp_path / "linked"
    _write_navigation_docs_database(ssd_path, [])
    monkeypatch.setattr(metadata_probe, "_contains_link_component", lambda _: True)

    report = diagnostic.observe_navigation_docs_collection_readonly(str(ssd_path))

    assert report["failure_classification"] == "SQLITE_LINK_COMPONENT_REJECTED"


def test_hardlinked_database_path_is_rejected_before_open(tmp_path: Path) -> None:
    target = _write_navigation_docs_database(tmp_path / "target", [])
    linked_ssd = tmp_path / "linked"
    database = linked_ssd / "vectors" / "chroma.sqlite3"
    database.parent.mkdir(parents=True)
    os.link(target, database)

    report = diagnostic.observe_navigation_docs_collection_readonly(str(linked_ssd))

    assert report == {
        "navigation_docs_available": False,
        "error": "chroma_readonly_metadata_probe_failed",
        "failure_classification": "SQLITE_HARDLINK_REJECTED",
    }


def test_absolute_metadata_outranks_noncausal_filter_subset() -> None:
    h4 = {
        "rejected_target_count": 0,
        "h4_finding": "TARGETS_ADMITTED_WITH_POLICY_EXCLUSIONS",
    }
    h7 = {
        "navigation_docs_available": True,
        "h7_finding": "ABSOLUTE_METADATA_BREAKS_STRICT_TIER0_EXACT_LOOKUP",
    }

    assert diagnostic._classify_primary_root_cause(h4, h7) == (
        "ABSOLUTE_NAVIGATION_DOC_PATHS_BREAK_STRICT_TIER0_EXACT_LOOKUP"
    )


def test_h6_reports_current_zero_entry_observability_contract() -> None:
    report = diagnostic.probe_h6_observability()

    assert report["refresh_reward_withheld_on_zero_entries"] is True
    assert report["h6_finding"] == "ZERO_DOC_OBSERVABILITY_PRESENT"


def test_static_safety_scan_remains_mutation_free() -> None:
    report = diagnostic.static_safety_scan_self()

    assert report["passes_static_scan"] is True
    assert all(count == 0 for count in report["hit_counts"].values())
