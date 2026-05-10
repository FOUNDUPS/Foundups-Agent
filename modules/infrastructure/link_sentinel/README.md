# Link Sentinel

**WSP Domain**: `infrastructure` (WSP 3)
**Status**: `SCAFFOLD_ONLY` | `NO_RUNTIME_GATES_IMPLEMENTED`

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

**SCAFFOLD_ONLY**: This module contains documentation and interface contracts only.
No runtime validation, scoring, or consumer hooks are implemented.

### What Exists

- Module structure (WSP 49 compliant)
- Draft interface contracts (INTERFACE.md)
- Phased roadmap (ROADMAP.md)
- Memory directory (WSP 60 compliant)

### What Does NOT Exist

- URL parsing/normalization code
- Risk scoring algorithms
- Redirect chain analysis
- Browser hooks in `browser_actions`
- Chat hooks in `livechat` or `moltbot_bridge`
- Marketplace hooks in `pfmall`
- Sandbox detonation integration

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
