# Token Efficiency Module

**Status**: P1 (Bypass Classifier) ACTIVE
**Contract**: `docs/contracts/REDDOG_WSP99_RTK_TOKEN_EFFICIENCY_CONTRACT_PHASE1.md`
**WSP**: WSP_97, WSP_99

## Purpose

Provides token efficiency services for the RedDog/WRE stack:
- Bypass classification (which outputs must remain raw)
- M2M fidelity validation (round-trip preservation)
- Token savings telemetry (measurement, not claims)
- RTK integration seam (when ready)

## Current State (P1)

**Bypass Classifier** - Classifies command outputs to determine compression safety.

Output format: WSP-99 M2M.

### Bypass Classes

| Class | Description | Priority |
|-------|-------------|----------|
| BYPASS_SECURITY | CVE, vulnerability, security scans | 1 |
| BYPASS_AUTH | Tokens, keys, passwords, credentials | 2 |
| BYPASS_SIGNING | Signatures, PEM keys, fingerprints | 3 |
| BYPASS_PERMISSION | ALLOW/DENY/GRANT/REVOKE, scope | 4 |
| BYPASS_RECEIPT | Receipts, work orders, settlements | 5 |
| BYPASS_PROVENANCE | Git provenance, attestation, witness | 6 |
| ALLOW_COMPRESSION | Safe to compress | - |
| NEEDS_HUMAN_REVIEW | Unknown or ambiguous | - |

### Usage

```python
from modules.infrastructure.token_efficiency.src import (
    BypassClassifier,
    BypassDecision,
    get_bypass_classifier,
)

classifier = get_bypass_classifier()

# Classify command output
decision = classifier.classify(
    command="npm audit",
    output="Found CVE-2024-12345 in dependency"
)

# Check result
if decision.bypassed:
    print(f"Bypass: {decision.classification.value}")
    print(f"Reason: {decision.bypass_reason}")
else:
    print("Safe to compress")

# M2M output
print(decision.to_m2m_compact())
# L:BYPASS S:BYPASS_SECURITY M:classify T:abc123 R:[97,99] I:{bypassed:true,reason:pattern_match:BYPASS_SECURITY} O:[BYPASS_SECURITY]
```

## Fail-Closed Behavior

The classifier always fails closed:
- Unknown command -> NEEDS_HUMAN_REVIEW (bypassed)
- Classification error -> BYPASS (never silent compress)
- Multiple matches -> Highest priority class wins

## Implementation Sequence

| Phase | Slice | Status |
|-------|-------|--------|
| P1 | BYPASS_CLASSIFIER_SECURITY_GATE_PHASE1 | ACTIVE |
| P2 | WSP99_COMPILER_FIDELITY_GATE_PHASE1 | Planned |
| P3 | TOKEN_EFFICIENCY_TELEMETRY_SERVICE_PHASE1 | Planned |
| P4 | REDDOG_COMPUTE_GOVERNOR_PHASE1 | Planned |
| P5 | RTK_EVALUATION_DRY_RUN_PHASE1 | Planned |
| P6 | RTK_OPENCLAW_HERMES_ADAPTER_DRYRUN_PHASE1 | Planned |

## Files

```
modules/infrastructure/token_efficiency/
  src/
    __init__.py
    bypass_classifier.py      # P1: Bypass classification
  tests/
    test_bypass_classifier.py # Unit + adversarial tests
  config/
    bypass_patterns.yaml      # Pattern definitions
  README.md                   # This file
  INTERFACE.md                # Public API
```

## No Runtime RTK Yet

This module does NOT include RTK integration. RTK is planned for P5/P6 after:
- Bypass classifier proven (P1)
- M2M fidelity proven (P2)
- Telemetry operational (P3)
- Compute governor wired (P4)
