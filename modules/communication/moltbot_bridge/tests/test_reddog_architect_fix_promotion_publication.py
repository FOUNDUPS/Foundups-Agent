"""Crash and tamper tests for architect FIX two-phase publication."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
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
from modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_store import (
    AtomicJsonAuthoritativeWorkStateStore,
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


def test_refresh_and_publication_stores_share_one_writer_fence(
    tmp_path: Path,
) -> None:
    runtime, publication_store, _publisher = _runtime(tmp_path)
    refresh_store = AtomicJsonAuthoritativeWorkStateStore(
        runtime / "work_state.json",
        allowed_root=runtime,
        repo_root=tmp_path / "repo",
    )
    current = publication_store.load()
    publication_update = {
        key: value for key, value in current.items() if key != "revision"
    }
    publication_update["publication_marker"] = "committed"

    executor = ThreadPoolExecutor(max_workers=1)
    try:
        with refresh_store.locked_snapshot():
            future = executor.submit(
                publication_store.commit,
                publication_update,
                expected_revision=current["revision"],
            )
            with pytest.raises(FutureTimeout):
                future.result(timeout=0.1)
        assert future.result(timeout=2) != current["revision"]
    finally:
        executor.shutdown(wait=True)
    assert publication_store.lock_path == refresh_store.lock_path
    assert publication_store.load()["publication_marker"] == "committed"


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


def _write_unanchored_packets(
    publisher: AtomicArchitectFixPromotionPublisher,
    request: ArchitectFixPromotionPublicationRequest,
    *,
    profile: dict,
    active_state: dict,
) -> None:
    profile_digest = canonical_digest(profile)
    active_digest = canonical_digest(
        architect_fix_publication_state_projection(
            active_state,
            publication_id=request.publication_id,
        )
    )
    stage = {
        "schema_version": "reddog_architect_fix_staged_profile.v1",
        "publication_id": request.publication_id,
        "proposal_authenticity_attestation_id": (
            request.proposal_authenticity_attestation_id
        ),
        "authority_profile_digest": profile_digest,
        "active_work_state_digest": active_digest,
        "expected_work_state_revision": request.expected_work_state_revision,
        "authority_profile": profile,
        "active_work_state": active_state,
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
        "active_work_state_digest": active_digest,
        "expected_work_state_revision": request.expected_work_state_revision,
        "prepared_revision": None,
        "committed_revision": None,
    }
    journal["receipt_id"] = canonical_digest(journal)
    publisher.stage_path.write_text(json.dumps(stage), encoding="utf-8")
    publisher.journal_path.write_text(json.dumps(journal), encoding="utf-8")


def _forge_committed_packets(
    store: AtomicJsonAuthorityRuntimeStore,
    publisher: AtomicArchitectFixPromotionPublisher,
) -> None:
    stage = json.loads(publisher.stage_path.read_text(encoding="utf-8"))
    journal = json.loads(publisher.journal_path.read_text(encoding="utf-8"))
    profile = {**stage["authority_profile"], "attacker_note": "forged"}
    profile_digest = canonical_digest(profile)
    active = json.loads(json.dumps(stage["active_work_state"]))
    active["architect_fix_promotions"][0][
        "authority_profile_digest"
    ] = profile_digest
    active_digest = canonical_digest(
        architect_fix_publication_state_projection(
            active,
            publication_id=stage["publication_id"],
        )
    )
    stage.update(
        authority_profile=profile,
        authority_profile_digest=profile_digest,
        active_work_state=active,
        active_work_state_digest=active_digest,
    )
    stage["receipt_id"] = canonical_digest(
        {key: value for key, value in stage.items() if key != "receipt_id"}
    )
    journal.update(
        authority_profile_digest=profile_digest,
        active_work_state_digest=active_digest,
    )
    journal["receipt_id"] = canonical_digest(
        {key: value for key, value in journal.items() if key != "receipt_id"}
    )
    current = store.load()
    forged = json.loads(json.dumps(current))
    forged.pop("revision", None)
    forged["architect_fix_promotions"][0][
        "authority_profile_digest"
    ] = profile_digest
    forged["architect_fix_publications"][0].update(
        authority_profile_digest=profile_digest,
        active_work_state_digest=active_digest,
    )
    store.commit(forged, expected_revision=current["revision"])
    publisher._write(publisher.stage_path, stage)
    publisher._write(publisher.journal_path, journal)
    publisher._write(publisher._profile_artifact_path(profile_digest), profile)


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


def test_restart_rolls_back_prepared_state_before_authenticated_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, store, publisher = _runtime(tmp_path)
    request = _request(store)
    original = (runtime / "work_state.json").read_bytes()

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
    assert recovered.recover() is True
    assert (runtime / "work_state.json").read_bytes() == original
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


@pytest.mark.parametrize("missing", (None, "stage", "journal"))
def test_restart_requires_authenticated_retry_after_committed_state_crash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    missing: str | None,
) -> None:
    runtime, store, publisher = _runtime(tmp_path)
    request = _request(store)
    monkeypatch.setattr(
        publisher,
        "_publish_profile_cache",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(SimulatedCrash()),
    )

    with pytest.raises(SimulatedCrash):
        publisher.publish(request)

    assert store.load()["architect_fix_publications"][0]["state"] == "COMMITTED"
    assert not (runtime / "authority_profile.json").exists()
    if missing == "stage":
        publisher.stage_path.unlink()
    elif missing == "journal":
        publisher.journal_path.unlink()
    recovered = AtomicArchitectFixPromotionPublisher(
        repo_root=tmp_path / "repo",
        runtime_root=runtime,
        authority_profile_path=runtime / "authority_profile.json",
        work_state_store=store,
    )

    assert recovered.recover() is True
    assert not (runtime / "authority_profile.json").exists()
    recovered.publish(request)
    assert json.loads(
        (runtime / "authority_profile.json").read_text(encoding="utf-8")
    ) == request.authority_profile
    assert not recovered.stage_path.exists()
    assert not recovered.journal_path.exists()


def test_recovery_never_publishes_fully_rehashed_committed_packets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, store, publisher = _runtime(tmp_path)
    request = _request(store)
    monkeypatch.setattr(
        publisher,
        "_publish_profile_cache",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(SimulatedCrash()),
    )
    with pytest.raises(SimulatedCrash):
        publisher.publish(request)
    _forge_committed_packets(store, publisher)
    forged_state = (runtime / "work_state.json").read_bytes()

    assert publisher.recover() is True
    assert (runtime / "work_state.json").read_bytes() == forged_state
    assert not (runtime / "authority_profile.json").exists()
    assert not publisher.stage_path.exists()
    assert not publisher.journal_path.exists()
    with pytest.raises(RuntimeError, match="state_binding_invalid"):
        publisher.publish(request)


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


def test_unanchored_stage_cannot_delete_committed_immutable_profile(
    tmp_path: Path,
) -> None:
    runtime, store, publisher = _runtime(tmp_path)
    committed_request = _request(store)
    publisher.publish(committed_request)
    artifact = next(runtime.glob("*.immutable.json"))
    artifact_before = artifact.read_bytes()
    authoritative_before = (runtime / "work_state.json").read_bytes()
    unanchored = _request(
        store,
        publication_id="sha256:" + "7" * 64,
    )
    active_digest = canonical_digest(
        architect_fix_publication_state_projection(
            unanchored.updated_work_state,
            publication_id=unanchored.publication_id,
        )
    )
    stage = {
        "schema_version": "reddog_architect_fix_staged_profile.v1",
        "publication_id": unanchored.publication_id,
        "proposal_authenticity_attestation_id": (
            unanchored.proposal_authenticity_attestation_id
        ),
        "authority_profile_digest": canonical_digest(
            committed_request.authority_profile
        ),
        "active_work_state_digest": active_digest,
        "expected_work_state_revision": store.load()["revision"],
        "authority_profile": dict(committed_request.authority_profile),
        "active_work_state": dict(unanchored.updated_work_state),
    }
    stage["receipt_id"] = canonical_digest(stage)
    journal = {
        "schema_version": "reddog_architect_fix_promotion_publication.v1",
        "publication_id": unanchored.publication_id,
        "phase": "INTENT_PREPARED",
        "proposal_authenticity_attestation_id": (
            unanchored.proposal_authenticity_attestation_id
        ),
        "authority_profile_digest": stage["authority_profile_digest"],
        "active_work_state_digest": active_digest,
        "expected_work_state_revision": stage["expected_work_state_revision"],
        "prepared_revision": None,
        "committed_revision": None,
    }
    journal["receipt_id"] = canonical_digest(journal)
    publisher.stage_path.write_text(json.dumps(stage), encoding="utf-8")
    publisher.journal_path.write_text(json.dumps(journal), encoding="utf-8")

    assert publisher.recover() is True
    assert artifact.read_bytes() == artifact_before
    assert (runtime / "work_state.json").read_bytes() == authoritative_before
    assert not publisher.stage_path.exists()
    assert not publisher.journal_path.exists()


def test_attacker_rehashed_unanchored_packets_have_zero_effects(
    tmp_path: Path,
) -> None:
    runtime, store, publisher = _runtime(tmp_path)
    request = _request(store)
    authoritative_before = (runtime / "work_state.json").read_bytes()
    profile = {
        **request.authority_profile,
        "queue_item_id": "sha256:" + "9" * 64,
    }
    active = json.loads(json.dumps(request.updated_work_state, sort_keys=True))
    active["architect_fix_promotions"][0]["queue_item_id"] = profile[
        "queue_item_id"
    ]
    active["architect_fix_promotions"][0][
        "authority_profile_digest"
    ] = canonical_digest(profile)
    active["wre_queue_items"] = [
        {
            "queue_item_id": profile["queue_item_id"],
            "claim_id": active["architect_fix_promotions"][0]["claim_id"],
        }
    ]
    _write_unanchored_packets(
        publisher,
        request,
        profile=profile,
        active_state=active,
    )

    assert publisher.recover() is True
    assert (runtime / "work_state.json").read_bytes() == authoritative_before
    assert not (runtime / "authority_profile.json").exists()
    assert store.load().get("wre_queue_items") is None
    assert store.load().get("worker_claims") is None
    assert not publisher.stage_path.exists()
    assert not publisher.journal_path.exists()


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


def test_fully_rehashed_prepared_stage_and_journal_never_mint_authority(
    tmp_path: Path,
) -> None:
    runtime, store, publisher = _runtime(tmp_path)
    request = _request(store)
    original = (runtime / "work_state.json").read_bytes()
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
    current = store.load()
    prepared = json.loads(json.dumps(current, sort_keys=True))
    prepared.pop("revision", None)
    prepared["architect_fix_publications"] = [
        {
            "schema_version": (
                "reddog_architect_fix_promotion_publication.v1"
            ),
            "publication_id": request.publication_id,
            "state": "STATE_PREPARED",
            "proposal_authenticity_attestation_id": (
                request.proposal_authenticity_attestation_id
            ),
            "authority_profile_digest": profile_digest,
            "active_work_state_digest": stage[
                "active_work_state_digest"
            ],
            "base_work_state_digest": canonical_digest(
                {
                    key: value
                    for key, value in current.items()
                    if key != "revision"
                }
            ),
        }
    ]
    store.commit(prepared, expected_revision=current["revision"])
    journal = {
        "schema_version": "reddog_architect_fix_promotion_publication.v1",
        "publication_id": request.publication_id,
        "phase": "STATE_PREPARED",
        "proposal_authenticity_attestation_id": (
            request.proposal_authenticity_attestation_id
        ),
        "authority_profile_digest": profile_digest,
        "active_work_state_digest": stage["active_work_state_digest"],
        "expected_work_state_revision": stage[
            "expected_work_state_revision"
        ],
        "prepared_revision": store.load()["revision"],
        "committed_revision": None,
    }
    journal["receipt_id"] = canonical_digest(journal)
    publisher.stage_path.write_text(json.dumps(stage), encoding="utf-8")
    publisher.journal_path.write_text(json.dumps(journal), encoding="utf-8")

    assert publisher.recover() is True
    assert (runtime / "work_state.json").read_bytes() == original
    assert not (runtime / "authority_profile.json").exists()
    assert store.load().get("wre_queue_items") is None
    assert store.load().get("worker_claims") is None
    assert store.load().get("architect_fix_publications") is None
    assert not publisher.stage_path.exists()
    assert not publisher.journal_path.exists()


@pytest.mark.parametrize("missing", ("stage", "journal"))
def test_missing_recovery_artifact_rolls_back_prepared_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    missing: str,
) -> None:
    runtime, store, publisher = _runtime(tmp_path)
    request = _request(store)
    original = (runtime / "work_state.json").read_bytes()
    monkeypatch.setattr(
        publisher,
        "_publish_profile",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(SimulatedCrash()),
    )
    with pytest.raises(SimulatedCrash):
        publisher.publish(request)
    target = publisher.stage_path if missing == "stage" else publisher.journal_path
    target.unlink()

    recovered = AtomicArchitectFixPromotionPublisher(
        repo_root=tmp_path / "repo",
        runtime_root=runtime,
        authority_profile_path=runtime / "authority_profile.json",
        work_state_store=store,
    )

    assert recovered.recover() is True
    assert (runtime / "work_state.json").read_bytes() == original
    assert not recovered.stage_path.exists()
    assert not recovered.journal_path.exists()
    assert not (runtime / "authority_profile.json").exists()


def test_repeated_recovery_is_idempotent(tmp_path: Path) -> None:
    runtime, store, publisher = _runtime(tmp_path)
    request = _request(store)
    stage = {
        "schema_version": "reddog_architect_fix_staged_profile.v1",
        "publication_id": request.publication_id,
        "proposal_authenticity_attestation_id": (
            request.proposal_authenticity_attestation_id
        ),
        "authority_profile_digest": canonical_digest(
            request.authority_profile
        ),
        "active_work_state_digest": canonical_digest(
            architect_fix_publication_state_projection(
                request.updated_work_state,
                publication_id=request.publication_id,
            )
        ),
        "expected_work_state_revision": request.expected_work_state_revision,
        "authority_profile": dict(request.authority_profile),
        "active_work_state": dict(request.updated_work_state),
    }
    stage["receipt_id"] = canonical_digest(stage)
    publisher.stage_path.write_text(json.dumps(stage), encoding="utf-8")

    assert publisher.recover() is True
    after = (runtime / "work_state.json").read_bytes()
    assert publisher.recover() is False
    assert (runtime / "work_state.json").read_bytes() == after


def test_concurrent_exact_publishers_commit_one_publication(
    tmp_path: Path,
) -> None:
    runtime, store, publisher = _runtime(tmp_path)
    request = _request(store)
    second = AtomicArchitectFixPromotionPublisher(
        repo_root=tmp_path / "repo",
        runtime_root=runtime,
        authority_profile_path=runtime / "authority_profile.json",
        work_state_store=store,
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        revisions = tuple(
            executor.map(
                lambda item: item.publish(request),
                (publisher, second),
            )
        )

    assert len(set(revisions)) == 1
    state = store.load()
    assert len(state["architect_fix_publications"]) == 1
    assert state["architect_fix_publications"][0]["state"] == "COMMITTED"
    assert len(state["architect_fix_promotions"]) == 1


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
    assert not (runtime / "authority_profile.json").exists()

    monkeypatch.setattr(store, "commit", real_commit)
    recovered = AtomicArchitectFixPromotionPublisher(
        repo_root=tmp_path / "repo",
        runtime_root=runtime,
        authority_profile_path=runtime / "authority_profile.json",
        work_state_store=store,
    )
    assert recovered.recover() is True
    recovered.publish(request)
    assert store.load()["architect_fix_publications"][0][
        "state"
    ] == "COMMITTED"


def test_concurrent_refresh_after_profile_artifact_rolls_back_safely(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, store, publisher = _runtime(tmp_path)
    request = _request(store)
    real_commit = store.commit
    calls = 0

    def refresh_before_final_cas(snapshot, *, expected_revision):
        nonlocal calls
        calls += 1
        if calls != 2:
            return real_commit(
                snapshot,
                expected_revision=expected_revision,
            )
        current = store.load()
        refreshed = json.loads(json.dumps(current, sort_keys=True))
        refreshed.pop("revision", None)
        refreshed["refresh_marker"] = "preserved"
        real_commit(refreshed, expected_revision=current["revision"])
        raise RuntimeError("revision_conflict")

    monkeypatch.setattr(store, "commit", refresh_before_final_cas)
    with pytest.raises(RuntimeError, match="revision_conflict"):
        publisher.publish(request)

    assert not (runtime / "authority_profile.json").exists()
    assert list(runtime.glob("*.immutable.json"))
    monkeypatch.setattr(store, "commit", real_commit)
    recovered = AtomicArchitectFixPromotionPublisher(
        repo_root=tmp_path / "repo",
        runtime_root=runtime,
        authority_profile_path=runtime / "authority_profile.json",
        work_state_store=store,
    )

    assert recovered.recover() is True
    state = store.load()
    assert state["refresh_marker"] == "preserved"
    assert state.get("architect_fix_publications") is None
    assert list(runtime.glob("*.immutable.json"))
    assert not recovered.stage_path.exists()
    assert not recovered.journal_path.exists()


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
