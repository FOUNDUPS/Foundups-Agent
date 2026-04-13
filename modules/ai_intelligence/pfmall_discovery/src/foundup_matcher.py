"""
FoundUp Matcher - Map discovered content to existing catalog FoundUps.

Matching policy:
1. Exact channel_id match (confidence: 1.0)
2. Tag overlap match (confidence: 0.3-0.7 based on overlap)
3. Category match (confidence: 0.2)
4. Unmatched (confidence: 0.0)

WSP References:
- WSP 3: AI Intelligence domain
- WSP 97: Truthful matching (no invented mappings)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Default catalog path
DEFAULT_CATALOG_PATH = Path("public/member/mall-video-catalog.json")


@dataclass
class CatalogTarget:
    """A potential mapping target from the catalog."""

    foundup_id: str
    source_id: str  # YouTube channel ID
    source_handle: str
    tags: List[str]
    category: str


def load_catalog_targets(catalog_path: Optional[Path] = None) -> List[CatalogTarget]:
    """
    Load YouTube-backed FoundUps from catalog as matching targets.

    Args:
        catalog_path: Path to mall-video-catalog.json (default: public/member/)

    Returns:
        List of CatalogTarget objects
    """
    path = catalog_path or DEFAULT_CATALOG_PATH
    if not path.exists():
        logger.warning(f"[MATCHER] Catalog not found: {path}")
        return []

    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"[MATCHER] Failed to load catalog: {e}")
        return []

    targets = []
    for entry in catalog:
        if entry.get("source_type") != "youtube_channel":
            continue

        targets.append(
            CatalogTarget(
                foundup_id=entry.get("foundup_id", ""),
                source_id=entry.get("source_id", ""),
                source_handle=entry.get("source_handle", ""),
                tags=[t.lower() for t in entry.get("tags", [])],
                category=entry.get("category", "").lower(),
            )
        )

    logger.info(f"[MATCHER] Loaded {len(targets)} YouTube-backed catalog targets")
    return targets


def _calculate_tag_overlap(tags1: List[str], tags2: List[str]) -> float:
    """
    Calculate tag overlap score.

    Returns:
        Score between 0.0 and 1.0
    """
    if not tags1 or not tags2:
        return 0.0

    set1 = set(t.lower() for t in tags1)
    set2 = set(t.lower() for t in tags2)
    overlap = len(set1 & set2)

    # Jaccard-like score capped for reasonable confidence
    if overlap == 0:
        return 0.0

    # More overlap = higher confidence (max 0.7 for tags alone)
    union = len(set1 | set2)
    return min(0.7, 0.3 + (0.4 * overlap / union))


def match_to_foundup(
    channel_id: str,
    title: str,
    description: str,
    targets: List[CatalogTarget],
) -> Tuple[Optional[str], str, float]:
    """
    Match a discovered item to an existing FoundUp.

    Matching policy (priority order):
    1. Exact channel_id match -> confidence 1.0
    2. Tag overlap from title/description -> confidence 0.3-0.7
    3. Category hint from title/description -> confidence 0.2
    4. No match -> confidence 0.0

    Args:
        channel_id: YouTube channel ID of discovered item
        title: Title of discovered item
        description: Description of discovered item
        targets: List of catalog targets to match against

    Returns:
        Tuple of (matched_foundup_id, match_reason, confidence)
    """
    if not targets:
        return None, "no_targets", 0.0

    # Extract keywords from title and description for matching
    text = f"{title} {description}".lower()
    text_words = set(text.split())

    best_match: Optional[str] = None
    best_reason = "no_match"
    best_confidence = 0.0

    for target in targets:
        # Priority 1: Exact channel_id match
        if channel_id and target.source_id and channel_id == target.source_id:
            return target.foundup_id, "channel_id_match", 1.0

        # Priority 2: Tag overlap
        tag_overlap = _calculate_tag_overlap(list(text_words), target.tags)
        if tag_overlap > best_confidence:
            best_match = target.foundup_id
            best_reason = f"tag_overlap:{tag_overlap:.2f}"
            best_confidence = tag_overlap

        # Priority 3: Category match
        if target.category and target.category in text:
            category_score = 0.2
            if category_score > best_confidence:
                best_match = target.foundup_id
                best_reason = f"category_match:{target.category}"
                best_confidence = category_score

    # Only return match if confidence meets threshold
    if best_confidence >= 0.2:
        return best_match, best_reason, best_confidence

    return None, "no_match", 0.0


def match_proposals(
    proposals: List[Any],  # List[DiscoveryProposal]
    targets: Optional[List[CatalogTarget]] = None,
) -> List[Any]:
    """
    Match a list of discovery proposals to existing FoundUps.

    Args:
        proposals: List of DiscoveryProposal objects
        targets: Optional pre-loaded targets (loads from catalog if None)

    Returns:
        Proposals with matched_foundup_id, match_reason, confidence populated
    """
    if targets is None:
        targets = load_catalog_targets()

    for proposal in proposals:
        matched_id, reason, confidence = match_to_foundup(
            channel_id=proposal.channel_id,
            title=proposal.title,
            description=proposal.description,
            targets=targets,
        )

        proposal.matched_foundup_id = matched_id
        proposal.match_reason = reason
        proposal.confidence = confidence

    return proposals
