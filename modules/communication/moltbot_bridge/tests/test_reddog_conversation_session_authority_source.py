"""Security tests for the resident conversation session authority source."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    PrincipalAuthorityRecord,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_capability import (
    conversation_scope_authority_view,
    sign_record_with_scope_authority,
)
from modules.communication.moltbot_bridge.src.reddog_principal_memex_live_resident_source_supply import (
    principal_memex_session_runtime_root,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_session_authority_source import (
    ConversationSessionAuthoritySourceError,
    lease_current_generation_conversation_session,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_session_signing_context import (
    ConversationSessionSigningContextError,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_session_credential import (
    AUDIENCE,
    MODE,
    SCHEMA_VERSION,
    canonical_conversation_session_signing_input,
    credential_id,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_public_key,
    encode_ed25519_signature,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    raw_digest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_principal_authority import (
    CurrentGenerationPrincipalAuthorityResolver,
)


NOW = 1_000_000
REPO_ROOT = Path(__file__).resolve().parents[4]
REPO_FULL_NAME = "FOUNDUPS/Foundups-Agent"
PRIVATE_KEY = Ed25519PrivateKey.generate()
PUBLIC_KEY = encode_ed25519_public_key(PRIVATE_KEY.public_key().public_bytes_raw())


def _record(
    provider: str = "principal-signature",
    *, repo_scope: tuple[str, ...] = (REPO_FULL_NAME,),
) -> PrincipalAuthorityRecord:
    return PrincipalAuthorityRecord(
        principal_id="principal_012",
        principal_provider=provider,
        principal_public_key=PUBLIC_KEY,
        repo_scope=repo_scope,
        foundup_scope=("foundups_agent", "trade"),
        verified_subject_digest="sha256:" + "a" * 64,
    )


def _intent(principal: str = "principal_012", foundup: str = "foundups_agent") -> dict:
    return {
        "schema_version": "reddog_intent.v2",
        "intent_id": "sha256:" + "b" * 64,
        "principal_ref": principal,
        "foundup_id": foundup,
        "source_surface": "editor_thin_client",
    }


def _credential(
    *, principal: str = "principal_012", provider: str = "principal-signature",
    repo: str = REPO_FULL_NAME, scope: tuple[str, ...] = ("foundups_agent", "trade"),
    issued_at: int = NOW - 10, expires_at: int = NOW + 300,
    private_key: Ed25519PrivateKey = PRIVATE_KEY,
) -> str:
    value = {
        "schema_version": SCHEMA_VERSION,
        "credential_id": "",
        "principal_id": principal,
        "principal_provider": provider,
        "audience": AUDIENCE,
        "repo_full_name": repo,
        "foundup_scope": list(scope),
        "transport": "editor",
        "session_id": "sha256:" + "e" * 64,
        "credential_mode": MODE,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "signature": "",
    }
    value["credential_id"] = credential_id(value)
    value["signature"] = encode_ed25519_signature(
        private_key.sign(canonical_conversation_session_signing_input(value).encode("ascii"))
    )
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _install_current_generation(
    monkeypatch, *records: PrincipalAuthorityRecord
) -> dict[str, bool]:
    active = {"leased": False}
    values = {f"{item.principal_provider}|{item.principal_id}": item for item in records}

    @contextmanager
    def _lease(**_kwargs):
        active["leased"] = True
        try:
            yield {
                "manifest_id": "sha256:" + "c" * 64,
                "artifact_generation_digest": "sha256:" + "f" * 64,
            }
        finally:
            active["leased"] = False

    monkeypatch.setattr(
        "modules.communication.moltbot_bridge.src."
        "reddog_conversation_session_authority_source.lease_owner_e0_current_selection",
        _lease,
    )
    monkeypatch.setattr(
        "modules.communication.moltbot_bridge.src."
        "reddog_conversation_session_authority_source."
        "load_current_generation_principal_authority_resolver",
        lambda **_kwargs: CurrentGenerationPrincipalAuthorityResolver(values),
    )
    return active


def _lease(
    monkeypatch, *, credential: str | None = None, intent: dict | None = None,
    include_principal_scope_capability: bool = False,
    include_secondary_foundup_authority: bool = False,
    require_record_signing_context: bool = False,
):
    return lease_current_generation_conversation_session(
        repo_root=REPO_ROOT,
        intent=intent or _intent(),
        grounding_receipt_id="sha256:" + "d" * 64,
        serialized_credential=credential or _credential(),
        owner_config_path="O:/runtime/owner.json",
        now_epoch=NOW,
        include_principal_scope_capability=include_principal_scope_capability,
        include_secondary_foundup_authority=include_secondary_foundup_authority,
        require_record_signing_context=require_record_signing_context,
    )


def test_signed_session_is_repo_scoped_and_generation_leased(monkeypatch) -> None:
    active = _install_current_generation(monkeypatch, _record())
    serialized = _credential()
    signature = json.loads(serialized)["signature"]
    with _lease(monkeypatch, credential=serialized) as session:
        view = conversation_scope_authority_view(session.authority)
        assert active["leased"] is True
        assert session.principal_id == "principal_012"
        assert session.repo_full_name == REPO_FULL_NAME
        assert session.foundup_scope == ("foundups_agent", "trade")
        assert session.authority_receipt["grants_work_authority"] is False
        assert session.authority_receipt["receipt_id"].startswith("sha256:")
        assert view and view["principal_provider"] == "principal-signature"
        assert signature not in repr(session)
    assert active["leased"] is False


def test_principal_memex_requests_a_distinct_one_use_scope_capability(monkeypatch) -> None:
    _install_current_generation(monkeypatch, _record())
    monkeypatch.setattr(
        "modules.communication.moltbot_bridge.src."
        "reddog_conversation_session_authority_source._conversation_signing_context",
        lambda **_kwargs: (None, REPO_ROOT),
    )
    with _lease(monkeypatch, include_principal_scope_capability=True) as session:
        authorization = session.principal_memex_authorization
        assert authorization is not None
        assert principal_memex_session_runtime_root(authorization) == REPO_ROOT
        assert not hasattr(session, "principal_scope_capability")
        assert not hasattr(session, "principal_resolver")
    assert principal_memex_session_runtime_root(authorization) is None


def test_first_turn_requests_two_distinct_foundup_authorities(monkeypatch) -> None:
    _install_current_generation(monkeypatch, _record())
    with _lease(monkeypatch, include_secondary_foundup_authority=True) as session:
        secondary = session.secondary_authority
        assert secondary is not None
        assert secondary is not session.authority
        primary_view = conversation_scope_authority_view(session.authority)
        secondary_view = conversation_scope_authority_view(secondary)
        assert primary_view == secondary_view
        assert primary_view is not None
    assert conversation_scope_authority_view(session.authority) is None
    assert conversation_scope_authority_view(secondary) is None


def test_principal_and_second_foundup_delegation_cannot_share_one_root(monkeypatch) -> None:
    _install_current_generation(monkeypatch, _record())
    monkeypatch.setattr(
        "modules.communication.moltbot_bridge.src."
        "reddog_conversation_session_authority_source._conversation_signing_context",
        lambda **_kwargs: (None, REPO_ROOT),
    )
    with pytest.raises(
        ConversationSessionAuthoritySourceError,
        match="conversation_session_scope_delegation_failed",
    ):
        with _lease(
            monkeypatch, include_principal_scope_capability=True,
            include_secondary_foundup_authority=True,
        ):
            pass


def test_record_signing_context_is_independently_required(monkeypatch) -> None:
    _install_current_generation(monkeypatch, _record())
    calls: list[dict[str, object]] = []

    def unavailable(**kwargs):
        calls.append(kwargs)
        raise ConversationSessionSigningContextError(
            "conversation_session_signer_policy_unavailable"
        )

    monkeypatch.setattr(
        "modules.communication.moltbot_bridge.src."
        "reddog_conversation_session_authority_source._conversation_signing_context",
        unavailable,
    )
    with pytest.raises(
        ConversationSessionAuthoritySourceError,
        match="conversation_session_signer_policy_unavailable",
    ):
        with _lease(monkeypatch, require_record_signing_context=True):
            pass
    assert calls and calls[0]["required"] is True


@pytest.mark.parametrize(
    ("intent", "credential", "reason"),
    [
        (_intent(principal="forged"), _credential(), "conversation_session_expected_binding_mismatch"),
        (_intent(foundup="outside"), _credential(), "conversation_session_authority_scope_rejected"),
        (_intent(), _credential(scope=("trade",)), "conversation_session_authority_scope_rejected"),
        (_intent(), _credential(repo="OTHER/Repository"), "conversation_session_authority_verification_failed"),
        (_intent(), _credential(expires_at=NOW - 1), "conversation_session_authority_verification_failed"),
        (_intent(), _credential(private_key=Ed25519PrivateKey.generate()), "conversation_session_authority_verification_failed"),
    ],
)
def test_claimed_identity_scope_and_signature_fail_closed(
    monkeypatch, intent, credential, reason
) -> None:
    _install_current_generation(monkeypatch, _record())
    with pytest.raises(ConversationSessionAuthoritySourceError, match=reason):
        with _lease(monkeypatch, credential=credential, intent=intent):
            pass


def test_principal_repo_scope_is_enforced(monkeypatch) -> None:
    _install_current_generation(monkeypatch, _record(repo_scope=("OTHER/Repository",)))
    with pytest.raises(
        ConversationSessionAuthoritySourceError,
        match="conversation_session_authority_verification_failed",
    ):
        with _lease(monkeypatch):
            pass


def _install_real_manifest_generation(monkeypatch, tmp_path: Path) -> tuple[Path, dict]:
    repo_root = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    (repo_root / ".git").mkdir(parents=True)
    runtime_root.mkdir()
    (repo_root / ".git" / "config").write_text(
        '[remote "origin"]\n\turl = https://github.com/FOUNDUPS/Foundups-Agent.git\n',
        encoding="ascii",
    )
    artifact = {
        "schema_version": "reddog_authority_runtime_resolver_supply.v1",
        "principals": {"principal-signature|principal_012": _record().to_dict()},
        "principal_count": 1,
        "resolver_supply_receipt_id": "sha256:" + "7" * 64,
        "no_holoindex_reindex_performed": True,
    }
    raw = json.dumps(
        artifact, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    artifact_path = runtime_root / "principal_authority_records.json"
    artifact_path.write_bytes(raw)
    active = {"leased": False}

    @contextmanager
    def _lease_generation(**_kwargs):
        active["leased"] = True
        try:
            yield {
                "repo_root": str(repo_root),
                "runtime_root": str(runtime_root),
                "manifest_id": "sha256:" + "c" * 64,
                "artifact_generation_digest": "sha256:" + "f" * 64,
                "principal_authority_records_path": str(artifact_path),
                "principal_authority_records_digest": raw_digest(raw),
            }
        finally:
            active["leased"] = False

    monkeypatch.setattr(
        "modules.communication.moltbot_bridge.src."
        "reddog_conversation_session_authority_source.lease_owner_e0_current_selection",
        _lease_generation,
    )
    return repo_root, active


def test_real_manifest_bound_principal_artifact_authenticates_session(
    monkeypatch, tmp_path: Path
) -> None:
    repo_root, active = _install_real_manifest_generation(monkeypatch, tmp_path)
    runtime_root = tmp_path / "runtime"

    with lease_current_generation_conversation_session(
        repo_root=repo_root,
        intent=_intent(),
        grounding_receipt_id="sha256:" + "d" * 64,
        serialized_credential=_credential(),
        owner_config_path=str(runtime_root / "owner.json"),
        now_epoch=NOW,
    ) as session:
        assert active["leased"] is True
        assert session.principal_record_digest.startswith("sha256:")
        assert session.authority_receipt["current_generation_manifest_id"] == (
            "sha256:" + "c" * 64
        )
    assert active["leased"] is False


def test_signed_session_has_no_process_local_persistence_key(monkeypatch) -> None:
    _install_current_generation(monkeypatch, _record())
    serialized = _credential()
    record = {"scope_record": "same-input"}
    with _lease(monkeypatch, credential=serialized) as first:
        first_result = sign_record_with_scope_authority(first.authority, record)
    with _lease(monkeypatch, credential=serialized) as second:
        second_result = sign_record_with_scope_authority(second.authority, record)
    assert first_result is None
    assert second_result is None


def test_production_source_has_no_hmac_or_signing_material() -> None:
    source = (
        REPO_ROOT
        / "modules/communication/moltbot_bridge/src/"
        / "reddog_conversation_session_authority_source.py"
    ).read_text(encoding="utf-8")
    assert "FOUNDUPS_INTAKE_HMAC_SECRET" not in source
    assert "private_key" not in source
    assert "print(" not in source
    assert "logging" not in source
