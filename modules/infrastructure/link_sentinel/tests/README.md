# Link Sentinel - Tests

**Status**: `SCAFFOLD_ONLY` - No tests implemented yet

## Test Strategy (Planned)

### Unit Tests

- `test_url_parser.py` - URL parsing and normalization
- `test_risk_scorer.py` - Rule-based risk scoring
- `test_link_sentinel.py` - Main service validation

### Integration Tests

- `test_audit_integration.py` - FAM DAEmon event emission
- `test_consumer_hooks.py` - Consumer surface integration

### Test Fixtures (Planned)

```python
# Known malicious URLs (sanitized)
PHISHING_URLS = [...]

# Punycode/homograph examples
HOMOGRAPH_URLS = [...]

# Safe URLs for false positive testing
SAFE_URLS = [...]
```

## WSP Compliance

- **WSP 5**: Test coverage requirements (90%+ target)
- **WSP 6**: Test audit trail
- **WSP 49**: Test directory structure
