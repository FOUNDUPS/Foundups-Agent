# Stream Resolver Module Test Suite

This directory contains tests for the Stream Resolver module, which handles YouTube livestream discovery and metadata validation.

## Test Files
| Test File | Description |
|-----------|-------------|
| `test_no_quota_stream_checker.py` | Scrape/API verification, quota toggle matrix, both real entrypoints with fake HTTP/provider, and cache/timeout behavior |
| `test_stream_resolver.py` | Resolution flow, validation, metadata retrieval |
| `test_edge_cases.py` | Error conditions (expired streams, missing fields, 403/404) |
| `test_video.py` | Video detail validation and masking |
| `test_circuit_breaker.py` | Circuit breaker states, backoff, credential rotation |

## Running Tests
```bash
# Module-only
pytest modules/platform_integration/stream_resolver/tests/ -v

# With coverage
pytest modules/platform_integration/stream_resolver/tests/ \
  --cov=modules.platform_integration.stream_resolver.src --cov-report=term-missing
```

## WSP Compliance
- WSP 3: Platform integration domain
- WSP 34: Test docs and runnable commands present
- WSP 5: Target [GREATER_EQUAL]90% coverage
- WSP 49: Tests under module `tests/`
- WSP 50/64: No stray tests outside module; audited duplicates removed

## Recent Updates
- Added circuit breaker coverage (states, thresholds, reset) and credential rotation tests
- Corrected README paths/commands; consolidated suite execution alongside YouTube proxy
- Edge cases expanded; coverage maintained [GREATER_EQUAL]90%

### Focused offline quota verification (2026-10-23)

Run the existing file's unittest entrypoint from the repository root:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHON_DOTENV_DISABLED = "1"
python -B modules/platform_integration/stream_resolver/tests/test_no_quota_stream_checker.py -v
```

This runs all 31 checker tests using the whole real checker source and real
configuration module. Scoped test loading bypasses the package initializer's
unrelated Google/OAuth/social-posting imports. Database, lazy verifier and auth
factories are fake; HTTP responses and sleeps are mocked. The fixture clears
host environment input, denies HTTP/socket/database/subprocess effects, and
restores its module substitutions and environment on teardown. The real auth
cache accessor and both real checker entrypoints execute. Each entrypoint
covers seven toggle combinations, including global unset with local true.

On the lean qualification runtime, pytest collection of this file still fails
before fixture setup because the package initializer imports absent
`googleapiclient`. The direct command above passes without that dependency;
this is checker unit coverage, not package-wide integration or live YouTube,
credential, model, quota-account, deployment, or native RSI qualification.

The adjacent `test_no_quota_anti_rate_limit.py` retains its legacy `src` import.
Its one API-backed workflow now explicitly enables both API switches while
mocking the provider. All 13 adjacent cases passed in the external review
runner using the same real checker with scoped import aliases/effect guards;
that supplemental result does not claim the adjacent file runs standalone in
the lean environment. Both individual gate-reversion controls failed the
expected three quota-protected subcases. See `TestModLog.md` for evidence and
preserved initial failures.
