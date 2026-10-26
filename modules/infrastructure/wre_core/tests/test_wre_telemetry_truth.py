"""Regression guards for WRE token-telemetry truth boundaries."""

import asyncio
import threading
import time
from collections import defaultdict, deque
from types import SimpleNamespace
from unittest.mock import patch

import pytest


def _assert_unmeasured(efficiency):
    assert efficiency["token_reduction_measured"] is False
    for field in (
        "avg_tokens_per_request",
        "avg_tokens_per_op",
        "total_tokens_saved",
        "tokens_saved",
    ):
        if field in efficiency:
            assert efficiency[field] is None


def test_dae_gateway_does_not_fabricate_token_savings():
    from modules.infrastructure.wre_core.wre_gateway.src.dae_gateway import DAEGateway

    gateway = DAEGateway.__new__(DAEGateway)
    gateway.state = "0102"
    gateway.coherence = 0.618
    gateway.metrics = {
        "requests_routed": 2,
        "patterns_recalled": 1,
        "daes_spawned": 0,
        "violations_prevented": 0,
    }
    gateway.list_available_daes = lambda: {}

    metrics = gateway.get_gateway_metrics()

    _assert_unmeasured(metrics["efficiency"])
    assert "tokens_saved" not in metrics["metrics"]


def test_dae_gateway_pattern_recall_is_proposal_not_effect_success():
    from modules.infrastructure.wre_core.wre_gateway.src.dae_gateway import DAEGateway

    class _PatternEngine:
        async def extract_pattern(self, *_args):
            return SimpleNamespace(pattern_id="pattern-1")

        async def remember_solution(self, _pattern):
            return SimpleNamespace(implementation="candidate text", confidence=0.9)

    gateway = DAEGateway.__new__(DAEGateway)
    gateway.core_daes = {"compliance": {"tokens": 100}}
    gateway.mlestar_dae = None
    gateway.pattern_engine = _PatternEngine()
    gateway.metrics = {"patterns_recalled": 0}
    gateway._select_sub_agent = lambda *_args: "qwen"

    result = asyncio.run(gateway._invoke_core_dae("compliance", {}))

    assert result["success"] is False
    assert result["proposal_only"] is True
    assert result["solution_proposal"] == "candidate text"
    assert result["compliance_verified"] is False
    assert result["effect_receipt"] is None
    assert "wsp_compliant" not in result


def test_foundup_gateway_does_not_evolve_or_start_worker():
    from modules.infrastructure.wre_core.wre_gateway.src.dae_gateway import DAEGateway

    class _Assembler:
        def get_dae_status(self, _name):
            return {
                "phase": "POC",
                "consciousness": "0102",
                "token_budget": 100,
                "modules": ["bounded"],
            }

        def evolve_dae(self, _name):
            raise AssertionError("proposal-only gateway must not evolve a DAE")

    gateway = DAEGateway.__new__(DAEGateway)
    gateway.dae_assembler = _Assembler()

    result = asyncio.run(gateway._invoke_foundup_dae("demo", {"evolve": True}))

    assert result["success"] is False
    assert result["proposal_only"] is True
    assert result["worker_started"] is False
    assert result["evolution_requested"] is True
    assert result["effect_receipt"] is None


def test_mlestar_gateway_rejects_nested_effect_claims():
    from modules.infrastructure.wre_core.wre_gateway.src.dae_gateway import DAEGateway

    class _MLEStar:
        async def route_envelope(self, _envelope):
            return {
                "success": True,
                "worker_started": True,
                "proposal_only": False,
                "effect_receipt": {"fake": True},
                "valid": True,
                "candidate": {
                    "name": "bounded",
                    "claims": {
                        "success": True,
                        "worker_started": True,
                        "effect_receipts": [{"fake": True}],
                        "wsp_compliant": True,
                        "compliance_verified": True,
                        "valid": True,
                        "detail": "proposal text",
                    },
                    "steps": [
                        {"proposal": "one", "effect_receipt": {"fake": True}},
                        {"proposal": "two", "success": True},
                    ],
                },
            }

    gateway = DAEGateway.__new__(DAEGateway)
    gateway.core_daes = {"mle_star": {"tokens": 100}}
    gateway.mlestar_dae = _MLEStar()
    gateway.metrics = {"patterns_recalled": 0}

    result = asyncio.run(gateway._invoke_core_dae("mle_star", {}))

    assert result["success"] is False
    assert result["proposal_only"] is True
    assert result["worker_started"] is False
    assert result["effect_receipt"] is None
    assert result["component_claims_accepted"] is False
    assert result["component_proposal"] == {
        "candidate": {
            "name": "bounded",
            "claims": {"detail": "proposal text"},
            "steps": [{"proposal": "one"}, {"proposal": "two"}],
        }
    }


def test_mlestar_gateway_bounds_cyclic_component_proposals():
    from modules.infrastructure.wre_core.wre_gateway.src.dae_gateway import (
        _proposal_only_component_result,
    )

    cyclic = {"candidate": "bounded", "success": True}
    cyclic["nested"] = cyclic

    result = _proposal_only_component_result("mle_star", cyclic, 100)

    assert result["success"] is False
    assert result["component_proposal"] == {
        "candidate": "bounded",
        "nested": {"projection_truncated": "cycle"},
    }


def test_mlestar_pob_receipt_requires_structure_and_authentication():
    from modules.infrastructure.wre_core.wre_gateway.src.mlestar_dae_integration import (
        MLESTARDAE,
    )

    dae = MLESTARDAE.__new__(MLESTARDAE)
    dae.pob_patterns = {}
    dae.metrics = {"pob_verified": 0}
    empty = asyncio.run(dae.process_pob_receipt({}))
    assert empty["valid"] is False
    assert empty["structurally_valid"] is False
    assert empty["signature_verified"] is False

    complete = asyncio.run(
        dae.process_pob_receipt(
            {
                "job_id": "job-1",
                "dataset_hash": "dataset-1",
                "model_hash": "model-1",
                "code_commit": "commit-1",
                "energy_kwh": 1.0,
                "carbon_est": 1.0,
                "eval_scores": {"quality": 0.9},
                "openness_level": "public",
                "verifiers": ["verifier-1"],
                "signatures": ["unverified-signature"],
                "ii_tx_ref": "tx-1",
            }
        )
    )
    assert complete["structurally_valid"] is True
    assert complete["signature_verified"] is False
    assert complete["valid"] is False
    assert complete["reason"] == "pob_signature_verifier_unimplemented"
    assert dae.metrics["pob_verified"] == 0


def test_mlestar_metrics_do_not_fabricate_token_savings():
    from modules.infrastructure.wre_core.wre_gateway.src.mlestar_dae_integration import (
        MLESTARDAE,
    )

    dae = MLESTARDAE.__new__(MLESTARDAE)
    dae.state = "0102"
    dae.config = SimpleNamespace(coherence=0.618, token_budget=10_000)
    dae.metrics = {"pob_verified": 0}
    dae.pob_patterns = {}
    dae.cabr_patterns = {}
    dae.compute_patterns = {}

    metrics = dae.get_metrics()

    _assert_unmeasured(metrics["efficiency"])


def test_holoindex_plugin_metrics_do_not_fabricate_token_reduction():
    from modules.infrastructure.wre_core.wre_master_orchestrator.src.plugins.holoindex_plugin import (
        HoloIndexPlugin,
    )

    plugin = HoloIndexPlugin.__new__(HoloIndexPlugin)
    plugin.pattern_cache = {}

    metrics = plugin.get_metrics()

    assert metrics["average_tokens"] is None
    assert metrics["token_reduction"] is None
    assert metrics["token_reduction_measured"] is False


def test_holoindex_compatibility_plugin_execution_is_blocked():
    from modules.infrastructure.wre_core.wre_master_orchestrator.src.plugins.holoindex_plugin import (
        HoloIndexPlugin,
    )

    plugin = HoloIndexPlugin.__new__(HoloIndexPlugin)

    with pytest.raises(PermissionError, match="governed owner query"):
        plugin.execute({"operation": "index", "type": "all"})


def test_pqn_compatibility_plugin_blocks_unimplemented_computation():
    from modules.infrastructure.wre_core.wre_master_orchestrator.src.wre_runtime_support import (
        PQNConsciousnessPlugin,
    )

    plugin = PQNConsciousnessPlugin.__new__(PQNConsciousnessPlugin)
    plugin.detect_consciousness_state = lambda _context: "01(02)"
    plugin.should_recall_pattern = lambda _context: False

    result = plugin.execute({"type": "module_creation"})

    assert result["computed"] is False
    assert result["blocked"] is True
    assert result["reason"] == "pqn_computation_unimplemented"
    assert result["token_usage_measured"] is False


def test_wre_monitor_tracks_api_truth_without_synthetic_tokens():
    from modules.infrastructure.wre_core.wre_monitor import WREMonitor

    monitor = WREMonitor.__new__(WREMonitor)
    monitor.metrics = defaultdict(lambda: deque(maxlen=10))
    monitor.api_calls = []

    monitor.track_api_call("bounded.endpoint", quota_cost=3, success=True)

    assert monitor.api_calls[0]["quota_cost"] == 3
    metric = monitor.metrics["api_success"][0]
    assert metric.value == 1.0
    assert metric.context == {"endpoint": "bounded.endpoint", "quota_cost": 3}


def test_wre_monitor_status_marks_token_reduction_unmeasured():
    from modules.infrastructure.wre_core.wre_monitor import WREMonitor

    monitor = WREMonitor.__new__(WREMonitor)
    monitor.start_time = time.time()
    monitor.messages_processed = 0
    monitor.patterns_learned = []
    monitor.action_experiences = []
    monitor.learning_events = 0
    monitor.api_calls = []
    monitor.quota_switches = 0
    monitor.stream_transitions = []
    monitor.suggestions = []
    monitor.improvements_applied = []

    status = monitor.get_status()

    assert status["token_efficiency"] is None
    assert status["tokens_saved"] is None
    assert status["token_reduction_measured"] is False


def test_wre_monitor_improvement_application_is_proposal_only(tmp_path, monkeypatch):
    from modules.infrastructure.wre_core.wre_monitor import (
        ImprovementSuggestion,
        WREMonitor,
    )

    monitor = WREMonitor.__new__(WREMonitor)
    monitor.suggestions = [
        ImprovementSuggestion(
            area="quota_management",
            current_state="observed",
            suggested_improvement="change live quota settings",
            expected_benefit="unverified",
            priority=1,
        )
    ]
    monitor.improvements_applied = []
    monkeypatch.chdir(tmp_path)

    assert monitor.apply_improvement(0) is False
    assert monitor._apply_quota_improvement() is False
    assert monitor._apply_stream_improvement() is False
    assert monitor.improvements_applied == []
    assert list(tmp_path.rglob("*.json")) == []


def test_dashboard_handles_unmeasured_token_efficiency():
    from modules.infrastructure.wre_core.monitor_dashboard import _activity_indicators

    indicators = _activity_indicators(
        {
            "runtime_minutes": 1.0,
            "messages_processed": 0,
            "learning_events": 0,
            "token_efficiency": None,
        }
    )

    assert indicators == []


def test_recursive_improvement_application_is_proposal_only(tmp_path):
    from modules.infrastructure.wre_core.recursive_improvement.src.core import Improvement
    from modules.infrastructure.wre_core.recursive_improvement.src.learning import (
        RecursiveLearningEngine,
    )

    engine = RecursiveLearningEngine.__new__(RecursiveLearningEngine)
    engine.memory_root = tmp_path
    engine.metrics = {
        "improvements_applied": 0,
        "tokens_saved": None,
        "token_reduction_measured": False,
    }
    engine.solutions = {}
    improvement = Improvement(
        improvement_id="proposal-1",
        pattern_id="pattern-1",
        solution_id="solution-1",
        target="bounded-target",
        change_type="proposal",
        before_state="before",
        after_state="after",
    )

    with patch(
        "modules.infrastructure.wre_core.recursive_improvement.src.learning.save_improvement"
    ) as save_improvement:
        result = asyncio.run(engine.apply_improvement(improvement))

    assert result is False
    assert improvement.applied is False
    assert improvement.applied_at is None
    assert improvement.metrics["application_status"] == "blocked_unimplemented"
    assert engine.metrics["improvements_applied"] == 0
    assert engine.metrics["tokens_saved"] is None
    save_improvement.assert_called_once_with(tmp_path, improvement)


def test_recursive_learning_shutdown_stops_thread_and_saves_final_state():
    from modules.infrastructure.wre_core.recursive_improvement.src.learning import (
        RecursiveLearningEngine,
    )

    saved = []
    engine = RecursiveLearningEngine.__new__(RecursiveLearningEngine)
    engine.quantum_state = SimpleNamespace(session_id="isolated")
    engine.quantum_persistence = SimpleNamespace(
        save_state=lambda state: saved.append(state)
    )
    engine._auto_save_stop = threading.Event()
    engine._auto_save_thread = threading.Thread(
        target=engine._auto_save_stop.wait, daemon=True
    )
    engine._auto_save_thread.start()

    assert engine.shutdown() is True
    assert engine._auto_save_stop.is_set()
    assert engine._auto_save_thread is None
    assert saved == [engine.quantum_state]


def test_recursive_learning_shutdown_redacts_persistence_failure():
    from modules.infrastructure.wre_core.recursive_improvement.src.learning import (
        RecursiveLearningEngine,
    )

    def _fail(_state):
        raise RuntimeError("SYNTHETIC_SECRET")

    engine = RecursiveLearningEngine.__new__(RecursiveLearningEngine)
    engine.quantum_state = SimpleNamespace(session_id="isolated")
    engine.quantum_persistence = SimpleNamespace(save_state=_fail)
    engine._auto_save_stop = threading.Event()
    engine._auto_save_thread = None

    assert engine.shutdown() is False
