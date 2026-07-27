"""Crash and tamper tests for architect FIX two-phase publication."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_publication import (
    ArchitectFixPromotionPublicationRequest,
    AtomicArchitectFixPromotionPublisher,
    architect_fix_publication_state_projection,
)
from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_records import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    AtomicJsonAuthorityRuntimeStore,
)


class SimulatedCrash(BaseException):
    pass


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    return repo


def _runtime(
    tmp_path: Path,
) -> tuple[
    Path,
    AtomicJsonAuthorityRuntimeStore,
    AtomicArchitectFixPromotionPublisher,
]:
    repo = _repo(tmp_path)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    store = AtomicJsonAuthorityRuntimeStore(
        runtime / "work_state.json",
        allowed_root=runtime,
        repo_root=repo,
    )
    store.commit(
        {
            "schema_version": "reddog_authoritative_work_state.v1",
            "architect_fix_promotions": [],
        },
        expected_revision=None,
    )
    publisher = AtomicArchitectFixPromotionPublisher(
        repo_root=repo,
        runtime_root=runtime,
        authority_profile_path=runtime / "authority_profile.json",
        work_state_store=store,
    )
    return runtime, store, publisher


def _request(
    store: AtomicJsonAuthorityRuntimeStore,
    *,
    publication_id: str = "sha256:" + "1" * 64,
) -> ArchitectFixPromotionPublicationRequest:
    current = store.load()
    attestation_id = (
        "reddog_architect_proposal_attestation_" + "2" * 32
    )
    queue_item_id = "sha256:" + "3" * 64
    claim_id = "sha256:" + "4" * 64
    profile = {
        "schema_version": "reddog_authority_profile.v1",
        "promotion_publication_id": publication_id,
        "queue_item_id": queue_item_id,
    }
    profile_digest = canonical_digest(profile)
    updated = json.loads(json.dumps(current, sort_keys=True))
    updated.pop("revision", None)
    updated["architect_fix_promotions"] = [
        {
            "publication_id": publication_id,
            "queue_item_id": queue_item_id,
            "claim_id": claim_id,
            "authority_profile_digest": profile_digest,
            "proposal_authenticity_attestation_id": attestation_id,
        }
    ]
    updated["wre_queue_items"] = [
        {
            "queue_item_id": queue_item_id,
            "claim_id": claim_id,
        }
    ]
    updated["worker_claims"] = [{"claim_id": claim_id}]
    return ArchitectFixPromotionPublicationRequest(
        publication_id=publication_id,
        proposal_authenticity_attestation_id=attestation_id,
        authority_profile=profile,
        updated_work_state=updated,
        expected_work_state_revision=current["revision"],
    )


def test_publication_commits_state_then_profile_and_cleans_journal(
    tmp_path: Path,
) -> None:
    runtime, store, publisher = _runtime(tmp_path)
    request = _request(store)

    revision = publisher.publish(request)

    assert store.load()["revision"] == revision
    assert json.loads(
        (runtime / "authority_profile.json").read_text(encoding="utf-8")
    ) == request.authority_profile
    assert not publisher.journal_path.exists()
    assert not publisher.stage_path.exists()


def test_restart_discards_unanchored_artifacts_before_state_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, store, publisher = _runtime(tmp_path)
    request = _request(store)
    monkeypatch.setattr(
        store,
        "commit",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(SimulatedCrash()),
    )
    with pytest.raises(SimulatedCrash):
        publisher.publish(request)

    recovered_store = AtomicJsonAuthorityRuntimeStore(
        runtime / "work_state.json",
        allowed_root=runtime,
        repo_root=tmp_path / "repo",
    )
    recovered = AtomicArchitectFixPromotionPublisher(
        repo_root=tmp_path / "repo",
        runtime_root=runtime,
        authority_profile_path=runtime / "authority_profile.json",
        work_state_store=recovered_store,
    )
    assert recovered.recover() is True
    assert "architect_fix_publications" not in recovered_store.load()
    assert not (runtime / "authority_profile.json").exists()
    assert not recovered.journal_path.exists()
    assert not recovered.stage_path.exists()
    recovered.publish(request)
    assert recovered_store.load()["architect_fix_publications"][0][
        "state"
    ] == "COMMITTED"


def test_restart_completes_profile_when_state_commit_precedes_crash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, store, publisher = _runtime(tmp_path)
    request = _request(store)

    monkeypatch.setattr(
        publisher,
        "_publish_profile",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(SimulatedCrash()),
    )
    with pytest.raises(SimulatedCrash):
        publisher.publish(request)

    recovered = AtomicArchitectFixPromotionPublisher(
        repo_root=tmp_path / "repo",
        runtime_root=runtime,
        authority_profile_path=runtime / "authority_profile.json",
        work_state_store=store,
    )
    assert recovered.recover() is False
    assert not (runtime / "authority_profile.json").exists()
    recovered.publish(request)
    assert json.loads(
        (runtime / "authority_profile.json").read_text(encoding="utf-8")
    ) == request.authority_profile
    assert not recovered.journal_path.exists()
    assert not recovered.stage_path.exists()


def test_restart_finishes_cleanup_when_profile_was_already_published(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, store, publisher = _runtime(tmp_path)
    request = _request(store)
    real_remove = publisher._remove

    def crash_before_journal_removal(path: Path) -> None:
        if path == publisher.journal_path:
            raise SimulatedCrash()
        real_remove(path)

    monkeypatch.setattr(publisher, "_remove", crash_before_journal_removal)
    with pytest.raises(SimulatedCrash):
        publisher.publish(request)
    assert (runtime / "authority_profile.json").exists()
    assert publisher.journal_path.exists()
    assert not publisher.stage_path.exists()

    recovered = AtomicArchitectFixPromotionPublisher(
        repo_root=tmp_path / "repo",
        runtime_root=runtime,
        authority_profile_path=runtime / "authority_profile.json",
        work_state_store=store,
    )
    assert recovered.recover() is True
    assert not recovered.journal_path.exists()
    assert json.loads(
        (runtime / "authority_profile.json").read_text(encoding="utf-8")
    ) == request.authority_profile


def test_tampered_stage_fails_closed_after_state_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, store, publisher = _runtime(tmp_path)
    request = _request(store)
    monkeypatch.setattr(
        publisher,
        "_publish_profile",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(SimulatedCrash()),
    )
    with pytest.raises(SimulatedCrash):
        publisher.publish(request)
    stage = json.loads(publisher.stage_path.read_text(encoding="utf-8"))
    stage["authority_profile"]["queue_item_id"] = "queue:attacker"
    publisher.stage_path.write_text(
        json.dumps(stage, sort_keys=True),
        encoding="utf-8",
    )

    recovered = AtomicArchitectFixPromotionPublisher(
        repo_root=tmp_path / "repo",
        runtime_root=runtime,
        authority_profile_path=runtime / "authority_profile.json",
        work_state_store=store,
    )
    with pytest.raises(RuntimeError, match="stage_invalid"):
        recovered.recover()
    assert not (runtime / "authority_profile.json").exists()


def test_tampered_journal_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, store, publisher = _runtime(tmp_path)
    request = _request(store)
    monkeypatch.setattr(
        store,
        "commit",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(SimulatedCrash()),
    )
    with pytest.raises(SimulatedCrash):
        publisher.publish(request)
    journal = json.loads(publisher.journal_path.read_text(encoding="utf-8"))
    journal["authority_profile_digest"] = "sha256:" + "9" * 64
    publisher.journal_path.write_text(
        json.dumps(journal, sort_keys=True),
        encoding="utf-8",
    )

    recovered_store = AtomicJsonAuthorityRuntimeStore(
        runtime / "work_state.json",
        allowed_root=runtime,
        repo_root=tmp_path / "repo",
    )
    recovered = AtomicArchitectFixPromotionPublisher(
        repo_root=tmp_path / "repo",
        runtime_root=runtime,
        authority_profile_path=runtime / "authority_profile.json",
        work_state_store=recovered_store,
    )
    with pytest.raises(RuntimeError, match="journal_invalid"):
        recovered.recover()


def test_unanchored_stale_request_does_not_poison_publication_lane(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, store, publisher = _runtime(tmp_path)
    request = _request(store)
    real_commit = store.commit
    monkeypatch.setattr(
        store,
        "commit",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(SimulatedCrash()),
    )
    with pytest.raises(SimulatedCrash):
        publisher.publish(request)
    monkeypatch.setattr(store, "commit", real_commit)
    current = store.load()
    changed = dict(current)
    changed.pop("revision", None)
    changed["unrelated"] = True
    real_commit(changed, expected_revision=current["revision"])

    recovered = AtomicArchitectFixPromotionPublisher(
        repo_root=tmp_path / "repo",
        runtime_root=runtime,
        authority_profile_path=runtime / "authority_profile.json",
        work_state_store=store,
    )
    assert recovered.recover() is True
    assert not (runtime / "authority_profile.json").exists()
    assert not recovered.journal_path.exists()
    assert not recovered.stage_path.exists()
    with pytest.raises(RuntimeError, match="state_conflict"):
        recovered.publish(request)
    assert not recovered.journal_path.exists()
    assert not recovered.stage_path.exists()


def test_request_without_bound_publication_record_is_rejected(
    tmp_path: Path,
) -> None:
    _runtime_path, store, publisher = _runtime(tmp_path)
    request = _request(store)
    invalid = ArchitectFixPromotionPublicationRequest(
        publication_id=request.publication_id,
        proposal_authenticity_attestation_id=(
            request.proposal_authenticity_attestation_id
        ),
        authority_profile=request.authority_profile,
        updated_work_state={
            "schema_version": "reddog_authoritative_work_state.v1",
            "architect_fix_promotions": [],
        },
        expected_work_state_revision=request.expected_work_state_revision,
    )

    with pytest.raises(ValueError, match="record_missing"):
        publisher.publish(invalid)
    assert store.load().get("architect_fix_promotions") == []


def test_exact_retry_returns_same_committed_revision(tmp_path: Path) -> None:
    _runtime_path, store, publisher = _runtime(tmp_path)
    request = _request(store)

    first_revision = publisher.publish(request)
    second_revision = publisher.publish(request)

    assert second_revision == first_revision
    state = store.load()
    assert len(state["architect_fix_promotions"]) == 1
    assert len(state["architect_fix_publications"]) == 1
    assert state["architect_fix_publications"][0]["state"] == "COMMITTED"


def test_publication_preserves_prior_committed_history(tmp_path: Path) -> None:
    _runtime_path, store, publisher = _runtime(tmp_path)
    request = _request(store)
    prior = {
        "schema_version": "reddog_architect_fix_promotion_publication.v1",
        "publication_id": "sha256:" + "7" * 64,
        "state": "COMMITTED",
        "proposal_authenticity_attestation_id": (
            "reddog_architect_proposal_attestation_" + "8" * 32
        ),
        "authority_profile_digest": "sha256:" + "9" * 64,
        "active_work_state_digest": "sha256:" + "a" * 64,
        "base_work_state_digest": None,
    }
    updated = json.loads(json.dumps(request.updated_work_state))
    updated["architect_fix_publications"] = [prior]
    request = ArchitectFixPromotionPublicationRequest(
        publication_id=request.publication_id,
        proposal_authenticity_attestation_id=(
            request.proposal_authenticity_attestation_id
        ),
        authority_profile=request.authority_profile,
        updated_work_state=updated,
        expected_work_state_revision=request.expected_work_state_revision,
    )

    publisher.publish(request)

    publications = store.load()["architect_fix_publications"]
    assert [item["publication_id"] for item in publications] == [
        prior["publication_id"],
        request.publication_id,
    ]


def test_retry_with_altered_profile_fails_closed(tmp_path: Path) -> None:
    _runtime_path, store, publisher = _runtime(tmp_path)
    request = _request(store)
    publisher.publish(request)
    altered_profile = {
        **request.authority_profile,
        "queue_item_id": "queue:attacker",
    }
    altered_state = json.loads(json.dumps(request.updated_work_state))
    altered_state["architect_fix_promotions"][0][
        "authority_profile_digest"
    ] = canonical_digest(altered_profile)
    altered = ArchitectFixPromotionPublicationRequest(
        publication_id=request.publication_id,
        proposal_authenticity_attestation_id=(
            request.proposal_authenticity_attestation_id
        ),
        authority_profile=altered_profile,
        updated_work_state=altered_state,
        expected_work_state_revision=request.expected_work_state_revision,
    )

    with pytest.raises(RuntimeError, match="state_binding_invalid"):
        publisher.publish(altered)
    assert not publisher.journal_path.exists()
    assert not publisher.stage_path.exists()
    assert publisher.publish(request) == store.load()["revision"]


def test_fully_rehashed_unanchored_stage_and_journal_never_mint_authority(
    tmp_path: Path,
) -> None:
    runtime, store, publisher = _runtime(tmp_path)
    request = _request(store)
    profile = {
        **request.authority_profile,
        "queue_item_id": "sha256:" + "5" * 64,
    }
    profile_digest = canonical_digest(profile)
    queue_item_id = str(profile["queue_item_id"])
    claim_id = "sha256:" + "6" * 64
    active = {
        "schema_version": "reddog_authoritative_work_state.v1",
        "architect_fix_promotions": [
                {
                    "publication_id": request.publication_id,
                    "queue_item_id": queue_item_id,
                    "claim_id": claim_id,
                    "authority_profile_digest": profile_digest,
                "proposal_authenticity_attestation_id": (
                    request.proposal_authenticity_attestation_id
                ),
            }
        ],
        "wre_queue_items": [
            {"queue_item_id": queue_item_id, "claim_id": claim_id}
        ],
        "worker_claims": [{"claim_id": claim_id}],
    }
    stage = {
        "schema_version": "reddog_architect_fix_staged_profile.v1",
        "publication_id": request.publication_id,
        "proposal_authenticity_attestation_id": (
            request.proposal_authenticity_attestation_id
        ),
        "authority_profile_digest": profile_digest,
        "active_work_state_digest": canonical_digest(
            architect_fix_publication_state_projection(
                active,
                publication_id=request.publication_id,
            )
        ),
        "expected_work_state_revision": store.load()["revision"],
        "authority_profile": profile,
        "active_work_state": active,
    }
    stage["receipt_id"] = canonical_digest(stage)
    journal = {
        "schema_version": "reddog_architect_fix_promotion_publication.v1",
        "publication_id": request.publication_id,
        "phase": "INTENT_PREPARED",
        "proposal_authenticity_attestation_id": (
            request.proposal_authenticity_attestation_id
        ),
        "authority_profile_digest": profile_digest,
        "active_work_state_digest": stage["active_work_state_digest"],
        "expected_work_state_revision": store.load()["revision"],
        "prepared_revision": None,
        "committed_revision": None,
    }
    journal["receipt_id"] = canonical_digest(journal)
    publisher.stage_path.write_text(json.dumps(stage), encoding="utf-8")
    publisher.journal_path.write_text(json.dumps(journal), encoding="utf-8")

    assert publisher.recover() is True
    assert not (runtime / "authority_profile.json").exists()
    assert store.load().get("wre_queue_items") is None
    assert not publisher.stage_path.exists()
    assert not publisher.journal_path.exists()


def test_signed_retry_completes_after_final_cas_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, store, publisher = _runtime(tmp_path)
    request = _request(store)
    real_commit = store.commit
    calls = 0

    def fail_second_commit(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("revision_conflict")
        return real_commit(*args, **kwargs)

    monkeypatch.setattr(store, "commit", fail_second_commit)
    with pytest.raises(RuntimeError, match="revision_conflict"):
        publisher.publish(request)
    assert store.load()["architect_fix_publications"][0][
        "state"
    ] == "STATE_PREPARED"
    assert (runtime / "authority_profile.json").exists()

    monkeypatch.setattr(store, "commit", real_commit)
    recovered = AtomicArchitectFixPromotionPublisher(
        repo_root=tmp_path / "repo",
        runtime_root=runtime,
        authority_profile_path=runtime / "authority_profile.json",
        work_state_store=store,
    )
    assert recovered.recover() is False
    recovered.publish(request)
    assert store.load()["architect_fix_publications"][0][
        "state"
    ] == "COMMITTED"


def test_committed_publication_rejects_non_null_base_digest(
    tmp_path: Path,
) -> None:
    _runtime_path, store, publisher = _runtime(tmp_path)
    request = _request(store)
    publisher.publish(request)
    current = store.load()
    altered = json.loads(json.dumps(current))
    altered.pop("revision", None)
    altered["architect_fix_publications"][0][
        "base_work_state_digest"
    ] = "sha256:" + "f" * 64
    store.commit(altered, expected_revision=current["revision"])

    with pytest.raises(RuntimeError, match="state_binding_invalid"):
        publisher.publish(request)


def test_rehashed_journal_rejects_phase_revision_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, store, publisher = _runtime(tmp_path)
    request = _request(store)
    monkeypatch.setattr(
        store,
        "commit",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(SimulatedCrash()),
    )
    with pytest.raises(SimulatedCrash):
        publisher.publish(request)
    journal = json.loads(publisher.journal_path.read_text(encoding="utf-8"))
    journal["phase"] = "STATE_PREPARED"
    unsigned = dict(journal)
    unsigned.pop("receipt_id")
    journal["receipt_id"] = canonical_digest(unsigned)
    publisher.journal_path.write_text(
        json.dumps(journal, sort_keys=True),
        encoding="utf-8",
    )
    recovered = AtomicArchitectFixPromotionPublisher(
        repo_root=tmp_path / "repo",
        runtime_root=runtime,
        authority_profile_path=runtime / "authority_profile.json",
        work_state_store=AtomicJsonAuthorityRuntimeStore(
            runtime / "work_state.json",
            allowed_root=runtime,
            repo_root=tmp_path / "repo",
        ),
    )

    with pytest.raises(RuntimeError, match="journal_invalid"):
        recovered.recover()
