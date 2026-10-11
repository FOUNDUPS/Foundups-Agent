"""Security/availability acceptance for GotJunk -> Mall public read slice."""

import pytest
from fastapi.testclient import TestClient

from modules.foundups.pfmall.listing_discovery import (
    GOTJUNK_ID, ListingEvidence, ListingProviderUnavailable,
    PublicationApproval, SourceItem, search_gotjunk_public_listings,
)
from modules.foundups.pfmall.http_api import app


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


def test_http_public_only_and_missing_provider(monkeypatch):
    monkeypatch.delattr(app.state, "listing_evidence_provider", raising=False)
    client = TestClient(app)
    assert client.get("/pfmall/listings/search").status_code == 503
    provider = Provider([published(), published("private", status="draft")])
    app.state.listing_evidence_provider = provider
    try:
        r = client.get("/pfmall/listings/search", params={"q": "desk"})
        assert r.status_code == 200
        assert [v["source_item_id"] for v in r.json()["results"]] == ["item-1"]
        assert r.json()["foundup_id"] == GOTJUNK_ID
        route = client.get("/pfmall/resolve-route", params={"path": r.json()["results"][0]["deep_link"]})
        assert route.status_code == 200
        assert route.json()["kind"] == "foundup"
        assert route.json()["foundup_id"] == GOTJUNK_ID
        assert route.json()["foundup_path"] == "/listings/item-1"
        assert client.get("/pfmall/listings/search", params={"foundup_id": "getk_001"}).status_code == 403
        assert client.get("/pfmall/listings/search", params={"owner_uid": "alice"}).status_code == 403
        assert client.get("/pfmall/listings/search", params={"limit": 51}).status_code == 422
    finally:
        del app.state.listing_evidence_provider
