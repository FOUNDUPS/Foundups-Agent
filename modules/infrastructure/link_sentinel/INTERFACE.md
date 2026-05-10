# Link Sentinel - Interface Contracts

**Status**: `POC_IMPLEMENTED` | `STATIC_ANALYSIS_ONLY`

Core contracts are implemented. Consumer hooks are NOT implemented.

---

## Data Contracts

### LinkContext (Input)

Context provided by consumer surfaces when requesting URL validation.

```python
@dataclass
class LinkContext:
    """Input context for link validation request.
    
    STATUS: IMPLEMENTED (src/models.py)
    """
    # URL Information
    raw_url: str                    # Original URL as received
    normalized_url: Optional[str]   # Normalized form (populated by sentinel)
    final_url: Optional[str]        # After redirect resolution (if performed)
    
    # Actor Context
    surface: str                    # Consumer surface: "browser_actions", "livechat", etc.
    actor_id: Optional[str]         # User/agent ID if known
    actor_tier: Optional[str]       # Trust tier: "anonymous", "registered", "verified"
    
    # Scope Context
    foundup_id: Optional[str]       # FoundUp context if applicable
    dao_id: Optional[str]           # DAO context if applicable
    
    # Correlation
    correlation_id: str             # Request tracking ID (UUID)
```

### LinkDecision (Output)

Decision returned by Link Sentinel after validation.

```python
@dataclass
class LinkDecision:
    """Output decision from link validation.
    
    STATUS: IMPLEMENTED (src/models.py)
    """
    # Decision
    decision: DecisionAction        # ALLOW, BLOCK, WARN, SANDBOX
    risk_score: float               # 0.0 (safe) to 1.0 (dangerous)
    reason_codes: List[RiskReasonCode]  # Why this decision was made
    
    # Audit Trail
    audit_id: str                   # Unique audit record ID
    sandbox_job_id: Optional[str]   # If SANDBOX decision, job ID for detonation
    
    # Metadata
    validation_ms: int              # Processing time in milliseconds
    cache_hit: bool                 # Whether result came from cache
```

### RiskReasonCode (Enum)

Enumeration of risk detection reasons.

```python
class RiskReasonCode(Enum):
    """Risk reason codes for link decisions.
    
    STATUS: IMPLEMENTED (src/models.py)
    """
    # URL Structure
    PUNYCODE_HOMOGRAPH = "punycode_homograph"       # Unicode lookalike attack
    SUSPICIOUS_TLD = "suspicious_tld"               # Known malicious TLD
    IP_ADDRESS_URL = "ip_address_url"               # Direct IP, not domain
    EXCESSIVE_SUBDOMAINS = "excessive_subdomains"   # Phishing indicator
    
    # Redirect Chain
    REDIRECT_CHAIN_TOO_LONG = "redirect_chain_too_long"
    REDIRECT_TO_DIFFERENT_DOMAIN = "redirect_to_different_domain"
    REDIRECT_TO_PRIVATE_IP = "redirect_to_private_ip"  # SSRF attempt
    
    # OAuth/Auth Attacks
    OAUTH_REDIRECT_MISMATCH = "oauth_redirect_mismatch"
    SUSPICIOUS_OAUTH_SCOPE = "suspicious_oauth_scope"
    FAKE_LOGIN_PAGE = "fake_login_page"
    
    # Reputation
    KNOWN_MALICIOUS_DOMAIN = "known_malicious_domain"
    NEWLY_REGISTERED_DOMAIN = "newly_registered_domain"
    LOW_REPUTATION_SCORE = "low_reputation_score"
    
    # Content Indicators
    PHISHING_KEYWORDS = "phishing_keywords"
    CREDENTIAL_HARVESTING = "credential_harvesting"
    MALWARE_DOWNLOAD = "malware_download"
    
    # Special
    SANDBOX_REQUIRED = "sandbox_required"           # Needs detonation
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
```

### DecisionAction (Enum)

Actions Link Sentinel can recommend.

```python
class DecisionAction(Enum):
    """Link decision actions.
    
    STATUS: IMPLEMENTED (src/models.py)
    """
    ALLOW = "allow"         # URL is safe, proceed
    BLOCK = "block"         # URL is dangerous, reject
    WARN = "warn"           # URL is suspicious, show warning
    SANDBOX = "sandbox"     # URL needs sandboxed analysis
```

---

## Service Contracts

### analyze_link (Main API)

Primary validation function.

```python
def analyze_link(
    raw_url: str,
    context: Optional[LinkContext] = None
) -> LinkDecision:
    """Analyze a URL and return a decision.
    
    STATUS: IMPLEMENTED (src/analyzer.py)
    
    Static analysis only - no network calls, no redirect resolution,
    no reputation lookup, no sandbox detonation.
    
    Args:
        raw_url: The URL to analyze
        context: Optional context about the actor/surface
        
    Returns:
        LinkDecision with risk assessment
    """
```

### normalize_url (Helper)

URL normalization function.

```python
def normalize_url(raw_url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Normalize URL to canonical form.
    
    STATUS: IMPLEMENTED (src/normalizer.py)
    
    - Lowercase scheme and host
    - Remove default ports
    - Remove www. prefix
    - Sort query parameters
    - Handle missing scheme (default https)
    
    Returns:
        Tuple of (normalized_url, error_message, scheme)
    """
```

---

## Consumer Integration (Future - NOT IMPLEMENTED)

### browser_actions Hook (Future)

```python
# FUTURE - NOT IMPLEMENTED
# modules/infrastructure/browser_actions/src/foundups_actions.py

async def navigate(url: str) -> ActionResult:
    """Navigate to URL with Link Sentinel validation."""
    from modules.infrastructure.link_sentinel import analyze_link, LinkContext
    
    decision = analyze_link(url, LinkContext(surface="browser_actions"))
    
    if decision.decision == DecisionAction.BLOCK:
        return ActionResult(success=False, error=f"Blocked: {decision.reason_codes}")
    
    # Proceed with navigation...
```

### livechat Hook (Future)

```python
# FUTURE - NOT IMPLEMENTED
# modules/communication/livechat/src/message_processor.py

async def process_message(message: str) -> ProcessedMessage:
    """Process chat message with link validation."""
    from modules.infrastructure.link_sentinel import analyze_link, LinkContext
    
    urls = extract_urls(message)
    for url in urls:
        decision = analyze_link(url, LinkContext(
            surface="livechat",
            actor_id=message.author_id
        ))
        
        if decision.decision == DecisionAction.BLOCK:
            # Redact or warn about dangerous link
            pass
```

---

## Audit Events (Draft)

Link Sentinel will emit events to FAM DAEmon for audit trail.

```python
# DRAFT - NOT IMPLEMENTED
FAMEventType.LINK_VALIDATION_REQUESTED
FAMEventType.LINK_VALIDATION_COMPLETED
FAMEventType.LINK_BLOCKED
FAMEventType.LINK_SANDBOXED
```

---

## Version History

| Version | Date | Status | Notes |
|---------|------|--------|-------|
| 0.1.0 | 2026-05-10 | DRAFT | Initial scaffold, contracts defined |
| 0.2.0 | 2026-05-10 | POC | Static analyzer implemented, 47 tests |
