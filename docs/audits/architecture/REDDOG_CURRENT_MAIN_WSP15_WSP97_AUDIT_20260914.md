# RedDog current-main WSP 15 / WSP 97 audit — 2026-09-14

Status: point-in-time evidence and ranked work queue, not runtime authority.

## Audit boundary

- Repository: `FOUNDUPS/Foundups-Agent`
- Initial audit base: `bec40ffe52cd0076013a4bb9e5f7629b683741be`
- Reconciled current-main parent: `9b056d641442022022925bb2ad4b934f621298e3`
- Isolated branch: `audit/reddog-wsp15-wsp97-20260914`
- Owned paths: RedDog extension code/tests/module logs and this audit/navigation
  entry only.
- Protected sibling work: current RSI/WRE/Holo and YUMORI/eSingularity lanes.
- Excluded repository: `FOUNDUPS/autopost`, including
  `fix/mobile-youtube-oauth-gesture` at the operator-reported `aeab03c`. No
  AutoPost branch, worktree, deployment, OAuth state, or remote claim was
  changed by this audit.

The base was fresh `origin/main` when the task worktree was created. Remote main
then advanced by 18 sibling RSI/YUMORI commits. The task commit was rebased onto
the new main without taking sibling changes into its patch, and the RedDog
release closure was rerun against that reconciled parent. Remote main must still
be fetched again immediately before push/merge because concurrent owners remain
active.

## Canonical interpretation

The repository's WSP 15 scores four dimensions from one to five:
`Complexity + Importance + Deferability + Impact`. The total maps to P0
16–20, P1 13–15, P2 10–12, P3 7–9, and P4 4–6. The queue below uses that
formula without substituting a new framework.

WSP 97 requires retrieval and evidence before implementation, explicit unknowns
and assumptions, micro- and macro-analysis, dialectical and first-principles
checks, WSP 15 prioritization, reuse of existing owners/tests, the smallest
validated layer, and closure evidence. A passing focused test is not sufficient
when an exhaustive release contract disagrees.

The prototype Qwen roadmap-auditor skill supplied discovery criteria only. Its
own manifest says it still needs validation, so no sample result or generated
command was accepted as evidence.

## Retrieval result

The governed Holo query failed closed before returning admissible retrieval:

```text
authority_repo_head_sha: 5326080d583625aebbc230242117fb7fcf0044a6
workspace_repo_head_sha: 0c81418fe94a7786cfd55f01e138ddc5d510583d
error: HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH
freshness: UNKNOWN
index_gap_detected: true
ok: false
no_reindex: true
```

No Holo result was used and no query-side reindex or authority mutation was
attempted. Retrieval quality is therefore **unusable**, with high staleness risk
and all requested artifacts missing from that result. The fallback used the
canonical RedDog documentation map, module README/INTERFACE/ROADMAP/ModLogs,
root RSI roadmap and packet map, exact implementation/tests, scoped `rg`, Git
state, and live read-only PR metadata. Historical duplicates were treated as
evidence rather than current authority.

## Current RedDog truth

Completed and operational at this base:

- The VSIX source is version `0.4.141` and exposes one fast conversational and
  governed planning surface. It is not version 0.9.
- `package.json` already has operational `test`, `test:conversation`,
  `test:contract`, `test:package`, and `test:release` scripts. The old claim
  that it had no test scripts is obsolete.
- The fixed package boundary is 67 files and remains under its 1 MiB raw cap.
- Bounded model/retrieval requests, work-order construction/preview,
  policy/receipt checks, queue projections, architect-cycle primitives, and
  scoped one-use Memex disclosure exist.
- OpenClaw/Hermes, Nemotron, AI Gateway/AutoResearch, WRE and Memex have real
  components and bounded contracts; none of those documents alone proves a
  live end-to-end production path.

Missing or deliberately inactive:

- The VSIX cannot yet perform repository work. `extension.js` keeps
  `enableConcreteWriter` false and the live enqueue bridge supplies no writer.
  It has no extension-owned edit, shell, worktree, PR, merge, deployment, or
  promotion authority.
- There is no completed current-main canary from authenticated RedDog intent
  through a durable WRE job, a qualified OpenClaw/Hermes worker, independent
  verification, activation, and retained outcome.
- Durable ChatGPT-like conversation continuity and VSIX/pfMall/phone Memex
  adapters remain absent. Contact memory and the Memex projection emitter are
  specified rather than implemented; Mosh Pit inputs exist without the unified
  renderer.
- Nemotron is a routing proposer, not automatic authority. AI Gateway and
  AutoResearch still own evaluation/admission/promotion. The static model
  roster is an explicit disabled-by-default evaluation fallback.
- The existing backend closure is exactly at the 1,400-file hard ceiling and
  its 317,981-byte manifest is only 9,699 bytes below its cap.
- `extension.js` is 8,400 lines under a temporary 8,428-line WSP 62 exemption
  that expires 2026-09-30. `scripts/advisory_model_once.py` also exceeds its
  1,200-line target under a no-growth plan.
- No verified `0.4.141` VSIX existed at audit start. The last visible release
  artifact was `O:\\RedDog-Releases\\reddog-0.4.140.vsix`.

RedDog is the lightweight resident interaction/exchange surface backed by the
principal-scoped deep 0102 Digital Twin. It is not the 0102 identity itself.
OpenClaw is the admitted resident supervisor and Hermes a bounded worker, not a
place where an entire FoundUp or its production authority should implicitly
live.

## Ranked outstanding work

Scores are `C/I/D/Impact = total`.

| Priority | Score | Task and evidence | Current state / dependency | WSP 97 action and next executable step |
|---|---:|---|---|---|
| P0 | 20 (5/5/5/5) | Decompose `extensions/reddog/extension.js`; 8,400 lines versus temporary 8,428 cap, expiry 2026-09-30 | Executable and unblocked in RedDog after this release closure. | Extract exactly one existing ROADMAP seam per PR, preserve package membership/exports, rerun the exhaustive release gate, then repeat. |
| P0 | 19 (4/5/5/5) | Restore exact-current governed Holo retrieval; fail-closed receipt above and root R03 | Query is unusable for this source. Holo/RSI lane owns maintenance. | Requalify through the existing maintenance controller; never reindex inside a query or weaken current-source proof. |
| P0 | 19 (4/5/5/5) | Consolidate backend closure; compatibility manifest has 1,400/1,400 files and 317,981/327,680 bytes | Any new runtime dependency can breach the release boundary. | Profile reachability and duplicates, remove only proved dead/duplicated closure members, and retain exact hashing/fail-closed preflight. Do not raise caps first. |
| P0 | 19 (4/5/5/5) | Durable conversation/Memex adapters; RedDog README and documentation map | In-memory/scoped primitives exist; VSIX, pfMall and phone continuity are missing. | Bind one principal-scoped durable adapter to existing conversation/CAS contracts, then independently test replay, revocation, isolation and restart. |
| P0 | 19 (5/5/4/5) | R09 independent artifact verification | Depends on one admitted R06–R08 worker result; author evidence cannot certify its own candidate. | Reuse the existing autonomous slice verifier and bind exact base/candidate/runtime plus required test identifiers. |
| P0 | 18 (5/5/4/4) | OpenClaw/Hermes live qualification; RSI dispatch runbook | Installed/advisory surfaces are documented; local model/API admission and artifact-producing current-main canary are not proved. | Qualify pinned versions, runtime/API/provider/signing boundaries, then execute one admitted bounded leaf job. |
| P0 | 18 (4/5/4/5) | Nemotron/AutoResearch promotion binding; RedDog README/INTERFACE and AI Gateway | Proposal and evaluation machinery exists; authenticated production promotion remains blocked. | Keep Nemotron non-authoritative, measure proposals against held-out outcomes, and promote only through an independently owned gateway decision. |
| P0 | 18 (4/5/4/5) | R06 compile one planning packet into the signed work contract | Blocked on current retrieval and runtime/model binding; a planning packet is not execution authority. | Bind one documentation-artifact canary to exact SHA, scope, budget, expiry, provider, output and verifier using existing owners. |
| P0 | 17 (4/5/4/4) | R07 prove one actual OpenClaw/Hermes child lifecycle | Installed CLI/version evidence is not worker execution evidence; Hermes API and artifact-runtime admission remain unproved. | Reuse the existing adapters, qualify exact profile/auth/tools, and return one bounded artifact plus lifecycle receipt. Do not revive a legacy executor by name alone. |
| P0 | 17 (2/5/5/5) | Repair stale `0.4.141` exhaustive identity contract | **Completed in this sprint.** Focused identity passed while exhaustive core rejected old architect branding. | Rebound the three assertions, regenerated signed shard identity, strengthened the negative identity test, and ran the complete release gate. |
| P0 | 16 (3/4/5/4) | Finish WRE WSP 62 router/consumer decomposition before 2026-09-30 | Separate WRE-owned slice; not authority for this RedDog branch to absorb. | Reconcile the active WRE lane, preserve ceilings and tests, then take one non-overlapping extraction. |
| P0 | 16 (4/5/3/4) | R11-B accepted-memory transaction; root `ROADMAP.md` and RSI dispatch runbook | Pending/full-response recovery, readback, exposure guard and activation-ack recovery are merged. Cross-store atomicity, admitted runtime and retained benefit remain open in the active RSI lane. | Bind the accepted row and decision to one future SQLite transaction under current independent write authority. Do not create a second memory or response store. |
| P1 | 15 (3/4/4/4) | Reconcile eight open RedDog PRs and large local branch/worktree residue | Useful work is mixed with conflicts, stacked bases, failing CI and duplicate docs/skills. Squash merges make branch ancestry alone non-authoritative. | Review each patch against current main; merge only minimal current slices, close proved superseded PRs, and clean only owner-confirmed worktrees in a separate transaction. |
| P1 | 15 (3/5/3/4) | Reconcile RedDog identity/status documentation tables | Current README/INTERFACE contain historical status rows that disagree with later implementation sections. | Replace stale status claims with explicit implemented/connected/activated labels; do not rewrite historical receipts. |
| P1 | 15 (3/4/4/4) | Contact memory, unified Mosh Pit projection and Memex emitter | Architecture or partial inputs only; overlaps open PRs #1638, #1642, #1659, #1663 and #1689. | Consolidate contract ownership first, then implement behind the durable conversation identity boundary. |
| P1 | 14 (2/4/4/4) | Linked-worktree Windows RedDog test CLI | **Completed in this sprint.** The runner required a nonexistent worktree-local `.venv` and inherited C:-based temp. | Resolve the primary checkout via bounded Git metadata, validate its O:/E: venv, keep overrides authoritative, and use cleaned worktree-local O:/E: temp. |
| P1 | 14 (3/4/3/4) | Finish R02/R03 current-source and owner reconciliation; root roadmap and enforcement map | Partial and actively owned by the RSI lane. | Continue the existing packet/owner map and feature-branch retrieval matrix; do not duplicate it from RedDog. |
| P1 | 13 (3/4/3/3) | YUMORI/eSingularity mobile/deployment work | Explicitly protected concurrent lane; not a RedDog dependency for this sprint. | Keep its paths and deployment state isolated. Integrate a RedDog surface only through a later explicit adapter PR. |
| P2 | 11 (2/3/3/3) | YouTube/OAuth implementation-versus-roadmap reconciliation | Foundups-Agent YouTube auth docs retain older prototype/pending claims; AutoPost has a separate reported clean one-commit branch whose remote merge was not established here. | Verify current tests/interfaces and close only completed documentation items. Audit/merge the AutoPost branch in its own repository; do not absorb it here. |
| P2 | 11 (2/3/3/3) | AI Overseer monitoring documentation reconciliation | Current OpenClaw monitoring coexists with older proposed Gemma/Qwen/DAEmon wiring. | Audit callers and tests, then mark/archive stale designs. Do not build a duplicate monitor or emitter from old prose. |

## Open RedDog PR disposition

Live read-only metadata was inspected on 2026-09-14. It may change; re-query
immediately before any close or integration action.

| PR | Observed state | Evidence-based disposition |
|---|---|---|
| #1689 | Open; documentation continuity audit; conflicting; CI failure | Use as the newest documentation reconciliation candidate. Rebase and preserve only claims still true; do not merge while failing/conflicting. |
| #1680 | Open draft; current-main/host-lease reconciliation; conflicting; 18 commits | Audit as the likely successor to #1641. Extract a minimal current-main runtime slice after the active owner releases shared paths. |
| #1663 | Open; contact-action documentation; conflicting; CI failure | Consolidate with canonical Contact Memory ownership instead of adding another competing authority document. |
| #1659 | Open; contact index plus duplicated `.agents`/`.claude` skill copies; CI failure | Do not merge verbatim. Identify the canonical skill source/projection generator and land one source with generated mirrors only if required. |
| #1648 | Open stacked draft based on a Mosh branch; 58 files across RedDog, gateway, bridge, WSP, workflows and eSingularity | Do not merge as one PR. Decompose by owner; route public/eSingularity changes through that protected lane and separately audit credential/security boundaries. |
| #1642 | Open; documentation-only Mosh protocol; checks green | Useful design candidate. Reconcile against #1689 and current canonical docs, then land one non-duplicative documentation slice. |
| #1641 | Open draft; older host-lease work; conflicting | Treat as superseded by #1680 unless a patch-equivalence review finds unique current code; close only after that proof. |
| #1638 | Open; principal activity ledger; CI failure | Potentially useful Mosh/Memex input. Rebase, audit WSP 62/package/identity impact, and land as its own tested runtime slice rather than folding it into docs. |

The local `fix/reddog-release-mainline-candidate-gate` worktree is clean with a
gone upstream. `git cherry origin/main HEAD` returns `- 8d34d0db0`; its exact
patch is already integrated as `bd4ed9cb7` / PR #1527, and current main retains
the candidate/release-tier separation. Do not rebase, merge, resurrect or
duplicate it. Its worktree/branch removal is P3 destructive housekeeping and
must wait for a separate owner-verified cleanup transaction.

At audit time Git listed 155 worktrees, including 61 RedDog-named worktrees, and
220 RedDog-named local branches. Forty-seven RedDog worktrees were clean and 14
were dirty, including this task lane. `git branch --merged` is not a valid
cleanup oracle after squash merges. No branch or worktree was removed.

## First sprint closure

The selected sprint wins because it closes an authentic P0 release blocker and
the operator-reported P1 CLI defect without touching RSI, Holo, YUMORI,
eSingularity, AutoPost, provider, registry, or runtime-authority code.

The exhaustive contract was first reproduced failing on the superseded product
identity while the focused identity test passed. The repair binds the display
name and active documentation to the canonical fast-RedDog/deep-0102 boundary,
regenerates all authenticated shard constants, and expands the focused negative
set. This is evidence of incomplete prior WSP 97 closure, not enough evidence
to label a person or change as deliberate vibecoding.

The test CLI was first reproduced failing from this real linked worktree because
its local `.venv` did not exist. After resolving the trusted primary checkout,
the next authentic failure exposed C:-based ambient temp. The final runner uses
the primary O:/E: venv, an isolated worktree-local O:/E: temp tree, validated
explicit overrides, sealed Python controls, and cleanup after each invocation.
Independent hostile review then found that ambient Git controls could redirect
the first common-directory implementation. The repaired resolver now reuses the
identity-bound Git executable and closed environment, pins worktree/config
controls, and validates the current marker/common-directory topology before the
primary venv can be selected.

Final local evidence:

- WSP 00: PASS, coherence 0.748; independent RedDog auditor 0.789.
- Focused identity and shard integrity: PASS.
- Contract: 18 shards, 6,942 lines, 492 assertions,
  `sha256:e653fd5c3cbe0de8e6a235939d0531bb213748d6fa7c9a750f903c1aacc81f2e`.
- Backend compatibility: PASS, 1,400 files,
  `sha256:68b038e9ec86967c8e9a426e2fe9fa5e798a717966852466167fe8434a935c02`.
- Fast tier: 15/15 PASS in 5.394 seconds after the hostile-review repair.
- Conversation: 32 Python tests and 15 JavaScript vectors PASS.
- Contract tier: 3/3 PASS.
- Candidate WSP 62: PASS.
- Package: 67 files / 950,440 raw bytes,
  `sha256:aeace93f0386c549ac6c70e6aae25ba6aaac10738ea76ee76585735668135773`.
- Full release: all four groups PASS in 229.074 seconds, no timeout.

These are candidate-branch results. They do not claim a pushed PR, remote CI,
squash merge, exact-main VSIX, deployment, or activation. Those claims require
fresh verification after the commit exists and current `origin/main` is
reconciled.

## Next executable RedDog task

After this release/CLI closure lands, the highest-value executable RedDog-owned
task is the first WSP 62 extraction from `extension.js`, following the existing
ROADMAP order. The end-to-end worker vertical has equal priority but is blocked
on actively owned RSI/WRE/Holo authority work. One extraction is local,
non-duplicative, deadline-bound, independently testable, and reduces the risk
of every subsequent RedDog feature.
