"""
pfMALL YouTube Discovery - AI hook for exploratory video/channel discovery.

WSP References:
- WSP 3: AI Intelligence domain
- WSP 97: Truthful discovery (no fake claims)
"""

from modules.ai_intelligence.pfmall_discovery.src.youtube_discovery import (
    search_youtube,
    DiscoveryProposal,
)
from modules.ai_intelligence.pfmall_discovery.src.foundup_matcher import (
    match_to_foundup,
    load_catalog_targets,
)
from modules.ai_intelligence.pfmall_discovery.src.proposal_generator import (
    generate_discovery_proposals,
    write_proposal_artifact,
)

__all__ = [
    "search_youtube",
    "DiscoveryProposal",
    "match_to_foundup",
    "load_catalog_targets",
    "generate_discovery_proposals",
    "write_proposal_artifact",
]
