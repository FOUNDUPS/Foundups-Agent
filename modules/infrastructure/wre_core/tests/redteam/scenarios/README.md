# Red-Team Adversarial Scenarios

Phase 2 placeholder. The harness skeleton currently loads scenarios from
an in-memory catalog in `conftest.py::threat_scenario`.

Phase 3+ slices populate this directory with YAML/JSON adversarial packs
per family:

```
scenarios/
├── scope_lock/
│   ├── SL-001.yaml
│   ├── SL-002.yaml
│   └── ...
├── credential_exfiltration/
│   ├── CE-001.yaml
│   └── ...
└── holoindex_poisoning/
    ├── HP-001.yaml
    └── ...
```

YAML files must NEVER contain real secrets — only `SYNTHETIC_*` patterns
that pass the harness invariant 1 check at fixture load time
(spec §3.3 / `conftest.py::_validate_synthetic_only`).

Spec reference:
[`docs/audits/security/FOUNDUPS_AGENT_REDTEAM_REGRESSION_SPEC_PHASE1.md`](../../../../../../docs/audits/security/FOUNDUPS_AGENT_REDTEAM_REGRESSION_SPEC_PHASE1.md) §3.1.

---

## Deferred Scenarios

The following scenarios are documented but do NOT have runtime tests in this
phase. Per spec §6.3, we do not use `@pytest.mark.skip` in `redteam/` — if a
scenario cannot be tested yet, it is simply not implemented.

### CE-005: Indirect Log Leak

**Status**: DEFERRED pending Layer 1 1Password integration

**Description**: Detects when agent code inadvertently logs secret values via
patterns like `logger.info(f"Using API key: {API_KEY}")`.

**Blocking dependency**: Requires static-analysis surface from the credential-
access layer to scan agent-generated code for indirect exfiltration vectors.

**Spec reference**: §4.2 — "HOLD pending Layer 1 1Password integration"

**Audit doc**: [`FOUNDUPS_AGENT_REDTEAM_FAMILY_B_CREDENTIAL_EXFIL_PHASE1.md`](../../../../../../docs/audits/security/FOUNDUPS_AGENT_REDTEAM_FAMILY_B_CREDENTIAL_EXFIL_PHASE1.md)
