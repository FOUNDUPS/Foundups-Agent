# Link Sentinel

**WSP Domain**: `infrastructure` (WSP 3)
**Status**: `POC_IMPLEMENTED` | `STATIC_ANALYSIS_ONLY`

## Purpose

Centralized URL safety validation for the pAVS ecosystem. Link Sentinel provides
threat detection before URLs reach browser automation, chat systems, or marketplace
surfaces.

## Placement Rationale

Per `LINK_SENTINEL_CODEBASE_PLACEMENT_AUDIT.md` (2026-05-10):

- No existing module owns URL threat analysis
- `security_scanner` is for dependency vulnerabilities, not URL threats
- Vendor tools (`url_safety.py`, `tirith_security.py`) are partial solutions
- Multiple consumer surfaces require centralized validation
- Cross-cutting concern spanning FoundUp boundaries requires infrastructure placement

Final verdict: `PLACE_AS_NEW_INFRASTRUCTURE_MODULE`

## Consumer Surfaces

| Surface | Location | URL Source |
|---------|----------|------------|
| `browser_actions` | `modules/infrastructure/browser_actions/` | `navigate(url)` action |
| `livechat` | `modules/communication/livechat/` | User-posted chat links |
| `moltbot_bridge` | `modules/communication/moltbot_bridge/` | Discord/livechat URLs |
| `pfmall` | `modules/foundups/pfmall/` | FoundUp content links |
| Future DAO/marketplace | TBD | User-generated content links |

## Non-Goals

Link Sentinel is NOT:

- **Dependency scanning**: Use `security_scanner` for CVE/package vulnerabilities
- **OpenClaw skill sentinel**: Skill permission/safety is a separate concern
- **FAM token/rate sentinel**: Token economics validation is separate
- **Browser automation**: Link Sentinel validates URLs, does not navigate them

## Architecture (Draft)

```
Consumer Surfaces                    Link Sentinel
================                    ==============

browser_actions ----+
                    |
livechat ---------->+----> [LinkSentinel] --> LinkDecision
                    |           |
moltbot_bridge ----+            +-> URL Parse/Normalize
                    |           +-> Punycode/Lookalike Detection
pfmall -------------+           +-> Redirect Chain Analysis
                                +-> Risk Scoring
                                +-> Audit Event Emission
```

## Current Status

**POC_IMPLEMENTED**: Static URL analysis is functional. No consumer hooks.

### What Exists (PoC)

- Module structure (WSP 49 compliant)
- URL parsing and normalization (`normalizer.py`)
- Static risk scoring (`analyzer.py`)
- Data models (`models.py`)
- 47 unit tests with full coverage
- Memory directory (WSP 60 compliant)

### Static Analysis Features

| Feature | Status | Notes |
|---------|--------|-------|
| URL parsing | IMPLEMENTED | stdlib `urllib.parse` |
| URL normalization | IMPLEMENTED | Lowercase, default ports, www removal |
| Scheme validation | IMPLEMENTED | http/https only |
| Punycode detection | IMPLEMENTED | IDN/homograph warning |
| Private IP detection | IMPLEMENTED | 10.x, 172.16.x, 192.168.x |
| Link-local IP detection | IMPLEMENTED | 169.254.x.x (SSRF) |
| Localhost detection | IMPLEMENTED | localhost, 127.0.0.1, ::1 |
| Credential-in-URL | IMPLEMENTED | user:pass@host |
| URL shortener detection | IMPLEMENTED | bit.ly, t.co, etc. |
| Excessive subdomains | IMPLEMENTED | >4 subdomain depth |
| Suspicious TLD | IMPLEMENTED | .xyz, .top, etc. |

### What Does NOT Exist (Future Slices)

- Redirect chain resolution (requires network)
- Live reputation lookup (requires external API)
- Sandbox detonation (requires browser isolation)
- OAuth scam detection (requires consent flow analysis)
- Browser hooks in `browser_actions`
- Chat hooks in `livechat` or `moltbot_bridge`
- Marketplace hooks in `pfmall`

## Usage

```python
from modules.infrastructure.link_sentinel import analyze_link, LinkContext

# Basic analysis
result = analyze_link("https://example.com/page")
print(result.decision)  # DecisionAction.ALLOW

# With context
context = LinkContext(surface="browser_actions", actor_id="user123")
result = analyze_link("https://bit.ly/abc123", context=context)
print(result.decision)      # DecisionAction.WARN
print(result.reason_codes)  # [RiskReasonCode.URL_SHORTENER]

# Blocked URL
result = analyze_link("http://192.168.1.1/admin")
print(result.decision)      # DecisionAction.BLOCK
print(result.reason_codes)  # [RiskReasonCode.PRIVATE_IP]
```

## WSP Compliance

- **WSP 3**: Infrastructure domain (cross-cutting validation service)
- **WSP 11**: Interface contracts defined (INTERFACE.md)
- **WSP 22**: ModLog initialized (ModLog.md)
- **WSP 49**: Full module structure
- **WSP 60**: Memory directory with documentation

## Related Documentation

- [Placement Audit](../../../docs/audits/security/link_sentinel/LINK_SENTINEL_CODEBASE_PLACEMENT_AUDIT.md)
- [INTERFACE.md](./INTERFACE.md) - API contracts
- [ROADMAP.md](./ROADMAP.md) - Phased delivery plan
