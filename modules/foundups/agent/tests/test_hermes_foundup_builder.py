"""
Focused dry-run tests for HermesFoundUpBuilder.

WSP References:
- WSP 50: Pre-action verification (test fixtures verified before assertions)
- WSP 97: System Execution Prompting (no live extraction, no external mutation)
- WSP 106: FoundUp API Gateway (build endpoint contract)

Scope (Phase 1 / Worker DD):
- Unit tests use tmp_path fixtures so they do not depend on live repo state.
- Integration-style assertions against real modules are limited to read-only
  boundary inspection. No git filter-repo. No GitHub push. No external mutation.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Iterable

import pytest

from modules.foundups.agent.src.hermes_adapter import (
    BoundaryAnalysis,
    ExfoliationGate,
    HermesFoundUpBuilder,
)


# --------------------------------------------------------------------------- #
# Fixture builders
# --------------------------------------------------------------------------- #

REPO_ROOT = Path(__file__).resolve().parents[4]


def _write(path: Path, body: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _make_module(
    base: Path,
    module_subpath: str,
    *,
    contracts: Iterable[str] = ("README.md", "INTERFACE.md", "ROADMAP.md", "ModLog.md"),
    manifest: Dict | None = None,
    deploy_kind: str = "firebase",
    add_tests: bool = True,
    extra_files: Iterable[str] = (),
) -> Path:
    """
    Create a minimal FoundUp-shaped module under ``base / module_subpath``.

    deploy_kind controls which deploy surface is materialised:
      - "firebase":  drops a firebase.json (legacy detector path)
      - "manifest":  manifest declares entry_url + launch_readiness=ready only
      - "app":       drops app/index.html only
      - "frontend":  drops frontend/index.html only
      - "none":      no deploy surface (gate should fail this check)
    """
    module_path = base / module_subpath
    module_path.mkdir(parents=True, exist_ok=True)

    for contract in contracts:
        _write(module_path / contract, f"# {contract}\n")

    if add_tests:
        _write(module_path / "tests" / "test_smoke.py", "def test_smoke():\n    assert True\n")

    if manifest is not None:
        _write(module_path / "foundup_manifest.json", json.dumps(manifest, indent=2))

    _write(module_path / "src" / "__init__.py", "")
    _write(module_path / "src" / "core.py", "VALUE = 1\n")

    if deploy_kind == "firebase":
        _write(module_path / "firebase.json", "{}")
    elif deploy_kind == "app":
        _write(module_path / "app" / "index.html", "<html></html>")
    elif deploy_kind == "frontend":
        _write(module_path / "frontend" / "index.html", "<html></html>")
    elif deploy_kind == "manifest":
        # nothing extra; manifest provides the evidence
        pass
    elif deploy_kind == "none":
        pass
    else:
        raise ValueError(f"Unknown deploy_kind: {deploy_kind}")

    for extra in extra_files:
        _write(module_path / extra)

    return module_path


def _ready_manifest(foundup_id: str = "fixture", entry_url: str = "https://example.com/app/") -> Dict:
    return {
        "$schema": "https://foundups.org/schemas/foundup-manifest/v1.json",
        "foundup_id": foundup_id,
        "name": foundup_id,
        "version": "0.1.0",
        "entry_url": entry_url,
        "launch_readiness": "ready",
        "tier": "F0_DAE",
        "lifecycle_stage": "incubating",
    }


@pytest.fixture
def builder_no_security(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> HermesFoundUpBuilder:
    """Builder rooted in tmp_path with the security gate disabled."""
    monkeypatch.setenv("HERMES_BUILDER_SECURITY_GATE", "0")
    monkeypatch.setenv("HERMES_BUILDER_DRY_RUN", "1")
    monkeypatch.setenv("HERMES_BUILDER_ENABLED", "1")
    return HermesFoundUpBuilder(repo_root=tmp_path)


@pytest.fixture
def real_repo_builder(monkeypatch: pytest.MonkeyPatch) -> HermesFoundUpBuilder:
    """Builder rooted in the real repo for read-only boundary checks."""
    monkeypatch.setenv("HERMES_BUILDER_SECURITY_GATE", "0")
    monkeypatch.setenv("HERMES_BUILDER_DRY_RUN", "1")
    return HermesFoundUpBuilder(repo_root=REPO_ROOT)


# --------------------------------------------------------------------------- #
# init / availability
# --------------------------------------------------------------------------- #

class TestInitialization:
    def test_init_does_not_crash_when_fam_unavailable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """FAM daemon init failure must not crash the builder.

        Simulates the documented 'FAM database unavailable' case by stubbing
        get_fam_daemon to raise. The builder must still construct and expose
        a None breadcrumb sink rather than propagating the exception.
        """
        import modules.foundups.agent.src.hermes_adapter as adapter_mod

        if adapter_mod.FAM_DAEMON_AVAILABLE:
            monkeypatch.setattr(
                adapter_mod, "get_fam_daemon", lambda: (_ for _ in ()).throw(RuntimeError("FAM down"))
            )

        builder = HermesFoundUpBuilder(repo_root=tmp_path)
        assert builder._fam_daemon is None
        # Emitting with no daemon must be a no-op, not a crash.
        builder._emit_breadcrumb("hermes_test_event", {"k": "v"})

    def test_check_qwen_available_reports_unavailable_not_crashes(
        self, builder_no_security: HermesFoundUpBuilder
    ) -> None:
        """LM Studio absent must surface as {available: False, error: ...}."""
        result = builder_no_security.check_qwen_available()
        assert isinstance(result, dict)
        assert "available" in result
        if not result["available"]:
            assert "error" in result and result["error"]


# --------------------------------------------------------------------------- #
# analyze_boundary
# --------------------------------------------------------------------------- #

class TestAnalyzeBoundary:
    def test_returns_product_files_imports_blockers(
        self, builder_no_security: HermesFoundUpBuilder, tmp_path: Path
    ) -> None:
        _make_module(
            tmp_path,
            "modules/foundups/widget",
            manifest=_ready_manifest("widget"),
            deploy_kind="firebase",
        )
        # Add a file that imports a core module so core_imports is populated.
        _write(
            tmp_path / "modules/foundups/widget/src/wre_caller.py",
            "from modules.infrastructure.wre_core import skill_loader\n",
        )

        analysis = builder_no_security.analyze_boundary("modules/foundups/widget")

        assert isinstance(analysis, BoundaryAnalysis)
        assert analysis.module_path == "modules/foundups/widget"
        assert any(p.endswith("core.py") for p in analysis.product_files)
        assert "modules.infrastructure.wre_core" in analysis.core_imports
        assert "wre_adapter" in analysis.adapters_needed
        assert analysis.blockers == []
        assert analysis.exfoliation_ready is True

    def test_blockers_when_contracts_missing(
        self, builder_no_security: HermesFoundUpBuilder, tmp_path: Path
    ) -> None:
        _make_module(
            tmp_path,
            "modules/foundups/incomplete",
            contracts=("ROADMAP.md", "ModLog.md"),  # missing README + INTERFACE
            manifest=None,                          # missing manifest
            deploy_kind="none",
        )
        analysis = builder_no_security.analyze_boundary("modules/foundups/incomplete")

        assert "Missing README.md" in analysis.blockers
        assert "Missing INTERFACE.md" in analysis.blockers
        assert "Missing foundup_manifest.json" in analysis.blockers
        assert analysis.exfoliation_ready is False

    def test_missing_module_produces_blocker(
        self, builder_no_security: HermesFoundUpBuilder
    ) -> None:
        analysis = builder_no_security.analyze_boundary("modules/foundups/does_not_exist")
        assert analysis.exfoliation_ready is False
        assert any("not found" in b.lower() for b in analysis.blockers)


# --------------------------------------------------------------------------- #
# check_exfoliation_gate
# --------------------------------------------------------------------------- #

class TestExfoliationGate:
    def test_returns_structured_booleans_no_crash(
        self, builder_no_security: HermesFoundUpBuilder, tmp_path: Path
    ) -> None:
        _make_module(
            tmp_path,
            "modules/foundups/widget",
            manifest=_ready_manifest("widget"),
            deploy_kind="firebase",
        )
        gate = builder_no_security.check_exfoliation_gate("modules/foundups/widget")

        assert isinstance(gate, ExfoliationGate)
        for field in (
            "passed",
            "module_boundary_clear",
            "contracts_explicit",
            "runtime_testable",
            "deploy_surface_understood",
            "shared_deps_adapter_level",
            "claw_can_participate",
        ):
            assert isinstance(getattr(gate, field), bool), f"{field} not bool"

    def test_full_fixture_passes_gate(
        self, builder_no_security: HermesFoundUpBuilder, tmp_path: Path
    ) -> None:
        _make_module(
            tmp_path,
            "modules/foundups/widget",
            manifest=_ready_manifest("widget"),
            deploy_kind="firebase",
        )
        gate = builder_no_security.check_exfoliation_gate("modules/foundups/widget")
        assert gate.passed is True
        assert gate.deploy_surface_understood is True

    def test_manifest_entry_url_satisfies_deploy_surface(
        self, builder_no_security: HermesFoundUpBuilder, tmp_path: Path
    ) -> None:
        """Kosei-style evidence: manifest declares entry_url + launch_readiness=ready."""
        _make_module(
            tmp_path,
            "modules/foundups/kosei_like",
            manifest=_ready_manifest("kosei_like"),
            deploy_kind="manifest",  # only the manifest provides evidence
        )
        gate = builder_no_security.check_exfoliation_gate("modules/foundups/kosei_like")
        assert gate.deploy_surface_understood is True

    def test_app_index_html_satisfies_deploy_surface(
        self, builder_no_security: HermesFoundUpBuilder, tmp_path: Path
    ) -> None:
        _make_module(
            tmp_path,
            "modules/foundups/web_app",
            manifest=_ready_manifest("web_app"),
            deploy_kind="app",
        )
        gate = builder_no_security.check_exfoliation_gate("modules/foundups/web_app")
        assert gate.deploy_surface_understood is True

    def test_no_deploy_surface_blocks_check(
        self, builder_no_security: HermesFoundUpBuilder, tmp_path: Path
    ) -> None:
        bare = _ready_manifest("bare")
        bare["entry_url"] = None
        bare["launch_readiness"] = "incubating"
        _make_module(
            tmp_path,
            "modules/foundups/bare",
            manifest=bare,
            deploy_kind="none",
        )
        gate = builder_no_security.check_exfoliation_gate("modules/foundups/bare")
        assert gate.deploy_surface_understood is False
        assert gate.passed is False


# --------------------------------------------------------------------------- #
# sign_manifest
# --------------------------------------------------------------------------- #

class TestSignManifest:
    def test_signature_is_deterministic(
        self, builder_no_security: HermesFoundUpBuilder
    ) -> None:
        manifest = {"foundup_id": "x", "version": "1.0.0", "tier": "F0_DAE"}
        sig_a = builder_no_security.sign_manifest(manifest, secret_key=b"k")
        sig_b = builder_no_security.sign_manifest(manifest, secret_key=b"k")
        assert sig_a == sig_b
        assert len(sig_a) == 64  # sha256 hex

    def test_signature_excludes_existing_signature_field(
        self, builder_no_security: HermesFoundUpBuilder
    ) -> None:
        manifest = {"foundup_id": "x", "version": "1.0.0"}
        sig_a = builder_no_security.sign_manifest(manifest, secret_key=b"k")
        manifest_with_sig = {**manifest, "signature": "ignored"}
        sig_b = builder_no_security.sign_manifest(manifest_with_sig, secret_key=b"k")
        assert sig_a == sig_b

    def test_signature_changes_when_payload_changes(
        self, builder_no_security: HermesFoundUpBuilder
    ) -> None:
        a = builder_no_security.sign_manifest({"foundup_id": "a"}, secret_key=b"k")
        b = builder_no_security.sign_manifest({"foundup_id": "b"}, secret_key=b"k")
        assert a != b


# --------------------------------------------------------------------------- #
# generate_adapters (dry-run)
# --------------------------------------------------------------------------- #

class TestGenerateAdaptersDryRun:
    def test_dry_run_returns_code_without_writing(
        self, builder_no_security: HermesFoundUpBuilder, tmp_path: Path
    ) -> None:
        _make_module(
            tmp_path,
            "modules/foundups/widget",
            manifest=_ready_manifest("widget"),
            deploy_kind="firebase",
        )
        # Force adapter need
        _write(
            tmp_path / "modules/foundups/widget/src/uses_fam.py",
            "from modules.foundups.agent_market import fam_daemon\n",
        )

        result = builder_no_security.generate_adapters("modules/foundups/widget")

        assert result["success"] is True
        assert result["dry_run"] is True
        assert result["adapters_created"] == []  # nothing written in dry-run
        assert "fam_adapter" in result["adapter_code"]
        assert "class FAMAdapter" in result["adapter_code"]["fam_adapter"]
        # Confirm filesystem was NOT touched
        assert not (tmp_path / "modules/foundups/widget/adapters").exists()


# --------------------------------------------------------------------------- #
# extract_foundup (dry-run, fixture targets)
# --------------------------------------------------------------------------- #

class TestExtractFoundUpDryRun:
    def test_complete_fixture_dry_run_succeeds(
        self, builder_no_security: HermesFoundUpBuilder, tmp_path: Path
    ) -> None:
        _make_module(
            tmp_path,
            "modules/foundups/widget",
            manifest=_ready_manifest("widget"),
            deploy_kind="firebase",
        )
        result = builder_no_security.extract_foundup("modules/foundups/widget")

        assert result["success"] is True
        assert result["dry_run"] is True
        assert result["target_repo"] == "FOUNDUPS/widget"
        assert result["exfoliation_gate"]["passed"] is True
        assert "manifest" in result
        assert result["manifest"]["signature"]  # signed
        # No real filesystem mutation outside the fixture
        assert not (tmp_path / "modules/foundups/widget/adapters").exists()

    def test_incomplete_fixture_returns_exfoliation_gate_failed(
        self, builder_no_security: HermesFoundUpBuilder, tmp_path: Path
    ) -> None:
        _make_module(
            tmp_path,
            "modules/foundups/incomplete",
            contracts=("README.md",),  # missing INTERFACE/ROADMAP/ModLog
            manifest=None,
            deploy_kind="none",
            add_tests=False,
        )
        result = builder_no_security.extract_foundup("modules/foundups/incomplete")

        assert result["success"] is False
        assert result["error"] == "exfoliation_gate_failed"
        assert result["exfoliation_gate"]["passed"] is False
        # Specific failed checks should be visible to the caller.
        checks = result["exfoliation_gate"]["checks"]
        assert checks["contracts_explicit"] is False
        assert checks["deploy_surface_understood"] is False


# --------------------------------------------------------------------------- #
# Read-only assertion against real GotJunk module
# --------------------------------------------------------------------------- #

class TestRealRepoReadOnly:
    """Sanity checks against the live repo. Strictly read-only — no extraction."""

    def test_gotjunk_boundary_analysis_returns_structure(
        self, real_repo_builder: HermesFoundUpBuilder
    ) -> None:
        analysis = real_repo_builder.analyze_boundary("modules/foundups/gotjunk")
        # We assert only on shape + the fact that GotJunk has product files.
        assert isinstance(analysis, BoundaryAnalysis)
        assert analysis.product_files, "GotJunk should have at least one .py file"

    def test_kosei_deploy_surface_now_recognized(
        self, real_repo_builder: HermesFoundUpBuilder
    ) -> None:
        """Phase 1 fix: Kosei has manifest entry_url + launch_readiness=ready."""
        gate = real_repo_builder.check_exfoliation_gate("modules/foundups/kosei")
        assert gate.deploy_surface_understood is True, (
            "Kosei manifest declares entry_url and launch_readiness=ready; "
            "deploy surface should be recognized after Phase 1 detection fix."
        )


# --------------------------------------------------------------------------- #
# HERMES_BUILDER_DRYRUN_DEFAULT_SAFETY_PHASE1 acceptance (A1-A3, A5)
# --------------------------------------------------------------------------- #

class TestDryRunDefaultSafety:
    """Builder must default to dry-run; real writes need an explicit double opt-in.

    Acceptance criteria per
    docs/audits/architecture/HERMES_BUILDER_DRYRUN_DEFAULT_SAFETY_PHASE1.md:
      A1 fresh builder with no env -> dry_run is True
      A2 default builder extract/generate_adapters emit dry_run: true, write nothing
      A3 real-write path requires BOTH opt-in env vars; otherwise dry_run stays True
      A5 no test enables real writes (DRY_RUN=0) without a real-write opt-in marker
    """

    def test_a1_default_is_dry_run_with_no_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("HERMES_BUILDER_DRY_RUN", raising=False)
        monkeypatch.delenv("HERMES_BUILDER_ALLOW_REAL_WRITES", raising=False)
        builder = HermesFoundUpBuilder(repo_root=tmp_path)
        assert builder.dry_run is True
        assert builder.allow_real_writes is False

    def test_a2_default_builder_writes_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("HERMES_BUILDER_DRY_RUN", raising=False)
        monkeypatch.delenv("HERMES_BUILDER_ALLOW_REAL_WRITES", raising=False)
        monkeypatch.setenv("HERMES_BUILDER_SECURITY_GATE", "0")
        _make_module(
            tmp_path,
            "modules/foundups/widget",
            manifest=_ready_manifest("widget"),
            deploy_kind="firebase",
        )
        _write(
            tmp_path / "modules/foundups/widget/src/uses_fam.py",
            "from modules.foundups.agent_market import fam_daemon\n",
        )
        builder = HermesFoundUpBuilder(repo_root=tmp_path)
        assert builder.dry_run is True

        extract = builder.extract_foundup("modules/foundups/widget")
        assert extract["dry_run"] is True

        gen = builder.generate_adapters("modules/foundups/widget")
        assert gen["dry_run"] is True
        assert gen["adapters_created"] == []
        # No adapter directory materialised on disk in the default (safe) path.
        assert not (tmp_path / "modules/foundups/widget/adapters").exists()

    def test_a3_dry_run_zero_alone_stays_safe(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # HERMES_BUILDER_DRY_RUN=0 WITHOUT the allow flag must NOT enable writes.
        monkeypatch.setenv("HERMES_BUILDER_DRY_RUN", "0")
        monkeypatch.delenv("HERMES_BUILDER_ALLOW_REAL_WRITES", raising=False)
        assert HermesFoundUpBuilder(repo_root=tmp_path).dry_run is True

    def test_a3_allow_flag_alone_stays_safe(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # allow flag alone (DRY_RUN not explicitly 0) must NOT enable writes.
        monkeypatch.setenv("HERMES_BUILDER_ALLOW_REAL_WRITES", "1")
        monkeypatch.delenv("HERMES_BUILDER_DRY_RUN", raising=False)
        assert HermesFoundUpBuilder(repo_root=tmp_path).dry_run is True

    def test_a3_double_opt_in_enables_real_writes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # BOTH flags -> dry_run False (explicit, deliberate real-write opt-in).
        monkeypatch.setenv("HERMES_BUILDER_ALLOW_REAL_WRITES", "1")
        monkeypatch.setenv("HERMES_BUILDER_DRY_RUN", "0")
        builder = HermesFoundUpBuilder(repo_root=tmp_path)
        assert builder.allow_real_writes is True
        assert builder.dry_run is False

    def test_a5_no_test_enables_real_writes_without_opt_in_marker(self) -> None:
        """CI tripwire: a test file that forces HERMES_BUILDER_DRY_RUN=0 must also
        carry the HERMES_BUILDER_ALLOW_REAL_WRITES marker (deliberate opt-in)."""
        import re

        tests_dir = Path(__file__).resolve().parent
        pattern = re.compile(r"HERMES_BUILDER_DRY_RUN[\"'],\s*[\"']0[\"']")
        offenders = []
        for pyf in sorted(tests_dir.glob("*.py")):
            text = pyf.read_text(encoding="utf-8")
            if pattern.search(text) and "HERMES_BUILDER_ALLOW_REAL_WRITES" not in text:
                offenders.append(pyf.name)
        assert offenders == [], (
            "test files set HERMES_BUILDER_DRY_RUN=0 without a real-write opt-in "
            f"marker: {offenders}"
        )
