# AI Gateway TestModLog

## 2026-07-24 - Scheduled provider discovery replay guard

Scope: offline-only adversarial verification of scheduled replay admission
around the unchanged direct OpenRouter discovery boundary.

- Concurrent same-loop callers and two subprocesses permit one transport call.
- `ARMED`, indeterminate, malformed, deep-nested, capacity-exhausted, linked,
  missing-candidate, and candidate-only states fail closed.
- Pre-ledger exact terminal evidence can migrate; exact blocked evidence cannot
  retry. Every missing ledger ID must prove fixed evidence strictly predates the
  new scheduled window, while guard-owned blocked entries remain retryable.
- Ledger `updated_at_ms` is enforced as a high-water mark so expiry pruning
  followed by wall-clock rollback cannot reopen transport admission.
- Event-driven cancellation cases prove that a cancelled active caller and a
  cancelled lock waiter leave their worker threads governed by the same outer
  lock, complete without deadlock, and never duplicate transport.
- Terminal ledger-write failure preserves the exact prior `ARMED` bytes and
  recovers only from the exact same-invocation terminal attempt.
- A valid candidate artifact larger than 1 MiB replays under the conservative
  bound derived from the direct 8 MiB response limit.
- Protected AST/file/function gates enforce no scheduler, startup, selection,
  promotion, registry, runtime-binding, or manual-surface authority expansion.

Focused scheduled/replay/protected result: `44 passed, 1 skipped` (unavailable
unprivileged Windows symlink creation only). Full ai_gateway: `378 passed, 2
skipped`. Idle automation: `126 passed`. Runtime artifact safety: `11 passed, 1
skipped`. Ruff, compileall, and diff-check passed.

## 2026-07-24 - Provider discovery defensive reliability hotfix

Scope: offline-only regressions for redirect-history receipt coherence,
retained-handle publication, rollback, and pathname integrity.

- `test_redirected_200_emits_truthful_terminal_receipt_and_preserves_lkg`
  requires a canonical `FAILED/redirect_history_rejected` receipt, exact final
  HTTP status, rehydration, and unchanged last-known-good candidate.
- `test_precommit_path_attack_never_publishes_substituted_bytes` covers
  pathname replacement, hard-link creation, and file-symlink substitution.
  Unsupported unprivileged Windows symlink creation is reported as one
  platform skip; ambiguous foreign substitutes are preserved, never unlinked.
- Post-validation and Windows final-check substitution cases prove that no
  substituted bytes become the candidate; Windows publishes the exact verified
  handle object. Wrong-publication and held-target failures restore exact prior
  bytes/mode or absence and clean only identity-owned temporary files.
- Receipt-unit cases require redirect-history evidence with a non-3xx final
  status and keep raw 3xx evidence bound to `redirect_rejected`.
- WSP 62 AST enforcement remains green for every touched production function.

Hotfix focused gate (the five provider/catalog files): `98 passed, 1 skipped`.
Full `modules/ai_intelligence/ai_gateway/tests`: `339 passed, 1 skipped`.

## 2026-07-23 - Direct provider catalog durability and WSP62 repair

Scope: offline-only verification for the bounded OpenRouter catalog discovery
slice. No test invokes a live provider, scheduler, runtime binding, or network
transport.

### Focused test files

| Test file | Cases | Scope |
|---|---:|---|
| `test_model_provider_catalog_snapshot.py` | 40 | Strict invocation, receipt, candidate, sanitization, freshness, and fail-closed evidence contracts |
| `test_model_openrouter_direct_discovery.py` | 27 | Manual/scheduled admission, bounded transport outcomes, durable receipt transitions, and candidate ordering |
| `test_model_provider_catalog_artifact_store.py` | 5 | Partial write, fsync, replace, cleanup, exact UTF-8, and permission-preserving atomic replacement |
| `test_model_provider_catalog_protected_surfaces.py` | 5 | Authority isolation, file ceilings, and AST-based 50-line production function ceiling |

Focused result: `77 passed`.

Supporting compatibility coverage:

- `test_model_intelligence_catalog.py`: `8 passed`, including OpenRouter
  normalization behavior preserved after cohesive single-record extraction.
- Combined provider-catalog and catalog-normalization focus: `85 passed`.
- Full `modules/ai_intelligence/ai_gateway/tests`: `326 passed`.

The counts above include the WSP62 AST regression added in this repair. The
artifact-store file is also run independently as the five-case atomic failure
matrix.
