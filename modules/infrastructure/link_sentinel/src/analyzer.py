"""Link Sentinel - Static URL Analyzer

Status: POC_IMPLEMENTED
WSP: 97 (Truth Boundaries)

Static analysis only:
- URL parsing and normalization
- Punycode detection
- Private IP detection
- Credential-in-URL detection
- Suspicious pattern detection

NOT implemented (future slices):
- Redirect chain resolution
- Live reputation lookup
- Sandbox detonation
- OAuth consent scam detection
- Browser navigation enforcement
- Consumer surface hooks
"""

from typing import Optional
from urllib.parse import urlparse
import ipaddress
import re

from .models import (
    LinkContext,
    LinkDecision,
    DecisionAction,
    RiskReasonCode,
    URL_SHORTENER_DOMAINS,
    SUSPICIOUS_TLDS,
    ALLOWED_SCHEMES,
)
from .normalizer import normalize_url, decode_punycode, extract_tld, count_subdomains


# Risk score weights
RISK_WEIGHTS = {
    RiskReasonCode.INVALID_URL: 1.0,
    RiskReasonCode.EMPTY_URL: 1.0,
    RiskReasonCode.UNSUPPORTED_SCHEME: 0.9,
    RiskReasonCode.MISSING_HOST: 1.0,
    RiskReasonCode.LOCALHOST: 0.95,
    RiskReasonCode.PRIVATE_IP: 0.95,
    RiskReasonCode.LINK_LOCAL_IP: 0.95,
    RiskReasonCode.LOOPBACK_IP: 0.95,
    RiskReasonCode.RESERVED_IP: 0.9,
    RiskReasonCode.NUMERIC_HOST: 0.7,
    RiskReasonCode.CREDENTIALS_IN_URL: 0.85,
    RiskReasonCode.PUNYCODE_DOMAIN: 0.6,
    RiskReasonCode.EXCESSIVE_SUBDOMAINS: 0.5,
    RiskReasonCode.URL_SHORTENER: 0.4,
    RiskReasonCode.SUSPICIOUS_TLD: 0.3,
    RiskReasonCode.CLEAN: 0.0,
}

# Subdomain depth threshold
MAX_SUBDOMAIN_DEPTH = 4


def _is_ip_address(host: str) -> bool:
    """Check if host is an IP address."""
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _check_ip_risks(host: str) -> list[RiskReasonCode]:
    """Check IP address for risks."""
    reasons = []

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return reasons

    if ip.is_loopback:
        reasons.append(RiskReasonCode.LOOPBACK_IP)
    elif ip.is_link_local:
        # Check link-local BEFORE private (169.254.x.x is both link_local AND private in some cases)
        reasons.append(RiskReasonCode.LINK_LOCAL_IP)
    elif ip.is_private:
        reasons.append(RiskReasonCode.PRIVATE_IP)
    elif ip.is_reserved:
        reasons.append(RiskReasonCode.RESERVED_IP)

    return reasons


def _is_localhost(host: str) -> bool:
    """Check if host is localhost."""
    localhost_names = {"localhost", "localhost.localdomain", "127.0.0.1", "::1"}
    return host.lower() in localhost_names


def _has_credentials(raw_url: str) -> bool:
    """Check if URL contains credentials.

    Must check raw URL because normalization strips credentials.
    """
    try:
        parsed = urlparse(raw_url)
        return bool(parsed.username or parsed.password)
    except Exception:
        return False


def _is_url_shortener(host: str) -> bool:
    """Check if host is a known URL shortener."""
    # Check exact match
    if host in URL_SHORTENER_DOMAINS:
        return True

    # Check with www. prefix removed
    if host.startswith("www."):
        if host[4:] in URL_SHORTENER_DOMAINS:
            return True

    return False


def _calculate_risk_score(reason_codes: list[RiskReasonCode]) -> float:
    """Calculate risk score from reason codes."""
    if not reason_codes:
        return 0.0

    if RiskReasonCode.CLEAN in reason_codes:
        return 0.0

    # Take maximum risk from all reasons
    max_risk = max(RISK_WEIGHTS.get(code, 0.5) for code in reason_codes)
    return max_risk


def _determine_decision(
    reason_codes: list[RiskReasonCode],
    risk_score: float
) -> DecisionAction:
    """Determine decision action based on reason codes and risk score."""

    # Immediate blocks
    blocking_codes = {
        RiskReasonCode.INVALID_URL,
        RiskReasonCode.EMPTY_URL,
        RiskReasonCode.MISSING_HOST,
        RiskReasonCode.LOCALHOST,
        RiskReasonCode.LOOPBACK_IP,
        RiskReasonCode.PRIVATE_IP,
        RiskReasonCode.LINK_LOCAL_IP,
    }

    if any(code in blocking_codes for code in reason_codes):
        return DecisionAction.BLOCK

    # Quarantine
    quarantine_codes = {
        RiskReasonCode.CREDENTIALS_IN_URL,
        RiskReasonCode.UNSUPPORTED_SCHEME,
        RiskReasonCode.RESERVED_IP,
    }

    if any(code in quarantine_codes for code in reason_codes):
        return DecisionAction.QUARANTINE

    # Warnings
    warning_codes = {
        RiskReasonCode.PUNYCODE_DOMAIN,
        RiskReasonCode.EXCESSIVE_SUBDOMAINS,
        RiskReasonCode.URL_SHORTENER,
        RiskReasonCode.SUSPICIOUS_TLD,
        RiskReasonCode.NUMERIC_HOST,
    }

    if any(code in warning_codes for code in reason_codes):
        return DecisionAction.WARN

    # High risk score without specific code
    if risk_score >= 0.7:
        return DecisionAction.QUARANTINE
    elif risk_score >= 0.4:
        return DecisionAction.WARN

    return DecisionAction.ALLOW


def analyze_link(
    raw_url: str,
    context: Optional[LinkContext] = None
) -> LinkDecision:
    """Analyze a URL and return a decision.

    Static analysis only - no network calls, no redirect resolution,
    no reputation lookup, no sandbox detonation.

    Args:
        raw_url: The URL to analyze
        context: Optional context about the actor/surface

    Returns:
        LinkDecision with risk assessment
    """
    decision = LinkDecision(raw_url=raw_url, context=context)
    reason_codes: list[RiskReasonCode] = []

    # Step 1: Normalize URL
    normalized, error, scheme = normalize_url(raw_url)

    if error == "empty_url":
        reason_codes.append(RiskReasonCode.EMPTY_URL)
        decision.reason_codes = reason_codes
        decision.risk_score = _calculate_risk_score(reason_codes)
        decision.decision = DecisionAction.BLOCK
        return decision

    if error == "invalid_url":
        reason_codes.append(RiskReasonCode.INVALID_URL)
        decision.reason_codes = reason_codes
        decision.risk_score = _calculate_risk_score(reason_codes)
        decision.decision = DecisionAction.BLOCK
        return decision

    if error == "missing_host":
        reason_codes.append(RiskReasonCode.MISSING_HOST)
        decision.scheme = scheme
        decision.reason_codes = reason_codes
        decision.risk_score = _calculate_risk_score(reason_codes)
        decision.decision = DecisionAction.BLOCK
        return decision

    decision.normalized_url = normalized
    decision.scheme = scheme

    # Step 2: Parse normalized URL for detailed analysis
    try:
        parsed = urlparse(normalized)
    except Exception:
        reason_codes.append(RiskReasonCode.INVALID_URL)
        decision.reason_codes = reason_codes
        decision.risk_score = _calculate_risk_score(reason_codes)
        decision.decision = DecisionAction.BLOCK
        return decision

    host = (parsed.hostname or "").lower()
    decision.host = host
    try:
        decision.port = parsed.port
    except ValueError:
        decision.port = None
    decision.path = parsed.path

    # Step 3: Check scheme
    if scheme and scheme not in ALLOWED_SCHEMES:
        reason_codes.append(RiskReasonCode.UNSUPPORTED_SCHEME)

    # Step 4: Check for credentials in URL (check RAW url, not normalized)
    if _has_credentials(raw_url):
        reason_codes.append(RiskReasonCode.CREDENTIALS_IN_URL)

    # Step 5: Check localhost
    if _is_localhost(host):
        reason_codes.append(RiskReasonCode.LOCALHOST)

    # Step 6: Check IP address
    if _is_ip_address(host):
        ip_risks = _check_ip_risks(host)
        if ip_risks:
            reason_codes.extend(ip_risks)
        else:
            # Numeric host that isn't private - still suspicious
            reason_codes.append(RiskReasonCode.NUMERIC_HOST)
    else:
        # Step 7: Domain-based checks (only for non-IP hosts)

        # Check punycode
        decoded_host, is_punycode = decode_punycode(host)
        if is_punycode:
            decision.punycode_host = host
            decision.decoded_host = decoded_host
            reason_codes.append(RiskReasonCode.PUNYCODE_DOMAIN)

        # Check URL shortener
        if _is_url_shortener(host):
            reason_codes.append(RiskReasonCode.URL_SHORTENER)

        # Check subdomain depth
        subdomain_count = count_subdomains(host)
        if subdomain_count > MAX_SUBDOMAIN_DEPTH:
            reason_codes.append(RiskReasonCode.EXCESSIVE_SUBDOMAINS)

        # Check TLD
        tld = extract_tld(host)
        if tld and tld in SUSPICIOUS_TLDS:
            reason_codes.append(RiskReasonCode.SUSPICIOUS_TLD)

    # Step 8: Calculate final score and decision
    if not reason_codes:
        reason_codes.append(RiskReasonCode.CLEAN)

    decision.reason_codes = reason_codes
    decision.risk_score = _calculate_risk_score(reason_codes)
    decision.decision = _determine_decision(reason_codes, decision.risk_score)

    return decision
