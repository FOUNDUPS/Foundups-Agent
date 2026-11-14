"""Tests for deterministic, proposal-only FMAS health triage."""

import time
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from modules.infrastructure.wre_core.src.fmas_health_triage import (
    HealthAuditBinding,
    HealthFindingDisposition,
    _exact_head_tracked_paths,
    _triage_verified_health_audit,
    run_wsp62_health_audit,
    validate_health_audit_result,
)


HEAD = "a" * 40
BASE = "b" * 40
TOOL = "sha256:" + ("c" * 64)


def _binding(*, baseline=True):
    return HealthAuditBinding(
        authority_repo_head_sha=HEAD,
        baseline_repo_head_sha=BASE if baseline else None,
        audit_tool_id="tools.modular_audit.wsp62",
        audit_tool_digest=TOOL,
    )


def _triage(raw, *, baseline=True, **kwargs):
    with patch(
            "modules.infrastructure.wre_core.src.fmas_health_triage._finding_scope_is_confined",
            return_value=True,
        ):
        return _triage_verified_health_audit(
            raw,
            binding=_binding(baseline=baseline),
            candidate_repo_root=Path.cwd(),
            tracked_paths=frozenset(),
            **kwargs,
        )


def _clean_repo(tmp_path):
    repo = tmp_path / "candidate"
    (repo / "modules").mkdir(parents=True)
    (repo / "modules" / ".keep").write_text("fixture\n", encoding="utf-8")
    source = repo / "modules" / "infrastructure" / "example" / "src" / "a.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    tool = repo / "audit.py"
    tool.write_text("# audit\n", encoding="utf-8")
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.invalid"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "WRE Test"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "add", "modules", "audit.py"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "fixture"],
        check=True,
        capture_output=True,
    )
    return repo, tool


def test_wsp62_candidate_error_is_scoped_and_idempotent():
    raw = [
        "WSP 62 ERROR: candidate size growth "
        "ai_intelligence/example/src/large.py (1490->1501)"
    ]
    first = _triage(raw)
    time.sleep(0.002)
    second = _triage(raw)

    assert first.receipt.receipt_id == second.receipt.receipt_id
    assert first.jobs[0].job_id == second.jobs[0].job_id
    assert first.jobs[0].dry_run is True
    assert first.jobs[0].scope.module_path == "modules/ai_intelligence/example"
    assert first.jobs[0].scope.file_paths == [
        "modules/ai_intelligence/example/src/large.py"
    ]
    assert first.findings[0].disposition == HealthFindingDisposition.CANDIDATE_CHANGE


def test_unattributed_critical_is_health_debt_not_candidate_job():
    result = _triage(
        [
            "WSP 62 CRITICAL: ai_intelligence/example/src/large.py "
            "(1600 lines >= hard limit 1500)"
        ],
        baseline=False,
    )

    assert result.findings[0].disposition == HealthFindingDisposition.HEALTH_DEBT
    assert result.receipt.candidate_count == 0
    assert not result.jobs


def test_inherited_and_advisory_rows_never_emit_jobs():
    result = _triage(
        [
            "WSP 62 INHERITED: infrastructure/wre_core/src/legacy.py (1700 lines)",
            "WSP 62 WARNING: infrastructure/wre_core/src/watch.py "
            "(1100 lines > critical window 1000)",
        ],
    )

    dispositions = {item.disposition for item in result.findings}
    assert dispositions == {
        HealthFindingDisposition.INHERITED_DEBT,
        HealthFindingDisposition.ADVISORY,
    }
    assert not result.jobs


@pytest.mark.parametrize("level", ["ADVISORY_ARCHIVE", "EXEMPTION_EXPIRED"])
def test_canonical_wsp62_advisory_levels_never_emit_jobs(level):
    result = _triage(
        [
            f"WSP 62 {level}: infrastructure/wre_core/src/a.py "
            "(advisory producer state)"
        ]
    )

    assert result.findings[0].disposition == HealthFindingDisposition.ADVISORY
    assert not result.jobs


def test_duplicate_rows_are_collapsed_and_counted():
    finding = (
        "WSP 62 ERROR: candidate size growth "
        "infrastructure/wre_core/src/a.py (1490->1501)"
    )
    result = _triage([finding, finding])

    assert result.receipt.raw_finding_count == 2
    assert result.receipt.unique_finding_count == 1
    assert result.receipt.duplicate_finding_count == 1
    assert len(result.jobs) == 1


def test_short_display_id_collision_preserves_distinct_evidence_and_jobs():
    findings = [
        "WSP 62 ERROR: candidate growth infrastructure/wre_core/src/a.py (50->51)",
        "WSP 62 ERROR: candidate growth infrastructure/wre_core/src/b.py (50->51)",
    ]
    with patch(
        "modules.infrastructure.wre_core.src.fmas_improvement_bridge.generate_finding_id",
        return_value="display_collision",
    ):
        result = _triage(findings)

    assert result.receipt.unique_finding_count == 2
    assert len(result.jobs) == 2
    assert result.jobs[0].job_id != result.jobs[1].job_id
    assert len(set(result.receipt.proposed_finding_ids)) == 2


def test_candidate_job_limit_is_fail_closed_and_reports_overflow():
    findings = [
        f"WSP 62 ERROR: candidate size growth infrastructure/wre_core/src/a{i}.py "
        "(1490->1501)"
        for i in range(3)
    ]
    result = _triage(
        findings,
        candidate_job_limit=1,
    )

    assert result.receipt.candidate_count == 3
    assert result.receipt.emitted_job_count == 1
    assert result.receipt.candidate_overflow_count == 2
    assert result.receipt.no_model_invocation_performed is True
    assert result.receipt.no_worker_dispatch_performed is True
    assert result.receipt.no_queue_mutation_performed is True
    assert result.receipt.no_source_mutation_performed is True


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"authority_repo_head_sha": "bad"}, "authority_repo_head_sha_invalid"),
        ({"audit_tool_digest": "bad"}, "audit_tool_digest_invalid"),
    ],
)
def test_binding_rejects_untrusted_identity(kwargs, error):
    values = {
        "authority_repo_head_sha": HEAD,
        "baseline_repo_head_sha": BASE,
        "audit_tool_id": "tools.modular_audit.wsp62",
        "audit_tool_digest": TOOL,
    }
    values.update(kwargs)
    with pytest.raises(ValueError, match=error):
        HealthAuditBinding(**values)


def test_non_string_finding_and_oversized_limit_fail_closed():
    with pytest.raises(TypeError, match="raw_finding_must_be_string"):
        _triage_verified_health_audit(
            [123],
            binding=_binding(),
            candidate_repo_root=Path.cwd(),
            tracked_paths=frozenset(),
        )
    with pytest.raises(ValueError, match="candidate_job_limit_out_of_range"):
        _triage_verified_health_audit(
            [],
            binding=_binding(),
            candidate_repo_root=Path.cwd(),
            tracked_paths=frozenset(),
            candidate_job_limit=101,
        )
    with pytest.raises(ValueError, match="raw_finding_empty"):
        _triage_verified_health_audit(
            ["  "],
            binding=_binding(),
            candidate_repo_root=Path.cwd(),
            tracked_paths=frozenset(),
        )


def test_traversal_shaped_wsp62_path_is_blocked_before_job_creation():
    raw = [
        "WSP 62 ERROR: candidate size growth "
        "modules/infrastructure/example/../../.env.py (1490->1501)"
    ]
    result = _triage_verified_health_audit(
        raw,
        binding=_binding(),
        candidate_repo_root=Path.cwd(),
        tracked_paths=frozenset(),
    )

    assert result.findings[0].disposition == HealthFindingDisposition.BLOCKED
    assert result.findings[0].reason_code == "wsp62_scope_invalid_or_missing"
    assert not result.jobs


def test_public_triage_rejects_unverified_dirty_candidate_authority(tmp_path):
    repo, tool = _clean_repo(tmp_path)
    (repo / "dirty.txt").write_text("dirty", encoding="utf-8")
    with pytest.raises(ValueError, match="candidate_repo_not_clean"):
        run_wsp62_health_audit(
            candidate_repo_root=repo,
        )


def test_ignored_existing_file_is_not_exact_head_scope(tmp_path):
    repo, _tool = _clean_repo(tmp_path)
    ignored = repo / "modules" / "infrastructure" / "example" / "src" / "ignored.py"
    (repo / ".gitignore").write_text("ignored.py\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(repo), "add", ".gitignore"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "ignore runtime"],
        check=True,
        capture_output=True,
    )
    ignored.write_text("RUNTIME = True\n", encoding="utf-8")
    raw = [
        "WSP 62 ERROR: candidate size growth "
        "infrastructure/example/src/ignored.py (1490->1501)"
    ]

    result = _triage_verified_health_audit(
        raw,
        binding=_binding(),
        candidate_repo_root=repo,
        tracked_paths=frozenset(),
    )

    assert result.findings[0].disposition == HealthFindingDisposition.BLOCKED
    assert not result.jobs


def test_exact_head_tracked_file_is_valid_candidate_scope(tmp_path):
    repo, _tool = _clean_repo(tmp_path)
    raw = [
        "WSP 62 ERROR: candidate size growth "
        "infrastructure/example/src/a.py (1490->1501)"
    ]

    result = _triage_verified_health_audit(
        raw,
        binding=_binding(),
        candidate_repo_root=repo,
        tracked_paths=frozenset(
            {"modules/infrastructure/example/src/a.py"}
        ),
    )

    assert result.findings[0].disposition == HealthFindingDisposition.CANDIDATE_CHANGE
    assert len(result.jobs) == 1


def test_public_runner_rejects_authority_change_after_scan():
    changed = HealthAuditBinding(
        authority_repo_head_sha="d" * 40,
        baseline_repo_head_sha=None,
        audit_tool_id="tools/modular_audit/modular_audit.py:audit_file_sizes",
        audit_tool_digest=TOOL,
    )
    with (
        patch(
            "modules.infrastructure.wre_core.src.fmas_health_triage._bind_health_audit",
            side_effect=[_binding(baseline=False), changed],
        ),
        patch(
            "modules.infrastructure.wre_core.src.fmas_health_triage._exact_head_tracked_paths",
            return_value=frozenset(),
        ),
        patch(
            "modules.infrastructure.wre_core.src.fmas_health_triage.canonical_fmas.audit_file_sizes",
            return_value=[],
        ),
    ):
        with pytest.raises(ValueError, match="health_audit_authority_changed_during_scan"):
            run_wsp62_health_audit(Path.cwd())


def test_public_receipt_excludes_untracked_producer_observations():
    tracked = "modules/infrastructure/example/src/a.py"
    raw = [
        "WSP 62 CRITICAL: infrastructure/example/src/a.py (1600 lines)",
        "WSP 62 CRITICAL: infrastructure/example/src/ignored.py (1600 lines)",
    ]
    with (
        patch(
            "modules.infrastructure.wre_core.src.fmas_health_triage._bind_health_audit",
            return_value=_binding(baseline=False),
        ),
        patch(
            "modules.infrastructure.wre_core.src.fmas_health_triage._exact_head_tracked_paths",
            return_value=frozenset({tracked}),
        ),
        patch(
            "modules.infrastructure.wre_core.src.fmas_health_triage.canonical_fmas.audit_file_sizes",
            return_value=raw,
        ),
        patch(
            "modules.infrastructure.wre_core.src.fmas_health_triage._finding_scope_is_confined",
            return_value=True,
        ),
    ):
        result = run_wsp62_health_audit(Path.cwd())

    assert result.receipt.raw_finding_count == 1
    assert result.receipt.unique_finding_count == 1
    assert result.producer_observation_count == 2
    assert result.excluded_non_authoritative_observation_count == 1
    assert result.receipt.producer_observation_count == 2
    assert result.receipt.excluded_non_authoritative_observation_count == 1
    assert result.receipt.exclusion_reason_counts == {
        "non_string": 0,
        "non_wsp62_or_unparseable": 0,
        "not_exact_head_tracked": 1,
    }
    assert result.receipt.producer_observation_digest.startswith("sha256:")


def test_receipt_identity_binds_full_producer_observation_digest():
    tracked = frozenset({"modules/infrastructure/example/src/a.py"})
    raw = ["WSP 62 CRITICAL: infrastructure/example/src/a.py (1600 lines)"]
    kwargs = {
        "binding": _binding(baseline=False),
        "candidate_repo_root": Path.cwd(),
        "tracked_paths": tracked,
        "producer_observation_count": 2,
        "excluded_non_authoritative_observation_count": 1,
        "exclusion_reason_counts": {"not_exact_head_tracked": 1},
    }
    with patch(
        "modules.infrastructure.wre_core.src.fmas_health_triage._finding_scope_is_confined",
        return_value=True,
    ):
        first = _triage_verified_health_audit(
            raw, producer_observation_digest="sha256:" + "1" * 64, **kwargs
        )
        second = _triage_verified_health_audit(
            raw, producer_observation_digest="sha256:" + "2" * 64, **kwargs
        )

    assert first.receipt.finding_set_digest == second.receipt.finding_set_digest
    assert first.receipt.audit_id != second.receipt.audit_id
    assert first.receipt.receipt_id != second.receipt.receipt_id


def test_receipt_nested_fields_are_immutable_and_job_mutation_is_detected():
    result = _triage([
        "WSP 62 ERROR: candidate growth infrastructure/wre_core/src/a.py (50->51)"
    ])

    assert validate_health_audit_result(result) is True
    with pytest.raises(TypeError):
        result.receipt.disposition_counts["candidate_change"] = 99
    with pytest.raises(AttributeError):
        result.receipt.proposed_finding_ids.append("forged")

    result.jobs[0].evidence_refs.clear()
    assert validate_health_audit_result(result) is False


def test_exact_head_inventory_preserves_distinct_unicode_paths(tmp_path):
    repo, _tool = _clean_repo(tmp_path)
    composed = repo / "modules" / "infrastructure" / "caf\u00e9" / "src" / "a.py"
    decomposed = repo / "modules" / "infrastructure" / "cafe\u0301" / "src" / "b.py"
    composed.parent.mkdir(parents=True)
    decomposed.parent.mkdir(parents=True)
    composed.write_text("A = 1\n", encoding="utf-8")
    decomposed.write_text("B = 1\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(repo), "add", "modules"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "unicode paths"],
        check=True,
        capture_output=True,
    )

    inventory = _exact_head_tracked_paths(repo)

    assert "modules/infrastructure/caf\u00e9/src/a.py" in inventory
    assert "modules/infrastructure/cafe\u0301/src/b.py" in inventory
