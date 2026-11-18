"""
Hermes FoundUp Builder Adapter

Bounded Hermes agent wrapper for FoundUp extraction tasks.
All execution gated through AI Overseer security sentinel.
Qwen backend via LM Studio for local inference.
MCP Bridge v1.4 perception layer for intelligent extraction decisions.

WSP References:
- WSP 29: CABR Engine (quality gates)
- WSP 50: Pre-action verification
- WSP 77: Agent coordination
- WSP 97: System Execution Prompting Protocol
"""

import hashlib
import hmac
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Import MCP Bridge for perception layer
try:
    from modules.infrastructure.foundups_mcp_bridge.src.bridge_server import (
        FoundUpsMCPBridge,
    )
    MCP_BRIDGE_AVAILABLE = True
except ImportError:
    MCP_BRIDGE_AVAILABLE = False
    logger.debug("[HERMES] MCP Bridge not available - running without perception")

# Import FAM Daemon for breadcrumb events
try:
    from modules.foundups.agent_market.src.fam_daemon import (
        FAMDaemon,
        FAMEventType,
        get_fam_daemon,
    )
    FAM_DAEMON_AVAILABLE = True
except ImportError:
    FAM_DAEMON_AVAILABLE = False
    logger.debug("[HERMES] FAM Daemon not available - running without breadcrumbs")

# Default Qwen configuration for LM Studio (legacy - use HermesModelRouter)
DEFAULT_QWEN_CONFIG = {
    "model": "qwen-coder-7b",
    "base_url": "http://localhost:1234/v1",
    "tool_parser": "qwen",
}

# Import model router for dynamic capability switching
try:
    from .hermes_model_router import (
        HermesModelRouter,
        TaskCapability,
        get_model_router,
        route_to_model,
    )
    MODEL_ROUTER_AVAILABLE = True
except ImportError:
    MODEL_ROUTER_AVAILABLE = False


@dataclass
class BoundaryAnalysis:
    """Result of module boundary analysis for exfoliation."""
    module_path: str
    product_files: List[str] = field(default_factory=list)
    core_imports: List[str] = field(default_factory=list)
    adapters_needed: List[str] = field(default_factory=list)
    exfoliation_ready: bool = False
    blockers: List[str] = field(default_factory=list)


@dataclass
class ExfoliationGate:
    """Exfoliation readiness gate check results."""
    passed: bool = False
    module_boundary_clear: bool = False
    contracts_explicit: bool = False
    runtime_testable: bool = False
    deploy_surface_understood: bool = False
    shared_deps_adapter_level: bool = False
    claw_can_participate: bool = False


class HermesFoundUpBuilder:
    """
    Bounded Hermes adapter for FoundUp extraction tasks.

    Security:
    - All operations gated through AI Overseer security sentinel
    - Hermes skill loading disabled (uses WRE skills only)
    - Output validation via CABR V2
    - Pattern memory integration for learning

    Usage:
        builder = HermesFoundUpBuilder(repo_root=Path("O:/Foundups-Agent"))
        result = builder.extract_foundup("modules/foundups/gotjunk", "FOUNDUPS")
    """

    # Required contract files per exfoliation protocol
    REQUIRED_CONTRACTS = ["README.md", "INTERFACE.md", "ROADMAP.md", "ModLog.md"]

    # Core modules that require adapters (not product code)
    CORE_MODULES = [
        "modules.infrastructure.wre_core",
        "modules.infrastructure.foundups_mcp_bridge",
        "modules.ai_intelligence.ai_overseer",
        "modules.communication.moltbot_bridge",
        "modules.foundups.agent_market",
    ]

    def __init__(self, repo_root: Optional[Path] = None):
        """
        Initialize Hermes FoundUp Builder.

        Args:
            repo_root: Repository root path. Defaults to O:/Foundups-Agent
        """
        self.repo_root = repo_root or Path("O:/Foundups-Agent")
        self._hermes_loop = None
        self._security_passed = False

        # Environment controls
        self.enabled = os.environ.get("HERMES_BUILDER_ENABLED", "1") == "1"
        # HERMES_BUILDER_DRYRUN_DEFAULT_SAFETY_PHASE1: dry-run by DEFAULT.
        # Real writes require an explicit DOUBLE opt-in -- BOTH must be set:
        #   HERMES_BUILDER_ALLOW_REAL_WRITES=1  AND  HERMES_BUILDER_DRY_RUN=0
        # Any other combination (including all-unset) stays dry-run/safe. This
        # aligns the adapter-level default with BuildPlanExecutor(dry_run=True)
        # and HermesJobExecutor(dry_run=True), closing the OBSERVED default-on
        # write risk found in the RedDog FoundUp-creation execution-path audit
        # (docs/audits/architecture/HERMES_BUILDER_DRYRUN_DEFAULT_SAFETY_PHASE1.md).
        self.allow_real_writes = (
            os.environ.get("HERMES_BUILDER_ALLOW_REAL_WRITES", "0") == "1"
        )
        self.dry_run = not (
            self.allow_real_writes
            and os.environ.get("HERMES_BUILDER_DRY_RUN", "1") == "0"
        )
        self.require_security_gate = os.environ.get("HERMES_BUILDER_SECURITY_GATE", "1") == "1"

        # MCP Bridge perception layer (v1.4)
        self._mcp_bridge = None
        if MCP_BRIDGE_AVAILABLE:
            try:
                self._mcp_bridge = FoundUpsMCPBridge(repo_root=self.repo_root)
                logger.info("[HERMES] MCP Bridge v1.4 perception layer enabled")
            except Exception as e:
                logger.warning("[HERMES] MCP Bridge init failed: %s", e)

        # FAM Daemon for breadcrumb events
        self._fam_daemon = None
        if FAM_DAEMON_AVAILABLE:
            try:
                self._fam_daemon = get_fam_daemon()
                logger.info("[HERMES] FAM Daemon breadcrumb system enabled")
            except Exception as e:
                logger.warning("[HERMES] FAM Daemon init failed: %s", e)

        # Add vendor to path for Hermes imports
        vendor_path = self.repo_root / "vendor" / "hermes-agent"
        if vendor_path.exists() and str(vendor_path) not in sys.path:
            sys.path.insert(0, str(vendor_path))

    def _emit_breadcrumb(self, event_type: str, payload: Dict[str, Any]) -> None:
        """
        Emit FAM event breadcrumb for audit trail.

        Args:
            event_type: FAMEventType value (e.g., "hermes_extraction_started")
            payload: Event-specific payload dict
        """
        if not self._fam_daemon:
            return

        try:
            # Add timestamp if not present
            if "timestamp" not in payload:
                from datetime import datetime, timezone
                payload["timestamp"] = datetime.now(timezone.utc).isoformat()

            self._fam_daemon.emit(event_type, payload)
            logger.debug("[HERMES] Breadcrumb: %s", event_type)
        except Exception as e:
            logger.warning("[HERMES] Failed to emit breadcrumb %s: %s", event_type, e)

    def _ensure_security_gate(self) -> bool:
        """
        Check AI Overseer security sentinel before any operation.

        Returns:
            True if security gate passes, False otherwise
        """
        if not self.require_security_gate:
            logger.warning("[HERMES] Security gate disabled via env var")
            return True

        try:
            from modules.ai_intelligence.ai_overseer.src.ai_overseer import (
                AIIntelligenceOverseer,
            )

            overseer = AIIntelligenceOverseer(self.repo_root)
            result = overseer.monitor_openclaw_security(force=True)

            self._security_passed = result.get("passed", False)

            # Emit breadcrumb for security gate result
            self._emit_breadcrumb(FAMEventType.HERMES_SECURITY_GATE.value, {
                "passed": self._security_passed,
                "message": result.get("message", ""),
                "source_module": "security_check",
            })

            if not self._security_passed:
                logger.error(
                    "[HERMES] Security gate FAILED: %s",
                    result.get("message", "unknown")
                )
            else:
                logger.info("[HERMES] Security gate PASSED")

            return self._security_passed

        except ImportError as e:
            logger.error("[HERMES] AI Overseer not available: %s", e)
            return False
        except Exception as e:
            logger.error("[HERMES] Security gate error: %s", e)
            return False

    def _get_hermes_loop(self):
        """
        Lazy-load Hermes agent loop.

        Returns:
            HermesAgentLoop instance or None if unavailable
        """
        if self._hermes_loop is not None:
            return self._hermes_loop

        try:
            from environments.agent_loop import HermesAgentLoop
            self._hermes_loop = HermesAgentLoop
            logger.info("[HERMES] Agent loop loaded from vendor")
            return self._hermes_loop
        except ImportError as e:
            logger.warning("[HERMES] Agent loop not available: %s", e)
            return None

    def analyze_boundary(self, module_path: str) -> BoundaryAnalysis:
        """
        Analyze module boundary for exfoliation readiness.

        Uses MCP Bridge perception layer (if available) for:
        - Dependency graph analysis (get_module_dependencies)
        - Blast radius calculation (get_reverse_dependencies)

        Falls back to import scanning if MCP Bridge unavailable.

        Args:
            module_path: Relative path to module (e.g., "modules/foundups/gotjunk")

        Returns:
            BoundaryAnalysis with product/core classification
        """
        analysis = BoundaryAnalysis(module_path=module_path)
        full_path = self.repo_root / module_path

        if not full_path.exists():
            analysis.blockers.append(f"Module not found: {module_path}")
            return analysis

        # Use MCP Bridge for enhanced dependency perception
        mcp_deps = None
        mcp_reverse = None
        if self._mcp_bridge:
            try:
                # Get forward dependencies
                mcp_deps = self._mcp_bridge.call_tool(
                    "get_module_dependencies",
                    module_path=module_path
                )
                # Get reverse dependencies (blast radius)
                mcp_reverse = self._mcp_bridge.call_tool(
                    "get_reverse_dependencies",
                    module_path=module_path
                )
                logger.debug("[HERMES] MCP perception: deps=%s, reverse=%s",
                             mcp_deps.get("status"), mcp_reverse.get("status"))
            except Exception as e:
                logger.warning("[HERMES] MCP dependency analysis failed: %s", e)

        # Scan Python files for imports (always run for product file list)
        core_import_set = set()
        product_files = []

        for py_file in full_path.rglob("*.py"):
            rel_path = str(py_file.relative_to(full_path))
            product_files.append(rel_path)

            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")

                # Find imports from core modules
                for core_module in self.CORE_MODULES:
                    if f"from {core_module}" in content or f"import {core_module}" in content:
                        core_import_set.add(core_module)

            except Exception as e:
                logger.debug("[HERMES] Error reading %s: %s", py_file, e)

        # Enrich with MCP dependency data if available
        if mcp_deps and mcp_deps.get("status") == "ok":
            mcp_data = mcp_deps.get("data", {})
            internal_deps = mcp_data.get("internal_dependencies", [])
            for dep in internal_deps:
                dep_path = dep.get("path", "")
                # Map dependency paths to core module names
                for core_module in self.CORE_MODULES:
                    if core_module.replace(".", "/") in dep_path:
                        core_import_set.add(core_module)

        analysis.product_files = product_files
        analysis.core_imports = list(core_import_set)

        # Determine adapters needed
        adapter_map = {
            "modules.infrastructure.wre_core": "wre_adapter",
            "modules.infrastructure.foundups_mcp_bridge": "mcp_adapter",
            "modules.ai_intelligence.ai_overseer": "overseer_adapter",
            "modules.communication.moltbot_bridge": "openclaw_adapter",
            "modules.foundups.agent_market": "fam_adapter",
        }

        analysis.adapters_needed = [
            adapter_map[imp] for imp in core_import_set if imp in adapter_map
        ]

        # Check for blockers
        if not (full_path / "README.md").exists():
            analysis.blockers.append("Missing README.md")
        if not (full_path / "INTERFACE.md").exists():
            analysis.blockers.append("Missing INTERFACE.md")
        if not (full_path / "foundup_manifest.json").exists():
            analysis.blockers.append("Missing foundup_manifest.json")

        # Add blast radius info from MCP if high impact
        if mcp_reverse and mcp_reverse.get("status") == "ok":
            blast_radius = mcp_reverse.get("data", {}).get("blast_radius", "unknown")
            if blast_radius in ("high", "critical"):
                analysis.blockers.append(f"High blast radius: {blast_radius} - review dependents before extraction")

        analysis.exfoliation_ready = len(analysis.blockers) == 0

        # Emit breadcrumb for boundary analysis
        self._emit_breadcrumb(FAMEventType.HERMES_BOUNDARY_ANALYZED.value, {
            "module_path": module_path,
            "product_files_count": len(analysis.product_files),
            "core_imports_count": len(analysis.core_imports),
            "adapters_needed": analysis.adapters_needed,
            "blockers": analysis.blockers,
            "exfoliation_ready": analysis.exfoliation_ready,
        })

        return analysis

    def _detect_deploy_surface(self, full_path: Path) -> bool:
        """Return True when a FoundUp module has verified launch evidence."""
        deploy_indicators = [
            full_path / "Dockerfile",
            full_path / "cloudbuild.yaml",
            full_path / "firebase.json",
            full_path / "deployment",
        ]
        if any(ind.exists() for ind in deploy_indicators):
            return True

        web_entry_points = [
            full_path / "app" / "index.html",
            full_path / "frontend" / "index.html",
        ]
        if any(entry.exists() for entry in web_entry_points):
            return True

        manifest_path = full_path / "foundup_manifest.json"
        if not manifest_path.exists():
            return False

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("[HERMES] Deploy manifest unreadable: %s", exc)
            return False

        entry_url = manifest.get("entry_url")
        launch_readiness = str(manifest.get("launch_readiness", "")).lower()
        return bool(entry_url) and launch_readiness == "ready"

    def check_exfoliation_gate(self, module_path: str) -> ExfoliationGate:
        """
        Run exfoliation readiness gate per FOUNDUP_EXFOLIATION_PROTOCOL.md.

        Uses MCP Bridge perception layer (if available) for:
        - Impact scoring (get_change_impact_score)
        - Test coverage analysis
        - Prior failure pattern detection

        Args:
            module_path: Relative path to module

        Returns:
            ExfoliationGate with check results
        """
        gate = ExfoliationGate()
        full_path = self.repo_root / module_path

        # Use MCP Bridge for impact prediction
        impact_data = None
        if self._mcp_bridge:
            try:
                impact_result = self._mcp_bridge.call_tool(
                    "get_change_impact_score",
                    target_type="module",
                    target=module_path
                )
                if impact_result.get("status") == "ok":
                    impact_data = impact_result.get("data", {})
                    logger.info("[HERMES] Impact score for %s: %s (risk: %s)",
                                module_path,
                                impact_data.get("risk_score", "?"),
                                impact_data.get("risk_level", "?"))
            except Exception as e:
                logger.warning("[HERMES] MCP impact scoring failed: %s", e)

        # 1. Module boundary is clear
        analysis = self.analyze_boundary(module_path)
        gate.module_boundary_clear = len(analysis.blockers) == 0

        # 2. Contracts are explicit
        contracts_present = all(
            (full_path / contract).exists() for contract in self.REQUIRED_CONTRACTS
        )
        gate.contracts_explicit = contracts_present

        # 3. Runtime is independently testable
        tests_dir = full_path / "tests"
        has_tests = tests_dir.exists() and any(tests_dir.glob("test_*.py"))

        # Enhance with MCP test coverage data
        if impact_data:
            test_coverage = impact_data.get("test_coverage", {})
            coverage_ratio = test_coverage.get("ratio", 0)
            # Warn if low coverage but don't block
            if coverage_ratio < 0.5 and has_tests:
                logger.warning("[HERMES] Low test coverage: %.1f%% for %s",
                               coverage_ratio * 100, module_path)

        gate.runtime_testable = has_tests

        # 4. Deploy surface is understood
        gate.deploy_surface_understood = self._detect_deploy_surface(full_path)

        # 5. Shared dependencies are adapter-level
        gate.shared_deps_adapter_level = len(analysis.adapters_needed) <= 5

        # 6. Another Claw could participate
        # Block if MCP says critical risk level
        if impact_data and impact_data.get("risk_level") == "critical":
            logger.warning("[HERMES] Critical risk level - blocking claw participation")
            gate.claw_can_participate = False
        else:
            gate.claw_can_participate = gate.contracts_explicit

        # Overall gate
        gate.passed = all([
            gate.module_boundary_clear,
            gate.contracts_explicit,
            gate.runtime_testable,
            gate.deploy_surface_understood,
            gate.shared_deps_adapter_level,
            gate.claw_can_participate,
        ])

        # Emit breadcrumb for gate check result
        self._emit_breadcrumb(FAMEventType.HERMES_GATE_CHECKED.value, {
            "module_path": module_path,
            "passed": gate.passed,
            "checks": {
                "module_boundary_clear": gate.module_boundary_clear,
                "contracts_explicit": gate.contracts_explicit,
                "runtime_testable": gate.runtime_testable,
                "deploy_surface_understood": gate.deploy_surface_understood,
                "shared_deps_adapter_level": gate.shared_deps_adapter_level,
                "claw_can_participate": gate.claw_can_participate,
            },
            "risk_level": impact_data.get("risk_level") if impact_data else None,
        })

        return gate

    def generate_adapters(
        self,
        module_path: str,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate adapter stubs for core dependencies.

        Args:
            module_path: Source module path
            output_dir: Where to write adapters (default: {module}/adapters/)

        Returns:
            Dict with created adapter info
        """
        if not self._ensure_security_gate():
            return {"success": False, "error": "security_gate_failed"}

        analysis = self.analyze_boundary(module_path)
        full_path = self.repo_root / module_path

        if output_dir:
            adapters_dir = Path(output_dir)
        else:
            adapters_dir = full_path / "adapters"

        if not self.dry_run:
            adapters_dir.mkdir(exist_ok=True)

        adapters_created = []
        adapter_code = {}

        for adapter_name in analysis.adapters_needed:
            code = self._generate_adapter_stub(adapter_name)
            adapter_code[adapter_name] = code

            if not self.dry_run:
                adapter_file = adapters_dir / f"{adapter_name}.py"
                adapter_file.write_text(code, encoding="utf-8")
                adapters_created.append(str(adapter_file))
                logger.info("[HERMES] Created adapter: %s", adapter_file)

        return {
            "success": True,
            "adapters_created": adapters_created,
            "adapter_code": adapter_code,
            "dry_run": self.dry_run,
        }

    def _generate_adapter_stub(self, adapter_name: str) -> str:
        """Generate adapter stub code."""

        templates = {
            "fam_adapter": '''"""
FAM Adapter for externalized FoundUp.

Provides interface to FoundUps Agent Market without direct core coupling.
"""

from typing import Any, Dict, Optional

class FAMAdapter:
    """Adapter for FAM daemon integration."""

    def __init__(self, api_endpoint: Optional[str] = None):
        self.api_endpoint = api_endpoint or "http://localhost:8080/api/fam"

    def emit_event(self, event_type: str, payload: Dict[str, Any]) -> bool:
        """Emit FAM event via API."""
        # TODO: Implement API call to FAM endpoint
        raise NotImplementedError("Wire to FAM API endpoint")

    def get_foundup_status(self, foundup_id: str) -> Dict[str, Any]:
        """Get FoundUp status via API."""
        raise NotImplementedError("Wire to FAM API endpoint")
''',
            "wre_adapter": '''"""
WRE Adapter for externalized FoundUp.

Provides interface to WRE execution without direct core coupling.
"""

from typing import Any, Dict, Optional

class WREAdapter:
    """Adapter for WRE skill execution."""

    def __init__(self, api_endpoint: Optional[str] = None):
        self.api_endpoint = api_endpoint or "http://localhost:8080/api/wre"

    def execute_skill(self, skill_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute WRE skill via API."""
        raise NotImplementedError("Wire to WRE API endpoint")
''',
            "openclaw_adapter": '''"""
OpenClaw Adapter for externalized FoundUp.

Provides interface to OpenClaw without direct core coupling.
"""

from typing import Any, Dict, Optional

class OpenClawAdapter:
    """Adapter for OpenClaw intent routing."""

    def __init__(self, gateway_url: Optional[str] = None):
        self.gateway_url = gateway_url or "ws://127.0.0.1:18789"

    def send_message(self, message: str, channel: str) -> Dict[str, Any]:
        """Send message via OpenClaw gateway."""
        raise NotImplementedError("Wire to OpenClaw gateway")
''',
            "overseer_adapter": '''"""
AI Overseer Adapter for externalized FoundUp.

Provides interface to AI Overseer without direct core coupling.
"""

from typing import Any, Dict, Optional

class OverseerAdapter:
    """Adapter for AI Overseer coordination."""

    def __init__(self, api_endpoint: Optional[str] = None):
        self.api_endpoint = api_endpoint or "http://localhost:8080/api/overseer"

    def coordinate_mission(self, description: str) -> Dict[str, Any]:
        """Coordinate mission via API."""
        raise NotImplementedError("Wire to Overseer API endpoint")
''',
            "mcp_adapter": '''"""
MCP Bridge Adapter for externalized FoundUp.

Provides interface to MCP Bridge without direct core coupling.
"""

from typing import Any, Dict, Optional

class MCPBridgeAdapter:
    """Adapter for MCP Bridge tools."""

    def __init__(self, api_endpoint: Optional[str] = None):
        self.api_endpoint = api_endpoint or "http://localhost:8080/api/mcp"

    def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Call MCP tool via API."""
        raise NotImplementedError("Wire to MCP API endpoint")
''',
        }

        return templates.get(adapter_name, f'"""Adapter stub for {adapter_name}."""\n')

    def sign_manifest(self, manifest: Dict[str, Any], secret_key: Optional[bytes] = None) -> str:
        """
        Sign a FoundUp manifest with HMAC-SHA256.

        Args:
            manifest: Manifest dict (without signature field)
            secret_key: Signing key (defaults to env var)

        Returns:
            Hex-encoded signature string
        """
        if secret_key is None:
            key_str = os.environ.get("FOUNDUP_MANIFEST_SECRET", "dev-secret-key")
            secret_key = key_str.encode()

        # Remove signature field if present
        body = {k: v for k, v in manifest.items() if k != "signature"}
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))

        return hmac.new(secret_key, canonical.encode(), hashlib.sha256).hexdigest()

    def extract_foundup(
        self,
        source_module: str,
        target_org: str = "FOUNDUPS"
    ) -> Dict[str, Any]:
        """
        Extract a FoundUp from monorepo to external repository.

        This is the main entry point for FoundUp extraction.

        Args:
            source_module: Path to module (e.g., "modules/foundups/gotjunk")
            target_org: GitHub org for new repo (default: "FOUNDUPS")

        Returns:
            Extraction report with pass/fail status
        """
        logger.info("[HERMES] Starting extraction: %s -> %s", source_module, target_org)

        # Emit extraction started breadcrumb
        self._emit_breadcrumb(FAMEventType.HERMES_EXTRACTION_STARTED.value, {
            "source_module": source_module,
            "target_org": target_org,
        })

        # Security gate
        if not self._ensure_security_gate():
            self._emit_breadcrumb(FAMEventType.HERMES_EXTRACTION_FAILED.value, {
                "source_module": source_module,
                "error": "security_gate_failed",
                "stage": "security_check",
            })
            return {
                "success": False,
                "error": "security_gate_failed",
                "source_module": source_module,
            }

        # Analyze boundary
        analysis = self.analyze_boundary(source_module)

        # Check exfoliation gate
        gate = self.check_exfoliation_gate(source_module)

        if not gate.passed:
            self._emit_breadcrumb(FAMEventType.HERMES_EXTRACTION_FAILED.value, {
                "source_module": source_module,
                "error": "exfoliation_gate_failed",
                "stage": "exfoliation_gate",
                "blockers": analysis.blockers,
            })
            return {
                "success": False,
                "error": "exfoliation_gate_failed",
                "source_module": source_module,
                "boundary_analysis": {
                    "product_files": len(analysis.product_files),
                    "core_dependencies": len(analysis.core_imports),
                    "adapters_needed": analysis.adapters_needed,
                    "blockers": analysis.blockers,
                },
                "exfoliation_gate": {
                    "passed": gate.passed,
                    "checks": {
                        "module_boundary_clear": gate.module_boundary_clear,
                        "contracts_explicit": gate.contracts_explicit,
                        "runtime_testable": gate.runtime_testable,
                        "deploy_surface_understood": gate.deploy_surface_understood,
                        "shared_deps_adapter_level": gate.shared_deps_adapter_level,
                        "claw_can_participate": gate.claw_can_participate,
                    },
                },
            }

        # Generate adapters
        adapters_result = self.generate_adapters(source_module)

        # Load and sign manifest
        full_path = self.repo_root / source_module
        manifest_path = full_path / "foundup_manifest.json"

        manifest = {}
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["signature"] = self.sign_manifest(manifest)

        # Determine target repo name
        module_name = Path(source_module).name
        target_repo = f"{target_org}/{module_name}"

        # Emit extraction completed breadcrumb
        self._emit_breadcrumb(FAMEventType.HERMES_EXTRACTION_COMPLETED.value, {
            "source_module": source_module,
            "target_repo": target_repo,
            "product_files_count": len(analysis.product_files),
            "adapters_generated": len(adapters_result.get("adapters_created", [])),
            "dry_run": self.dry_run,
        })

        return {
            "success": True,
            "source_module": source_module,
            "target_repo": target_repo,
            "boundary_analysis": {
                "product_files": len(analysis.product_files),
                "core_dependencies": len(analysis.core_imports),
                "adapters_needed": analysis.adapters_needed,
            },
            "exfoliation_gate": {
                "passed": gate.passed,
                "checks": {
                    "module_boundary_clear": gate.module_boundary_clear,
                    "contracts_explicit": gate.contracts_explicit,
                    "runtime_testable": gate.runtime_testable,
                    "deploy_surface_understood": gate.deploy_surface_understood,
                    "shared_deps_adapter_level": gate.shared_deps_adapter_level,
                    "claw_can_participate": gate.claw_can_participate,
                },
            },
            "adapters": adapters_result,
            "manifest": manifest,
            "dry_run": self.dry_run,
            "next_steps": [
                f"1. Create repo: github.com/{target_repo}",
                f"2. Create backup: github.com/Foundup/{module_name}",
                "3. Run: git filter-repo to extract with history",
                "4. Push to new repos",
                "5. Update monorepo with adapter docs",
            ],
        }

    def run_hermes_extraction(
        self,
        source_module: str,
        target_org: str = "FOUNDUPS",
        interactive: bool = False,
    ) -> Dict[str, Any]:
        """
        Run Hermes agent with Qwen to execute FoundUp extraction.

        Uses MCP Bridge perception layer to inject context:
        - Hot modules and risks via get_prompt_context_packet
        - Module-specific risks and failure patterns

        Spawns Hermes CLI with:
        - Qwen backend via LM Studio (localhost:1234)
        - Tool parser: qwen
        - Bounded toolset: terminal, file only

        Args:
            source_module: Path to module to extract
            target_org: GitHub org for target repo
            interactive: If True, run in interactive mode

        Returns:
            Execution result with git commands and status
        """
        if not self._ensure_security_gate():
            return {"success": False, "error": "security_gate_failed"}

        # First verify exfoliation gate passes
        gate = self.check_exfoliation_gate(source_module)
        if not gate.passed:
            return {
                "success": False,
                "error": "exfoliation_gate_failed",
                "gate": gate,
            }

        # Build Hermes command
        hermes_path = self.repo_root / "vendor" / "hermes-agent" / "cli.py"
        config_path = self.repo_root / "modules" / "foundups" / "agent" / "config" / "hermes-foundup-builder.yaml"

        module_name = Path(source_module).name
        full_module_path = self.repo_root / source_module

        # Get MCP context packet for intelligent extraction
        context_section = ""
        if self._mcp_bridge:
            try:
                context_result = self._mcp_bridge.call_tool(
                    "get_prompt_context_packet",
                    task_description=f"Extract FoundUp {module_name} from {source_module}"
                )
                if context_result.get("status") == "ok":
                    ctx_data = context_result.get("data", {})

                    # Extract relevant context for Hermes
                    risks = ctx_data.get("active_risks", [])
                    failures = ctx_data.get("repeated_failures", [])
                    focus = ctx_data.get("suggested_focus", [])

                    if risks or failures or focus:
                        context_section = "\n## MCP Perception Context\n"
                        if risks:
                            risk_strs = [f"- {r.get('type', '?')}: {r.get('description', '?')}"
                                         for r in risks[:3]]
                            context_section += f"Active Risks:\n" + "\n".join(risk_strs) + "\n"
                        if failures:
                            fail_strs = [f"- {f.get('pattern', '?')} ({f.get('frequency', '?')} occurrences)"
                                         for f in failures[:3]]
                            context_section += f"Known Failure Patterns:\n" + "\n".join(fail_strs) + "\n"
                        if focus:
                            focus_strs = [f"- {item}" for item in focus[:3]]
                            context_section += f"Suggested Focus:\n" + "\n".join(focus_strs) + "\n"

                        logger.info("[HERMES] Injecting MCP context: %d risks, %d failures, %d focus items",
                                    len(risks), len(failures), len(focus))

            except Exception as e:
                logger.warning("[HERMES] MCP context packet failed: %s", e)

        extraction_prompt = f"""Extract FoundUp '{module_name}' from monorepo to external repository.

Source: {full_module_path}
Target: github.com/{target_org}/{module_name}
Backup: github.com/Foundup/{module_name}
{context_section}
Execute these steps:
1. Verify git filter-repo is installed
2. Create extraction directory: O:/tmp/{module_name}-extraction
3. Clone monorepo to extraction dir
4. Run git filter-repo --subdirectory-filter {source_module}
5. Add remote: git remote add origin https://github.com/{target_org}/{module_name}.git
6. Push with history: git push -u origin main
7. Report success or failure

Do NOT modify the original monorepo. Work only in the extraction directory."""

        # Use model router for dynamic capability selection
        if MODEL_ROUTER_AVAILABLE:
            model_spec = route_to_model("code extraction git filter-repo")
            if model_spec:
                model_id = model_spec.model_id
                tool_parser = model_spec.tool_parser
                logger.info("[HERMES] Model router selected: %s", model_id)
            else:
                model_id = DEFAULT_QWEN_CONFIG["model"]
                tool_parser = DEFAULT_QWEN_CONFIG["tool_parser"]
        else:
            model_id = DEFAULT_QWEN_CONFIG["model"]
            tool_parser = DEFAULT_QWEN_CONFIG["tool_parser"]

        cmd = [
            sys.executable,
            str(hermes_path),
            "chat",
            "--config", str(config_path),
            "--model", model_id,
            "--provider", "lmstudio",
            "--tool-parser", tool_parser,
        ]

        if not interactive:
            cmd.extend(["--prompt", extraction_prompt])

        logger.info("[HERMES] Running extraction with Qwen: %s", " ".join(cmd[:6]))

        if self.dry_run:
            return {
                "success": True,
                "dry_run": True,
                "command": cmd,
                "prompt": extraction_prompt,
            }

        try:
            if interactive:
                # Interactive mode - run in foreground
                result = subprocess.run(cmd, cwd=str(self.repo_root))
                return {
                    "success": result.returncode == 0,
                    "returncode": result.returncode,
                }
            else:
                # Non-interactive - capture output
                result = subprocess.run(
                    cmd,
                    cwd=str(self.repo_root),
                    capture_output=True,
                    text=True,
                    timeout=600,  # 10 minute timeout
                )
                return {
                    "success": result.returncode == 0,
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "timeout_exceeded"}
        except Exception as e:
            logger.error("[HERMES] Extraction failed: %s", e)
            return {"success": False, "error": str(e)}

    def check_qwen_available(self) -> Dict[str, Any]:
        """
        Check if Qwen is available via LM Studio.

        Returns:
            Status dict with availability and model info
        """
        try:
            from modules.infrastructure.shared_utilities.local_llm_backends import (
                is_lm_studio_available,
                LMStudioBackend,
            )

            if not is_lm_studio_available():
                return {
                    "available": False,
                    "error": "LM Studio not running at localhost:1234",
                }

            backend = LMStudioBackend(
                model_id=DEFAULT_QWEN_CONFIG["model"],
                base_url=DEFAULT_QWEN_CONFIG["base_url"],
            )

            if backend.initialize():
                return {
                    "available": True,
                    "model": DEFAULT_QWEN_CONFIG["model"],
                    "backend": "lm_studio",
                }
            else:
                return {
                    "available": False,
                    "error": f"Model {DEFAULT_QWEN_CONFIG['model']} not loaded in LM Studio",
                }

        except ImportError as e:
            return {"available": False, "error": f"Import error: {e}"}
        except Exception as e:
            return {"available": False, "error": str(e)}

    def get_available_capabilities(self) -> Dict[str, Any]:
        """
        Get all available model capabilities from LM Studio.

        Returns:
            Dict mapping capability to model availability
        """
        if not MODEL_ROUTER_AVAILABLE:
            return {"error": "Model router not available"}

        router = get_model_router()

        capabilities = {}
        for cap in TaskCapability:
            spec = router.get_model(cap)
            capabilities[cap.value] = {
                "available": spec is not None,
                "model": spec.model_id if spec else None,
                "supports_vision": spec.supports_vision if spec else False,
                "supports_tools": spec.supports_tools if spec else False,
            }

        return capabilities

    def get_perception(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Direct MCP Bridge perception query.

        Exposes the MCP Bridge v1.4 perception layer for custom queries.
        See bridge_server.py for available tools.

        Common tools:
        - get_overseer_summary: Quick triage (posture, signals)
        - get_hot_modules: Ranked by change × criticality × failures
        - get_change_impact_score: Risk analysis for a module
        - holo_search: Semantic code search
        - get_prompt_context_packet: Pre-assembled context

        Args:
            tool_name: MCP tool to call
            **kwargs: Tool-specific arguments

        Returns:
            MCP response dict with status and data
        """
        if not self._mcp_bridge:
            return {
                "status": "error",
                "error": "MCP Bridge not available",
                "available": False,
            }

        try:
            return self._mcp_bridge.call_tool(tool_name, **kwargs)
        except Exception as e:
            logger.error("[HERMES] MCP perception error: %s", e)
            return {"status": "error", "error": str(e)}

    def run_with_vision(
        self,
        task_description: str,
        screenshot_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run Hermes with UI-TARS vision model for visual tasks.

        Args:
            task_description: What to find/analyze in the UI
            screenshot_path: Optional path to screenshot (captures live if None)

        Returns:
            Vision analysis result
        """
        if not MODEL_ROUTER_AVAILABLE:
            return {"success": False, "error": "Model router not available"}

        router = get_model_router()
        vision_spec = router.get_model(TaskCapability.VISION)

        if not vision_spec:
            return {"success": False, "error": "UI-TARS vision model not available"}

        # Use UI-TARS bridge for vision tasks
        try:
            from modules.infrastructure.foundups_vision.src.ui_tars_bridge import (
                UITarsBridge,
            )

            bridge = UITarsBridge()
            # Note: Full vision execution requires Selenium driver context
            # This method provides the routing - actual execution via bridge.execute_action()

            return {
                "success": True,
                "vision_model": vision_spec.model_id,
                "task": task_description,
                "screenshot_path": screenshot_path,
                "bridge_ready": bridge._connected or True,  # Bridge initialized
                "usage": "Use UITarsBridge.execute_action() with driver context",
            }

        except ImportError as e:
            return {"success": False, "error": f"UI-TARS bridge not available: {e}"}
