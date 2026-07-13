# Token Efficiency Module

**Status**: P6 (OpenClaw/Hermes RTK Adapter Dry-Run) ACTIVE
**Contract**: `docs/contracts/REDDOG_WSP99_RTK_TOKEN_EFFICIENCY_CONTRACT_PHASE1.md`
**WSP**: WSP_97, WSP_99

## Purpose

Provides token efficiency services for the RedDog/WRE stack:
- Bypass classification (which outputs must remain raw)
- M2M fidelity validation (round-trip preservation)
- Token savings telemetry (measurement, not claims)
- Compute governor routing decisions before tool execution
- RTK evaluation dry-runs over caller-supplied candidate output
- OpenClaw/Hermes RTK seam dry-runs that never rewrite output

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
| P1 | BYPASS_CLASSIFIER_SECURITY_GATE_PHASE1 | LANDED (#940) |
| P2 | WSP99_COMPILER_FIDELITY_GATE_PHASE1 | LANDED (#943) |
| P3 | TOKEN_EFFICIENCY_TELEMETRY_SERVICE_PHASE1 | LANDED (#944) |
| P4 | REDDOG_COMPUTE_GOVERNOR_PHASE1 | LANDED (#946) |
| P5 | RTK_EVALUATION_DRY_RUN_PHASE1 | LANDED (#1006) |
| P6 | RTK_OPENCLAW_HERMES_ADAPTER_DRYRUN_PHASE1 | ACTIVE |

## Files

```
modules/infrastructure/token_efficiency/
  src/
    __init__.py
    bypass_classifier.py      # P1: Bypass classification
    m2m_fidelity_gate.py      # P2: Round-trip validation
    telemetry_service.py      # P3: Token savings measurement
    compute_governor.py       # P4: Routing decisions (not compression authority)
    rtk_evaluation_dryrun.py  # P5: Candidate evaluation, no RTK invocation
    rtk_openclaw_hermes_adapter_dryrun.py # P6: Seam planner, no rewrite
  tests/
    test_bypass_classifier.py # Unit + adversarial tests
    test_m2m_fidelity.py      # Fidelity + CTX.HOLO tests
    test_m2m_compiler_compat.py # Compiler backward-compat
    test_telemetry_service.py # Telemetry service tests
    test_compute_governor.py  # Routing + invariant tests
    test_rtk_evaluation_dryrun.py # Dry-run candidate evaluation tests
    test_rtk_openclaw_hermes_adapter_dryrun.py # Seam dry-run tests
  config/
    bypass_patterns.yaml      # Pattern definitions
  README.md                   # This file
  INTERFACE.md                # Public API
```

## No Runtime RTK Yet

This module does NOT include runtime RTK integration. P6 only plans the
OpenClaw/Hermes command-output seam over caller-supplied raw output and a
caller-supplied candidate. It records hashes, dry-run receipts, and in-memory
telemetry IDs, but it does not invoke an RTK binary, execute commands, rewrite
OpenClaw/Hermes output, enqueue work, or mutate HoloIndex.

Live RTK integration remains blocked until a future slice proves:
- Bypass classifier proven (P1)
- M2M fidelity proven (P2)
- Telemetry operational (P3)
- Compute governor wired (P4)
- RTK evaluation dry-run accepted (P5)
- OpenClaw/Hermes seam dry-run accepted (P6)
