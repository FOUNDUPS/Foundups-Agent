"""Crash-recoverable two-phase publication of an architect FIX promotion."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_records import (
    canonical_digest,
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
    runtime_operation_lock,
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)

PUBLICATION_SCHEMA_VERSION = "reddog_architect_fix_promotion_publication.v1"
STAGED_PROFILE_SCHEMA_VERSION = "reddog_architect_fix_staged_profile.v1"
PUBLICATION_INTENT_PREPARED = "INTENT_PREPARED"
PUBLICATION_STATE_PREPARED = "STATE_PREPARED"
PUBLICATION_PROFILE_PUBLISHED = "PROFILE_PUBLISHED"
PUBLICATION_COMMITTED = "COMMITTED"
_JOURNAL_PHASES = {
    PUBLICATION_INTENT_PREPARED,
    PUBLICATION_STATE_PREPARED,
    PUBLICATION_PROFILE_PUBLISHED,
    PUBLICATION_COMMITTED,
}
_PUBLICATION_RECORD_FIELDS = {
    "schema_version",
    "publication_id",
    "state",
    "proposal_authenticity_attestation_id",
    "authority_profile_digest",
    "active_work_state_digest",
    "base_work_state_digest",
}
_STAGE_FIELDS = {
    "schema_version",
    "publication_id",
    "proposal_authenticity_attestation_id",
    "authority_profile_digest",
    "active_work_state_digest",
    "expected_work_state_revision",
    "authority_profile",
    "active_work_state",
    "receipt_id",
}
_JOURNAL_FIELDS = {
    "schema_version",
    "publication_id",
    "phase",
    "proposal_authenticity_attestation_id",
    "authority_profile_digest",
    "active_work_state_digest",
    "expected_work_state_revision",
    "prepared_revision",
    "committed_revision",
    "receipt_id",
}


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

    def publish(
        self,
        request: ArchitectFixPromotionPublicationRequest,
    ) -> str:
        with runtime_operation_lock(str(self.journal_path) + ".operation"):
            self._recover_unlocked()
            profile_digest = canonical_digest(request.authority_profile)
            _validate_request(request, profile_digest=profile_digest)
            stage = _stage_payload(request, profile_digest=profile_digest)
            current = self.work_state_store.load()
            record = _publication_record(
                current,
                publication_id=request.publication_id,
            )
            if record is not None:
                _validate_publication_record(record, stage)
                if record.get("state") == PUBLICATION_COMMITTED:
                    if not self._profile_matches(profile_digest):
                        raise RuntimeError(
                            "architect_fix_publication_committed_profile_mismatch"
                        )
                    return str(current.get("revision") or "")
                _validate_prepared_snapshot(current, record, stage)
            elif current.get("revision") != request.expected_work_state_revision:
                raise RuntimeError("architect_fix_publication_state_conflict")
            journal = _journal_payload(
                stage,
                phase=PUBLICATION_INTENT_PREPARED,
                prepared_revision=None,
                committed_revision=None,
            )
            self._write(self.stage_path, stage)
            self._write(self.journal_path, journal)
            return self._advance_unlocked(stage, journal)

    def recover(self) -> bool:
        """Complete or discard one interrupted publication."""

        with runtime_operation_lock(str(self.journal_path) + ".operation"):
            return self._recover_unlocked()

    def _recover_unlocked(self) -> bool:
        journal_exists = self.journal_path.exists()
        stage_exists = self.stage_path.exists()
        if not journal_exists and not stage_exists:
            return False
        if not stage_exists:
            journal = self._read(self.journal_path)
            _validate_journal(journal)
            current = self.work_state_store.load()
            record = _publication_record(
                current,
                publication_id=str(journal["publication_id"]),
            )
            if record is None:
                self._remove(self.journal_path)
                return True
            if record.get("state") == PUBLICATION_STATE_PREPARED:
                self._remove(self.journal_path)
                return True
            if (
                record.get("state") != PUBLICATION_COMMITTED
                or not self._profile_matches(journal["authority_profile_digest"])
            ):
                raise RuntimeError("architect_fix_publication_stage_missing")
            self._remove(self.journal_path)
            return True
        stage = self._read(self.stage_path)
        _validate_stage(stage)
        if journal_exists:
            journal = self._read(self.journal_path)
            _validate_journal(journal)
            _validate_stage_journal_binding(stage, journal)
        else:
            current = self.work_state_store.load()
            record = _publication_record(
                current,
                publication_id=str(stage["publication_id"]),
            )
            if record is None:
                self._remove(self.stage_path)
                return True
        current = self.work_state_store.load()
        record = _publication_record(
            current,
            publication_id=str(stage["publication_id"]),
        )
        if record is None:
            self._remove(self.stage_path)
            self._remove(self.journal_path)
            return True
        _validate_publication_record(record, stage)
        if record.get("state") == PUBLICATION_STATE_PREPARED:
            _validate_prepared_snapshot(current, record, stage)
            return False
        if (
            record.get("state") != PUBLICATION_COMMITTED
            or not self._profile_matches(stage["authority_profile_digest"])
        ):
            raise RuntimeError("architect_fix_publication_recovery_binding_invalid")
        self._remove(self.stage_path)
        self._remove(self.journal_path)
        return True

    def _advance_unlocked(
        self,
        stage: Mapping[str, Any],
        journal: Mapping[str, Any],
    ) -> str:
        current = self.work_state_store.load()
        record = _publication_record(
            current,
            publication_id=str(stage["publication_id"]),
        )
        if record is None:
            if current.get("revision") != stage.get(
                "expected_work_state_revision"
            ):
                raise RuntimeError("architect_fix_publication_state_conflict")
            prepared = _prepared_state(current, stage)
            prepared_revision = self.work_state_store.commit(
                prepared,
                expected_revision=stage.get("expected_work_state_revision"),
            )
            journal = _journal_payload(
                stage,
                phase=PUBLICATION_STATE_PREPARED,
                prepared_revision=prepared_revision,
                committed_revision=None,
            )
            self._write(self.journal_path, journal)
            current = self.work_state_store.load()
            record = _publication_record(
                current,
                publication_id=str(stage["publication_id"]),
            )
        assert record is not None
        _validate_publication_record(record, stage)
        if record.get("state") == PUBLICATION_COMMITTED:
            if not self._profile_matches(stage["authority_profile_digest"]):
                raise RuntimeError(
                    "architect_fix_publication_committed_profile_mismatch"
                )
            revision = str(current.get("revision") or "")
            self._remove(self.stage_path)
            self._remove(self.journal_path)
            return revision
        if record.get("state") != PUBLICATION_STATE_PREPARED:
            raise RuntimeError("architect_fix_publication_state_invalid")
        _validate_prepared_snapshot(current, record, stage)
        self._publish_profile(stage)
        journal = _journal_payload(
            stage,
            phase=PUBLICATION_PROFILE_PUBLISHED,
            prepared_revision=str(current.get("revision") or ""),
            committed_revision=None,
        )
        self._write(self.journal_path, journal)
        active = _committed_state(stage)
        revision = self.work_state_store.commit(
            active,
            expected_revision=current.get("revision"),
        )
        committed_journal = _journal_payload(
            stage,
            phase=PUBLICATION_COMMITTED,
            prepared_revision=str(current.get("revision") or ""),
            committed_revision=revision,
        )
        self._write(self.journal_path, committed_journal)
        self._remove(self.stage_path)
        self._remove(self.journal_path)
        return revision

    def _publish_profile(self, stage: Mapping[str, Any]) -> None:
        profile = stage.get("authority_profile")
        if not isinstance(profile, Mapping):
            raise RuntimeError("architect_fix_publication_profile_invalid")
        self._write(self.authority_profile_path, profile)
        if not self._profile_matches(stage["authority_profile_digest"]):
            raise RuntimeError("architect_fix_publication_profile_verify_failed")

    def _profile_matches(self, expected_digest: Any) -> bool:
        if not self.authority_profile_path.exists():
            return False
        return (
            canonical_digest(self._read(self.authority_profile_path))
            == expected_digest
        )

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

    def _sibling(self, suffix: str) -> Path:
        return validate_runtime_artifact_path(
            self.authority_profile_path.with_name(
                self.authority_profile_path.name + suffix
            ),
            repo_root=self.repo_root,
            allowed_root=self.runtime_root,
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


def _publication_binding(
    stage: Mapping[str, Any],
    *,
    state: str,
    base_work_state_digest: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": PUBLICATION_SCHEMA_VERSION,
        "publication_id": stage["publication_id"],
        "state": state,
        "proposal_authenticity_attestation_id": stage[
            "proposal_authenticity_attestation_id"
        ],
        "authority_profile_digest": stage["authority_profile_digest"],
        "active_work_state_digest": stage["active_work_state_digest"],
        "base_work_state_digest": base_work_state_digest,
    }


def _validate_prepared_snapshot(
    current: Mapping[str, Any],
    record: Mapping[str, Any],
    stage: Mapping[str, Any],
) -> None:
    without_publication = _without_revision(current)
    without_publication["architect_fix_publications"] = [
        dict(item)
        for item in without_publication.get("architect_fix_publications") or ()
        if isinstance(item, Mapping)
        and item.get("publication_id") != stage["publication_id"]
    ]
    if not without_publication["architect_fix_publications"]:
        without_publication.pop("architect_fix_publications", None)
    if canonical_digest(without_publication) != record.get(
        "base_work_state_digest"
    ):
        raise RuntimeError("architect_fix_publication_prepared_state_changed")


def _validate_publication_record(
    record: Mapping[str, Any],
    stage: Mapping[str, Any],
) -> None:
    state = record.get("state")
    if (
        set(record) != _PUBLICATION_RECORD_FIELDS
        or record.get("schema_version") != PUBLICATION_SCHEMA_VERSION
        or not _is_sha256(record.get("publication_id"))
        or not _is_attestation_id(
            record.get("proposal_authenticity_attestation_id")
        )
        or not _is_sha256(record.get("authority_profile_digest"))
        or not _is_sha256(record.get("active_work_state_digest"))
        or record.get("publication_id") != stage.get("publication_id")
        or record.get("proposal_authenticity_attestation_id")
        != stage.get("proposal_authenticity_attestation_id")
        or record.get("authority_profile_digest")
        != stage.get("authority_profile_digest")
        or record.get("active_work_state_digest")
        != stage.get("active_work_state_digest")
        or state not in {PUBLICATION_STATE_PREPARED, PUBLICATION_COMMITTED}
        or (
            state == PUBLICATION_STATE_PREPARED
            and not _is_sha256(record.get("base_work_state_digest"))
        )
        or (
            state == PUBLICATION_COMMITTED
            and record.get("base_work_state_digest") is not None
        )
    ):
        raise RuntimeError("architect_fix_publication_state_binding_invalid")


def _validate_journal(journal: Mapping[str, Any]) -> None:
    unsigned = dict(journal)
    receipt_id = str(unsigned.pop("receipt_id", ""))
    phase = journal.get("phase")
    if (
        set(journal) != _JOURNAL_FIELDS
        or journal.get("schema_version") != PUBLICATION_SCHEMA_VERSION
        or phase not in _JOURNAL_PHASES
        or not _is_sha256(journal.get("publication_id"))
        or not _is_attestation_id(
            journal.get("proposal_authenticity_attestation_id")
        )
        or not _is_sha256(journal.get("authority_profile_digest"))
        or not _is_sha256(journal.get("active_work_state_digest"))
        or not _is_optional_revision(journal.get("expected_work_state_revision"))
        or not _journal_revisions_match_phase(journal, phase=phase)
        or not _is_sha256(receipt_id)
        or receipt_id != canonical_digest(unsigned)
    ):
        raise RuntimeError("architect_fix_publication_journal_invalid")


def _validate_stage(stage: Mapping[str, Any]) -> None:
    unsigned = dict(stage)
    receipt_id = str(unsigned.pop("receipt_id", ""))
    profile = stage.get("authority_profile")
    active = stage.get("active_work_state")
    if (
        set(stage) != _STAGE_FIELDS
        or stage.get("schema_version") != STAGED_PROFILE_SCHEMA_VERSION
        or receipt_id != canonical_digest(unsigned)
        or not _is_sha256(stage.get("publication_id"))
        or not _is_attestation_id(
            stage.get("proposal_authenticity_attestation_id")
        )
        or not _is_sha256(stage.get("authority_profile_digest"))
        or not _is_sha256(stage.get("active_work_state_digest"))
        or not _is_optional_revision(stage.get("expected_work_state_revision"))
        or not _is_sha256(receipt_id)
        or not isinstance(profile, Mapping)
        or not isinstance(active, Mapping)
        or canonical_digest(profile) != stage.get("authority_profile_digest")
        or canonical_digest(
            architect_fix_publication_state_projection(
                active,
                publication_id=str(stage.get("publication_id") or ""),
            )
        )
        != stage.get("active_work_state_digest")
    ):
        raise RuntimeError("architect_fix_publication_stage_invalid")


def _validate_stage_journal_binding(
    stage: Mapping[str, Any],
    journal: Mapping[str, Any],
) -> None:
    for key in (
        "publication_id",
        "proposal_authenticity_attestation_id",
        "authority_profile_digest",
        "active_work_state_digest",
        "expected_work_state_revision",
    ):
        if stage.get(key) != journal.get(key):
            raise RuntimeError("architect_fix_publication_journal_binding_invalid")


def _publication_record(
    snapshot: Mapping[str, Any],
    *,
    publication_id: str,
) -> Mapping[str, Any] | None:
    matches = [
        item
        for item in snapshot.get("architect_fix_publications") or ()
        if isinstance(item, Mapping)
        and str(item.get("publication_id") or "") == publication_id
    ]
    if len(matches) > 1:
        raise RuntimeError("architect_fix_publication_record_ambiguous")
    return matches[0] if matches else None


def _promotion_record(
    snapshot: Mapping[str, Any],
    *,
    publication_id: str,
) -> Mapping[str, Any] | None:
    matches = [
        item
        for item in snapshot.get("architect_fix_promotions") or ()
        if isinstance(item, Mapping)
        and str(item.get("publication_id") or "") == publication_id
    ]
    if len(matches) > 1:
        raise RuntimeError("architect_fix_promotion_record_ambiguous")
    return matches[0] if matches else None


def architect_fix_publication_state_projection(
    snapshot: Mapping[str, Any],
    *,
    publication_id: str,
) -> dict[str, Any]:
    """Return the immutable promotion lineage bound by one publication."""

    promotion = _promotion_record(
        snapshot,
        publication_id=publication_id,
    )
    if promotion is None:
        raise ValueError("architect_fix_publication_record_missing")
    queue_item_id = str(promotion.get("queue_item_id") or "")
    claim_id = str(promotion.get("claim_id") or "")
    promotions = _exact_records(
        snapshot.get("architect_fix_promotions"),
        "publication_id",
        publication_id,
    )
    queue_items = _exact_records(
        snapshot.get("wre_queue_items"),
        "queue_item_id",
        queue_item_id,
    )
    claims = _exact_records(
        snapshot.get("worker_claims"),
        "claim_id",
        claim_id,
    )
    if (
        not _is_sha256(publication_id)
        or not _is_sha256(queue_item_id)
        or not _is_sha256(claim_id)
        or len(promotions) != 1
        or len(queue_items) != 1
        or len(claims) != 1
        or str(queue_items[0].get("claim_id") or "") != claim_id
        or str(claims[0].get("claim_id") or "") != claim_id
    ):
        raise ValueError("architect_fix_publication_lineage_invalid")
    return {
        "schema_version": str(snapshot.get("schema_version") or ""),
        "publication_id": publication_id,
        "promotion": dict(promotions[0]),
        "queue_item": dict(queue_items[0]),
        "worker_claim": dict(claims[0]),
    }


def _exact_records(
    values: Any,
    field: str,
    expected: str,
) -> list[Mapping[str, Any]]:
    return [
        item
        for item in values or ()
        if isinstance(item, Mapping)
        and str(item.get(field) or "") == expected
    ]


def _is_sha256(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 71 and text.startswith("sha256:") and all(
        char in "0123456789abcdef" for char in text[7:]
    )


def _is_revision(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 64 and all(
        char in "0123456789abcdef" for char in text
    )


def _is_optional_revision(value: Any) -> bool:
    return value is None or _is_revision(value)


def _journal_revisions_match_phase(
    journal: Mapping[str, Any],
    *,
    phase: Any,
) -> bool:
    prepared = journal.get("prepared_revision")
    committed = journal.get("committed_revision")
    if phase == PUBLICATION_INTENT_PREPARED:
        return prepared is None and committed is None
    if phase in {PUBLICATION_STATE_PREPARED, PUBLICATION_PROFILE_PUBLISHED}:
        return _is_revision(prepared) and committed is None
    if phase == PUBLICATION_COMMITTED:
        return _is_revision(prepared) and _is_revision(committed)
    return False


def _is_attestation_id(value: Any) -> bool:
    text = str(value or "")
    prefix = "reddog_architect_proposal_attestation_"
    suffix = text.removeprefix(prefix)
    return (
        text.startswith(prefix)
        and len(suffix) == 32
        and all(char in "0123456789abcdef" for char in suffix)
    )


def _without_revision(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    payload = json.loads(json.dumps(snapshot, sort_keys=True))
    payload.pop("revision", None)
    return payload


__all__ = [
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
