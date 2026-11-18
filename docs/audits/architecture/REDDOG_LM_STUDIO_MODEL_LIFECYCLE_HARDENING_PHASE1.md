# RedDog LM Studio Model Lifecycle Hardening Phase 1

**Date:** 2026-08-22 (JST)
**Owner:** 0102
**Authority:** 012 directed RedDog hardening, WSP_97 verification, and scalable modular operation.
**WSP basis:** WSP_00, WSP_15, WSP_50, WSP_62, WSP_73, WSP_97

## Problem

RedDog documents the Nemotron topology proposer as using an exact,
already-loaded LM Studio model without starting LM Studio. The current backend
checks OpenAI-compatible `GET /v1/models`. LM Studio may expose downloaded
models through that route when just-in-time loading is enabled, so model-key
presence is not proof that the model is resident. A proposal call can therefore
load a large model implicitly while its receipt claims an already-loaded route.

The native LM Studio inventory is the required truth source. `GET
/api/v1/models` distinguishes installed models from resident instances through
`loaded_instances`. Native `POST /api/v1/models/load` and
`POST /api/v1/models/unload` provide explicit instance lifecycle operations.

## Retrieval Evaluation

The mandatory governed HoloIndex query failed closed with
`HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH` (authority root
`80328ac3df40c22cd280efe45242e21d921a7c65`, workspace root
`27ccf9942df645072039f17ad199c89c16d91acc`). It was not retried, repaired, or
reindexed. Discovery used the exact committed tree at
`cff2694e566b3cc5bd2724cf9452def43ab65446`, module documentation, tests, and
official LM Studio documentation.

| Dimension | Evaluation |
|---|---|
| Noise | Low; exact resolver, backend, proposer, and runtime-lock owners were found. |
| Ordering | Direct committed-tree search located the existing owners before design. |
| Missing artifacts | Holo semantic evidence is unavailable until its separate authority-root transaction completes. |
| Staleness risk | Repository evidence is exact-base; official LM Studio REST documentation was checked on 2026-08-22. |
| Duplication | One backend/resolver stack and one reusable cross-process runtime lock already exist. |

## Assumptions

1. LM Studio is an externally owned local server. RedDog must never start,
   stop, download, or discover providers from this lifecycle adapter.
2. Exact native model keys and exact loaded instance IDs are the only accepted
   identity evidence.
3. A pre-existing instance is borrowed and must never be unloaded by RedDog.
4. A transaction-created instance is unloaded by the same transaction and its
   absence is verified before successful evidence is issued.
5. One bounded cross-process lock per physical loopback node/port governs all
   managed models. Loopback aliases share the same lock and an additive load is
   rejected while any model instance already occupies the node.
6. API authentication, when configured, must reach native and OpenAI-compatible
   requests without entering receipts, logs, errors, or repository files.
7. The ordinary `main.py` preflight remains probe-only. Only an explicit
   Nemotron proposal transaction may request a managed load.
8. Phone and PFMall clients remain thin authenticated conversation surfaces;
   local model lifecycle belongs to the resident OpenClaw/RedDog hub.

## Failure Modes

- `/v1/models` lists Nemotron while native `loaded_instances` is empty.
- The exact model is not installed, multiple exact resident instances make the
  lease ambiguous, or the server changes instance identity during the call.
- Authentication returns 401/403, a response exceeds its byte cap, a native
  response is malformed, or a redirect leaves the loopback boundary.
- A load times out or returns an instance that cannot be re-observed. The
  transaction must durably quarantine the intent, re-observe once, and never
  blindly retry or guess ownership.
- An interrupted load survives process death. Native inventory exposes no
  documented server boot/generation identity, so even a matching instance ID
  may have been reused after restart. Zero residency recovers automatically;
  any residency remains quarantined for explicit operator recovery.
- A requested context exceeds native `max_context_length`, another model is
  resident, or the node-wide lock cannot be acquired before its bounded wait.
- Cleanup attempts to unload a pre-existing instance, or unload confirmation
  does not match the exact transaction-owned instance.
- A proposer call lacks or structurally disagrees with its lifecycle receipt.
  Content hashes do not authenticate an adversary; the existing signed
  proposer-provenance layer supplies that trust boundary.
- Global preflight or availability checks wake `llmster` or load a model.

## Alternatives Considered

1. **Relabel documentation only.** Rejected; implicit JIT loading remains.
2. **Use native residency checks but require manual loading.** Useful truth fix,
   but it leaves the explicit Nemotron workflow operationally incomplete.
3. **Reuse `dependency_launcher.load_all_models()`.** Rejected; it performs
   fuzzy multi-model loading and is not an exact transaction owner.
4. **Use `lms` subprocess commands.** Rejected; CLI inspection can wake the
   daemon and would duplicate the native REST lifecycle. The CLI documents
   identifiers and TTL, but the native load request used here does not; this
   implementation therefore uses a durable recovery intent instead of sending
   undocumented REST fields.
5. **Add the LM Studio SDK.** Deferred; the native REST surface and stdlib HTTP
   client are sufficient for this layer and avoid another dependency.
6. **Add an exact managed model transaction adapter.** Selected as the smallest
   truthful layer: observe, reserve node capacity, journal intent,
   borrow-or-load, call, unload-owned-only, verify, and emit content-addressed
   evidence under one bounded cross-process lock.

## Decision

**PROCEED** with bounded sibling modules and no new router, daemon, queue, or
database: `lm_studio_native_transport.py` owns native transport/inventory,
`lm_studio_model_lifecycle.py` owns leases, `lm_studio_lifecycle_intent.py`
owns one outside-repository recovery intent per node/port, and
`runtime_operation_locking.py` owns the platform lock implementation.

The adapter will expose installed/resident truth, `BORROW_ONLY` and
`MANAGED_LOAD` modes, bounded authenticated native requests, exact instance
verification, and a deterministic content-addressed lifecycle receipt.
That receipt proves internal structural agreement only; authenticated authority
requires its existing externally signed proposer-provenance envelope.
`LMStudioBackend` will
initialize only from native residency evidence. The Nemotron shadow proposer
will use one managed transaction and bind the lifecycle receipt into its call
receipt. Custom/injected proposer backends must supply an independently
rehydratable lifecycle receipt; absence fails closed.

This phase deliberately permits one managed model transaction per node/port
and never evicts a pre-existing model. Horizontal scale is achieved by
independent resident hubs with independent capacity; campaign pooling is not
claimed by this phase. A phone or PFMall
surface sends intent/status/cancel events to the hub and never hosts Nemotron.

## Acceptance Gates

1. Installed-but-not-resident is not accepted by `LMStudioBackend.initialize()`.
2. Empty native inventory still proves server reachability without proving any
   model ready.
3. A borrowed exact instance is never loaded or unloaded.
4. A managed exact instance is loaded once, re-observed, called, unloaded once,
   and verified absent. Post-load inventory must contain exactly that one
   instance; a concurrent foreign load cleans up only the owned instance and
   fails the transaction.
5. Load timeout/cancellation is durably quarantined and followed by observation,
   never a blind second load or unproved unload; restart proceeds automatically
   only after native inventory proves zero residency.
6. Authentication is forwarded to both API surfaces but absent from evidence.
   Governed native requests ignore environment proxy variables; legacy
   OpenAI-compatible convenience calls are not lifecycle authority.
7. Non-loopback URLs, redirects, oversized/malformed bodies, ambiguity,
   occupied capacity, over-max context, use-time instance change, and structural
   lifecycle/call disagreement fail closed.
8. Resolver and `main.py` remain non-launching; no `lms` subprocess is added.
9. The canonical importlib-mode shared-utility/AI Gateway gate passes `121`
   tests with one platform-specific skip, using a unique outside-repository
   pytest base directory and no live network/model dependency. The inherited
   NAVIGATION collection/registry drift remains an explicit separate blocker,
   not a hidden exclusion or lifecycle claim.
10. New files and functions satisfy WSP_62 thresholds and module documentation
    states installed, resident, borrowed, and transaction-owned truth exactly.
11. API credentials are excluded from lease representation/equality, receipts,
    journal records, logs, and errors; authenticated probes preserve named auth
    failures.
