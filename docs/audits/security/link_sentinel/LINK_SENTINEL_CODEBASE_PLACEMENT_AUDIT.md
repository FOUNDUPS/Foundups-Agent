# Link Sentinel Codebase Placement Audit

**Audit Date**: 2026-05-10  
**Slice**: `LINK_SENTINEL_CODEBASE_PLACEMENT_AUDIT_PHASE1`  
**Worker**: W2  
**WSP Lock**: WSP 00 → WSP 97 → WSP 15 → WSP 50  
**Mode**: Architecture research — not implementation

---

## 1. Final Verdict

### **PLACE_AS_NEW_INFRASTRUCTURE_MODULE**

Link Sentinel should be placed as a **new infrastructure module** at `modules/infrastructure/link_sentinel/`.

**Key Rationale**:
- No existing module owns URL threat analysis (security_scanner is for dependencies)
- Vendor tools (url_safety.py, tirith_security.py) are partial solutions, not comprehensive
- Multiple consumer surfaces require centralized validation (browser_actions, livechat, moltbot_bridge)
- Cross-cutting concern spanning FoundUp boundaries requires infrastructure placement

---

## 2. HoloIndex Discovery

### 2.1 Search Command

```bash
python holo_index.py --search "Link Sentinel URL safety browser_actions livechat pfmall OAuth Discord malicious links WSP 49 WSP 96" --limit 10
```

### 2.2 Top Hits

| Rank | File | Relevance |
|------|------|-----------|
| 1 | `modules/communication/livechat/src/message_processor.py` | Consumer surface (chat links) |
| 2 | `modules/communication/livechat/src/peertube_relay_handler.py` | Consumer surface |
| 3 | `modules/infrastructure/browser_actions/src/foundups_actions.py` | Consumer surface (navigate) |
| 4 | `WSP_framework/src/WSP_108_Documentation_Compliance_Guardian.md` | Guardian pattern reference |
| 5 | `WSP_framework/src/WSP_MODULE_PLACEMENT_GUIDE.md` | Module placement guidance |

---

## 3. Codebase Evidence

### 3.1 Existing URL Safety Tools (Vendor)

| File | Purpose | Coverage Gap |
|------|---------|-------------|
| `vendor/hermes-agent/tools/url_safety.py` | SSRF protection (blocks private IPs) | No phishing, punycode, OAuth attack detection |
| `vendor/hermes-agent/tools/website_policy.py` | Domain blocklist from config | Static list only, no threat intelligence |
| `vendor/hermes-agent/tools/tirith_security.py` | Pre-exec scanning (homograph URLs) | Command scanning, not URL-at-rest validation |

### 3.2 Existing Security Modules (FoundUps)

| Module | Location | Purpose | Link Sentinel Fit |
|--------|----------|---------|-------------------|
| `security_scanner` | `modules/infrastructure/security_scanner/` | CLI vuln scanning (snyk, trivy, semgrep) | NO - dependency focus |
| `wre_core/security_*` | `modules/infrastructure/wre_core/src/` | SEC1-SEC9 stack (file changes, patterns) | NO - different threat class |
| `audit_logger` | `modules/infrastructure/shared_utilities/audit_logger/` | Event logging | YES - consumer for telemetry |
| `container_isolation` | `modules/infrastructure/container_isolation/` | Execution isolation | NO - runtime isolation |

### 3.3 Consumer Surfaces (Would Call Link Sentinel)

| Surface | Location | URL Source |
|---------|----------|------------|
| `browser_actions` | `modules/infrastructure/browser_actions/` | navigate(url) action |
| `livechat` | `modules/communication/livechat/` | User-posted chat links |
| `moltbot_bridge` | `modules/communication/moltbot_bridge/` | Discord/livechat URLs |
| `pfmall` | `modules/foundups/pfmall/` | FoundUp content links |
| `youtube_auth` | `modules/platform_integration/youtube_auth/` | OAuth redirect URLs |

---

## 4. Existing Anchors

### 4.1 Reusable Vendor Code

**`vendor/hermes-agent/tools/url_safety.py`** (98 lines):
- `is_safe_url(url)` - SSRF protection
- Pattern: IP validation, blocked hostname set
- **Reuse**: Import for SSRF layer in Link Sentinel

**`vendor/hermes-agent/tools/website_policy.py`** (283 lines):
- `check_website_access(url)` - Domain blocklist
- Pattern: Config-driven, fnmatch rules
- **Reuse**: Pattern for dynamic blocklist loading

**`vendor/hermes-agent/tools/tirith_security.py`** (homograph detection):
- External binary invocation
- Pattern: Exit code as verdict source
- **Reference**: Homograph detection logic

### 4.2 Existing Audit Infrastructure

**`modules/infrastructure/shared_utilities/audit_logger/`**:
- `log_security_event()` - Security event logging
- `AuditCategory.SECURITY` - Category enum
- **Integration**: Link Sentinel emits events here

---

## 5. Existing Gaps

| Gap | Description | Link Sentinel Coverage |
|-----|-------------|----------------------|
| **Phishing detection** | No URL reputation/classification | Pattern + optional API integration |
| **Punycode/IDN homograph** | Tirith covers commands, not URLs at rest | IDN normalization + visual similarity check |
| **OAuth consent attack** | No detection of malicious OAuth redirect | OAuth redirect pattern matching |
| **Shortened URL resolution** | No unshortening before validation | Follow redirects, validate final destination |
| **Calendar invite injection** | Google Calendar link abuse | calendar.google.com pattern matching |
| **Quarantine workflow** | No isolated preview/sandbox | Link quarantine + human review gate |
| **Cross-surface coordination** | Each module validates independently | Centralized validation + threat memory |

---

## 6. Recommended Module Placement

### 6.1 Primary Location

```
modules/infrastructure/link_sentinel/
├── README.md
├── INTERFACE.md
├── ModLog.md
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── link_sentinel.py          # Core validator
│   ├── threat_classifier.py      # URL threat classification
│   ├── punycode_analyzer.py      # IDN/homograph detection
│   ├── redirect_resolver.py      # URL unshortening
│   └── quarantine_manager.py     # Quarantine workflow
├── tests/
│   └── test_link_sentinel.py
└── memory/
    └── threat_hotlist.json       # Known malicious patterns
```

### 6.2 Justification

| Criterion | Assessment |
|-----------|------------|
| **WSP 3 Domain** | infrastructure (cross-cutting security) |
| **WSP 49 Structure** | Standard module layout |
| **Independence (WSP 72)** | Self-contained, consumers import |
| **Single Responsibility** | URL threat analysis only |
| **HoloIndex Discoverable** | infrastructure/ is indexed |

---

## 7. Proposed Module Name

**`link_sentinel`**

| Component | Meaning |
|-----------|---------|
| `link` | URL/href target |
| `sentinel` | Gate/watchdog pattern (consistent with git_main_merge_sentinel, prompt_security_sentinel) |

---

## 8. Consumer Surfaces

### 8.1 Primary Consumers

| Consumer | Integration Point | Priority |
|----------|-------------------|----------|
| `browser_actions` | Before `navigate(url)` execution | P0 |
| `livechat` | Before displaying user-posted links | P0 |
| `moltbot_bridge` | Before relaying external URLs | P1 |
| `pfmall` | Before loading FoundUp content | P1 |
| `youtube_auth` | Before OAuth redirect handling | P2 |

### 8.2 Consumer Interface

```python
from modules.infrastructure.link_sentinel import LinkSentinel

sentinel = LinkSentinel()
result = sentinel.check_url(url, context={"source": "livechat", "foundup_id": "move2japan"})

if result.safe:
    # Proceed with navigation/display
else:
    # Quarantine or block
    audit_logger.log_security_event(
        source="livechat",
        action="link_blocked",
        details={"url": url, "threat_type": result.threat_type}
    )
```

---

## 9. Non-Goals (Phase 1)

| Non-Goal | Reason |
|----------|--------|
| **Real-time threat intelligence API** | Cost/latency; defer to Phase 2 |
| **ML-based phishing classifier** | Requires training data; defer |
| **Browser sandbox preview** | Complex; separate container_isolation concern |
| **Automated takedown requests** | Legal complexity; human workflow |
| **Cross-FoundUp threat sharing** | Requires pAVS federation; defer |

---

## 10. Risk Taxonomy Draft

### 10.1 Threat Classes

| Threat Class | Examples | Detection Method |
|--------------|----------|------------------|
| **SSRF** | `http://169.254.169.254/`, localhost | IP range blocking (reuse url_safety.py) |
| **Phishing** | Lookalike domains, credential harvesting | Pattern matching + optional API |
| **IDN Homograph** | `аpple.com` (Cyrillic 'а') | Punycode normalization + visual similarity |
| **OAuth Hijack** | Malicious redirect_uri | OAuth parameter validation |
| **Calendar Injection** | calendar.google.com invite abuse | Known pattern matching |
| **Shortened URL Abuse** | bit.ly → malicious target | Redirect resolution + final validation |
| **File Protocol** | `file:///etc/passwd` | Protocol whitelist |
| **JavaScript Protocol** | `javascript:alert(1)` | Protocol whitelist |

### 10.2 Severity Mapping

| Severity | Action | Examples |
|----------|--------|----------|
| **CRITICAL** | Block immediately | SSRF, file://, javascript: |
| **HIGH** | Block + alert | IDN homograph, known phishing |
| **MEDIUM** | Quarantine + human review | Suspicious redirect chain |
| **LOW** | Allow + log | Unknown domain, first-seen |

---

## 11. Event/Envelope Draft

### 11.1 Check Result

```python
@dataclass
class LinkCheckResult:
    url: str
    safe: bool
    threat_class: Optional[str]  # "phishing", "ssrf", "homograph", etc.
    severity: str  # "critical", "high", "medium", "low"
    final_url: Optional[str]  # After redirect resolution
    evidence: List[str]  # Detection reasons
    quarantine_id: Optional[str]  # If quarantined
```

### 11.2 Audit Event

```python
{
    "event_type": "link_check",
    "url": "https://аpple.com/login",
    "final_url": "https://xn--pple-43d.com/login",
    "threat_class": "idn_homograph",
    "severity": "high",
    "action": "blocked",
    "source": "livechat",
    "foundup_id": "move2japan",
    "timestamp": "2026-05-10T08:45:00Z"
}
```

---

## 12. Suggested PR Sequence

| PR | Scope | Dependencies |
|----|-------|--------------|
| **PR 1** | Module scaffold (README, INTERFACE, tests) | None |
| **PR 2** | Core link_sentinel.py with protocol/SSRF blocking | PR 1 |
| **PR 3** | IDN/punycode analyzer | PR 2 |
| **PR 4** | Redirect resolver | PR 2 |
| **PR 5** | browser_actions integration | PR 2 |
| **PR 6** | livechat integration | PR 2 |
| **PR 7** | Quarantine manager + audit_logger integration | PR 2, audit_logger |
| **PR 8** | Threat hotlist memory + HoloIndex persistence | PR 7 |

---

## 13. Files Likely to Change Later

| File | Change Type |
|------|-------------|
| `modules/infrastructure/browser_actions/src/foundups_actions.py` | Add link_sentinel gate |
| `modules/communication/livechat/src/message_processor.py` | Add link_sentinel check |
| `modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py` | Add link_sentinel check |
| `modules/foundups/pfmall/content_load_policy.py` | Add link_sentinel check |
| `modules/infrastructure/shared_utilities/audit_logger/src/audit_logger.py` | Add LINK_THREAT category |

---

## 14. Files Explicitly Not to Touch

| File | Reason |
|------|--------|
| `vendor/hermes-agent/tools/url_safety.py` | Vendor code; import only |
| `vendor/hermes-agent/tools/website_policy.py` | Vendor code; reference pattern only |
| `vendor/hermes-agent/tools/tirith_security.py` | Vendor code; reference only |
| `modules/infrastructure/security_scanner/` | Different concern (dependency vulns) |
| `modules/infrastructure/wre_core/src/security_*.py` | Different concern (SEC1-SEC9 stack) |
| `modules/foundups/*/` | Consumer surfaces; separate PRs |

---

## 15. WSP 97 Truth Table

| Claim | Status | Evidence |
|-------|--------|----------|
| No existing module owns URL threat analysis | VERIFIED | security_scanner is dependencies; wre_core is file changes |
| vendor/url_safety.py covers SSRF only | VERIFIED | File read: blocks private IPs, no phishing detection |
| vendor/tirith_security.py scans commands | VERIFIED | File read: pre-exec scanning, not URL-at-rest |
| browser_actions has navigate() action | VERIFIED | INTERFACE.md documents navigate action |
| livechat handles user-posted links | VERIFIED | message_processor.py in HoloIndex results |
| audit_logger has security event logging | VERIFIED | README.md documents log_security_event() |
| Link Sentinel fits infrastructure domain | ASSESSED | Cross-cutting security concern |
| Module name follows sentinel pattern | ASSESSED | Consistent with git_main_merge_sentinel |

### 15.1 Uncertainty Acknowledgment

| Item | Uncertainty Level |
|------|------------------|
| Exact threat detection patterns | HIGH - Requires research |
| API integration for threat intelligence | MEDIUM - Cost/latency tradeoffs |
| Quarantine workflow UX | MEDIUM - Requires design |
| Performance impact on navigate() | MEDIUM - Needs benchmarking |

---

## 16. Gitignore Status

**BLOCKER**: `docs/audits/security/` is currently gitignored (line 321: `docs/audits/*`). No exception exists for `!docs/audits/security/`.

Per slice instructions, I did NOT edit `.gitignore`. This audit file is created but will not be tracked until an exception is added.

---

## Sources

### Internal (FoundUps)
- `vendor/hermes-agent/tools/url_safety.py` — SSRF protection
- `vendor/hermes-agent/tools/website_policy.py` — Domain blocklist
- `vendor/hermes-agent/tools/tirith_security.py` — Pre-exec scanning
- `modules/infrastructure/security_scanner/README.md` — Dependency scanning
- `modules/infrastructure/browser_actions/README.md` — Action router
- `modules/infrastructure/shared_utilities/audit_logger/README.md` — Audit logging
- `modules/foundups/docs/PFMALL_DATA_ISOLATION_MODEL.md` — Sentinel layer model

---

## WSP 97 Note

**Truth Boundaries Applied**:

1. All claims sourced from codebase files (direct reads)
2. Placement recommendation is architectural assessment, not implementation
3. No runtime code created in this slice
4. Consumer integration deferred to separate PRs
5. Uncertainties acknowledged with levels
6. Gitignore blocker reported per slice instructions

---

*Audit performed by Worker W2 under WSP 97 truth boundaries.*
