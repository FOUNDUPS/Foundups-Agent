"""Crash-recoverable two-phase publication of an architect FIX promotion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_records import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_publication_validation import (
    PUBLICATION_COMMITTED,
    PUBLICATION_INTENT_PREPARED,
    PUBLICATION_PROFILE_PUBLISHED,
    PUBLICATION_SCHEMA_VERSION,
    PUBLICATION_STATE_PREPARED,
    STAGED_PROFILE_SCHEMA_VERSION,
    architect_fix_committed_publication_reasons,
    architect_fix_publication_state_projection,
    is_attestation_id as _is_attestation_id,
    is_sha256 as _is_sha256,
    _promotion_record,
    publication_binding as _publication_binding,
    publication_record as _publication_record,
    validate_committed_snapshot as _validate_committed_snapshot,
    validate_journal as _validate_journal,
    validate_journal_record_binding as _validate_journal_record_binding,
    validate_prepared_snapshot as _validate_prepared_snapshot,
    validate_publication_record as _validate_publication_record,
    validate_stage as _validate_stage,
    validate_stage_journal_binding as _validate_stage_journal_binding,
    without_revision as _without_revision,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_refresh_runtime import (
    AuthoritativeWorkStateStore,
)
from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    atomic_replace_confined_mapping,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_json_read import (
    read_reddog_runtime_json_mapping,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    confined_runtime_operation_lock,
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)



@dataclass(frozen=True)
class ArchitectFixPromotionPublicationRequest:
    publication_id: str
    proposal_authenticity_attestation_id: str
    authority_profile: Mapping[str, Any]
    updated_work_state: Mapping[str, Any]
    expected_work_state_revision: str | None


class AtomicArchitectFixPromotionPublisher:
    """Publish a profile and queue state through PREPARED -> COMMITTED."""

    def __init__(
        self,
        *,
        repo_root: str | Path,
        runtime_root: str | Path,
        authority_profile_path: str | Path,
        work_state_store: AuthoritativeWorkStateStore,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.runtime_root = validate_runtime_root_path(
            runtime_root,
            repo_root=self.repo_root,
        )
        self.authority_profile_path = validate_runtime_artifact_path(
            authority_profile_path,
            repo_root=self.repo_root,
            allowed_root=self.runtime_root,
        )
        self.work_state_store = work_state_store
        self.journal_path = self._sibling(".publication.json")
        self.stage_path = self._sibling(".staged.json")
        self.operation_lock_path = self._sibling(".publication.operation.lock")

    def publish(
        self,
        request: ArchitectFixPromotionPublicationRequest,
    ) -> str:
        with self._operation_lock(self.operation_lock_path):
            return _publish_unlocked(self, request)

    def recover(self) -> bool:
        """Rollback or clean one interruption without creating authority."""

        with self._operation_lock(self.operation_lock_path):
            return _recover_unlocked(self)

    def _publish_profile(self, stage: Mapping[str, Any]) -> None:
        _publish_profile_artifact(self, stage)

    def _publish_profile_cache(self, stage: Mapping[str, Any]) -> None:
        _publish_profile_cache(self, stage)

    def _profile_matches(self, expected_digest: Any) -> bool:
        return _profile_matches(self, expected_digest)

    def _profile_artifact_path(self, expected_digest: Any) -> Path:
        return _profile_artifact_path(self, expected_digest)

    def _read(self, path: Path) -> dict[str, Any]:
        return dict(
            read_reddog_runtime_json_mapping(
                path,
                allowed_root=self.runtime_root,
            )
        )

    def _write(self, path: Path, payload: Mapping[str, Any]) -> None:
        atomic_replace_confined_mapping(
            path,
            payload,
            allowed_root=self.runtime_root,
            repo_root=self.repo_root,
        )

    def _remove(self, path: Path) -> None:
        validated = validate_runtime_artifact_path(
            path,
            repo_root=self.repo_root,
            allowed_root=self.runtime_root,
        )
        validated.unlink(missing_ok=True)

    def _operation_lock(self, path: Path):
        return confined_runtime_operation_lock(
            path,
            repo_root=self.repo_root,
            allowed_root=self.runtime_root,
        )

    def _sibling(self, suffix: str) -> Path:
        return validate_runtime_artifact_path(
            self.authority_profile_path.with_name(
                self.authority_profile_path.name + suffix
            ),
            repo_root=self.repo_root,
            allowed_root=self.runtime_root,
        )


def _publish_unlocked(
    publisher: AtomicArchitectFixPromotionPublisher,
    request: ArchitectFixPromotionPublicationRequest,
) -> str:
    _recover_unlocked(publisher)
    profile_digest = canonical_digest(request.authority_profile)
    _validate_request(request, profile_digest=profile_digest)
    stage = _stage_payload(request, profile_digest=profile_digest)
    current = publisher.work_state_store.load()
    record = _publication_record(
        current,
        publication_id=request.publication_id,
    )
    if record is not None:
        _validate_publication_record(record, stage)
        if record.get("state") == PUBLICATION_COMMITTED:
            return _complete_committed(publisher, stage, current)
        _validate_prepared_snapshot(current, record, stage)
    elif current.get("revision") != request.expected_work_state_revision:
        raise RuntimeError("architect_fix_publication_state_conflict")
    journal = _journal_payload(
        stage,
        phase=PUBLICATION_INTENT_PREPARED,
        prepared_revision=None,
        committed_revision=None,
    )
    publisher._write(publisher.stage_path, stage)
    publisher._write(publisher.journal_path, journal)
    return _advance_unlocked(publisher, stage)


def _recover_unlocked(
    publisher: AtomicArchitectFixPromotionPublisher,
) -> bool:
    journal_exists = publisher.journal_path.exists()
    stage_exists = publisher.stage_path.exists()
    if not journal_exists and not stage_exists:
        return False
    if not stage_exists:
        return _recover_without_stage(publisher)
    stage = publisher._read(publisher.stage_path)
    _validate_stage(stage)
    if journal_exists:
        journal = publisher._read(publisher.journal_path)
        _validate_journal(journal)
        _validate_stage_journal_binding(stage, journal)
    return _recover_with_stage(publisher, stage)


def _recover_without_stage(
    publisher: AtomicArchitectFixPromotionPublisher,
) -> bool:
    journal = publisher._read(publisher.journal_path)
    _validate_journal(journal)
    current = publisher.work_state_store.load()
    record = _publication_record(
        current,
        publication_id=str(journal["publication_id"]),
    )
    if record is None:
        publisher._remove(publisher.journal_path)
        return True
    _validate_journal_record_binding(journal, record)
    if record.get("state") == PUBLICATION_STATE_PREPARED:
        _rollback_prepared(publisher, current, record)
        publisher._remove(publisher.journal_path)
        return True
    if record.get("state") != PUBLICATION_COMMITTED:
        raise RuntimeError("architect_fix_publication_stage_missing")
    _validate_committed_snapshot(current, record)
    publisher._remove(publisher.journal_path)
    return True


def _recover_with_stage(
    publisher: AtomicArchitectFixPromotionPublisher,
    stage: Mapping[str, Any],
) -> bool:
    current = publisher.work_state_store.load()
    record = _publication_record(
        current,
        publication_id=str(stage["publication_id"]),
    )
    if record is None:
        _discard_unanchored(publisher, stage)
        return True
    _validate_publication_record(record, stage)
    if record.get("state") == PUBLICATION_STATE_PREPARED:
        _rollback_prepared(publisher, current, record)
        _discard_unanchored(publisher, stage)
        return True
    if record.get("state") != PUBLICATION_COMMITTED:
        raise RuntimeError("architect_fix_publication_recovery_binding_invalid")
    _validate_committed_snapshot(current, record)
    publisher._remove(publisher.stage_path)
    publisher._remove(publisher.journal_path)
    return True


def _rollback_prepared(
    publisher: AtomicArchitectFixPromotionPublisher,
    current: Mapping[str, Any],
    record: Mapping[str, Any],
) -> None:
    rolled_back = _without_revision(current)
    rolled_back["architect_fix_publications"] = [
        dict(item)
        for item in rolled_back.get("architect_fix_publications") or ()
        if not (
            isinstance(item, Mapping)
            and item.get("publication_id") == record.get("publication_id")
        )
    ]
    if not rolled_back["architect_fix_publications"]:
        rolled_back.pop("architect_fix_publications")
    publisher.work_state_store.commit(
        rolled_back,
        expected_revision=current.get("revision"),
    )


def _discard_unanchored(
    publisher: AtomicArchitectFixPromotionPublisher,
    stage: Mapping[str, Any],
) -> None:
    del stage
    publisher._remove(publisher.stage_path)
    publisher._remove(publisher.journal_path)


def _advance_unlocked(
    publisher: AtomicArchitectFixPromotionPublisher,
    stage: Mapping[str, Any],
) -> str:
    current, record = _prepare_publication_state(publisher, stage)
    _validate_publication_record(record, stage)
    if record.get("state") == PUBLICATION_COMMITTED:
        return _complete_committed(publisher, stage, current)
    if record.get("state") != PUBLICATION_STATE_PREPARED:
        raise RuntimeError("architect_fix_publication_state_invalid")
    _validate_prepared_snapshot(current, record, stage)
    return _commit_prepared_publication(publisher, stage, current)


def _prepare_publication_state(
    publisher: AtomicArchitectFixPromotionPublisher,
    stage: Mapping[str, Any],
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    current = publisher.work_state_store.load()
    record = _publication_record(
        current,
        publication_id=str(stage["publication_id"]),
    )
    if record is None:
        expected = stage.get("expected_work_state_revision")
        if current.get("revision") != expected:
            raise RuntimeError("architect_fix_publication_state_conflict")
        revision = publisher.work_state_store.commit(
            _prepared_state(current, stage),
            expected_revision=expected,
        )
        publisher._write(
            publisher.journal_path,
            _journal_payload(
                stage,
                phase=PUBLICATION_STATE_PREPARED,
                prepared_revision=revision,
                committed_revision=None,
            ),
        )
        current = publisher.work_state_store.load()
        record = _publication_record(
            current,
            publication_id=str(stage["publication_id"]),
        )
    if record is None:
        raise RuntimeError("architect_fix_publication_state_missing")
    return current, record


def _commit_prepared_publication(
    publisher: AtomicArchitectFixPromotionPublisher,
    stage: Mapping[str, Any],
    current: Mapping[str, Any],
) -> str:
    publisher._publish_profile(stage)
    prepared_revision = str(current.get("revision") or "")
    publisher._write(
        publisher.journal_path,
        _journal_payload(
            stage,
            phase=PUBLICATION_PROFILE_PUBLISHED,
            prepared_revision=prepared_revision,
            committed_revision=None,
        ),
    )
    revision = publisher.work_state_store.commit(
        _committed_state(stage),
        expected_revision=current.get("revision"),
    )
    publisher._write(
        publisher.journal_path,
        _journal_payload(
            stage,
            phase=PUBLICATION_COMMITTED,
            prepared_revision=prepared_revision,
            committed_revision=revision,
        ),
    )
    publisher._publish_profile_cache(stage)
    publisher._remove(publisher.stage_path)
    publisher._remove(publisher.journal_path)
    return revision


def _publish_profile_artifact(
    publisher: AtomicArchitectFixPromotionPublisher,
    stage: Mapping[str, Any],
) -> None:
    profile = stage.get("authority_profile")
    if not isinstance(profile, Mapping):
        raise RuntimeError("architect_fix_publication_profile_invalid")
    artifact = publisher._profile_artifact_path(
        stage["authority_profile_digest"]
    )
    if artifact.exists():
        if canonical_digest(publisher._read(artifact)) != stage[
            "authority_profile_digest"
        ]:
            raise RuntimeError(
                "architect_fix_publication_profile_artifact_conflict"
            )
        return
    _write_profile_mapping(publisher, artifact, profile)
    if canonical_digest(publisher._read(artifact)) != stage[
        "authority_profile_digest"
    ]:
        raise RuntimeError("architect_fix_publication_profile_verify_failed")


def _publish_profile_cache(
    publisher: AtomicArchitectFixPromotionPublisher,
    stage: Mapping[str, Any],
) -> None:
    _publish_profile_cache_digest(
        publisher,
        stage["authority_profile_digest"],
    )


def _publish_profile_cache_digest(
    publisher: AtomicArchitectFixPromotionPublisher,
    expected_digest: Any,
) -> None:
    artifact = publisher._profile_artifact_path(expected_digest)
    if not artifact.exists():
        raise RuntimeError(
            "architect_fix_publication_profile_artifact_missing"
        )
    profile = publisher._read(artifact)
    if canonical_digest(profile) != expected_digest:
        raise RuntimeError(
            "architect_fix_publication_profile_artifact_mismatch"
        )
    _write_profile_mapping(
        publisher,
        publisher.authority_profile_path,
        profile,
    )
    if not publisher._profile_matches(expected_digest):
        raise RuntimeError("architect_fix_publication_profile_verify_failed")


def _complete_committed(
    publisher: AtomicArchitectFixPromotionPublisher,
    stage: Mapping[str, Any],
    current: Mapping[str, Any],
) -> str:
    publisher._publish_profile(stage)
    publisher._publish_profile_cache(stage)
    publisher._remove(publisher.stage_path)
    publisher._remove(publisher.journal_path)
    return str(current.get("revision") or "")


def _profile_matches(
    publisher: AtomicArchitectFixPromotionPublisher,
    expected_digest: Any,
) -> bool:
    if not publisher.authority_profile_path.exists():
        return False
    return (
        canonical_digest(publisher._read(publisher.authority_profile_path))
        == expected_digest
    )


def _profile_artifact_path(
    publisher: AtomicArchitectFixPromotionPublisher,
    expected_digest: Any,
) -> Path:
    digest = str(expected_digest or "")
    if not _is_sha256(digest):
        raise RuntimeError("architect_fix_publication_profile_digest_invalid")
    return publisher._sibling(f".{digest[7:]}.immutable.json")


def _write_profile_mapping(
    publisher: AtomicArchitectFixPromotionPublisher,
    path: Path,
    payload: Mapping[str, Any],
) -> None:
    lock_path = validate_runtime_artifact_path(
        path.with_name(path.name + ".operation.lock"),
        repo_root=publisher.repo_root,
        allowed_root=publisher.runtime_root,
    )
    with publisher._operation_lock(lock_path):
        atomic_replace_confined_mapping(
            path,
            payload,
            allowed_root=publisher.runtime_root,
            repo_root=publisher.repo_root,
        )


def _validate_request(
    request: ArchitectFixPromotionPublicationRequest,
    *,
    profile_digest: str,
) -> None:
    if (
        not _is_sha256(request.publication_id)
        or not _is_attestation_id(
            request.proposal_authenticity_attestation_id
        )
    ):
        raise ValueError("architect_fix_publication_id_invalid")
    record = _promotion_record(
        request.updated_work_state,
        publication_id=request.publication_id,
    )
    if record is None:
        raise ValueError("architect_fix_publication_record_missing")
    if (
        str(record.get("authority_profile_digest") or "") != profile_digest
        or str(record.get("proposal_authenticity_attestation_id") or "")
        != request.proposal_authenticity_attestation_id
    ):
        raise ValueError("architect_fix_publication_record_binding_invalid")


def _stage_payload(
    request: ArchitectFixPromotionPublicationRequest,
    *,
    profile_digest: str,
) -> dict[str, Any]:
    active_state = _without_revision(request.updated_work_state)
    active_projection = architect_fix_publication_state_projection(
        active_state,
        publication_id=request.publication_id,
    )
    body = {
        "schema_version": STAGED_PROFILE_SCHEMA_VERSION,
        "publication_id": request.publication_id,
        "proposal_authenticity_attestation_id": (
            request.proposal_authenticity_attestation_id
        ),
        "authority_profile_digest": profile_digest,
        "active_work_state_digest": canonical_digest(active_projection),
        "expected_work_state_revision": request.expected_work_state_revision,
        "authority_profile": dict(request.authority_profile),
        "active_work_state": active_state,
    }
    body["receipt_id"] = canonical_digest(body)
    return body


def _journal_payload(
    stage: Mapping[str, Any],
    *,
    phase: str,
    prepared_revision: str | None,
    committed_revision: str | None,
) -> dict[str, Any]:
    body = {
        "schema_version": PUBLICATION_SCHEMA_VERSION,
        "publication_id": stage["publication_id"],
        "phase": phase,
        "proposal_authenticity_attestation_id": stage[
            "proposal_authenticity_attestation_id"
        ],
        "authority_profile_digest": stage["authority_profile_digest"],
        "active_work_state_digest": stage["active_work_state_digest"],
        "expected_work_state_revision": stage[
            "expected_work_state_revision"
        ],
        "prepared_revision": prepared_revision,
        "committed_revision": committed_revision,
    }
    body["receipt_id"] = canonical_digest(body)
    return body


def _prepared_state(
    current: Mapping[str, Any],
    stage: Mapping[str, Any],
) -> dict[str, Any]:
    base = _without_revision(current)
    base_digest = canonical_digest(base)
    publication = _publication_binding(
        stage,
        state=PUBLICATION_STATE_PREPARED,
        base_work_state_digest=base_digest,
    )
    base["architect_fix_publications"] = [
        dict(item)
        for item in base.get("architect_fix_publications") or ()
        if isinstance(item, Mapping)
        and item.get("publication_id") != stage["publication_id"]
    ] + [publication]
    return base


def _committed_state(stage: Mapping[str, Any]) -> dict[str, Any]:
    active = _without_revision(stage["active_work_state"])
    active["architect_fix_publications"] = [
        dict(item)
        for item in active.get("architect_fix_publications") or ()
        if isinstance(item, Mapping)
        and item.get("publication_id") != stage["publication_id"]
    ] + [
        _publication_binding(
            stage,
            state=PUBLICATION_COMMITTED,
            base_work_state_digest=None,
        )
    ]
    return active


__all__ = [
    "architect_fix_committed_publication_reasons",
    "architect_fix_publication_state_projection",
    "ArchitectFixPromotionPublicationRequest",
    "AtomicArchitectFixPromotionPublisher",
    "PUBLICATION_COMMITTED",
    "PUBLICATION_INTENT_PREPARED",
    "PUBLICATION_PROFILE_PUBLISHED",
    "PUBLICATION_SCHEMA_VERSION",
    "PUBLICATION_STATE_PREPARED",
    "STAGED_PROFILE_SCHEMA_VERSION",
]
