"""No-growth enforcement for focused RedDog security-repair exemptions."""

from __future__ import annotations

import ast
from datetime import date
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_ROOT = Path(__file__).resolve().parents[1]
SLICE_DATE = date(2026, 7, 18)
EXPECTED_MODULE_FILES = {
    "src/reddog_main_resident_queue_next_stage_dispatch_bootstrap.py",
    "src/reddog_main_resident_queue_runtime_dependency_bundle.py",
    "src/reddog_main_resident_queue_serial_loop_bootstrap.py",
    "src/reddog_openclaw_live_enqueue.py",
    "src/reddog_signed_worker_openclaw_queue_loop_runtime_binding.py",
    "src/reddog_signed_worker_queue_serial_loop_runner.py",
    "src/reddog_signer_delegated_authority_runtime.py",
    "src/reddog_wre_queue_authority_request_dryrun.py",
    "src/reddog_wre_queue_consumer_dryrun.py",
    "src/reddog_wre_worktree_create.py",
    "tests/test_reddog_governed_execution_valve_production_wiring.py",
    "tests/test_reddog_main_openclaw_signed_worker_claim_loop_preflight.py",
    "tests/test_reddog_main_resident_queue_serial_loop_bootstrap.py",
    "tests/test_reddog_signed_worker_dispatch_task_executor.py",
}


def _exemptions(path: Path) -> list[dict]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict) and isinstance(payload.get("exemptions"), list)
    return [item for item in payload["exemptions"] if "no_growth_ceiling" in item]


def _named_sizes(path: Path) -> dict[str, int]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name: node.end_lineno - node.lineno + 1
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and node.end_lineno is not None
    }


def _assert_exact_temporary_exemption(item: dict, root: Path) -> None:
    assert item["owner"] and item["architect_reviewer"] == "0102 Technical Architect"
    expiry = date.fromisoformat(item["expires_on"])
    assert SLICE_DATE < expiry <= date(2026, 9, 30)
    assert item["temporary"] is True and item["remediation"]
    target = root / item["file"]
    ceiling = item["no_growth_ceiling"]
    assert len(target.read_text(encoding="utf-8").splitlines()) <= ceiling["file_lines"]
    sizes = _named_sizes(target) if target.suffix == ".py" else {}
    for name, limit in ceiling.get("functions", {}).items():
        assert name in sizes and sizes[name] <= limit


def test_module_security_repair_exemptions_are_exact_and_do_not_grow() -> None:
    items = _exemptions(MODULE_ROOT / "wsp_62_exemptions.yaml")
    assert {item["file"] for item in items} == EXPECTED_MODULE_FILES
    for item in items:
        _assert_exact_temporary_exemption(item, MODULE_ROOT)


def test_root_main_exemption_has_an_exact_security_repair_ceiling() -> None:
    items = _exemptions(REPO_ROOT / "wsp_62_exemptions.yaml")
    main_item = next(item for item in items if item["file"] == "main.py")
    _assert_exact_temporary_exemption(main_item, REPO_ROOT)
