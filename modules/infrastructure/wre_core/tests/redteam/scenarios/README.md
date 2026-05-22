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
