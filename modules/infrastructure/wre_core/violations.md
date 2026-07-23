# WSP Violations Log - wre_core

## 2026-07-23: inherited WSP 62 decomposition debt

**Status:** ACTIVE TEMPORARY EXEMPTIONS

**Owner:** WRE Core Maintainers

**Remediation:** [FoundUp job router and consumer WSP62 decomposition](ROADMAP.md#foundup-job-router-and-consumer-wsp62-decomposition)

The create-route decision was extracted without changing route behavior, but
the two legacy host files still exceed canonical WSP 62 limits. Their
exemptions are exact no-growth ceilings, not test exemptions:

| File | Exact file ceiling | Exact inherited function ceilings |
|---|---:|---|
| `src/foundup_job_router.py` | 1193 | `validate_foundup_job_envelope`: 212; `_validate_live_mode_gates`: 88; `_validate_evidence_refs`: 113; `_validate_compute_budget`: 163 |
| `src/foundup_job_consumer.py` | 1110 | `_dispatch_to_hermes`: 111; `_attach_context_bundle_dry_run`: 160; `drain_openclaw_queue_with_retention`: 94 |

Every newly extracted or touched create-route function is at or below 75
lines. The temporary exemptions expire on 2026-09-30 and may only shrink.
