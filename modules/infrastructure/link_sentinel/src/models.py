"""Link Sentinel - Data Models

Status: POC_IMPLEMENTED
WSP: 97 (Truth Boundaries)

Static analysis models only. No runtime consumer hooks.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import uuid


class DecisionAction(Enum):
    """Link decision actions."""
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    QUARANTINE = "quarantine"
    SANDBOX_REQUIRED = "sandbox_required"


class RiskReasonCode(Enum):
    """Risk reason codes for link decisions."""
    # URL Structure
    INVALID_URL = "invalid_url"
    EMPTY_URL = "empty_url"
    UNSUPPORTED_SCHEME = "unsupported_scheme"
    MISSING_HOST = "missing_host"

    # Host Analysis
    LOCALHOST = "localhost"
    PRIVATE_IP = "private_ip"
    LINK_LOCAL_IP = "link_local_ip"
    LOOPBACK_IP = "loopback_ip"
    RESERVED_IP = "reserved_ip"
    NUMERIC_HOST = "numeric_host"

    # Credential Exposure
    CREDENTIALS_IN_URL = "credentials_in_url"

    # Suspicious Patterns
    PUNYCODE_DOMAIN = "punycode_domain"
    EXCESSIVE_SUBDOMAINS = "excessive_subdomains"
    URL_SHORTENER = "url_shortener"
    SUSPICIOUS_TLD = "suspicious_tld"

    # Safe
    CLEAN = "clean"


@dataclass
class LinkContext:
    """Input context for link validation request."""
    # Actor Context
    surface: Optional[str] = None
    actor_id: Optional[str] = None
    actor_tier: Optional[str] = None

    # Scope Context
    foundup_id: Optional[str] = None
    dao_id: Optional[str] = None

    # Correlation
    correlation_id: Optional[str] = None


@dataclass
class LinkDecision:
    """Output decision from link validation."""
    # Input
    raw_url: str

    # Normalized
    normalized_url: Optional[str] = None
    host: Optional[str] = None
    scheme: Optional[str] = None
    port: Optional[int] = None
    path: Optional[str] = None

    # Punycode tracking
    punycode_host: Optional[str] = None
    decoded_host: Optional[str] = None

    # Decision
    decision: DecisionAction = DecisionAction.BLOCK
    risk_score: float = 1.0
    reason_codes: List[RiskReasonCode] = field(default_factory=list)

    # Audit Trail
    audit_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Context (preserved from input)
    context: Optional[LinkContext] = None

    # Truth flags (WSP 97)
    analysis_type: str = "static"
    redirect_resolved: bool = False
    reputation_checked: bool = False
    sandbox_analyzed: bool = False


# URL shortener domains (small built-in list)
URL_SHORTENER_DOMAINS = frozenset({
    "bit.ly",
    "t.co",
    "goo.gl",
    "tinyurl.com",
    "ow.ly",
    "is.gd",
    "buff.ly",
    "adf.ly",
    "j.mp",
    "tr.im",
    "cli.gs",
    "short.to",
    "budurl.com",
    "ping.fm",
    "post.ly",
    "just.as",
    "bkite.com",
    "snipr.com",
    "fic.kr",
    "loopt.us",
    "doiop.com",
    "su.pr",
    "twurl.nl",
    "snipurl.com",
    "short.ie",
    "rebrand.ly",
    "shorturl.at",
    "cutt.ly",
    "v.gd",
    "rb.gy",
})

# Suspicious TLDs (high spam/phishing association)
SUSPICIOUS_TLDS = frozenset({
    "xyz",
    "top",
    "club",
    "work",
    "click",
    "link",
    "loan",
    "win",
    "download",
    "stream",
    "racing",
    "review",
    "country",
    "science",
    "party",
    "date",
    "faith",
    "accountant",
    "cricket",
    "trade",
    "webcam",
    "bid",
    "gdn",
    "men",
})

# Allowed schemes for web URLs
ALLOWED_SCHEMES = frozenset({
    "http",
    "https",
})
