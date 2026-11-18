"""Security tests for authenticated Principal Memex resident admission."""

from __future__ import annotations

import ast
import copy
import json
import pickle
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    AtomicJsonAuthorityRuntimeStore,
    InMemoryAuthorityRuntimeStore,
    PrincipalAuthorityRecord,
)
from modules.communication.moltbot_bridge.src.reddog_backend_architect_context_projection import (
    build_architect_context,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_capability import (
    split_conversation_scope_capability,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_principal_memex_disclosure import (
    AUDIENCE,
    PURPOSE,
    RUNTIME_SURFACE,
    SCHEMA_VERSION,
    AuthorityRuntimePrincipalMemexDisclosureGuard,
    canonical_principal_memex_disclosure_signing_input,
    disclosure_id,
)
from modules.communication.moltbot_bridge.src.reddog_principal_memex_resident_admission import (
    AuthenticatedPrincipalMemexContext,
    consume_authenticated_principal_memex_context,
    prepare_authenticated_principal_memex_context,
    validate_principal_memex_admission_output,
)
from modules.communication.moltbot_bridge.tests.reddog_conversation_scope_signing_test_support import (
    NOW,
    PRINCIPAL_KEY,
    REPO,
    Resolver,
    capability,
    context,
    create,
    credential,
    store,
)
from modules.communication.moltbot_bridge.tests.reddog_conversation_scope_test_support import (
    TestAgentDb,
    item,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_signature,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_session_credential import (
    canonical_conversation_session_signing_input,
    credential_id,
)


MODEL_RECEIPT = "reddog_model_runtime_binding:" + "6" * 64
MODEL_DIGEST = "sha256:" + "7" * 64
INTENT_ID = "sha256:" + "9" * 64
GROUNDING_RECEIPT_ID = "sha256:" + "a" * 64
RESIDENT_CYCLE_ID = "sha256:" + "b" * 64
SESSION_BINDING_DIGEST = canonical_digest(
    {"transport": "editor", "session_binding": "window:one"}
)
GENERATION_MANIFEST_ID = "sha256:" + "c" * 64
ARTIFACT_GENERATION_DIGEST = "sha256:" + "d" * 64
SOURCE_MODULES = (
    Path(__file__).resolve().parents[1] / "src" / "reddog_principal_memex_disclosure.py",
    Path(__file__).resolve().parents[1]
    / "src"
    / "reddog_principal_memex_resident_admission.py",
)


def _principal_scope(path: Path):
    serialized = credential()
    signing_context, _ = context(serialized)
    accepted = item("Audit before implementation.")
    rejected = item("Skip verification.")
    question = item("Which FoundUp should receive this principle?", "unresolved")
    created = create(
        path,
        signing_context,
        serialized,
        request_overrides={
            "scope_kind": "principal",
            "work_focus": "Discuss a cross-FoundUp operating principle.",
            "grounding_receipt": {},
            "discussion_foundup_ids": (),
            "active_topic": "Principal operating principles",
            "current_objective": "Do not expose this objective canary.",
            "accepted_decisions": (accepted,),
            "rejected_options": (rejected,),
            "open_questions": (question,),
            "repository_evidence_refs": (),
            "source_snapshot_id": "",
            "source_snapshot_digest": "",
        },
    )
    assert created.accepted is True
    record = store(path).load(created.conversation_id)["record"]
    return serialized, signing_context, record, accepted


def _principal_scope_with_two_decisions(path: Path):
    serialized = credential()
    signing_context, _ = context(serialized)
    first = item("Audit before implementation.")
    second = item("Prefer extending an existing module.")
    created = create(
        path,
        signing_context,
        serialized,
        request_overrides={
            "scope_kind": "principal",
            "work_focus": "Discuss cross-FoundUp operating principles.",
            "grounding_receipt": {},
            "discussion_foundup_ids": (),
            "active_topic": "Principal operating principles",
            "current_objective": "Preserve scoped operating principles.",
            "accepted_decisions": (first, second),
            "rejected_options": (),
            "open_questions": (),
            "repository_evidence_refs": (),
            "source_snapshot_id": "",
            "source_snapshot_digest": "",
        },
    )
    assert created.accepted is True, created.rejection_reasons
    record = store(path).load(created.conversation_id)["record"]
    return serialized, signing_context, record, first, second


def _disclosure(record, decision, **overrides) -> str:
    value = {
        "schema_version": SCHEMA_VERSION,
        "disclosure_id": "",
        "principal_id": record["principal_id"],
        "principal_provider": record["principal_provider"],
        "audience": AUDIENCE,
        "repo_full_name": REPO,
        "transport": "editor",
        "credential_id": record["credential_id"],
        "session_id": record["session_id"],
        "conversation_id": record["conversation_id"],
        "conversation_revision": record["conversation_revision"],
        "conversation_record_digest": record["record_digest"],
        "decision_item_ids": [decision["item_id"]],
        "sensitivity": "public",
        "purpose": PURPOSE,
        "runtime_surface": RUNTIME_SURFACE,
        "model_runtime_binding_receipt_id": MODEL_RECEIPT,
        "model_runtime_binding_digest": MODEL_DIGEST,
        "intent_id": INTENT_ID,
        "grounding_receipt_id": GROUNDING_RECEIPT_ID,
        "session_binding_digest": SESSION_BINDING_DIGEST,
        "nonce": "sha256:" + "8" * 64,
        "issued_at": NOW - 1,
        "expires_at": NOW + 60,
        "signature": "",
    }
    value.update(overrides)
    value["disclosure_id"] = disclosure_id(value)
    value["signature"] = encode_ed25519_signature(
        PRINCIPAL_KEY.sign(
            canonical_principal_memex_disclosure_signing_input(value).encode("ascii")
        )
    )
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _prepared(
    path: Path,
    runtime_store=None,
    *,
    model_receipt: str = MODEL_RECEIPT,
    model_digest: str = MODEL_DIGEST,
    principal_resolver=None,
    **disclosure_overrides,
):
    serialized, signing_context, record, decision = _principal_scope(path)
    guard = AuthorityRuntimePrincipalMemexDisclosureGuard(
        runtime_store or InMemoryAuthorityRuntimeStore({})
    )
    disclosure_values = {
        "model_runtime_binding_receipt_id": model_receipt,
        "model_runtime_binding_digest": model_digest,
        **disclosure_overrides,
    }
    children = split_conversation_scope_capability(
        capability(signing_context, serialized)
    )
    assert children is not None
    result = prepare_authenticated_principal_memex_context(
        store=store(path), capability=children[1],
        serialized_disclosure=_disclosure(record, decision, **disclosure_values),
        principal_resolver=principal_resolver or Resolver(), guard=guard,
        conversation_id=record["conversation_id"], expected_revision=0,
        expected_repo_full_name=REPO, expected_transport="editor",
        model_runtime_binding_receipt_id=model_receipt,
        model_runtime_binding_digest=model_digest,
        expected_intent_id=INTENT_ID,
        expected_grounding_receipt_id=GROUNDING_RECEIPT_ID,
        expected_resident_cycle_id=RESIDENT_CYCLE_ID,
        expected_session_binding_digest=SESSION_BINDING_DIGEST,
        current_generation_manifest_id=GENERATION_MANIFEST_ID,
        artifact_generation_digest=ARTIFACT_GENERATION_DIGEST,
        now_epoch=NOW,
    )
    return result, record


def _consume(context_value):
    return consume_authenticated_principal_memex_context(
        context_value,
        model_runtime_binding_receipt_id=MODEL_RECEIPT,
        model_runtime_binding_digest=MODEL_DIGEST,
        now_epoch=NOW + 1,
    )


def test_signed_principal_decision_is_admitted_once_without_authority(tmp_path: Path) -> None:
    prepared, _ = _prepared(tmp_path / "principal.sqlite")
    assert prepared.accepted is True
    admitted = _consume(prepared.context)
    assert admitted.accepted is True
    assert admitted.no_work_authority_granted is True
    assert admitted.no_foundup_projection_performed is True
    assert admitted.context_view["items"][0]["statement"] == "Audit before implementation."
    assert admitted.context_view["authority_effect"] == "none"
    assert admitted.admission_receipt["no_work_authority_granted"] is True
    assert str(
        admitted.admission_receipt["conversation_scope_authority_digest"]
    ).startswith("sha256:")
    assert admitted.admission_receipt["source_decision_item_ids"]
    assert _consume(prepared.context).accepted is False


def test_accepted_output_is_deeply_immutable_and_digest_bound(tmp_path: Path) -> None:
    prepared, _ = _prepared(tmp_path / "deep-freeze.sqlite")
    admitted = _consume(prepared.context)
    assert admitted.accepted is True

    with pytest.raises(TypeError):
        admitted.context_view["items"][0]["statement"] = "FORGED_AFTER_ADMISSION"
    with pytest.raises(AttributeError):
        admitted.context_view["items"].append({"item_id": "forged"})
    with pytest.raises(TypeError):
        admitted.admission_receipt["source_decision_item_ids"][0] = "forged"

    receipt = dict(admitted.admission_receipt)
    context_view = dict(admitted.context_view)
    context_view["items"] = [dict(item) for item in context_view["items"]]
    context_view["items"][0]["statement"] = "FORGED_AFTER_ADMISSION"
    assert validate_principal_memex_admission_output(receipt, context_view) is None


def test_only_accepted_operator_decisions_reach_context(tmp_path: Path) -> None:
    prepared, _ = _prepared(tmp_path / "bounded.sqlite")
    admitted = _consume(prepared.context)
    validated = validate_principal_memex_admission_output(
        admitted.admission_receipt, admitted.context_view
    )
    assert validated is not None
    encoded = json.dumps(validated[1], sort_keys=True)
    assert "Audit before implementation." in encoded
    assert "Skip verification." not in encoded
    assert "Which FoundUp" not in encoded
    assert "objective canary" not in encoded
    assert "credential" not in encoded


def test_signed_subset_and_order_are_preserved(tmp_path: Path) -> None:
    subset = _consume(
        _prepare_two_decision_selection(
            tmp_path / "subset.sqlite", subset=True
        ).context
    )
    reordered = _consume(
        _prepare_two_decision_selection(
            tmp_path / "order.sqlite", subset=False
        ).context
    )

    assert subset.accepted is True
    assert [item["statement"] for item in subset.context_view["items"]] == [
        "Prefer extending an existing module."
    ]
    assert all(
        item["statement"] != "Audit before implementation."
        for item in subset.context_view["items"]
    )
    assert [item["statement"] for item in reordered.context_view["items"]] == [
        "Prefer extending an existing module.",
        "Audit before implementation.",
    ]


@pytest.mark.parametrize(
    "field,value",
    [
        ("sensitivity", "private"),
        ("runtime_surface", "worker"),
        ("conversation_revision", 1),
        ("model_runtime_binding_digest", "sha256:" + "9" * 64),
        ("intent_id", "sha256:" + "e" * 64),
        ("grounding_receipt_id", "sha256:" + "e" * 64),
        ("session_binding_digest", "sha256:" + "e" * 64),
        ("expires_at", NOW),
    ],
)
def test_disclosure_binding_tamper_fails_closed(tmp_path: Path, field: str, value) -> None:
    prepared, _ = _prepared(tmp_path / f"tamper-{field}.sqlite", **{field: value})
    assert prepared.accepted is False


def test_invalid_projection_does_not_consume_scope_capability(tmp_path: Path) -> None:
    path = tmp_path / "capability-not-burned.sqlite"
    serialized, signing_context, record, decision = _principal_scope(path)
    children = split_conversation_scope_capability(
        capability(signing_context, serialized)
    )
    assert children is not None
    scope_capability = children[1]
    guard = AuthorityRuntimePrincipalMemexDisclosureGuard(
        InMemoryAuthorityRuntimeStore({})
    )
    common = {
        "store": store(path),
        "capability": scope_capability,
        "principal_resolver": Resolver(),
        "guard": guard,
        "conversation_id": record["conversation_id"],
        "expected_revision": 0,
        "expected_repo_full_name": REPO,
        "expected_transport": "editor",
        "model_runtime_binding_receipt_id": MODEL_RECEIPT,
        "model_runtime_binding_digest": MODEL_DIGEST,
        "expected_intent_id": INTENT_ID,
        "expected_grounding_receipt_id": GROUNDING_RECEIPT_ID,
        "expected_resident_cycle_id": RESIDENT_CYCLE_ID,
        "expected_session_binding_digest": SESSION_BINDING_DIGEST,
        "current_generation_manifest_id": GENERATION_MANIFEST_ID,
        "artifact_generation_digest": ARTIFACT_GENERATION_DIGEST,
        "now_epoch": NOW,
    }
    invalid = prepare_authenticated_principal_memex_context(
        serialized_disclosure=_disclosure(
            record, decision, decision_item_ids=["sha256:" + "f" * 64]
        ),
        **common,
    )
    assert invalid.accepted is False

    valid = prepare_authenticated_principal_memex_context(
        serialized_disclosure=_disclosure(record, decision),
        **common,
    )
    assert valid.accepted is True


def _credential_with_session(session_id: str) -> str:
    value = json.loads(credential())
    value["session_id"] = session_id
    value["credential_id"] = ""
    value["signature"] = ""
    value["credential_id"] = credential_id(value)
    value["signature"] = encode_ed25519_signature(
        PRINCIPAL_KEY.sign(
            canonical_conversation_session_signing_input(value).encode("ascii")
        )
    )
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _prepare_two_decision_selection(path: Path, *, subset: bool):
    serialized, signing_context, record, first, second = (
        _principal_scope_with_two_decisions(path)
    )
    selected = (
        [second["item_id"]]
        if subset
        else [second["item_id"], first["item_id"]]
    )
    children = split_conversation_scope_capability(
        capability(signing_context, serialized)
    )
    assert children is not None
    return prepare_authenticated_principal_memex_context(
        store=store(path), capability=children[1],
        serialized_disclosure=_disclosure(
            record, first, decision_item_ids=selected,
        ),
        principal_resolver=Resolver(),
        guard=AuthorityRuntimePrincipalMemexDisclosureGuard(
            InMemoryAuthorityRuntimeStore({})
        ),
        conversation_id=record["conversation_id"], expected_revision=0,
        expected_repo_full_name=REPO, expected_transport="editor",
        model_runtime_binding_receipt_id=MODEL_RECEIPT,
        model_runtime_binding_digest=MODEL_DIGEST,
        expected_intent_id=INTENT_ID,
        expected_grounding_receipt_id=GROUNDING_RECEIPT_ID,
        expected_resident_cycle_id=RESIDENT_CYCLE_ID,
        expected_session_binding_digest=SESSION_BINDING_DIGEST,
        current_generation_manifest_id=GENERATION_MANIFEST_ID,
        artifact_generation_digest=ARTIFACT_GENERATION_DIGEST,
        now_epoch=NOW,
    )


def test_fresh_session_reauthorizes_immutable_historical_record(
    tmp_path: Path,
) -> None:
    path = tmp_path / "new-session.sqlite"
    _old_serialized, _old_context, record, decision = _principal_scope(path)
    current_credential = _credential_with_session("sha256:" + "f" * 64)
    current_signing_context, _ = context(current_credential)
    children = split_conversation_scope_capability(
        capability(current_signing_context, current_credential)
    )
    assert children is not None

    prepared = prepare_authenticated_principal_memex_context(
        store=store(path),
        capability=children[1],
        serialized_disclosure=_disclosure(record, decision),
        principal_resolver=Resolver(),
        guard=AuthorityRuntimePrincipalMemexDisclosureGuard(
            InMemoryAuthorityRuntimeStore({})
        ),
        conversation_id=record["conversation_id"],
        expected_revision=record["conversation_revision"],
        expected_repo_full_name=REPO,
        expected_transport="editor",
        model_runtime_binding_receipt_id=MODEL_RECEIPT,
        model_runtime_binding_digest=MODEL_DIGEST,
        expected_intent_id=INTENT_ID,
        expected_grounding_receipt_id=GROUNDING_RECEIPT_ID,
        expected_resident_cycle_id=RESIDENT_CYCLE_ID,
        expected_session_binding_digest=SESSION_BINDING_DIGEST,
        current_generation_manifest_id=GENERATION_MANIFEST_ID,
        artifact_generation_digest=ARTIFACT_GENERATION_DIGEST,
        now_epoch=NOW,
    )

    assert prepared.accepted is True
    admitted = _consume(prepared.context)
    assert admitted.accepted is True
    assert admitted.admission_receipt["conversation_record_digest"] == record[
        "record_digest"
    ]


def test_runtime_binding_substitution_consumes_context_but_not_disclosure(tmp_path: Path) -> None:
    prepared, _ = _prepared(tmp_path / "binding.sqlite")
    result = consume_authenticated_principal_memex_context(
        prepared.context,
        model_runtime_binding_receipt_id=MODEL_RECEIPT,
        model_runtime_binding_digest="sha256:" + "0" * 64,
        now_epoch=NOW + 1,
    )
    assert result.accepted is False
    assert result.rejection_reasons == ("principal_memex_disclosure_rejected",)


def test_changed_or_expired_conversation_fails_at_use(tmp_path: Path) -> None:
    path = tmp_path / "changed.sqlite"
    prepared, record = _prepared(path)
    with TestAgentDb(path).db.get_connection() as conn:
        conn.execute(
            "UPDATE reddog_conversation_scopes SET scope_json = ? WHERE conversation_id = ?",
            (json.dumps({**record, "active_topic": "tampered"}), record["conversation_id"]),
        )
    assert _consume(prepared.context).accepted is False


def test_revocation_and_atomic_replay_fail_closed(tmp_path: Path) -> None:
    revoked_store = InMemoryAuthorityRuntimeStore(
        {"revocations": {"principal_ids": ["principal_012"]}}
    )
    revoked, _ = _prepared(tmp_path / "revoked.sqlite", runtime_store=revoked_store)
    assert revoked.accepted is False

    runtime_store = InMemoryAuthorityRuntimeStore({})
    first, _ = _prepared(tmp_path / "first.sqlite", runtime_store=runtime_store)
    second, _ = _prepared(tmp_path / "second.sqlite", runtime_store=runtime_store)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(_consume, (first.context, second.context)))
    assert sum(result.accepted for result in results) == 1


def test_malformed_revocation_state_fails_closed(tmp_path: Path) -> None:
    runtime_store = InMemoryAuthorityRuntimeStore(
        {"revocations": {"principal_ids": "principal_012"}}
    )
    prepared, _ = _prepared(
        tmp_path / "malformed-revocation.sqlite", runtime_store=runtime_store
    )
    assert prepared.accepted is False


def test_resolver_cannot_substitute_another_principal_record(tmp_path: Path) -> None:
    class SubstitutingResolver:
        def resolve(self, _principal_id: str, _principal_provider: str):
            legitimate = Resolver().resolve("principal_012", "principal-signature")
            return PrincipalAuthorityRecord(
                **{
                    **legitimate.to_dict(),
                    "principal_id": "principal_attacker",
                }
            )

    prepared, _ = _prepared(
        tmp_path / "resolver-substitution.sqlite",
        principal_resolver=SubstitutingResolver(),
    )
    assert prepared.accepted is False


def test_durable_store_rejects_cross_process_nonce_replay(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    authority_path = runtime_root / "authority.json"
    first_store = AtomicJsonAuthorityRuntimeStore(
        authority_path, allowed_root=runtime_root, repo_root=Path(__file__).resolve().parents[4]
    )
    first, _ = _prepared(tmp_path / "durable-first.sqlite", runtime_store=first_store)
    assert _consume(first.context).accepted is True
    second_store = AtomicJsonAuthorityRuntimeStore(
        authority_path, allowed_root=runtime_root, repo_root=Path(__file__).resolve().parents[4]
    )
    second, _ = _prepared(tmp_path / "durable-second.sqlite", runtime_store=second_store)
    assert _consume(second.context).accepted is False


def test_opaque_context_cannot_be_constructed_copied_or_pickled(tmp_path: Path) -> None:
    prepared, _ = _prepared(tmp_path / "opaque.sqlite")
    with pytest.raises(TypeError):
        AuthenticatedPrincipalMemexContext()
    with pytest.raises(TypeError):
        copy.copy(prepared.context)
    with pytest.raises(TypeError):
        copy.deepcopy(prepared.context)
    with pytest.raises(TypeError):
        pickle.dumps(prepared.context)


def test_architect_context_contains_only_admitted_principal_memex_view(tmp_path: Path) -> None:
    prepared, _ = _prepared(tmp_path / "context.sqlite")
    admitted = _consume(prepared.context)

    class Context:
        context_view_id = "sha256:" + "1" * 64
        snapshot_receipt_id = "sha256:" + "2" * 64
        text = "repository evidence"

    class Evidence:
        evidence_bundle_id = "sha256:" + "3" * 64

    validated = validate_principal_memex_admission_output(
        admitted.admission_receipt, admitted.context_view
    )
    assert validated is not None
    encoded = build_architect_context(
        context_view=Context(), evidence_bundle=Evidence(), reports=(),
        conversation_binding=None, max_chars=20_000,
        principal_memex_view=validated[1],
    )
    payload = json.loads(encoded)
    assert payload["principal_memex_context"] == validated[1]
    assert payload["conversation_work_binding"] == {}


def test_api_never_accepts_a_caller_supplied_structural_projection() -> None:
    import inspect
    from modules.communication.moltbot_bridge.src import (
        reddog_principal_memex_resident_admission as admission,
    )

    signature = inspect.signature(admission.prepare_authenticated_principal_memex_context)
    assert "projection" not in signature.parameters


def test_principal_memex_runtime_is_bounded_and_has_no_effect_surface() -> None:
    banned_imports = {"subprocess", "shutil"}
    banned_calls = {("os", "system"), ("os", "popen"), ("os", "spawn")}
    for path in SOURCE_MODULES:
        source = path.read_text(encoding="ascii")
        assert len(source.splitlines()) <= 675
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert (node.end_lineno or node.lineno) - node.lineno + 1 <= 60
            if isinstance(node, ast.ClassDef):
                assert (node.end_lineno or node.lineno) - node.lineno + 1 <= 200
            if isinstance(node, ast.Import):
                assert all(alias.name not in banned_imports for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in banned_imports
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                owner = node.func.value
                if isinstance(owner, ast.Name):
                    assert (owner.id, node.func.attr) not in banned_calls
