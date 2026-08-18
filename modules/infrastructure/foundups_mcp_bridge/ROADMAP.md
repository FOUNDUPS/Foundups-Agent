# foundups_mcp_bridge Roadmap

## 2026-08-16: Explicit-Module Tier-0 Owner Projection

**Complete:** global owner flattening now reserves at most two existing exact
root README/INTERFACE hits for explicit uniquely evidenced module queries,
after generation-bound Holo retrieval and path projection. Low-K,
ambiguous-query, and adversarial lookup behavior is pinned by focused tests.

**Deferred:** post-commit exact-SHA maintenance/publication and live governed
owner acceptance. The resident owner is not restarted by this change.

## Current P0: HoloIndex / RedDog Operational Truth Boundary POC

**Priority:** 20 / P0 under WSP_15
**Phase:** Implementation present; focused validation/PR evidence pending
**Owner:** 0102 architect for 012

The Phase-1 target is one query/health-only HoloIndex owner, one trusted-host
maintenance handshake, process-private bearer handoff, exact clean-HEAD and generation
binding, semantic-only health, and complete canonical proof for all seven
baseline collections.

Acceptance will require the focused HoloIndex, owner lifecycle, HTTP, RedDog
boundary, startup-dispatch, and operational-consumer matrices plus static
contract checks. The persistent store is not current for the merge SHA until
the post-merge activation run completes.

## Post-Merge Activation

1. Use a clean main checkout at the merge SHA.
2. Run the trusted full-maintenance handshake against the canonical store.
3. Require seven complete canonical source-scope proofs at the exact SHA.
4. Start the private owner and require an authenticated semantic canary bound
   to the receipt generation.
5. Run one activation-style RedDog query and retain only secret-free receipt
   identifiers and result metadata.
6. Stop the owned process and confirm no maintenance lease or invalidation is
   left behind.

## Next Operational Slices

- Bind the resident RedDog/WRE control loop to the owner handoff without
  granting query workers index-write authority.
- Add durable maintenance-request receipts and retry/backoff policy owned by
  WRE, not by the query process.
- Add post-merge scheduled refresh and generation-health monitoring.
- Migrate or explicitly retire the legacy `src/holo_tools.py` direct-store
  HoloIndex consumer.
- Replace the cooperative-writer/exclusive-window POC assumption with an
  immutable exact-commit source snapshot, and add orphan-process reclamation
  for abrupt host death.
- Add semantic recall/capacity gates for representative FoundUp creation,
  repair, and enhancement tasks.
- Prove governed build-to-test-to-draft-PR recursion in isolated worktrees
  before considering unattended merge authority.

## WSP_62 Remediation Register

Phase-1 validation will check the new owner, gate, HTTP, supervisor, bootstrap,
and handshake files against the infrastructure module limit and record any
architect-approved exemptions. The following pre-existing or
test/documentation debt remains explicit:

- Split src/holo_tools.py into request normalization, semantic adapter, and
  response-envelope components.
- Split src/signal_normalization.py by risk, failure, focus, and prompt-packet
  responsibilities.
- Split tests/test_mcp_bridge.py by public tool family.
- Keep owner service and bootstrap test modules divided by service, transport,
  lifecycle, and private-handoff behavior as their contracts grow.
- Archive or split INTERFACE.md before it reaches the 1,000-line Markdown
  threshold.

No global WSP_62 compliance claim is made until those historical items are
completed and the repository-wide size gate is green.
