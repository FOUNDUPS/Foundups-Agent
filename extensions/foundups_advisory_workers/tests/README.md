# Foundups(R)Agent Extension Tests

## Test strategy

Contract tests run **without OpenRouter, Cursor UI, or live bridge calls**. They validate extension source shape, exported helpers, bounded-context assembly, and Copy MD schema.

**Reuse rule (WSP 50):** Before adding tests, read `fixtures.js`, `TestModLog.md` TEST_REGISTRY, and `verify_extension_contract.js`. Extend existing fixtures and assertions; do not duplicate prompt strings or EXT-ACC probes.

## How to run

From repo root:

```powershell
node --check extensions/foundups_advisory_workers/extension.js
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
git diff --check -- extensions/foundups_advisory_workers
```

HoloIndex bundle recall (separate module tests):

```powershell
python -m pytest holo_index/tests/test_reddog_extension_bundle_recall.py -q
```

## Fixtures

| File | Purpose |
| --- | --- |
| `fixtures.js` | Shared prompts and path lists (EXT-ACC-001, denied paths) |
| `verify_extension_contract.js` | Single contract runner; ADDENDUM E ~line 518+, ADDENDUM F gate probe ~line 595+ |

## TEST_REGISTRY

See `TestModLog.md` for TCI-001 through TCI-010, THG-001 through THG-006, UNI-001 through UNI-007, and WFTD-001 through WFTD-013 (free-form work-focus target derivation).

## Expected behavior

- `inferRecallTargetPaths(EXT_ACC_001_PROMPT)` includes `extension.js`.
- `resolveAutoContextMode(EXT_ACC_001_PROMPT tier HIGH)` unchanged; REGULAR -> `wsp_holo`.
- ADDENDUM F: sanitized snippets pass Python `evaluate_redaction_gate` (TCI-009/TCI-010).
- THG-001..006: REGULAR HoloIndex grounding (see TestModLog registry).
- Path safety rejects absolute, traversal, `.env`, `.git`, `node_modules`, `.vsix`.

## Integration requirements

- VSCode API mocked via `node_modules/vscode` stub in contract runner.
- Workspace root = repo root (three levels above `tests/`).
