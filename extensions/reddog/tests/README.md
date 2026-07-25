# RedDog Extension Tests

## Test strategy

Contract tests run **without OpenRouter, Cursor UI, or live bridge calls**. They validate extension source shape, exported helpers, bounded-context assembly, and Copy MD schema.

**Reuse rule (WSP 50):** Before adding tests, read `fixtures.js`, `TestModLog.md` TEST_REGISTRY, and `verify_extension_contract.js`. Extend existing fixtures and assertions; do not duplicate prompt strings or EXT-ACC probes.

## How to run

From repo root:

```powershell
node --check extensions/reddog/extension.js
node extensions/reddog/tests/test_backend_compatibility_preflight.js
pytest -q scripts/tests/test_generate_reddog_backend_manifest.py
node extensions/reddog/tests/verify_repo_audit_grounding.js
node extensions/reddog/tests/verify_extension_contract.js
git diff --check -- extensions/reddog
```

HoloIndex bundle recall (separate module tests):

```powershell
python -m pytest holo_index/tests/test_reddog_extension_bundle_recall.py -q
python -m pytest holo_index/tests/test_repo_audit_discovery.py scripts/tests/test_advisory_model_defensive_critic.py -q
```

## Fixtures

| File | Purpose |
| --- | --- |
| `fixtures.js` | Shared prompts and path lists (EXT-ACC-001, denied paths) |
| `test_backend_compatibility_preflight.js` | Pinned manifest, runtime dependency-closure integrity, intermediate junction rejection, WSP_62 ceilings, canonical containment, and content-free failure contracts |
| `test_backend_compatibility_contract.js` | Independent executable roots, closure sentinels, pinned digest, runtime gate ordering, and allowlisted block projection |
| `test_backend_compatibility_async.js` | Worker-thread preflight, event-loop availability, and fail-closed invalid-root behavior |
| `test_authoritative_work_state_query.js` | Local authoritative-work classification, bridge failure handling, and no-Fusion routing |
| `scripts/tests/test_generate_reddog_backend_manifest.py` | Package-initializer resolution, executable roots, dynamic-load sentinels, and checked-in generator parity |
| `verify_extension_contract.js` | Single contract runner; ADDENDUM E ~line 518+, ADDENDUM F gate probe ~line 595+ |
| `verify_repo_audit_grounding.js` | Focused alias, receipt, protected-context non-vacuity, local block, repair-provenance, and defensive-prompt contracts |

## TEST_REGISTRY

See `TestModLog.md` for TCI-001 through TCI-010, THG-001 through THG-006, UNI-001 through UNI-007, WFTD-001 through WFTD-014 (free-form work-focus target derivation), WFTD-015 through WFTD-020 (flowing-prose read-capture tokenization + tiered strictness, v0.3.45), and WRE-DRY-001 through WRE-DRY-010 (WRE operational spine dry-run preview).

## Expected behavior

- `inferRecallTargetPaths(EXT_ACC_001_PROMPT)` includes `extension.js`.
- `resolveAutoContextMode(EXT_ACC_001_PROMPT tier HIGH)` unchanged; REGULAR -> `wsp_holo`.
- ADDENDUM F: sanitized snippets pass Python `evaluate_redaction_gate` (TCI-009/TCI-010).
- THG-001..006: REGULAR HoloIndex grounding (see TestModLog registry).
- Path safety rejects absolute, traversal, `.env`, `.git`, `node_modules`, `.vsix`.
- Repository/module audits require content-bearing implementation source plus independent test/contract evidence in final model context; missing proof blocks locally before any network call.

## Integration requirements

- VSCode API mocked via `node_modules/vscode` stub in contract runner.
- Workspace root = repo root (three levels above `tests/`).
