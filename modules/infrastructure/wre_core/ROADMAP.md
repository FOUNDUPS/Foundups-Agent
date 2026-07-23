# WRE Core Roadmap

## FoundUp job router and consumer WSP62 decomposition

The create-route prerequisite now isolates its routing decision in
`src/foundup_job_route_decision.py`; every function in that module and the
public `route_foundup_job` entrypoint is at or below 75 lines.

Remaining inherited WSP 62 debt is recorded with exact, non-ratcheting
ceilings in `wsp_62_exemptions.yaml`:

- Split envelope, evidence-reference, live-mode, and compute-budget validation
  out of `src/foundup_job_router.py`.
- Split Hermes dispatch, dry-run context attachment, and queue-retention
  orchestration out of `src/foundup_job_consumer.py`.
- Remove each function exemption when its extracted replacement is at or below
  75 lines, then remove the file exemption when the host is at or below the
  canonical file threshold.

Target: complete the decomposition before the temporary exemptions expire on
2026-09-30, without widening any recorded ceiling.

## FoundUp model-capability projection follow-up

Phase 1 projects existing route and runtime-binding authority into
`validate_foundup` only. Build and extract profiles intentionally keep all
capability requirements unspecified, and no consumer selection or binding
path has been added.

Before expanding consumption beyond validation:

- designate a production authority for modality, tool, structured-output,
  reasoning, selection-mode, and panel-limit requirements;
- define the selection-receipt handoff without letting a projection select,
  bind, call a provider, or mutate catalog/runtime state;
- add action-specific admission tests and preserve exact receipt lineage;
- keep `model_preference` limited to cost-class intent.

The injected runtime-binding resolver remains a trust anchor. A production
adapter must read the persisted result of the existing outside-repository
confined artifact-supply workflow. Detecting a malicious resolver that returns
a different self-consistent receipt requires a separately authorized
provenance/signature contract and is outside Phase 1.

## WRE documentation WSP62 decomposition

`INTERFACE.md`, `ModLog.md`, and `tests/TestModLog.md` contain inherited
chronological/API history above the canonical Markdown threshold. They are
governed by exact temporary no-growth ceilings in `wsp_62_exemptions.yaml`.
Before 2026-09-30, archive superseded history through an approved
documentation-retention workflow, preserve current interfaces and audit
lineage, and remove each exemption once the canonical threshold is met.
