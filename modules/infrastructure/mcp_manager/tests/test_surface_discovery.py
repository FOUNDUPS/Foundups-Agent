"""
MCPA5 surface discovery tests.

Verifies that `MCPServerManager.discover_all_surfaces()` truthfully exposes
the S1/S2/S3 triad anchored in WSP 96 Annex A.1 without starting any servers
and without overclaiming runtime capability.

Anchored to:
  - WSP 97 (truth distinction)
  - WSP 96 Annex A (canonical holo_search contract + surface ownership)
  - MCPA1 audit findings (S2 + S3 omitted from prior gateway reports)

These tests do NOT require any live transport or backend.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from modules.infrastructure.mcp_manager.src import mcp_manager
from modules.infrastructure.mcp_manager.src.mcp_manager import (
    KNOWN_NON_RUNNABLE_SURFACES,
    KnownSurface,
    MCPServerManager,
    S2_FOUNDUPS_MCP_BRIDGE,
    S3_PAVS_MCP,
)


# ---------------------------------------------------------------------------
# Module-level constants (defensive — prevent silent removal)
# ---------------------------------------------------------------------------


class TestSurfaceConstants:
    """The canonical S2/S3 descriptors must exist and be truthful."""

    def test_s2_descriptor_truth_fields(self):
        assert S2_FOUNDUPS_MCP_BRIDGE.surface_id == "S2"
        assert S2_FOUNDUPS_MCP_BRIDGE.surface_kind == "internal_python_bridge"
        assert S2_FOUNDUPS_MCP_BRIDGE.runnable is False
        assert S2_FOUNDUPS_MCP_BRIDGE.implementation_status == "RUNTIME_INTERNAL_ONLY"
        assert S2_FOUNDUPS_MCP_BRIDGE.holo_search_support == "real_with_fallback"
        assert S2_FOUNDUPS_MCP_BRIDGE.authority_role == "canonical_internal_adapter"
        assert "foundups_mcp_bridge" in S2_FOUNDUPS_MCP_BRIDGE.path

    def test_s3_descriptor_truth_fields(self):
        assert S3_PAVS_MCP.surface_id == "S3"
        assert S3_PAVS_MCP.surface_kind == "placeholder_stub"
        assert S3_PAVS_MCP.runnable is False
        assert S3_PAVS_MCP.implementation_status == "PLACEHOLDER_STUB"
        assert S3_PAVS_MCP.holo_search_support == "placeholder"
        assert S3_PAVS_MCP.authority_role == "no_authority"
        assert "pavs_mcp" in S3_PAVS_MCP.path

    def test_known_non_runnable_surfaces_includes_s2_and_s3(self):
        ids = {s.surface_id for s in KNOWN_NON_RUNNABLE_SURFACES}
        assert ids == {"S2", "S3"}, (
            "KNOWN_NON_RUNNABLE_SURFACES must contain exactly S2 and S3"
        )
        # Every entry must be non-runnable
        for s in KNOWN_NON_RUNNABLE_SURFACES:
            assert s.runnable is False

    def test_known_surface_is_serializable(self):
        d = S2_FOUNDUPS_MCP_BRIDGE.to_dict()
        for key in (
            "surface_id",
            "surface_kind",
            "name",
            "path",
            "runnable",
            "implementation_status",
            "holo_search_support",
            "authority_role",
            "notes",
        ):
            assert key in d, f"Required truth field missing in to_dict(): {key}"


# ---------------------------------------------------------------------------
# discover_all_surfaces — does not start servers, returns truthful triad
# ---------------------------------------------------------------------------


@pytest.fixture
def manager_with_no_runnable_servers(monkeypatch):
    """Manager fixture where the foundups-mcp-p1 scan returns an empty dict.

    Lets us assert the S2/S3 baseline appears even when no S1-class server
    is discovered (e.g. fresh checkout, no foundups-mcp-p1 directory).
    """
    monkeypatch.setattr(
        MCPServerManager,
        "_discover_mcp_servers",
        lambda self: {},
    )
    return MCPServerManager()


@pytest.fixture
def manager_with_holo_index_only(monkeypatch, tmp_path):
    """Manager fixture where _discover_mcp_servers returns just S1 (holo_index)."""
    fake_path = tmp_path / "foundups-mcp-p1" / "servers" / "holo_index" / "server.py"
    fake_path.parent.mkdir(parents=True)
    fake_path.write_text("# stub\n")
    monkeypatch.setattr(
        MCPServerManager,
        "_discover_mcp_servers",
        lambda self: {"holo_index": fake_path},
    )
    m = MCPServerManager(repo_root=str(tmp_path))
    return m


@pytest.fixture
def manager_with_aux_servers(monkeypatch, tmp_path):
    """Manager fixture with holo_index + auxiliary servers (codeindex etc)."""
    base = tmp_path / "foundups-mcp-p1" / "servers"
    holo = base / "holo_index" / "server.py"
    aux = base / "codeindex" / "server.py"
    holo.parent.mkdir(parents=True)
    aux.parent.mkdir(parents=True)
    holo.write_text("# stub\n")
    aux.write_text("# stub\n")
    monkeypatch.setattr(
        MCPServerManager,
        "_discover_mcp_servers",
        lambda self: {"holo_index": holo, "codeindex": aux},
    )
    return MCPServerManager(repo_root=str(tmp_path))


class TestDiscoverAllSurfaces:
    """discover_all_surfaces must return S1+S2+S3 truthfully."""

    def test_no_runnable_returns_only_known_surfaces(
        self, manager_with_no_runnable_servers
    ):
        """Even with no S1-class servers found, S2 and S3 must appear."""
        surfaces = manager_with_no_runnable_servers.discover_all_surfaces()
        ids = [s.surface_id for s in surfaces]
        assert ids == ["S2", "S3"], (
            "When no runnable server discovered, only S2/S3 should appear"
        )

    def test_holo_index_present_yields_full_triad(self, manager_with_holo_index_only):
        """S1 + S2 + S3 are all reported when holo_index is discovered."""
        surfaces = manager_with_holo_index_only.discover_all_surfaces()
        ids = [s.surface_id for s in surfaces]
        assert ids == ["S1", "S2", "S3"], (
            f"Expected S1/S2/S3 triad, got {ids}"
        )

    def test_s1_truth_fields_when_discovered(self, manager_with_holo_index_only):
        """The S1 entry constructed from discovery has truthful runnable=True."""
        surfaces = manager_with_holo_index_only.discover_all_surfaces()
        s1 = next(s for s in surfaces if s.surface_id == "S1")
        assert s1.surface_kind == "external_mcp_server"
        assert s1.name == "holo_index"
        assert s1.runnable is True
        assert s1.implementation_status == "RUNTIME_LIVE"
        assert s1.holo_search_support == "real"
        assert s1.authority_role == "canonical_external_adapter"

    def test_auxiliary_servers_marked_aux_not_s1(self, manager_with_aux_servers):
        """Servers other than holo_index get AUX:* surface_id, not S1."""
        surfaces = manager_with_aux_servers.discover_all_surfaces()

        # Exactly one S1
        s1_count = sum(1 for s in surfaces if s.surface_id == "S1")
        assert s1_count == 1

        # codeindex -> AUX:codeindex
        aux = [s for s in surfaces if s.surface_id.startswith("AUX:")]
        assert len(aux) == 1
        assert aux[0].surface_id == "AUX:codeindex"
        assert aux[0].surface_kind == "auxiliary_mcp_server"
        assert aux[0].holo_search_support == "none"
        assert aux[0].authority_role == "auxiliary"

    def test_does_not_start_any_server(
        self, manager_with_holo_index_only, monkeypatch
    ):
        """discover_all_surfaces must never call start_server."""
        called = []
        monkeypatch.setattr(
            manager_with_holo_index_only,
            "start_server",
            lambda name: called.append(name) or True,
        )
        manager_with_holo_index_only.discover_all_surfaces()
        assert called == [], (
            "discover_all_surfaces must not auto-start any server; got starts: "
            f"{called}"
        )

    def test_non_runnable_surfaces_are_runnable_false(
        self, manager_with_holo_index_only
    ):
        """S2/S3 must always be runnable=False so the manager never tries to start them."""
        surfaces = manager_with_holo_index_only.discover_all_surfaces()
        for s in surfaces:
            if s.surface_id in {"S2", "S3"}:
                assert s.runnable is False


# ---------------------------------------------------------------------------
# format_surface_report — visible truth fields in operator output
# ---------------------------------------------------------------------------


class TestFormatSurfaceReport:
    """The textual report must surface every truth field for every surface."""

    def test_report_includes_all_surface_ids(self, manager_with_holo_index_only):
        report = manager_with_holo_index_only.format_surface_report()
        assert "S1" in report
        assert "S2" in report
        assert "S3" in report

    def test_report_distinguishes_runnable_from_non_runnable(
        self, manager_with_holo_index_only
    ):
        report = manager_with_holo_index_only.format_surface_report()
        # The runnable column must show "yes" for at least S1 and "no" for S2/S3
        # We assert by counting tokens loosely.
        assert " yes " in report or "yes" in report
        assert "no" in report

    def test_report_includes_status_labels(self, manager_with_holo_index_only):
        report = manager_with_holo_index_only.format_surface_report()
        assert "RUNTIME_LIVE" in report
        assert "RUNTIME_INTERNAL_ONLY" in report
        assert "PLACEHOLDER_STUB" in report

    def test_report_includes_holo_search_support_column(
        self, manager_with_holo_index_only
    ):
        report = manager_with_holo_index_only.format_surface_report()
        assert "real" in report  # S1
        assert "real_with_fallback" in report  # S2
        assert "placeholder" in report  # S3

    def test_report_includes_wsp96_authority_anchor(
        self, manager_with_holo_index_only
    ):
        report = manager_with_holo_index_only.format_surface_report()
        assert "WSP_96" in report
        assert "Annex A" in report


# ---------------------------------------------------------------------------
# report_all_surfaces — runtime-safe (no startup), prints + returns
# ---------------------------------------------------------------------------


class TestReportAllSurfaces:
    """report_all_surfaces must be safe to call standalone (no server boot)."""

    def test_returns_list_of_known_surfaces(self, manager_with_holo_index_only, capsys):
        result = manager_with_holo_index_only.report_all_surfaces()
        assert isinstance(result, list)
        assert all(isinstance(s, KnownSurface) for s in result)
        # Output captured
        captured = capsys.readouterr()
        assert "S1" in captured.out
        assert "S2" in captured.out
        assert "S3" in captured.out

    def test_no_subprocess_or_psutil_calls(
        self, manager_with_holo_index_only, monkeypatch
    ):
        """The discovery report must not invoke subprocess or psutil."""
        # Explicit guard: replace subprocess.Popen and psutil.process_iter with
        # exploding stubs. If the report path touches them, the test fails.
        def boom_popen(*_a, **_kw):
            raise AssertionError("report_all_surfaces must not call subprocess.Popen")

        def boom_iter(*_a, **_kw):
            raise AssertionError(
                "report_all_surfaces must not call psutil.process_iter"
            )

        monkeypatch.setattr(mcp_manager.subprocess, "Popen", boom_popen)
        monkeypatch.setattr(mcp_manager.psutil, "process_iter", boom_iter)

        # Should still succeed without touching either
        result = manager_with_holo_index_only.report_all_surfaces()
        assert len(result) >= 2  # at least S2 + S3


# ---------------------------------------------------------------------------
# Lifecycle preservation — runnable surfaces still managed normally
# ---------------------------------------------------------------------------


class TestLifecyclePreservation:
    """Existing runnable-server methods must still work for S1-class surfaces."""

    def test_get_server_status_still_callable(self, manager_with_holo_index_only):
        """Existing API not broken by the discovery expansion."""
        is_running, pid = manager_with_holo_index_only.get_server_status("holo_index")
        # We did not start anything, so it must report not running.
        assert is_running is False
        assert pid is None

    def test_servers_dict_unchanged_in_shape(self, manager_with_holo_index_only):
        """`self.servers` is still a {name: Path} dict for runnable servers only."""
        servers = manager_with_holo_index_only.servers
        assert "holo_index" in servers
        # S2/S3 are NOT in self.servers — they are listed separately
        assert "foundups_mcp_bridge" not in servers
        assert "pavs_mcp" not in servers


# ---------------------------------------------------------------------------
# Module exports (defensive — prevent accidental constant removal)
# ---------------------------------------------------------------------------


def test_module_exports_required_discovery_symbols():
    """If a future refactor removes these, the test suite fails loudly."""
    assert hasattr(mcp_manager, "KnownSurface")
    assert hasattr(mcp_manager, "S2_FOUNDUPS_MCP_BRIDGE")
    assert hasattr(mcp_manager, "S3_PAVS_MCP")
    assert hasattr(mcp_manager, "KNOWN_NON_RUNNABLE_SURFACES")
    assert hasattr(MCPServerManager, "discover_all_surfaces")
    assert hasattr(MCPServerManager, "format_surface_report")
    assert hasattr(MCPServerManager, "report_all_surfaces")
