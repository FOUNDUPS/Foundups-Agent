"""Public-only item discovery for Mall, backed by server-reviewed evidence.

A FoundUp manifest is NOT a listing grant. The provider must join the source
item to an independently controlled publication-approval record; raw browser
or Firestore documents must never be passed through as trusted approvals.
No provider is configured by default. Nothing is fetched from production.
"""

from dataclasses import dataclass
import re
from typing import Optional, Protocol, Sequence

GOTJUNK_ID = "gotjunk_001"
_ITEM_ID = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_SAFE_CATEGORY = re.compile(r"[a-z0-9_-]{1,32}\Z")


class ListingProviderUnavailable(RuntimeError):
    """Provider is missing, failed, or returned an invalid response."""


@dataclass(frozen=True)
class SourceItem:
    foundup_id: str
    item_id: str
    owner_uid: str
    status: str


@dataclass(frozen=True)
class PublicationApproval:
    """Separate *server-owned* approval evidence, never a client-supplied flag."""

    foundup_id: str
    item_id: str
    owner_uid: str
    state: str
    public_title: str
    public_category: str


@dataclass(frozen=True)
class ListingEvidence:
    source: SourceItem
    approval: Optional[PublicationApproval]


class ListingEvidenceProvider(Protocol):
    """Trusted server adapter; must independently read item and approval ACLs."""

    def list_publication_evidence(self, foundup_id: str, limit: int) -> Sequence[ListingEvidence]:
        ...


def _public_projection(evidence: ListingEvidence) -> Optional[dict]:
    if not isinstance(evidence, ListingEvidence):
        return None
    item, approval = evidence.source, evidence.approval
    if not isinstance(item, SourceItem) or not isinstance(approval, PublicationApproval):
        return None
    if item.foundup_id != GOTJUNK_ID or approval.foundup_id != GOTJUNK_ID:
        return None
    if not isinstance(item.item_id, str) or not _ITEM_ID.fullmatch(item.item_id):
        return None
    if not isinstance(item.owner_uid, str) or not item.owner_uid or len(item.owner_uid) > 128:
        return None
    if (approval.item_id != item.item_id or approval.owner_uid != item.owner_uid
            or item.status != "listed" or approval.state != "approved_public"):
        return None
    title = approval.public_title
    category = approval.public_category
    # Approval must contain vetted public-only copy. No raw descriptions,
    # locations, messages, blob data or credential-bearing media URLs are exposed.
    if (not isinstance(title, str) or not 1 <= len(title.strip()) <= 100
            or any(ord(c) < 32 for c in title) or "://" in title or "@" in title):
        return None
    if not isinstance(category, str) or not _SAFE_CATEGORY.fullmatch(category):
        return None
    return {
        "foundup_id": GOTJUNK_ID,
        "source_item_id": item.item_id,
        "source_collection": "gotjunk_items",
        "title": title.strip(),
        "category": category,
        "deep_link": f"/f/{GOTJUNK_ID}/listings/{item.item_id}",
    }


def search_gotjunk_public_listings(
    provider: Optional[ListingEvidenceProvider], *, query: str = "",
    category: Optional[str] = None, limit: int = 20,
) -> list[dict]:
    """Server-side public-only read; no private or owner-specific search.

    A real provider MUST enforce item ACL and separately backed publication
    approval (not a user-set field). This function rechecks owner/tenant joins
    and emits only a fixed allowlist of fields. Missing/broken providers fail.
    """
    if provider is None or not callable(getattr(provider, "list_publication_evidence", None)):
        raise ListingProviderUnavailable("Listing provider not configured")
    if not isinstance(query, str) or len(query) > 80:
        raise ValueError("Invalid query")
    if category is not None and (not isinstance(category, str) or not _SAFE_CATEGORY.fullmatch(category)):
        raise ValueError("Invalid category")
    if not isinstance(limit, int) or not 1 <= limit <= 50:
        raise ValueError("Invalid limit")
    try:
        evidence = provider.list_publication_evidence(GOTJUNK_ID, min(limit * 10, 200))
    except Exception as exc:
        raise ListingProviderUnavailable("Listing provider failed") from exc
    if not isinstance(evidence, (list, tuple)) or len(evidence) > 200:
        raise ListingProviderUnavailable("Invalid listing provider response")
    results = []
    for row in evidence:
        listing = _public_projection(row)
        if listing is None:
            continue
        if category and listing["category"] != category:
            continue
        if query.casefold() not in listing["title"].casefold():
            continue
        results.append(listing)
        if len(results) >= limit:
            break
    return results
