from __future__ import annotations

import ast
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from modules.infrastructure.dependency_launcher.src.runtime_compatibility_preflight import (
    run_runtime_compatibility_advisory,
)
from modules.infrastructure.dependency_launcher.src.runtime_compatibility_receipt import (
    EVIDENCE_SCHEMA,
    REQUIRED_COMPONENTS,
    build_runtime_compatibility_receipt,
    canonical_digest,
)


NOW = datetime(2026, 8, 2, 4, 0, tzinfo=timezone.utc)


def _digest(seed: str) -> str:
    return canonical_digest({"seed": seed})


def _evidence(*, drift: str | None = None) -> dict[str, object]:
    components = []
    for component_id in REQUIRED_COMPONENTS:
        expected = f"{component_id}-expected"
        installed = "older" if component_id == drift else expected
        components.append(
            {
                "component_id": component_id,
                "installed_ref": installed,
                "expected_ref": expected,
                "evidence_kind": "UPSTREAM_RELEASE" if component_id in {"openclaw", "hermes"} else "PROMOTED_RUNTIME_BINDING",
                "evidence_receipt_id": _digest(component_id),
                "verification": "PASS",
            }
        )
    payload: dict[str, object] = {
        "schema_version": EVIDENCE_SCHEMA,
        "generated_at_utc": NOW.isoformat(),
        "expires_at_utc": (NOW + timedelta(days=1)).isoformat(),
        "verification": "PASS",
        "components": components,
    }
    payload["evidence_receipt_id"] = canonical_digest(payload)
    return payload


def test_current_receipt_is_digest_bound() -> None:
    receipt = build_runtime_compatibility_receipt(_evidence(), now=NOW)
    assert receipt.overall_state == "CURRENT"
    assert len(receipt.components) == len(REQUIRED_COMPONENTS)
    assert receipt.receipt_id.startswith("sha256:")
    assert receipt.no_network_call is True
    assert receipt.no_runtime_mutation is True
    assert receipt.no_model_load is True
    assert receipt.no_route_change is True


def test_drift_is_advisory_and_identifies_component() -> None:
    receipt = build_runtime_compatibility_receipt(_evidence(drift="hermes"), now=NOW)
    assert receipt.overall_state == "DRIFT"
    hermes = next(item for item in receipt.components if item.component_id == "hermes")
    assert hermes.state == "DRIFT"


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (lambda data: data.update(schema_version="wrong"), "evidence_schema_invalid"),
        (lambda data: data.update(verification="FAIL"), "evidence_verification_not_pass"),
        (lambda data: data.update(expires_at_utc=(NOW - timedelta(seconds=1)).isoformat()), "evidence_expired"),
        (lambda data: data.update(expires_at_utc=(NOW + timedelta(days=30)).isoformat()), "evidence_ttl_exceeds_policy"),
        (lambda data: data.update(generated_at_utc=(NOW + timedelta(hours=1)).isoformat()), "evidence_generated_in_future"),
        (lambda data: data["components"].pop(), "evidence_receipt_id_mismatch"),
    ],
)
def test_invalid_or_tampered_evidence_is_not_ready(mutation, reason: str) -> None:
    evidence = _evidence()
    mutation(evidence)
    receipt = build_runtime_compatibility_receipt(evidence, now=NOW)
    assert receipt.overall_state == "NOT_READY"
    assert reason in receipt.reasons


def test_missing_component_is_not_ready_with_no_guess() -> None:
    evidence = _evidence()
    evidence["components"] = evidence["components"][:-1]
    evidence["evidence_receipt_id"] = canonical_digest(
        {key: value for key, value in evidence.items() if key != "evidence_receipt_id"}
    )
    receipt = build_runtime_compatibility_receipt(evidence, now=NOW)
    assert receipt.overall_state == "NOT_READY"
    assert receipt.components[-1].reason == "component_missing"
    assert "component_not_ready:inference_backend:component_missing" in receipt.reasons


@pytest.mark.parametrize(
    "mutate_component",
    [
        lambda item: item.update(evidence_kind="CALLER_ASSERTION"),
        lambda item: item.update(installed_ref="x" * 513),
        lambda item: item.update(expected_ref="non-ascii-\u2603"),
        lambda item: item.update(evidence_receipt_id="sha256:bad"),
        lambda item: item.update(verification="UNKNOWN"),
    ],
)
def test_component_schema_is_exact_and_bounded(mutate_component) -> None:
    evidence = _evidence()
    mutate_component(evidence["components"][0])
    evidence["evidence_receipt_id"] = canonical_digest(
        {key: value for key, value in evidence.items() if key != "evidence_receipt_id"}
    )
    receipt = build_runtime_compatibility_receipt(evidence, now=NOW)
    assert receipt.overall_state == "NOT_READY"
    assert receipt.components[0].reason == "component_evidence_invalid"


def test_startup_adapter_reads_only_runtime_root(tmp_path: Path, capsys) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    runtime.mkdir()
    evidence_path = runtime / "compatibility.json"
    evidence_path.write_text(json.dumps(_evidence()), encoding="utf-8")
    before = evidence_path.read_bytes()

    receipt = run_runtime_compatibility_advisory(
        repo,
        environment={
            "REDDOG_RUNTIME_COMPATIBILITY_ROOT": str(runtime),
            "REDDOG_RUNTIME_COMPATIBILITY_EVIDENCE": str(evidence_path),
        },
    )

    assert receipt.overall_state == "CURRENT"
    assert evidence_path.read_bytes() == before
    assert "preflight=CURRENT" in capsys.readouterr().out


def test_startup_adapter_never_raises_or_blocks_for_missing_evidence(tmp_path: Path, capsys) -> None:
    receipt = run_runtime_compatibility_advisory(tmp_path, environment={})
    assert receipt.overall_state == "NOT_READY"
    assert "root_missing" in receipt.reasons[0]
    assert "preflight=NOT_READY" in capsys.readouterr().out


def test_startup_adapter_rejects_repo_and_oversized_paths(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    path = repo / "evidence.json"
    path.write_text("{}", encoding="utf-8")
    receipt = run_runtime_compatibility_advisory(
        repo,
        environment={
            "REDDOG_RUNTIME_COMPATIBILITY_ROOT": str(repo),
            "REDDOG_RUNTIME_COMPATIBILITY_EVIDENCE": str(path),
        },
    )
    assert receipt.overall_state == "NOT_READY"
    assert any("inside_repo" in reason for reason in receipt.reasons)


def test_runtime_modules_have_no_execution_or_network_imports() -> None:
    src = Path(__file__).resolve().parents[1] / "src"
    banned = {"subprocess", "socket", "requests", "urllib", "httpx", "aiohttp"}
    for name in ("runtime_compatibility_receipt.py", "runtime_compatibility_preflight.py"):
        tree = ast.parse((src / name).read_text(encoding="utf-8"))
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in (node.names if isinstance(node, ast.Import) else [ast.alias(node.module or "")])
        }
        assert not (imports & banned)


def test_runtime_modules_follow_wsp62_boundaries() -> None:
    src = Path(__file__).resolve().parents[1] / "src"
    for name in ("runtime_compatibility_receipt.py", "runtime_compatibility_preflight.py"):
        path = src / name
        lines = path.read_text(encoding="utf-8").splitlines()
        tree = ast.parse("\n".join(lines))
        assert len(lines) <= 600
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert (node.end_lineno or node.lineno) - node.lineno + 1 <= 50
            if isinstance(node, ast.ClassDef):
                assert (node.end_lineno or node.lineno) - node.lineno + 1 <= 200
