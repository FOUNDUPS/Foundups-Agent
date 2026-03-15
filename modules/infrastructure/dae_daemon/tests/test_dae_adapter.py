from types import SimpleNamespace

from modules.infrastructure.dae_daemon.src.dae_adapter import CentralDAEAdapter
from modules.infrastructure.dae_daemon.src.schemas import DAEEventType


class _FakeRegistry:
    def __init__(self):
        self.calls = []

    def report_event(self, dae_id, event_type, payload):
        self.calls.append((dae_id, event_type, payload))


def test_report_action_preserves_structured_details():
    adapter = CentralDAEAdapter("openclaw", "OpenClaw", "communication")
    fake_registry = _FakeRegistry()
    adapter._daemon = SimpleNamespace(registry=fake_registry)

    adapter.report_action(
        "research_simulation",
        target="pqn_theory_archive",
        result="completed",
        details={"outcome": "probe_advantage_requires_followup", "run_count": 6},
    )

    assert len(fake_registry.calls) == 1
    dae_id, event_type, payload = fake_registry.calls[0]
    assert dae_id == "openclaw"
    assert event_type == DAEEventType.ACTION_PERFORMED
    assert payload["action_type"] == "research_simulation"
    assert payload["target"] == "pqn_theory_archive"
    assert payload["result"] == "completed"
    assert payload["details"]["run_count"] == 6


def test_report_action_noops_without_daemon():
    adapter = CentralDAEAdapter("openclaw", "OpenClaw", "communication")

    adapter.report_action("intent_classified", target="research", result="ok")
