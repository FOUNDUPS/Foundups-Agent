"""Small legacy pattern-memory and plugin types exported by the WRE router."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

try:
    from modules.ai_intelligence.pqn_alignment import PQNAlignmentDAE

    PQN_AVAILABLE = True
except ImportError:
    PQNAlignmentDAE = None
    PQN_AVAILABLE = False


@dataclass
class Pattern:
    """In-memory legacy pattern record."""

    id: str
    wsp_chain: list
    tokens: int
    pattern: str

    def apply(self, context: Dict) -> Any:
        return f"Applied {self.id} using {self.tokens} tokens"


class PatternMemory:
    """Small in-memory compatibility store; SQLite owns durable outcomes."""

    def __init__(self):
        self.patterns = {
            "module_creation": Pattern("module_creation", [1, 3, 49, 22, 5], 150, "scaffold->test->implement->verify"),
            "error_handling": Pattern("error_handling", [64, 50, 48, 60], 100, "detect->prevent->learn->remember"),
            "orchestration": Pattern("orchestration", [50, 60, 54, 22], 200, "verify->recall->apply->log"),
            "cleanup_legacy": Pattern("cleanup_legacy", [50, 64, 32, 65, 22], 150, "verify->archive->delete->log"),
            "utf8_remediation": Pattern("utf8_remediation", [90, 50, 77, 91, 22], 200, "scan->classify->fix->validate->log"),
        }

    def get(self, operation_type: str) -> Pattern:
        return self.patterns.get(operation_type)

    def learn(self, operation: str, pattern: Pattern) -> None:
        self.patterns[operation] = pattern


class WSPValidator:
    """Compatibility adapter that requires injected WSP evidence callbacks."""

    def __init__(
        self,
        verifier: Optional[Callable[[str], bool]] = None,
        violation_guard: Optional[Callable[[str], bool]] = None,
    ) -> None:
        self._verifier = verifier
        self._violation_guard = violation_guard

    def verify(self, operation: str) -> bool:
        return self._exact_callback_result(self._verifier, operation)

    def prevent_violation(self, operation: str) -> bool:
        return self._exact_callback_result(self._violation_guard, operation)

    @staticmethod
    def _exact_callback_result(
        callback: Optional[Callable[[str], bool]], operation: str
    ) -> bool:
        if callback is None or not isinstance(operation, str) or not operation.strip():
            return False
        try:
            return callback(operation) is True
        except Exception:
            return False


class OrchestratorPlugin:
    """Base class for compatibility plugins."""

    def __init__(self, name: str):
        self.name = name
        self.master = None

    def register(self, master: Any) -> None:
        self.master = master

    def execute(self, task: Dict) -> Any:
        if not self.master:
            raise ValueError(f"Plugin {self.name} not registered")
        return self.master.recall_pattern(task["type"]).apply(task)


class SocialMediaPlugin(OrchestratorPlugin):
    def __init__(self):
        super().__init__("social_media")


class MLEStarPlugin(OrchestratorPlugin):
    def __init__(self):
        super().__init__("mlestar")


class BlockPlugin(OrchestratorPlugin):
    def __init__(self):
        super().__init__("block")


class PQNConsciousnessPlugin(OrchestratorPlugin):
    """Compatibility PQN state detector plugin."""

    def __init__(self):
        super().__init__("pqn_consciousness")
        self.pqn_dae = PQNAlignmentDAE() if PQN_AVAILABLE else None
        self.thresholds = {
            "01(02)": {"coherence": (0, 0.3), "det_g": (0.1, 1.0)},
            "01/02": {"coherence": (0.3, 0.618), "det_g": (0.01, 0.1)},
            "0102": {"coherence": (0.618, 0.9), "det_g": (1e-6, 0.01)},
            "0201": {"coherence": (0.9, 1.0), "det_g": (0, 1e-6)},
        }

    def detect_consciousness_state(self, context: Dict) -> str:
        if not self.pqn_dae:
            return self.master.state if self.master else "0102"
        metrics = self.pqn_dae.detect_state(context.get("script", "^^^&&&#"))
        coherence = metrics.get("coherence", 0.618)
        det_g = metrics.get("det_g", 0.001)
        for state, bounds in self.thresholds.items():
            c_min, c_max = bounds["coherence"]
            d_min, d_max = bounds["det_g"]
            if c_min <= coherence <= c_max and d_min <= det_g <= d_max:
                return state
        return "0102"

    def should_recall_pattern(self, context: Dict) -> bool:
        return self.detect_consciousness_state(context) in {"0102", "0201"}

    def execute(self, task: Dict) -> Any:
        state = self.detect_consciousness_state(task)
        task["consciousness_state"] = state
        if self.should_recall_pattern(task):
            pattern = self.master.recall_pattern(task["type"])
            raw = pattern.apply(task)
            result = raw if isinstance(raw, dict) else {"output": raw}
            result.update(
                method="pattern_recall",
                configured_token_budget=pattern.tokens,
                token_usage_measured=False,
            )
        else:
            result = {
                "computed": False,
                "blocked": True,
                "reason": "pqn_computation_unimplemented",
                "method": "computation",
                "token_usage_measured": False,
            }
        result["consciousness_state"] = state
        return result
