"""Pre-publication exact-schema regressions for architect FIX promotion."""

from __future__ import annotations

from copy import deepcopy
from unittest.mock import Mock

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_architect_fix_signed_wsp15_work_order_promotion as promotion,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_refresh_runtime import (
    InMemoryAuthoritativeWorkStateStore,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_fix_signed_wsp15_work_order_promotion import (
    _authority_profile,
    _determination,
    _memex_supply,
    _model_selection,
    _promote,
    _runtime_binding,
    _work_state,
    NOW_EPOCH,
)
from modules.communication.moltbot_bridge.tests.test_reddog_authority_profile_seed_supply import (
    _plan_bound_determination,
)
from modules.communication.moltbot_bridge.tests.architect_proposal_promotion_test_helpers import (
    build_proposal_runtime_inputs,
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


def _plan_profile(determination, **overrides):
    admission = determination["proposal_admission"]
    return _authority_profile(
        requested_operation=admission["requested_operation"],
        bounded_worker_plan=deepcopy(admission["bounded_worker_plan"]),
        **overrides,
    )


def _direct_promotion(determination, profile, store):
    return promotion.promote_reddog_architect_fix_to_signed_wsp15_work_order(
        architect_determination=determination, authority_profile=profile,
        work_state_store=store, model_selection_receipt={}, memex_supply_receipt={},
        proposal_authenticity_attestation={}, signer_runtime_config=None,
        principal_key_resolver=None, worker_id="fixture", now_iso="2026-07-16T00:00:00Z",
    )


@pytest.mark.parametrize("kind", ("omitted", "null", "empty", "action", "bool_int", "int_float"))
def test_profile_proposal_plan_mismatch_rejects_before_store_load(kind):
    determination = _plan_bound_determination()
    profile = _plan_profile(determination)
    plan = profile["bounded_worker_plan"]
    if kind == "omitted":
        del profile["bounded_worker_plan"]
    elif kind in {"null", "empty"}:
        profile["bounded_worker_plan"] = None if kind == "null" else {}
    elif kind == "action":
        plan["m2m_envelope"]["A"] = "Different task"
    else:
        plan["m2m_envelope"]["I"]["fixture"][0 if kind == "bool_int" else 1] = (
            1 if kind == "bool_int" else 1.0
        )
    store = Mock()
    store.load.side_effect = AssertionError("store read before plan agreement")
    result = _direct_promotion(determination, profile, store)
    assert result.accepted is False
    assert any(reason.startswith(promotion.ArchitectFixPromotionReason.AUTHORITY_PROFILE_INCOMPLETE)
               for reason in result.rejection_reasons)
    store.load.assert_not_called()


@pytest.mark.parametrize("kind", ("empty", "m2m"))
@pytest.mark.parametrize("wrapper", ("raw", "receipt", "empty", "null", "nested"))
def test_matching_profile_plan_preserves_single_receipt_selection(kind, wrapper):
    determination = _plan_bound_determination({} if kind == "empty" else None)
    profile = _plan_profile(determination)
    if wrapper == "nested":
        determination["receipt"] = {"unselected": True}
    elif wrapper in {"empty", "null"}:
        determination["receipt"] = {} if wrapper == "empty" else None
    attestation, config, resolver = build_proposal_runtime_inputs(
        determination, profile, _memex_supply(), now_epoch=NOW_EPOCH,
    )
    if wrapper in {"receipt", "nested"}:
        determination = {"receipt": determination}
    result, _ = _promote(
        architect_determination=determination, authority_profile=profile,
        proposal_authenticity_attestation=attestation,
        signer_runtime_config=config, principal_key_resolver=resolver,
    )
    assert result.accepted is True, result.rejection_reasons
    projected = result.authority_profile
    expected = profile["bounded_worker_plan"]
    assert projected["bounded_worker_plan"] == expected
    assert projected["proposal_admission"]["bounded_worker_plan"] == expected
    assert projected["operational_context_binding"]["proposal_admission"]["bounded_worker_plan"] == expected


@pytest.mark.parametrize("field,value", (
    ("requested_operation", "feature_slice"),
    ("allowed_paths", ["unrelated/**"]),
    ("denied_paths", ["modules/**"]),
    ("required_tests", ["different test"]),
    ("required_policy_gates", ["different gate"]),
))
def test_profile_plan_declared_scope_rejects_before_store_load(field, value):
    determination = _plan_bound_determination()
    admission = determination["proposal_admission"]
    plan = deepcopy(admission["bounded_worker_plan"])
    plan["m2m_envelope"]["I"][field] = deepcopy(admission[field])
    determination = _plan_bound_determination(plan)
    profile = _plan_profile(determination)
    profile[field] = value
    store = Mock()
    store.load.side_effect = AssertionError("store read before scope agreement")
    result = _direct_promotion(determination, profile, store)
    assert result.accepted is False
    assert (promotion.ArchitectFixPromotionReason.AUTHORITY_PROFILE_INCOMPLETE
            + ":proposal_plan_binding") in result.rejection_reasons
    store.load.assert_not_called()


@pytest.mark.parametrize("part", ("receipt_id", "candidate_id", "stage_digest", "cycle", "non_json"))
def test_profile_plan_lineage_rejects_before_store_load(part):
    determination = _plan_bound_determination()
    profile = _plan_profile(determination)
    if part == "receipt_id":
        determination["proposal_admission"]["receipt_id"] = "sha256:" + "0" * 64
    elif part == "candidate_id":
        determination["queue_candidate"]["queue_candidate_id"] = "sha256:" + "0" * 64
    elif part == "stage_digest":
        determination["queue_candidate"]["progressive_policy_stage_digest"] = "sha256:" + "0" * 64
    elif part == "cycle":
        determination["cycle"] = determination
    else:
        determination["non_json"] = object()
    store = Mock()
    store.load.side_effect = AssertionError("store read before lineage rejection")
    result = _direct_promotion(determination, profile, store)
    assert result.accepted is False
    store.load.assert_not_called()


@pytest.mark.parametrize("with_plan", (False, True))
def test_promotion_snapshots_presence_and_inputs_before_store_callback(with_plan):
    determination = _plan_bound_determination() if with_plan else _determination()
    profile = _plan_profile(determination) if with_plan else _authority_profile()
    expected_plan = deepcopy(profile.get("bounded_worker_plan"))
    store = InMemoryAuthoritativeWorkStateStore(_work_state())
    original_load = store.load

    def mutate_then_load():
        if with_plan:
            profile["bounded_worker_plan"]["m2m_envelope"]["A"] = "Callback substitution"
        else:
            determination.clear()
            determination.update(_plan_bound_determination())
        return original_load()

    store.load = mutate_then_load
    result, _ = _promote(
        store=store, architect_determination=determination, authority_profile=profile,
    )
    assert result.accepted is True, result.rejection_reasons
    assert result.authority_profile.get("bounded_worker_plan") == expected_plan
    assert ("bounded_worker_plan" in result.authority_profile["proposal_admission"]) is with_plan


class _HiddenMapping(dict):
    def get(self, key, default=None):
        return default

    def __contains__(self, key):
        return False


@pytest.mark.parametrize("part", ("plan", "packet", "invariants", "nested"))
def test_plan_codec_rejects_nonplain_mapping_before_generic_walkers(part):
    determination = _plan_bound_determination()
    profile = _plan_profile(determination)
    events = []

    class Unwalkable(_HiddenMapping):
        def items(self):
            events.append("overridden_items")
            raise RuntimeError("malformed mapping traversed")

    plan = profile["bounded_worker_plan"]
    packet = plan["m2m_envelope"]
    if part == "plan":
        profile["bounded_worker_plan"] = Unwalkable(plan)
    elif part == "packet":
        plan["m2m_envelope"] = Unwalkable(packet)
    elif part == "invariants":
        packet["I"] = Unwalkable(packet["I"])
    else:
        packet["I"]["nested"] = Unwalkable(value=True)
    store = Mock()
    store.load.side_effect = AssertionError("store read before type rejection")
    result = _direct_promotion(determination, profile, store)
    assert result.accepted is False
    assert events == []
    store.load.assert_not_called()


@pytest.mark.parametrize("part", ("outer", "wrapped", "admission", "profile", "plan"))
def test_promotion_rejects_mapping_subclass_before_presence_checks(part):
    determination = _plan_bound_determination()
    profile = _plan_profile(determination)
    if part == "outer":
        determination = _HiddenMapping(determination)
    elif part == "wrapped":
        determination = {"receipt": _HiddenMapping(determination)}
    elif part == "admission":
        determination["proposal_admission"] = _HiddenMapping(determination["proposal_admission"])
    elif part == "profile":
        profile = _HiddenMapping(profile)
    else:
        profile["bounded_worker_plan"] = _HiddenMapping(profile["bounded_worker_plan"])
    store = Mock()
    store.load.side_effect = AssertionError("store read before type rejection")
    result = _direct_promotion(determination, profile, store)
    assert result.accepted is False
    store.load.assert_not_called()


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


def test_authority_profile_type_confusion_rejects_before_publication() -> None:
    profile = _authority_profile()
    profile["allowed_paths"] = {"attacker_extra": "value"}
    store = InMemoryAuthoritativeWorkStateStore(_work_state())
    before = store.load()
    calls, publish = _publisher_probe(store)

    result, _ = _promote(
        store=store,
        authority_profile=profile,
        authority_profile_publication_publisher=publish,
    )

    assert result.accepted is False
    assert (
        promotion.ArchitectFixPromotionReason.AUTHORITY_PROFILE_INCOMPLETE
        + ":typed_rehydration"
    ) in result.rejection_reasons
    assert calls == []
    assert store.load() == before
