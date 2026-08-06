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


MODEL_RECEIPT = "reddog_model_runtime_binding:" + "6" * 64
MODEL_DIGEST = "sha256:" + "7" * 64
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
    result = prepare_authenticated_principal_memex_context(
        store=store(path), capability=capability(signing_context, serialized),
        serialized_disclosure=_disclosure(record, decision, **disclosure_values),
        principal_resolver=principal_resolver or Resolver(), guard=guard,
        conversation_id=record["conversation_id"], expected_revision=0,
        expected_repo_full_name=REPO, expected_transport="editor",
        model_runtime_binding_receipt_id=model_receipt,
        model_runtime_binding_digest=model_digest, now_epoch=NOW,
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


def test_only_accepted_operator_decisions_reach_context(tmp_path: Path) -> None:
    prepared, _ = _prepared(tmp_path / "bounded.sqlite")
    admitted = _consume(prepared.context)
    encoded = json.dumps(dict(admitted.context_view), sort_keys=True)
    assert "Audit before implementation." in encoded
    assert "Skip verification." not in encoded
    assert "Which FoundUp" not in encoded
    assert "objective canary" not in encoded
    assert "credential" not in encoded


@pytest.mark.parametrize(
    "field,value",
    [
        ("sensitivity", "private"),
        ("runtime_surface", "worker"),
        ("conversation_revision", 1),
        ("model_runtime_binding_digest", "sha256:" + "9" * 64),
        ("expires_at", NOW),
    ],
)
def test_disclosure_binding_tamper_fails_closed(tmp_path: Path, field: str, value) -> None:
    prepared, _ = _prepared(tmp_path / f"tamper-{field}.sqlite", **{field: value})
    assert prepared.accepted is False


def test_invalid_projection_does_not_consume_scope_capability(tmp_path: Path) -> None:
    path = tmp_path / "capability-not-burned.sqlite"
    serialized, signing_context, record, decision = _principal_scope(path)
    scope_capability = capability(signing_context, serialized)
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

    encoded = build_architect_context(
        context_view=Context(), evidence_bundle=Evidence(), reports=(),
        conversation_binding=None, max_chars=20_000,
        principal_memex_view=admitted.context_view,
    )
    payload = json.loads(encoded)
    assert payload["principal_memex_context"] == dict(admitted.context_view)
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
