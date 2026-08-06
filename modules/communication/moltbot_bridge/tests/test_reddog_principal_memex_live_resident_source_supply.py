"""Tests for live one-call Principal Memex source supply."""

from __future__ import annotations

import copy
import pickle
from pathlib import Path

import pytest

from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_digest import (
    canonical_model_runtime_binding_digest,
)
from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    InMemoryAuthorityRuntimeStore,
)
from modules.communication.moltbot_bridge.src.reddog_principal_memex_live_resident_source_supply import (
    DeferredPrincipalMemexResidentSource,
    consume_principal_memex_live_resident_source,
    defer_principal_memex_live_resident_source,
    issue_principal_memex_session_authorization,
    parse_principal_memex_live_resident_source_supply,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_capability import (
    split_conversation_scope_capability,
)
from modules.communication.moltbot_bridge.src.reddog_principal_memex_resident_admission import (
    consume_authenticated_principal_memex_context,
)
from modules.communication.moltbot_bridge.tests.model_runtime_binding_receipt_test_helpers import (
    model_runtime_binding_receipt,
)
from modules.communication.moltbot_bridge.tests.reddog_conversation_scope_signing_test_support import (
    NOW,
    REPO,
    Resolver,
    capability,
    store,
)
from modules.communication.moltbot_bridge.tests.test_reddog_principal_memex_resident_admission import (
    ARTIFACT_GENERATION_DIGEST,
    GENERATION_MANIFEST_ID,
    GROUNDING_RECEIPT_ID,
    INTENT_ID,
    RESIDENT_CYCLE_ID,
    SESSION_BINDING_DIGEST,
    _disclosure,
    _principal_scope,
)


def _input(serialized: str, conversation_id: str, revision: int = 0) -> dict:
    return {
        "serialized_disclosure": serialized,
        "conversation_id": conversation_id,
        "expected_conversation_revision": revision,
    }


def _authorization(
    serialized_session, signing_context, tmp_path: Path, *,
    intent_id: str = INTENT_ID, grounding_receipt_id: str = GROUNDING_RECEIPT_ID,
):
    children = split_conversation_scope_capability(
        capability(signing_context, serialized_session)
    )
    assert children is not None
    return issue_principal_memex_session_authorization(
        capability=children[1],
        principal_resolver=Resolver(),
        repo_full_name=REPO,
        intent_id=intent_id,
        grounding_receipt_id=grounding_receipt_id,
        session_binding_digest=SESSION_BINDING_DIGEST,
        generation_manifest_id=GENERATION_MANIFEST_ID,
        artifact_generation_digest=ARTIFACT_GENERATION_DIGEST,
        runtime_root=tmp_path,
    )


def _prepared_live_source(
    tmp_path: Path, *, intent_id: str = INTENT_ID,
    grounding_receipt_id: str = GROUNDING_RECEIPT_ID,
    now_epoch=lambda: NOW, binding=None, consume: bool = True,
):
    path = tmp_path / "principal-live.sqlite"
    serialized_session, signing_context, record, decision = _principal_scope(path)
    binding = binding or model_runtime_binding_receipt(
        runtime_surface="reddog_backend_architect"
    )
    binding_digest = canonical_model_runtime_binding_digest(binding)
    serialized_disclosure = _disclosure(
        record,
        decision,
        model_runtime_binding_receipt_id=binding["receipt_id"],
        model_runtime_binding_digest=binding_digest,
        intent_id=intent_id,
        grounding_receipt_id=grounding_receipt_id,
    )
    supply, reasons = parse_principal_memex_live_resident_source_supply(
        _input(serialized_disclosure, record["conversation_id"])
    )
    assert supply is not None and reasons == ()
    source = defer_principal_memex_live_resident_source(
        supply=supply,
        authorization=_authorization(
            serialized_session, signing_context, tmp_path,
            intent_id=intent_id, grounding_receipt_id=grounding_receipt_id,
        ),
        authority_store=InMemoryAuthorityRuntimeStore({}),
        model_runtime_binding_receipt=binding,
        now_epoch=now_epoch,
        conversation_store=store(path),
    )
    assert source is not None
    prepared = None
    if consume:
        prepared = consume_principal_memex_live_resident_source(
            source, resident_cycle_id=RESIDENT_CYCLE_ID,
            conversation_store=store(path),
        )
    return prepared, source, binding, binding_digest, path


def test_optional_supply_is_exact_shape_and_secret_safe() -> None:
    assert parse_principal_memex_live_resident_source_supply(None) == (None, ())
    valid, reasons = parse_principal_memex_live_resident_source_supply(
        _input("{}", "sha256:" + "1" * 64)
    )
    assert reasons == ()
    assert valid is not None
    assert "{}" not in repr(valid)
    with pytest.raises(TypeError, match="pickle_forbidden"):
        pickle.dumps(valid)

    for invalid in (
        {},
        {"serialized_disclosure": "{}"},
        {**_input("{}", "sha256:" + "1" * 64), "extra": True},
        _input("{}", "not-a-digest"),
        _input("{}", "sha256:" + "1" * 64, True),
        _input("\N{SNOWMAN}", "sha256:" + "1" * 64),
    ):
        parsed, rejected = parse_principal_memex_live_resident_source_supply(invalid)
        assert parsed is None
        assert rejected == ("principal_memex_source_supply_invalid",)


def test_live_supply_reuses_authenticated_one_use_admission(tmp_path: Path) -> None:
    prepared, source, binding, binding_digest, path = _prepared_live_source(tmp_path)

    assert prepared.accepted is True
    assert prepared.now_epoch == NOW
    assert prepared.trusted_now_epoch is not None
    admitted = consume_authenticated_principal_memex_context(
        prepared.context,
        model_runtime_binding_receipt_id=binding["receipt_id"],
        model_runtime_binding_digest=binding_digest,
        now_epoch=NOW + 1,
    )
    assert admitted.accepted is True
    assert admitted.context_view["source_class"] == "principal_memex"
    assert admitted.context_view["authority_effect"] == "none"
    assert admitted.context_view["items"][0]["statement"] == (
        "Audit before implementation."
    )
    assert consume_authenticated_principal_memex_context(
        prepared.context,
        model_runtime_binding_receipt_id=binding["receipt_id"],
        model_runtime_binding_digest=binding_digest,
        now_epoch=NOW + 1,
    ).accepted is False
    assert consume_principal_memex_live_resident_source(
        source,
        resident_cycle_id=RESIDENT_CYCLE_ID,
        conversation_store=store(path),
    ).accepted is False


def test_model_binding_substitution_fails_before_context_issue(tmp_path: Path) -> None:
    path = tmp_path / "principal-binding.sqlite"
    serialized_session, signing_context, record, decision = _principal_scope(path)
    binding = model_runtime_binding_receipt(
        runtime_surface="reddog_backend_architect"
    )
    serialized_disclosure = _disclosure(record, decision)
    supply, _ = parse_principal_memex_live_resident_source_supply(
        _input(serialized_disclosure, record["conversation_id"])
    )
    assert supply is not None

    source = defer_principal_memex_live_resident_source(
        supply=supply,
        authorization=_authorization(serialized_session, signing_context, tmp_path),
        authority_store=InMemoryAuthorityRuntimeStore({}),
        model_runtime_binding_receipt=binding,
        now_epoch=lambda: NOW,
        conversation_store=store(path),
    )
    assert source is not None
    result = consume_principal_memex_live_resident_source(
        source,
        resident_cycle_id=RESIDENT_CYCLE_ID,
        conversation_store=store(path),
    )

    assert result.accepted is False
    assert result.context is None


def _raise_clock() -> int:
    raise RuntimeError("clock unavailable")


@pytest.mark.parametrize("clock", [lambda: "1", _raise_clock])
def test_invalid_clock_fails_closed_and_consumes_source(tmp_path: Path, clock) -> None:
    path = tmp_path / "principal-clock.sqlite"
    serialized_session, signing_context, record, decision = _principal_scope(path)
    binding = model_runtime_binding_receipt(
        runtime_surface="reddog_backend_architect"
    )
    serialized_disclosure = _disclosure(
        record,
        decision,
        model_runtime_binding_receipt_id=binding["receipt_id"],
        model_runtime_binding_digest=canonical_model_runtime_binding_digest(binding),
    )
    supply, _ = parse_principal_memex_live_resident_source_supply(
        _input(serialized_disclosure, record["conversation_id"])
    )
    assert supply is not None
    source = defer_principal_memex_live_resident_source(
        supply=supply,
        authorization=_authorization(serialized_session, signing_context, tmp_path),
        authority_store=InMemoryAuthorityRuntimeStore({}),
        model_runtime_binding_receipt=binding,
        now_epoch=clock,
        conversation_store=store(path),
    )
    assert source is not None
    first = consume_principal_memex_live_resident_source(
        source, resident_cycle_id=RESIDENT_CYCLE_ID
    )
    second = consume_principal_memex_live_resident_source(
        source, resident_cycle_id=RESIDENT_CYCLE_ID
    )
    assert first.accepted is False
    assert second.rejection_reasons == (
        "principal_memex_live_source_invalid_or_replayed",
    )


def test_deferred_source_is_opaque_immutable_and_one_use(tmp_path: Path) -> None:
    path = tmp_path / "principal-opaque.sqlite"
    serialized_session, signing_context, record, decision = _principal_scope(path)
    binding = model_runtime_binding_receipt(
        runtime_surface="reddog_backend_architect"
    )
    serialized_disclosure = _disclosure(
        record,
        decision,
        model_runtime_binding_receipt_id=binding["receipt_id"],
        model_runtime_binding_digest=canonical_model_runtime_binding_digest(binding),
    )
    supply, _ = parse_principal_memex_live_resident_source_supply(
        _input(serialized_disclosure, record["conversation_id"])
    )
    assert supply is not None
    source = defer_principal_memex_live_resident_source(
        supply=supply,
        authorization=_authorization(serialized_session, signing_context, tmp_path),
        authority_store=InMemoryAuthorityRuntimeStore({}),
        model_runtime_binding_receipt=binding,
        now_epoch=lambda: NOW,
        conversation_store=store(path),
    )
    assert source is not None
    assert "serialized_disclosure" not in repr(source)
    with pytest.raises(TypeError, match="direct_construction_forbidden"):
        DeferredPrincipalMemexResidentSource()
    for operation in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(TypeError):
            operation(source)


def test_invalid_cycle_binding_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "principal-cycle.sqlite"
    serialized_session, signing_context, record, decision = _principal_scope(path)
    binding = model_runtime_binding_receipt(
        runtime_surface="reddog_backend_architect"
    )
    supply, _ = parse_principal_memex_live_resident_source_supply(
        _input(
            _disclosure(
                record,
                decision,
                model_runtime_binding_receipt_id=binding["receipt_id"],
                model_runtime_binding_digest=canonical_model_runtime_binding_digest(binding),
            ),
            record["conversation_id"],
        )
    )
    assert supply is not None
    source = defer_principal_memex_live_resident_source(
        supply=supply,
        authorization=_authorization(serialized_session, signing_context, tmp_path),
        authority_store=InMemoryAuthorityRuntimeStore({}),
        model_runtime_binding_receipt=binding,
        now_epoch=lambda: NOW,
        conversation_store=store(path),
    )
    result = consume_principal_memex_live_resident_source(
        source,
        resident_cycle_id="not-a-cycle",
        conversation_store=store(path),
    )
    assert result.accepted is False
    assert result.context is None
