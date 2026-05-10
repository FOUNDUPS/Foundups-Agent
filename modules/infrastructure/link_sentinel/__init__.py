# Link Sentinel - Centralized URL Safety Validation
#
# Status: POC_IMPLEMENTED - static analysis only
# WSP 97: No consumer hooks, no network calls, no redirect resolution

from .src import (
    # Core API
    analyze_link,
    # Models
    LinkContext,
    LinkDecision,
    DecisionAction,
    RiskReasonCode,
    # Normalizer
    normalize_url,
    decode_punycode,
    extract_tld,
    count_subdomains,
    # Constants
    URL_SHORTENER_DOMAINS,
    SUSPICIOUS_TLDS,
    ALLOWED_SCHEMES,
)

__all__ = [
    "analyze_link",
    "LinkContext",
    "LinkDecision",
    "DecisionAction",
    "RiskReasonCode",
    "normalize_url",
    "decode_punycode",
    "extract_tld",
    "count_subdomains",
    "URL_SHORTENER_DOMAINS",
    "SUSPICIOUS_TLDS",
    "ALLOWED_SCHEMES",
]
