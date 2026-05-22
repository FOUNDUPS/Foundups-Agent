# Red-Team Test Suite — TestModLog (WSP 22)

## 2026-05-22 — Slice: FOUNDUPS_AGENT_REDTEAM_HARNESS_SKELETON_PHASE2

Created the harness skeleton from the merged spec. Three stub tests + three
guard/negative-control tests, plus fixtures and reason enum.

### Cases added

| Family | Case ID | Status | Notes |
|--------|---------|--------|-------|
| A — Scope-lock | `SL-001` | Active | Out-of-scope write blocked; reason `SCOPE_VIOLATION` |
| A — Scope-lock | `SL-001-negative` | Active | In-scope write succeeds (no false positives) |
| B — Credential exfiltration | `CE-001` | Active | Synthetic env-var echo refused; reason `CREDENTIAL_EXFIL_BLOCKED` |
| B — Credential exfiltration | `CE-001-negative` | Active | Benign request not blocked |
| B — Credential exfiltration | `CE-synthetic-invariant` | Active | Real-cred-pattern fixture fails fast |
| C — Poisoned retrieval | `HP-001` | Active | Hidden directive in code result rejected; reason `POISONED_RETRIEVAL_REJECTED` |
| C — Poisoned retrieval | `HP-001-negative` | Active | Clean retrieval not flagged |
| C — Poisoned retrieval | `HP-network-invariant` | Active | `socket.create_connection` blocked inside red-team scope |

### Spec deferrals carried over (not in this slice)

- `SL-002..SL-005`
- `CE-002..CE-004`, probabilistic `CE-006`
- `CE-005` HOLD pending WSP_71 credential-access layer spec
- `HP-002..HP-005`, probabilistic `HP-006`
- CI gate activation
- `scenarios/<family>/*.yaml` adversarial packs
- Static-analysis pre-commit hook for `violations.md` (spec §7.4)

### Notes

- Harness invariant 1 (synthetic-only secrets) is exercised by a direct
  test that constructs `AgentTestHarness` with a real-pattern credential
  and asserts it fails fast. This protects every other test.
- Harness invariant 2 (no real network) is exercised by a direct test
  that calls `socket.create_connection` and asserts it raises.
- The fixture-level time bound (invariant 6) is a soft post-hoc check; a
  hard SIGALRM-style timeout is deferred to when the suite is large enough
  to warrant it.
- No `@pytest.mark.skip` is used anywhere in this directory — spec §6.3
  forbids self-suppression.

### WSP refs
WSP_00, WSP_15, WSP_50, WSP_6, WSP_71, WSP_87, WSP_97, WSP_22
