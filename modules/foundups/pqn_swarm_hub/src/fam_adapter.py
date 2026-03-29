"""
PQN Swarm Hub - FAM Adapter

Adapter layer for FAMDaemon integration.
Phase 1: Contribution event emission through adapter boundary.

HARD BOUNDARY (per directive):
- Allowed: emit_contribution_event(ContributionRecord)
- NOT allowed: direct mutation of FAM event store
- NOT allowed: direct access to core control-plane modules

WSP 72: Module independence
WSP 91: Observability — contribution events are audit-safe
"""

from dataclasses import asdict
from typing import Any, Callable, Dict, Optional, Tuple

from .contracts import ContributionRecord, VerificationDecision


# Type alias for event emission function
EventEmitter = Callable[[str, Dict[str, Any], str, Optional[str], Optional[str]], Tuple[bool, str]]


class FAMAdapterError(Exception):
    """Raised when FAM adapter operation fails."""
    pass


class FAMAdapter:
    """
    Adapter for FAMDaemon integration.

    Routes PQN Swarm Hub events to FAMDaemon through stable interface.
    Does NOT access FAM internals directly.

    Phase 1: Lazy connection to FAMDaemon singleton.
    Proto+: Stable adapter interface for exfoliated repo.
    """

    def __init__(
        self,
        auto_connect: bool = False,
        fam_module_path: str = "modules.foundups.agent_market.src.fam_daemon",
    ) -> None:
        self._fam_daemon = None
        self._connected = False
        self._fam_module_path = fam_module_path
        self._emit_fn: Optional[EventEmitter] = None

        if auto_connect:
            self.connect()

    def connect(self) -> bool:
        """
        Lazily connect to FAMDaemon singleton.

        Returns True if connection successful, False otherwise.
        Does not raise — caller decides how to handle failure.
        """
        if self._connected:
            return True

        try:
            from modules.foundups.agent_market.src.fam_daemon import get_fam_daemon
            self._fam_daemon = get_fam_daemon(auto_start=False)
            self._emit_fn = self._fam_daemon.emit
            self._connected = True
            return True
        except ImportError:
            # FAMDaemon not available — stub mode
            self._connected = False
            return False
        except Exception:
            self._connected = False
            return False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def emit_contribution_event(
        self,
        contribution: ContributionRecord,
        actor_id: str = "pqn_swarm_hub",
    ) -> Tuple[bool, str]:
        """
        Emit contribution event to FAMDaemon.

        This is the ONLY allowed emission point per adapter boundary.

        Args:
            contribution: ContributionRecord from contribution reporter
            actor_id: Actor emitting the event (default: pqn_swarm_hub)

        Returns:
            (success, message) tuple
        """
        if not self._connected:
            if not self.connect():
                # Stub mode — log locally but don't fail
                return self._stub_emit(contribution, actor_id)

        payload = {
            "contribution_id": contribution.contribution_id,
            "work_unit_id": contribution.work_unit_id,
            "submission_id": contribution.submission_id,
            "decision_id": contribution.decision_id,
            "contributor_id": contribution.contributor_id,
            "score": contribution.score,
            "recorded_at": contribution.recorded_at.isoformat(),
            "source": "pqn_swarm_hub",
        }

        try:
            # Use FAMDaemon's emit interface
            # Event type: pqn_contribution_recorded (new event type for PQN)
            success, msg = self._emit_fn(
                event_type="pqn_contribution_recorded",
                payload=payload,
                actor_id=actor_id,
                foundup_id=None,  # PQN Swarm Hub is cross-FoundUp
                task_id=contribution.work_unit_id,  # Map work_unit to task_id
            )
            return success, msg
        except Exception as e:
            return False, f"FAM emission failed: {e}"

    def emit_verification_event(
        self,
        decision: VerificationDecision,
        work_unit_id: str,
        actor_id: str = "pqn_swarm_hub",
    ) -> Tuple[bool, str]:
        """
        Emit verification event to FAMDaemon.

        Secondary emission point for verification audit trail.

        Args:
            decision: VerificationDecision from verification engine
            work_unit_id: Associated work unit ID
            actor_id: Actor emitting the event

        Returns:
            (success, message) tuple
        """
        if not self._connected:
            if not self.connect():
                return self._stub_emit_verification(decision, work_unit_id, actor_id)

        payload = {
            "decision_id": decision.decision_id,
            "submission_id": decision.submission_id,
            "work_unit_id": work_unit_id,
            "decision": decision.decision,
            "verifier_id": decision.verifier_id,
            "rationale": decision.rationale,
            "decided_at": decision.decided_at.isoformat(),
            "source": "pqn_swarm_hub",
        }

        try:
            success, msg = self._emit_fn(
                event_type="pqn_verification_recorded",
                payload=payload,
                actor_id=actor_id,
                foundup_id=None,
                task_id=work_unit_id,
            )
            return success, msg
        except Exception as e:
            return False, f"FAM emission failed: {e}"

    def _stub_emit(
        self,
        contribution: ContributionRecord,
        actor_id: str,
    ) -> Tuple[bool, str]:
        """
        Stub emission when FAMDaemon is not available.

        Phase 1: Returns success with stub message.
        Allows PQN Swarm Hub to function without FAMDaemon dependency.
        """
        return True, f"STUB: contribution {contribution.contribution_id} logged locally (FAM not connected)"

    def _stub_emit_verification(
        self,
        decision: VerificationDecision,
        work_unit_id: str,
        actor_id: str,
    ) -> Tuple[bool, str]:
        """Stub emission for verification events."""
        return True, f"STUB: verification {decision.decision_id} logged locally (FAM not connected)"

    def get_status(self) -> Dict[str, Any]:
        """Return adapter connection status."""
        return {
            "connected": self._connected,
            "fam_module_path": self._fam_module_path,
            "daemon_running": self._fam_daemon.get_status().get("running", False) if self._fam_daemon else False,
        }


# Singleton instance for module-level access
_adapter_instance: Optional[FAMAdapter] = None


def get_fam_adapter(auto_connect: bool = False) -> FAMAdapter:
    """
    Get singleton FAMAdapter instance.

    Args:
        auto_connect: If True, attempt connection on first access

    Returns:
        FAMAdapter singleton
    """
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = FAMAdapter(auto_connect=auto_connect)
    return _adapter_instance
