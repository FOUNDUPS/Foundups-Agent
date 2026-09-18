# OpenRouter credential consumers

Reviewed: 2026-09-09. Scope: tracked source in `FOUNDUPS/Foundups-Agent`.
This is a source and mocked-transport audit, not confirmation of running hosts.

## One credential name, separate runtime owners

Every active credential reader uses `OPENROUTER_API_KEY`. Supply it through the
authorized runtime secret configuration; never copy its value into source,
browser code, prompts, diagnostics, or this document. A repository checkout does
not transport an ignored `.env`, and editing an environment file does not change
the environment of an already-running process. None of these consumers should
search arbitrary working directories for credential files.

| Consumer | Credential source and refresh action | Authorization retained |
| --- | --- | --- |
| AI Gateway (`modules/ai_intelligence/ai_gateway/src/ai_gateway.py`) | Process environment, captured when `AIGateway` is constructed. Restart the owner with its updated secret configuration and reconstruct gateway instances. | Exact configured OpenRouter route; excluded from ordinary automatic fallback. |
| Cursor advisory bridge (`scripts/advisory_model_once.py`) | Process environment at each one-shot invocation. Restart the parent editor with the updated environment before spawning new bridge processes. | Redaction and verified model runtime binding. |
| Extension environment projection (`extensions/reddog/start_operations_environment.js`) | Inherits the key only into the `advisory_provider` profile. Relaunch the editor to update inherited environment. | Generic, resident, Git and read-only profiles must not gain the provider key. |
| FoundUps Fusion artifact runner (`reddog_foundups_fusion_artifact_provider.py` in the bridge `src/`) | Reads process environment per operation; restart its owning service with updated configuration. Uses the advisory transport. | Explicit mode, redaction and consumed artifact/model authority. |
| Read-only audit runner (`reddog_readonly_0102_audit_worker_runtime.py` in the bridge `src/`) | Reads process environment per operation; restart its owning service. Uses the advisory transport. | Explicit mode, model binding and redaction. |
| Architect runner (`reddog_backend_architect_determination_runtime.py` in the bridge `src/`) | Reads process environment per operation; restart its owning service. Uses the advisory transport. | Explicit mode, model binding, redaction and provider evidence. |
| Optional Fusion alias (`modules/communication/moltbot_bridge/src/fusion_alias_live.py`) | Reads process environment per invocation; update the owning process environment. | Disabled by default; typed 012 authorization, redaction and bounded budget still required. |
| Resident live canary (`reddog_resident_live_canary.py` in the bridge `src/`) | Checks presence in supplied environment only; update the actual service environment before a canary. | Presence is not provider access, consent or successful execution evidence. |
| Public website Worker (`modules/foundups/esingularity/frontend/lib/reddog-openrouter.ts`) | Sites server environment binding; apply updated secret configuration by deploying the reviewed saved Site. | Separate explicit `OPENROUTER_MODEL`, public admission, D1 budgets, ingress verification and enable gate. |

Both Foundups browser surfaces (landing/member concierge) and the eSingularity
chat call that same public Worker. They do not receive the provider key or need
their own copies of it. Their deployed source still must be verified separately.

The website model setting does not override private workers' signed model
bindings or AI Gateway task policy. Website usage limits remain specific to the
shared public service; they are not a repository-wide provider-spend cap.

## Deliberately excluded from credential propagation

- OpenRouter catalog/model freshness discovery uses the public catalog endpoint
  without a key. Its lack of a key is intentional.
- `modules/infrastructure/openrouter_client` remains dormant/contract-pending.
  Do not activate it or populate its parked configuration as a rotation step.
- The mock Fusion adapter does not read credentials or make live requests.
- The Sites sign-in bypass token is a different credential. Its authorized
  rotation completed; no named runtime consumer of that token was found in the
  tracked code search. That operation did not rotate the OpenRouter API key.

## Containment enforced at the shared transports

The advisory bridge, Fusion alias, AI Gateway OpenRouter route and public Worker
reject redirects. Advisory HTTP diagnostics retain status and bounded retry
metadata, without reading upstream error bodies or copying upstream reasons.
AI Gateway hides provider credentials from its generated representation and
returns content-free OpenRouter request exceptions, including timeouts. Existing
private worker gates and the dormant-module boundary are unchanged.

The focused offline security suite checks redirect handling with a synthetic
in-memory HTTPS handler, unread error bodies, safe exception rendering, provider
configuration representation and retained alias authorization. Existing advisory,
Fusion, model-budget and configured-runner tests check compatibility. No real
credential or live provider request is needed for these tests.

## Deployment evidence still required

The accessible checkout had no populated OpenRouter credential; its frontend
environment fields were empty. Hosted Sites environment revision 0 had no
entries. 012 identified a populated `.env` in another codebase location, which
has not yet been made accessible. Do not infer that the credential is absent on
that original machine, or claim that any remote process has been restarted.

After the secure credential source is resolved, update each actually deployed
owner above through its authorized secret configuration. Verify presence without
values, perform only the approved bounded call, and record success/failure per
owner. For the websites, retain the D1/ingress and Firebase publishing gates in
[the public runtime guide](../../../modules/foundups/esingularity/docs/REDDOG_PUBLIC_RUNTIME.md).
Do not revoke a separate OpenRouter credential as an incidental code edit.

WSP references: 15 (reuse existing shared transports), 50/97 (source versus live
evidence), 71 (secret containment), 73/106 (public/private authority separation).
