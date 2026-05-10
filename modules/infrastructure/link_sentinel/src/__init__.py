# Link Sentinel - Source
#
# Status: POC_IMPLEMENTED - static analysis only
# WSP 97: No consumer hooks, no network calls, no redirect resolution

from .models import (
    LinkContext,
    LinkDecision,
    DecisionAction,
    RiskReasonCode,
    URL_SHORTENER_DOMAINS,
    SUSPICIOUS_TLDS,
    ALLOWED_SCHEMES,
)
from .normalizer import (
    normalize_url,
    decode_punycode,
    extract_tld,
    count_subdomains,
)
from .analyzer import analyze_link

__all__ = [
    # Core API
    "analyze_link",
    # Models
    "LinkContext",
    "LinkDecision",
    "DecisionAction",
    "RiskReasonCode",
    # Normalizer
    "normalize_url",
    "decode_punycode",
    "extract_tld",
    "count_subdomains",
    # Constants
    "URL_SHORTENER_DOMAINS",
    "SUSPICIOUS_TLDS",
    "ALLOWED_SCHEMES",
]
