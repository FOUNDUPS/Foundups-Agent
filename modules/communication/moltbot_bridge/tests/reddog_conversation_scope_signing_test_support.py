"""Shared fixtures for conversation-scope signer security tests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from modules.communication.moltbot_bridge.src.reddog_authenticated_conversation_scope_state import (
    create_authenticated_conversation_scope,
)
from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    PrincipalAuthorityRecord,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_authentication import (
    authenticate_signed_conversation_scope,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_digest import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_request import (
    ConversationScopeCreateRequest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_signing import (
    ConversationScopeSignerPolicy,
    ConversationScopeSigningContext,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_store import (
    AgentDbConversationScopeStore,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_session_credential import (
    AUDIENCE,
    MODE,
    SCHEMA_VERSION as CREDENTIAL_SCHEMA,
    canonical_conversation_session_signing_input,
    credential_id,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_public_key,
    encode_ed25519_signature,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
    Ed25519SignerBackend,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    SignerPeerAttestation,
)
from modules.communication.moltbot_bridge.src.reddog_signer_conversation_scope_anchor import (
    InMemorySignerConversationScopeAnchorStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    SigningResponse,
)
from modules.communication.moltbot_bridge.tests.reddog_conversation_scope_test_support import (
    FOCUS,
    SNAPSHOT_DIGEST,
    SNAPSHOT_ID,
    TestAgentDb,
    digest,
    grounding_receipt,
    item,
)


NOW = 1_800_000_000
REPO = "FOUNDUPS/Foundups-Agent"
REPO_ROOT = Path(__file__).resolve().parents[4]
PRINCIPAL_KEY = Ed25519PrivateKey.generate()
PRINCIPAL_PUBLIC = encode_ed25519_public_key(
    PRINCIPAL_KEY.public_key().public_bytes_raw()
)


class Resolver:
    def resolve(self, principal_id: str, principal_provider: str):
        if (principal_id, principal_provider) != ("principal_012", "principal-signature"):
            return None
        return PrincipalAuthorityRecord(
            principal_id=principal_id,
            principal_provider=principal_provider,
            principal_public_key=PRINCIPAL_PUBLIC,
            repo_scope=(REPO,),
            foundup_scope=("trade",),
            verified_subject_digest="sha256:" + "a" * 64,
        )


class AuditMacBuilder:
    def build(
        self, request: SigningRequest, signature: str, peer: SignerPeerAttestation
    ) -> str:
        return "audit:" + canonical_digest(
            {
                "request": request.payload_digest,
                "signature": signature,
                "peer": peer.peer_principal_id,
            }
        )


class ChangingAuditMacBuilder:
    def __init__(self) -> None:
        self.calls = 0

    def build(
        self, request: SigningRequest, signature: str, peer: SignerPeerAttestation
    ) -> str:
        self.calls += 1
        return "audit:" + canonical_digest(
            {
                "request": request.payload_digest,
                "signature": signature,
                "peer": peer.peer_principal_id,
                "call": self.calls,
            }
        )


@dataclass
class BackendClient:
    backend: Ed25519SignerBackend

    def sign(self, request: SigningRequest) -> SigningResponse:
        return self.backend.sign(
            request,
            SignerPeerAttestation(
                peer_principal_id="principal_012",
                transport="unix_socket",
                credential_source="kernel_peer_credential",
                boundary_attested=True,
            ),
        )


class UnavailableSignerClient:
    def sign(self, _request: SigningRequest) -> SigningResponse:
        raise ConnectionError("signer unavailable")


class CrashBeforeFinalizeTransactions:
    def __init__(self, transactions: object) -> None:
        self.transactions = transactions

    def stage(self, record: object, *, expected_revision: int):
        return self.transactions.stage(record, expected_revision=expected_revision)

    def finalize(self, record: object, *, expected_revision: int):
        del record, expected_revision
        raise RuntimeError("simulated_process_crash_after_signer_commit")


class CrashBeforeFinalizeStore:
    def __init__(self, store: AgentDbConversationScopeStore) -> None:
        self.store = store

    def load(self, conversation_id: str):
        return self.store.load(conversation_id)

    def pending_transactions(self) -> CrashBeforeFinalizeTransactions:
        return CrashBeforeFinalizeTransactions(self.store.pending_transactions())


def credential(*, key: Ed25519PrivateKey = PRINCIPAL_KEY) -> str:
    value = {
        "schema_version": CREDENTIAL_SCHEMA,
        "credential_id": "",
        "principal_id": "principal_012",
        "principal_provider": "principal-signature",
        "audience": AUDIENCE,
        "repo_full_name": REPO,
        "foundup_scope": ["trade"],
        "transport": "editor",
        "session_id": "sha256:" + "e" * 64,
        "credential_mode": MODE,
        "issued_at": NOW - 10,
        "expires_at": NOW + 300,
        "signature": "",
    }
    value["credential_id"] = credential_id(value)
    value["signature"] = encode_ed25519_signature(
        key.sign(canonical_conversation_session_signing_input(value).encode("ascii"))
    )
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def context(
    serialized: str,
    *,
    clock: list[int] | None = None,
    audit_builder: object | None = None,
):
    key = Ed25519PrivateKey.generate()
    public = encode_ed25519_public_key(key.public_key().public_bytes_raw())
    anchor = InMemorySignerConversationScopeAnchorStore()
    backend = Ed25519SignerBackend(
        private_key=key,
        public_key=public,
        key_epoch="epoch-1",
        audit_mac_builder=audit_builder or AuditMacBuilder(),
        proposal_clock=lambda: clock[0] if clock is not None else NOW,
        conversation_scope_signer_policy=ConversationScopeSignerPolicy(
            issuer_principal_id="principal_012",
            issuer_principal_provider="principal-signature",
            repo_full_name=REPO,
            signer_public_key=public,
            key_epoch="epoch-1",
        ),
        conversation_scope_principal_resolver=Resolver(),
        conversation_scope_anchor_store=anchor,
    )
    return ConversationScopeSigningContext(
        signer=BackendClient(backend),
        signer_public_key=public,
        key_epoch="epoch-1",
        serialized_session_credential=serialized,
    ), anchor


def capability(
    signing_context: ConversationScopeSigningContext,
    serialized: str,
    now: int = NOW,
):
    authenticated = authenticate_signed_conversation_scope(
        serialized_credential=serialized,
        transport="editor",
        session_binding="window:one",
        expected_repo_full_name=REPO,
        principal_resolver=Resolver(),
        now_epoch=now,
        record_signing_context=signing_context,
    )
    assert authenticated is not None
    return authenticated[0]


def store(path: Path) -> AgentDbConversationScopeStore:
    return AgentDbConversationScopeStore(lambda: TestAgentDb(path))


def anchor_payload(*, revision: int = 0, state: str = "2", nonce: str = "3"):
    return {
        "conversation_id": "sha256:" + "1" * 64,
        "conversation_revision": revision,
        "previous_record_auth_signature_digest": "",
        "record_state_digest": "sha256:" + state * 64,
        "record_auth_nonce": "sha256:" + nonce * 64,
        "credential_id": "sha256:" + "4" * 64,
        "principal_id": "principal_012",
        "principal_provider": "principal-signature",
        "repo_full_name": REPO,
        "session_id": "sha256:" + "5" * 64,
    }


def create(
    path: Path,
    signing_context: ConversationScopeSigningContext,
    serialized: str,
    *,
    store_override: object | None = None,
    store: object | None = None,
    request_overrides: dict[str, object] | None = None,
    now_epoch: int = NOW,
):
    selected_store = store_override or store
    request_values: dict[str, object] = {
        "work_focus": FOCUS,
        "grounding_receipt": grounding_receipt(),
        "discussion_foundup_ids": ("trade",),
        "conversation_nonce": "signed-conversation-one",
        "turn_id": digest({"turn": "signed-first"}),
        "active_topic": "TRADE runtime",
        "current_objective": "Identify the next grounded implementation slice.",
        "accepted_decisions": (
            item("Use current repository evidence.", "repository_fact"),
        ),
        "open_questions": (item("What is next?", "unresolved"),),
        "repository_evidence_refs": ("code:trade",),
        "source_snapshot_id": SNAPSHOT_ID,
        "source_snapshot_digest": SNAPSHOT_DIGEST,
        "ttl_seconds": 200,
    }
    request_values.update(request_overrides or {})
    return create_authenticated_conversation_scope(
        store=selected_store or AgentDbConversationScopeStore(
            lambda: TestAgentDb(path)
        ),
        capability=capability(signing_context, serialized, now_epoch),
        repo_root=REPO_ROOT,
        request=ConversationScopeCreateRequest(**request_values),
        now_epoch=now_epoch,
    )
