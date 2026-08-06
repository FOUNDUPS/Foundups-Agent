"""Pre-publication exact-schema regressions for architect FIX promotion."""

from __future__ import annotations

from modules.communication.moltbot_bridge.src import (
    reddog_architect_fix_signed_wsp15_work_order_promotion as promotion,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_refresh_runtime import (
    InMemoryAuthoritativeWorkStateStore,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_fix_signed_wsp15_work_order_promotion import (
    _model_selection,
    _promote,
    _runtime_binding,
    _work_state,
)


def _publisher_probe(store: InMemoryAuthoritativeWorkStateStore):
    calls = []

    def publish(request):
        calls.append(request)
        return store.commit(
            request.updated_work_state,
            expected_revision=request.expected_work_state_revision,
        )

    return calls, publish


def test_nested_model_selection_injection_rejects_before_publication() -> None:
    selection = _model_selection()
    selection["requirements"]["attacker_extra"] = "shadow-authority"
    store = InMemoryAuthoritativeWorkStateStore(_work_state())
    before = store.load()
    calls, publish = _publisher_probe(store)

    result, _ = _promote(
        store=store,
        model_selection_receipt=selection,
        authority_profile_publication_publisher=publish,
    )

    assert result.accepted is False
    assert promotion.ArchitectFixPromotionReason.MODEL_SELECTION_INVALID in (
        result.rejection_reasons
    )
    assert calls == []
    assert store.load() == before


def test_nested_runtime_binding_injection_rejects_before_publication() -> None:
    selection = _model_selection()
    binding = _runtime_binding(selection)
    binding["policy"]["attacker_extra"] = "shadow-authority"
    store = InMemoryAuthoritativeWorkStateStore(_work_state())
    before = store.load()
    calls, publish = _publisher_probe(store)

    result, _ = _promote(
        store=store,
        model_selection_receipt=selection,
        model_runtime_binding_receipt=binding,
        authority_profile_publication_publisher=publish,
    )

    assert result.accepted is False
    assert promotion.ArchitectFixPromotionReason.MODEL_RUNTIME_BINDING_INVALID in (
        result.rejection_reasons
    )
    assert calls == []
    assert store.load() == before
