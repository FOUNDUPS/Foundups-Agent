"""Server-injected Firestore evidence reader for approved GotJunk listings.

Read only. The caller must inject a privileged client from a separately
authorized server bootstrap; this module never initializes SDK credentials,
enables Firebase, starts services, or writes to either collection.

The approval collection must be server/IAM-only and *not* writable or
readable by browser clients. Current legacy Firestore catch-all rules deny it.
"""
from __future__ import annotations

from typing import Any, Mapping
import re

_SAFE_ITEM_ID = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")

from modules.foundups.pfmall.listing_discovery import (
    GOTJUNK_ID, ListingEvidence, PublicationApproval, SourceItem,
    ListingProviderUnavailable,
)


class FirestoreGotJunkPublicationProvider:
    """Server-side join of private publication approval and source item.

    No publication state is inferred from GotJunk client fields. Approvals
    must be independently reviewed and bound to a particular source revision.
    """

    def __init__(self, client: Any, *, expected_project_id: str):
        if (not isinstance(expected_project_id, str)
                or not expected_project_id.strip()
                or getattr(client, "project", None) != expected_project_id):
            raise ValueError("A matching explicit Firestore project is required")
        self._items = client.collection("gotjunk_items")
        self._approvals = client.collection("gotjunk_public_approvals")

    def list_publication_evidence(self, foundup_id: str, limit: int) -> list[ListingEvidence]:
        if foundup_id != GOTJUNK_ID:
            raise PermissionError("Cross-FoundUp evidence denied")
        if not isinstance(limit, int) or not 1 <= limit <= 200:
            raise ValueError("Invalid evidence limit")
        rows: list[ListingEvidence] = []
        try:
            approvals = (self._approvals.where("state", "==", "approved_public")
                         .limit(limit).stream())
            for snapshot in approvals:
                approval = snapshot.to_dict()
                if not isinstance(approval, Mapping):
                    continue
                item_id = approval.get("itemId")
                owner_uid = approval.get("ownerUid")
                reviewer_uid = approval.get("reviewerUid")
                if (not isinstance(item_id, str) or not _SAFE_ITEM_ID.fullmatch(item_id)
                        or getattr(snapshot, "id", None) != item_id
                        or not isinstance(owner_uid, str) or not owner_uid
                        or not isinstance(reviewer_uid, str) or not reviewer_uid
                        or reviewer_uid == owner_uid
                        or approval.get("foundupId") != GOTJUNK_ID
                        or approval.get("state") != "approved_public"
                        or approval.get("privacyReviewed") is not True
                        or approval.get("fieldAllowlistVersion") != "public_listing_v1"
                        or approval.get("reviewedAt") is None
                        or approval.get("approvedSourceUpdatedAt") is None):
                    continue
                item_snapshot = self._items.document(item_id).get()
                if not getattr(item_snapshot, "exists", False):
                    continue
                item = item_snapshot.to_dict()
                if not isinstance(item, Mapping):
                    continue
                if (item.get("id") != item_id
                        or item.get("ownerUid") != owner_uid
                        or item.get("status") != "listed"
                        or item.get("updatedAt") is None
                        or item.get("updatedAt") != approval.get("approvedSourceUpdatedAt")):
                    continue
                rows.append(ListingEvidence(
                    source=SourceItem(
                        foundup_id=GOTJUNK_ID, item_id=item_id,
                        owner_uid=owner_uid, status="listed",
                    ),
                    approval=PublicationApproval(
                        foundup_id=GOTJUNK_ID, item_id=item_id,
                        owner_uid=owner_uid, state="approved_public",
                        public_title=approval.get("publicTitle"),
                        public_category=approval.get("publicCategory"),
                    ),
                ))
            return rows
        except Exception as exc:
            # Do not return a partial successful page if any source/ACL read fails.
            raise ListingProviderUnavailable("Publication evidence backend unavailable") from exc
