"""Security/availability acceptance for GotJunk -> Mall public read slice."""

import pytest
from fastapi import HTTPException

from modules.foundups.pfmall.listing_discovery import (
    GOTJUNK_ID, ListingEvidence, ListingProviderUnavailable,
    PublicationApproval, SourceItem, search_gotjunk_public_listings,
)
from modules.foundups.pfmall.http_api import app, public_listing_search, resolve_route


class Provider:
    def __init__(self, evidence=(), error=None):
        self.evidence, self.error = list(evidence), error
        self.calls = []

    def list_publication_evidence(self, foundup_id, limit):
        self.calls.append((foundup_id, limit))
        if self.error:
            raise self.error
        return self.evidence


def published(item_id="item-1", *, owner="alice", foundup=GOTJUNK_ID,
              status="listed", approval_state="approved_public", approved_owner=None,
              title="Reusable desk", category="reuse"):
    return ListingEvidence(
        SourceItem(foundup, item_id, owner, status),
        PublicationApproval(foundup, item_id,
                            approved_owner if approved_owner is not None else owner,
                            approval_state, title, category),
    )


def test_valid_public_discovery_and_stable_link():
    provider = Provider([published()])
    results = search_gotjunk_public_listings(provider, query="DESK", category="reuse")
    assert results == [{
        "foundup_id": "gotjunk_001", "source_item_id": "item-1",
        "source_collection": "gotjunk_items", "title": "Reusable desk",
        "category": "reuse", "deep_link": "/f/gotjunk_001/listings/item-1",
    }]
    assert provider.calls == [(GOTJUNK_ID, 200)]


def test_private_cross_owner_and_cross_foundup_are_denied():
    evidence = [
        published("private", status="draft"),
        published("unapproved", approval_state="pending"),
        published("wrong-owner", approved_owner="mallory"),
        published("other-foundup", foundup="getk_001"),
        published("bad-link/.."),
        published("item-allowed"),
    ]
    results = search_gotjunk_public_listings(Provider(evidence))
    assert [r["source_item_id"] for r in results] == ["item-allowed"]


def test_public_projection_never_leaks_sensitive_fields():
    provider = Provider([published()])
    row = search_gotjunk_public_listings(provider)[0]
    assert set(row) == {"foundup_id", "source_item_id", "source_collection",
                        "title", "category", "deep_link"}
    assert "alice" not in str(row)
    for secret in ("blob", "latitude", "longitude", "message", "credential", "token", "url"):
        assert secret not in row
    assert search_gotjunk_public_listings(Provider([published(title="https://token.example")])) == []


def test_absent_broken_or_malformed_provider_is_not_empty_success():
    with pytest.raises(ListingProviderUnavailable):
        search_gotjunk_public_listings(None)
    with pytest.raises(ListingProviderUnavailable):
        search_gotjunk_public_listings(Provider(error=OSError("backend down")))
    provider = Provider()
    provider.evidence = None
    with pytest.raises(ListingProviderUnavailable):
        search_gotjunk_public_listings(provider)


def test_http_handler_public_only_and_missing_provider(monkeypatch):
    # Exercise handler admission/status without uninstalled httpx2 TestClient.
    monkeypatch.delattr(app.state, "listing_evidence_provider", raising=False)
    with pytest.raises(HTTPException) as missing:
        public_listing_search(foundup_id=GOTJUNK_ID, q="", category=None,
                              owner_uid=None, limit=20)
    assert missing.value.status_code == 503
    provider = Provider([published(), published("private", status="draft")])
    app.state.listing_evidence_provider = provider
    try:
        result = public_listing_search(foundup_id=GOTJUNK_ID, q="desk",
                                       category=None, owner_uid=None, limit=20)
        assert [v["source_item_id"] for v in result["results"]] == ["item-1"]
        assert result["foundup_id"] == GOTJUNK_ID
        route = resolve_route(path=result["results"][0]["deep_link"])
        assert route["kind"] == "foundup"
        assert route["foundup_id"] == GOTJUNK_ID
        assert route["foundup_path"] == "/listings/item-1"
        with pytest.raises(HTTPException) as other:
            public_listing_search(foundup_id="getk_001", q="", category=None,
                                  owner_uid=None, limit=20)
        assert other.value.status_code == 403
        with pytest.raises(HTTPException) as owner:
            public_listing_search(foundup_id=GOTJUNK_ID, q="", category=None,
                                  owner_uid="alice", limit=20)
        assert owner.value.status_code == 403
    finally:
        del app.state.listing_evidence_provider


# Server-only Firestore adapter is supplied a fake trusted client. This tests
# authorization/approval join without credentials, network or project changes.
from modules.foundups.pfmall.firestore_listing_provider import (
    FirestoreGotJunkPublicationProvider,
)


class _Doc:
    def __init__(self, name, data=None):
        self.id, self._data = name, data
        self.exists = data is not None

    def to_dict(self):
        return self._data


class _Items:
    def __init__(self, docs):
        self.docs = docs

    def document(self, item_id):
        return _Ref(self.docs, item_id)


class _Ref:
    def __init__(self, docs, item_id):
        self.docs, self.item_id = docs, item_id

    def get(self):
        if isinstance(self.docs, Exception):
            raise self.docs
        return _Doc(self.item_id, self.docs.get(self.item_id))


class _Approvals:
    def __init__(self, docs):
        self.docs, self.limit_n = docs, None

    def where(self, field, op, value):
        assert (field, op, value) == ("state", "==", "approved_public")
        return self

    def limit(self, count):
        self.limit_n = count
        return self

    def stream(self):
        if isinstance(self.docs, Exception):
            raise self.docs
        for item_id, record in list(self.docs.items())[:self.limit_n]:
            yield _Doc(item_id, record)


class _Client:
    project = "test-reviewer-project"

    def __init__(self, approvals, items):
        self.approvals, self.items = _Approvals(approvals), _Items(items)

    def collection(self, name):
        return {"gotjunk_public_approvals": self.approvals,
                "gotjunk_items": self.items}[name]


def _approved_pair(item_id="item-1", source_rev="rev-1", owner="alice"):
    return (
        {item_id: {
            "foundupId": GOTJUNK_ID, "itemId": item_id, "ownerUid": owner,
            "reviewerUid": "reviewer-1", "reviewedAt": "reviewed",
            "privacyReviewed": True, "fieldAllowlistVersion": "public_listing_v1",
            "approvedSourceUpdatedAt": source_rev,
            "state": "approved_public", "publicTitle": "Used table",
            "publicCategory": "reuse",
        }},
        {item_id: {"id": item_id, "ownerUid": owner,
                   "updatedAt": source_rev, "status": "listed"}},
    )


def test_firestore_provider_publishes_only_independently_reviewed_matching_revision():
    a, i = _approved_pair()
    provider = FirestoreGotJunkPublicationProvider(
        _Client(a, i), expected_project_id="test-reviewer-project")
    assert search_gotjunk_public_listings(provider)[0]["deep_link"] == (
        "/f/gotjunk_001/listings/item-1")
    assert provider._approvals.limit_n == 200


@pytest.mark.parametrize("change_collection,field,value", [
    ("approval", "ownerUid", "mallory"),
    ("approval", "foundupId", "getk_001"),
    ("approval", "state", "pending"),
    ("approval", "reviewerUid", "alice"),
    ("approval", "approvedSourceUpdatedAt", "old-revision"),
    ("approval", "reviewedAt", None),
    ("approval", "privacyReviewed", False),
    ("approval", "fieldAllowlistVersion", "unreviewed"),
    ("item", "status", "draft"),
    ("item", "updatedAt", "changed-revision"),
    ("item", "ownerUid", "other-owner"),
])
def test_firestore_provider_denies_unauthorized_and_stale(change_collection, field, value):
    a, i = _approved_pair()
    (a if change_collection == "approval" else i)["item-1"][field] = value
    provider = FirestoreGotJunkPublicationProvider(
        _Client(a, i), expected_project_id="test-reviewer-project")
    assert search_gotjunk_public_listings(provider) == []


def test_firestore_provider_denies_other_tenant_wrong_project_and_provider_errors():
    a, i = _approved_pair()
    with pytest.raises(ValueError):
        FirestoreGotJunkPublicationProvider(
            _Client(a, i), expected_project_id="different-project")
    provider = FirestoreGotJunkPublicationProvider(
        _Client(a, i), expected_project_id="test-reviewer-project")
    with pytest.raises(PermissionError):
        provider.list_publication_evidence("getk_001", 10)
    provider = FirestoreGotJunkPublicationProvider(
        _Client(RuntimeError("offline"), i), expected_project_id="test-reviewer-project")
    with pytest.raises(ListingProviderUnavailable):
        search_gotjunk_public_listings(provider)


def test_firestore_provider_failed_item_fetch_not_partial_success():
    a, i = _approved_pair()
    provider = FirestoreGotJunkPublicationProvider(
        _Client(a, RuntimeError("item provider down")),
        expected_project_id="test-reviewer-project")
    with pytest.raises(ListingProviderUnavailable):
        search_gotjunk_public_listings(provider)
