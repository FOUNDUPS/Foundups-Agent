#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exercise HoloIndex large-file health warnings without repository pollution."""

from __future__ import annotations

import io
import os
from pathlib import Path
import sys
import tempfile


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from holo_index.module_health.size_audit import SizeAuditor
from holo_index.qwen_advisor.rules_engine import ComplianceRulesEngine


def _enforce_utf8_console() -> None:
    if not sys.platform.startswith("win"):
        return
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except (AttributeError, OSError, ValueError):
        pass


def _external_temp_root() -> Path:
    configured = os.environ.get("HOLOINDEX_TEST_TEMP_ROOT")
    root = Path(configured) if configured else REPO_ROOT.parent / "RedDog-Test-Temp"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _create_fixture() -> Path:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, dir=_external_temp_root(), encoding="utf-8"
    ) as handle:
        for line_number in range(1, 1201):
            handle.write(f"# Line {line_number}\n")
        return Path(handle.name)


def _print_size_result(temp_path: Path) -> None:
    result = SizeAuditor().audit_file(temp_path)
    if result is None:
        raise RuntimeError("large-file fixture was not auditable")
    print("Size audit result:")
    print(f"  Lines: {result.line_count}")
    print(f"  Risk tier: {result.risk_tier}")
    print(f"  Needs attention: {result.needs_attention}")
    print(f"  Guidance: {result.guidance}")


def _print_rules_result(temp_path: Path) -> None:
    checks = ComplianceRulesEngine().check_module_size_health(
        [{"location": str(temp_path), "path": str(temp_path)}]
    )
    print("Rules engine health checks:")
    print(f"  Found {len(checks)} issues")
    for check in checks:
        print(f"  - Severity: {check.severity}")
        print(f"    Guidance: {check.guidance}")
        print(f"    Suggested fix: {check.suggested_fix}")
    if len(checks) != 1 or checks[0].severity != "HIGH":
        raise RuntimeError("large-file rules engine did not emit one HIGH finding")


def main() -> int:
    _enforce_utf8_console()
    temp_path = _create_fixture()
    try:
        _print_size_result(temp_path)
        _print_rules_result(temp_path)
    finally:
        temp_path.unlink(missing_ok=True)
    print("Large-file health warning proof: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
