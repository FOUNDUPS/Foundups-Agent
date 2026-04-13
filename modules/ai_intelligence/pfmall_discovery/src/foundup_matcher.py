"""
FoundUp Matcher - Map discovered content to existing catalog FoundUps.

Matching policy (priority order):
1. Exact channel_id match (confidence: 1.0)
2. High-confidence known-channel match (confidence: 0.9)
3. Ambiguous shared-topic match - multiple FoundUps viable (confidence: 0.3-0.5)
4. Single tag overlap match (confidence: 0.3-0.7)
5. Category match (confidence: 0.2)
6. Unmatched (confidence: 0.0)

WSP References:
- WSP 3: AI Intelligence domain
- WSP 97: Truthful matching (no invented mappings, represent ambiguity honestly)
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
) -> Tuple[Optional[str], str, float, List[str]]:
    """
    Match a discovered item to an existing FoundUp.

    Matching policy (priority order):
    1. Exact channel_id match -> confidence 1.0
    2. Ambiguous shared-topic match -> confidence 0.3-0.5 with candidates list
    3. Single tag overlap match -> confidence 0.3-0.7
    4. Category match -> confidence 0.2
    5. No match -> confidence 0.0

    Args:
        channel_id: YouTube channel ID of discovered item
        title: Title of discovered item
        description: Description of discovered item
        targets: List of catalog targets to match against

    Returns:
        Tuple of (matched_foundup_id, match_reason, confidence, ambiguous_candidates)
    """
    if not targets:
        return None, "no_targets", 0.0, []

    # Priority 1: Exact channel_id match (unambiguous)
    for target in targets:
        if channel_id and target.source_id and channel_id == target.source_id:
            return target.foundup_id, "channel_id_match", 1.0, []

    # Extract keywords from title and description for matching
    text = f"{title} {description}".lower()
    text_words = set(text.split())

    # Collect all candidates with tag overlap scores
    tag_candidates: List[Tuple[str, float]] = []
    category_candidates: List[Tuple[str, float]] = []

    for target in targets:
        # Tag overlap scoring
        tag_overlap = _calculate_tag_overlap(list(text_words), target.tags)
        if tag_overlap >= 0.2:  # Minimum threshold for consideration
            tag_candidates.append((target.foundup_id, tag_overlap))

        # Category scoring
        if target.category and target.category in text:
            category_candidates.append((target.foundup_id, 0.2))

    # Priority 2: Check for ambiguous shared-topic match
    # If multiple FoundUps have significant tag overlap, this is ambiguous
    significant_tag_matches = [(fid, score) for fid, score in tag_candidates if score >= 0.3]

    if len(significant_tag_matches) > 1:
        # Multiple FoundUps share this topic space - ambiguous!
        # Sort by score descending
        significant_tag_matches.sort(key=lambda x: x[1], reverse=True)
        ambiguous_ids = [fid for fid, _ in significant_tag_matches]

        # Use best score but cap confidence due to ambiguity
        best_score = significant_tag_matches[0][1]
        ambiguous_confidence = min(0.5, best_score * 0.7)  # Penalize for ambiguity

        logger.info(
            f"[MATCHER] Ambiguous shared-topic match: {ambiguous_ids} "
            f"(confidence {ambiguous_confidence:.2f})"
        )

        return (
            None,  # No single match
            "ambiguous_shared_topic",
            ambiguous_confidence,
            ambiguous_ids,
        )

    # Priority 3: Single tag overlap match (unambiguous)
    if tag_candidates:
        tag_candidates.sort(key=lambda x: x[1], reverse=True)
        best_fid, best_score = tag_candidates[0]
        return best_fid, f"tag_overlap:{best_score:.2f}", best_score, []

    # Priority 4: Category match
    if category_candidates:
        # Check for ambiguous category matches too
        if len(category_candidates) > 1:
            ambiguous_ids = [fid for fid, _ in category_candidates]
            return None, "ambiguous_category", 0.15, ambiguous_ids

        best_fid, best_score = category_candidates[0]
        return best_fid, f"category_match", best_score, []

    # Priority 5: No match
    return None, "no_match", 0.0, []


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
        Proposals with matched_foundup_id, match_reason, confidence,
        and ambiguous_candidates populated
    """
    if targets is None:
        targets = load_catalog_targets()

    for proposal in proposals:
        matched_id, reason, confidence, ambiguous = match_to_foundup(
            channel_id=proposal.channel_id,
            title=proposal.title,
            description=proposal.description,
            targets=targets,
        )

        proposal.matched_foundup_id = matched_id
        proposal.match_reason = reason
        proposal.confidence = confidence
        proposal.ambiguous_candidates = ambiguous

    return proposals
