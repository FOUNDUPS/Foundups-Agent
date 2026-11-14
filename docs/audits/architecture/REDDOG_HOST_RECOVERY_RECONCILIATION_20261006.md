# RedDog public host recovery — current-main reconciliation

Audited 2026-10-06; base `2837b0db389c567de9a5402e22fa711affcf176d`.
Scope: source repair under explicit 012 instruction; no runtime activation.
Execution plane: local isolated maintenance, WRE runtime dispatch not applicable.
WSP15 allocation: C3/I4/D4/impact3 = 14/P1. Need: restore stranded crash
accounting before public-host integration. Cost: bounded existing source/test
port, registry/manifest regeneration, independent review and hosted CI. Deferral
keeps the next host slice blocked. No new host/database/scheduler is warranted.

## Retrieved evidence and classification

- Governing WSP00/5/6/7/10/15/22/34/50/62/97, current contribution guidance,
  public admission contract, module docs and public TestModLog/README/fixtures
  were read before mutation. WSP97 section1.2A and WSP10 require terminal closure.
- #1680 remains a draft at `a60ea1e655f5247d871b0e958e7c5387ba40df7e`, 18 commits
  ahead and397 behind the observed main, with merge conflicts. Classification:
  `PRESERVED_NEEDS_REBASE`; rebuild its unique bounded delta, never merge it blind.
- On that head CodeQL passed, but CI34657437703 and admission34657437733 ended
  `action_required` with zero jobs. The previous admission run34657231522 passed;
  CI34657231431 failed `test_backend_compatibility_contract.js`. The successful
  repair run34657228351 passed8 manifest tests and pushed the final bot commit;
  that helper success is not final-head CI success.
- Temporary registry workflow was removed by766a8982; temporary backend workflow
  was removed bya60ea1e6. Neither survives in the final branch or current main.
- #1641 remains an open stale predecessor; #1640 is already closed. #1648 remains
  a separate draft website/OpenRouter/D1 lane. Reconcile parity rather than
  assuming its second session store is canonical. No website work is merged here.
- The two owning source files and pre-existing public tests match #1680's base
  exactly. Current main lacks `host_owner`, `busy_owner` and host leases.
  The implementation has not landed elsewhere in those authoritative owners.

## Local ownership and retrieval quality

Before isolation, O:/Foundups-Agent had161 registered worktrees; none was attached
to #1680/#1641's branch or head. Their remote tracking refs still existed. The
shared checkout had29 tracked modifications and11 untracked entries on
`feat/yumori-economic-impact-model`; all were preserved. This is evidence about
that Git common directory, not a claim about every repository on the machine.

Owned replacement: `fix/reddog-host-recovery-20261006` at
`E:/Agents/worktrees/reddog-host-recovery-20261006`. WSP00 bootstrap/tracker passed
there, using untracked state. The canonical owner query for "RedDog public host
lease recovery PublicSessionGate orphan busy_owner tests" returned
`HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`, freshnessUNKNOWN, gaptrue. Authority
head was a3def2a83; shared checkout was0c81418fe. No reindex or Holo mutation
was performed. Direct pinned Git evidence replaces stale search claims for this
bounded source audit; live owner freshness remains a separately unresolved gate.

Retrieval quality: initial broad search was noisy, then restricted to exact
owners/PR files; the local project reference was stale, so GitHub/pinned main
was used. The public test inventory omitted the existing Lick test, now repaired.
No duplicate recovery implementation was found. Autonomous native admission
was not available as verified evidence, so the authorized maintenance lane owns
this repair and does not claim a native RSI result.

## Smallest valid change and assumption audit

Port only the two owning sources and three tests from #1680; regenerate registry
and backend pins from current source. Preserve the existing Lick and quota
contracts. Reuse existing admission docs, work order, navigation and module log.
No temporary writer workflow, stale digest, threshold relaxation or public mount.

Alternative stale merge/rebase would mix397 later commits and generated state;
a fresh bounded port is directly reviewable because the owning source baseline
has not changed. Three new negative cases fail against the old port and now pass:
unconfigured recovery, legacy completion of owned work, missing lease as proof.
Exact expiry and repeated-recovery controls also pass.

High-impact failure controls: one-use hashed owners retain tombstones; renewal
requires a live lease; every configured public operation is lease-gated; completion
matches owner and reservation; recovery requires a live configured replacement
and known expired prior lease; legacy/missing-owner records remain closed.
Nonce/revision, expiry, budgets and Lick state survive recovery, with no replay
or refund. SQLite migration is additive and tested with the real DB wrapper.

Lease expiry does not prove provider/process death. The future trusted resident
supervisor must fence old work before recovery; current source supplies no such
adapter and does not activate the public router. This precondition prevents the
source test result from being misrepresented as a live concurrency guarantee.
Decision: proceed with bounded source repair; keep public activation gated.

## Verification and closure contract

Local pinned-dependency boundary:210passed, zero skips,95% combined branch-aware
coverage, with the unchanged90% floor and WSP62 bounds. Two inherited asyncio
configuration warnings reflect intentionally disabled plugin autoload; these
tests use asyncio.run. Registry/manifest, fast-tier and exact-head hosted results
belong in the replacement PR after execution. Independent review is separate.

Executed local follow-up: exact main baseline189passed; manifest integrity8/8;
all15 fast-tier groups; registry1691/270 current. FMAS exact-base diagnostic:
zero errors,129 pre-existing warnings. The initial audit caught growth of the
already oversized module log; compact reflow preserves its prior handoff facts
and keeps the total at the base line count. No exemption or ceiling changed.

Independent source review found no blocker in the bounded unmounted slice;
62 host/HTTP/Lick cases passed. Deployment must serialize first migration,
supply unique process owners and a trusted clock, and fence provider work.

The current GitHub ruleset requires a PR but zero approvals and no status checks;
that enforcement gap does not waive WSP review/validation. Do not confuse a
green CodeQL-only rollup with full CI. Do not weaken workflows to obtain green.

Terminal sequence: reviewed final head -> green current CI/admission/security ->
authorized squash -> read back affected main tree -> classify/close superseded
PRs -> preserve recovery evidence -> remove only clean disposable owned lanes.
If any required gate cannot be proven, record `BLOCKED_REQUIRED_GATE` with exact
branch/head/path. An open PR alone is not completion. No deployment is requested.

Recovery evidence is retained outside the repo at
`O:/Foundups-Agent-audits/reddog-host-recovery-20261006/`; rollback of a shared
merge must use a reviewed revert, not a reset of another worker's checkout.
