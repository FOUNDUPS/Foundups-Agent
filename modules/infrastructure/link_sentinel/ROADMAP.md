# Link Sentinel - Roadmap

**Status**: `SCAFFOLD_ONLY`

---

## Phase 1: PoC - Static URL Analysis

**Objective**: Core URL parsing, normalization, and rule-based risk scoring.

### Deliverables

- [ ] `src/url_parser.py` - URL parsing and normalization
- [ ] `src/risk_scorer.py` - Static rule-based scoring
- [ ] `src/link_sentinel.py` - Main service class
- [ ] Unit tests with 90%+ coverage
- [ ] Integration with `audit_logger` for event emission

### Risk Detection (Phase 1)

- Punycode/homograph detection
- Suspicious TLD matching
- Direct IP URL detection
- Excessive subdomain detection
- Known malicious domain blocklist

### Success Criteria

- `validate()` returns decisions for static analysis
- All unit tests pass
- Audit events emitted to FAM DAEmon

---

## Phase 2: Prototype - Redirect Chain Analysis

**Objective**: Follow redirects and detect redirect-based attacks.

### Deliverables

- [ ] `src/redirect_resolver.py` - Safe redirect following
- [ ] SSRF protection (private IP detection)
- [ ] Redirect chain length limits
- [ ] Domain change detection
- [ ] Cache layer for resolved URLs

### Risk Detection (Phase 2)

- Redirect chain too long
- Redirect to different domain
- Redirect to private IP (SSRF)
- Redirect loop detection

### Success Criteria

- Safe redirect resolution with timeout
- SSRF attempts blocked
- Cached results for performance

---

## Phase 3: MVP - Consumer Surface Hooks

**Objective**: Thin integration hooks in consumer surfaces.

### Deliverables

- [ ] `browser_actions` hook - Pre-navigate validation
- [ ] `livechat` hook - Message link validation
- [ ] `pfmall` hook - Content link validation
- [ ] `moltbot_bridge` hook - Discord/chat URL validation

### Integration Pattern

```python
# Thin hook pattern - consumer calls sentinel
decision = await link_sentinel.validate(context)
if decision.decision == DecisionAction.BLOCK:
    # Handle block
```

### Success Criteria

- All consumer surfaces call Link Sentinel
- Blocked links logged with audit trail
- No false positives on legitimate links

---

## Phase 4: Future - Advanced Detection

**Objective**: Sandbox detonation, reputation memory, OAuth scam detection.

### Deliverables

- [ ] Sandbox detonation integration (headless browser)
- [ ] Reputation memory (PatternMemory integration)
- [ ] OAuth redirect validation
- [ ] Credential harvesting detection
- [ ] ML-based phishing classifier (Gemma integration)

### Risk Detection (Phase 4)

- Sandbox-based analysis results
- Historical reputation scores
- OAuth redirect_uri mismatch
- Fake login page detection
- Credential harvesting indicators

### Success Criteria

- Sandbox jobs complete within SLA
- Reputation memory improves accuracy over time
- OAuth attacks detected before redirect

---

## Dependencies

### Required Infrastructure

| Component | Purpose | Status |
|-----------|---------|--------|
| `audit_logger` | Event emission | Available |
| `fam_daemon` | Event persistence | Available |
| `pattern_memory` | Reputation storage | Available |

### Optional Infrastructure

| Component | Purpose | Status |
|-----------|---------|--------|
| `gemma_rag_inference` | ML classification | Available (Phase 4) |
| `container_isolation` | Sandbox execution | Available (Phase 4) |

---

## Version History

| Version | Phase | Date | Notes |
|---------|-------|------|-------|
| 0.0.0 | Scaffold | 2026-05-10 | Initial scaffold only |
