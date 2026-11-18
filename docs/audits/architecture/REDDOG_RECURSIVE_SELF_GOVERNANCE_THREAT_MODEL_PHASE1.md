# REDDOG_RECURSIVE_SELF_GOVERNANCE_THREAT_MODEL_PHASE1

**Type:** Decision-only threat model. No code, no keys, no chain, no permission/authority change, no re-index.
**Author:** 0102 (RedDog Architect) | Commander: 012
**WSP:** 00, 15, 50, 97 (method); 48, 46, 54, 58, 95, 96, 100, 64 (governing).
**Base:** `8bb140f89` (main; after #925 live writer, #926 principal-identity contract, #927 operator-loop binding).
**Sequence position:** C.

---

## 0. Purpose + rename + reconciliation (WSP 50 / WSP 64)

This slice models the threats specific to **RedDog becoming recursively self-improving AND execution-capable** -- a continuously-running, 012-out-of-loop agent that DERIVES its own governance, WRITES repo changes, and could act on ITSELF. It deliberately does **not** re-model classic principal-identity spoofing: **#926 already owns that** (its Section 8 + the `RedDogPrincipalIdentity` / `RedDogDelegatedWorkAuthority` schema, generalizing the proven `intake_auth_provider.py` pattern -- HMAC over a signed prefix, verified subject NOT payload, durable single-use nonce).

Renamed from the working title `REDDOG_IDENTITY_SPOOFING_AND_DELEGATION_THREAT_MODEL` -> **`REDDOG_RECURSIVE_SELF_GOVERNANCE_THREAT_MODEL`** because identity spoofing is #926's territory; this doc's territory is self-governance under recursion.

**Corrected sequence (A-H):**
```
A. #925 narrow FoundUp live writer proof              (done, merged)
B. REDDOG_OPERATOR_LOOP_WSP97_BINDING_PHASE1          (done, #927)
C. REDDOG_RECURSIVE_SELF_GOVERNANCE_THREAT_MODEL_PHASE1   (THIS doc)
D. #926 principal identity / delegation / reward contract (already landed)
E. REDDOG_WORK_ORDER_SIGNATURE_VERIFIER_PHASE1        (next executable; generalize intake_auth)
F. signed receipt chain
G. reward mapping (FUTURE_BLOCKED settlement)
H. generic writer contract / implementation           (later; gated on B-G)
```

**Method:** WSP_97 CoT (retrieve #925/#926/#927 + WSP index) + CoR. A 4-lens completeness-critic sweep of the draft surfaced ~13 additional threat classes (concurrency/distributed-TOCTOU, executable-supply-chain-to-vault, derivation prompt-injection, timing side-channel, reviewer social-engineering, tamper-preserving audit rewrite, Goodhart/self-dealing/CABR-oracle economic attacks); all folded below. Nothing is assumed correct.

## 1. Governing WSPs

WSP 48 8.3 (propose-not-self-approve; agent-creation limits 5/min, max 50, depth 3) is the direct ground for "RedDog never self-grants." WSP 96 (3-agent consensus + 0102 veto on high-risk; supply-chain gate fail-closed). WSP 95 (Skillz prototype->production promotion gate, supply-chain security). WSP 54 (identity declared, not self-minted). WSP 58/100 (reward split governance-gated; payout FUTURE_BLOCKED). WSP 46 (Gateway routing, dry_run default). WSP 64 (extend, don't duplicate -- this doc cross-references #926/#927, does not restate them).

## 2. Trust boundaries + actors (extended)

| Surface | Trust | New threat this doc adds |
|---------|-------|--------------------------|
| VS Code / Cursor extension | UNTRUSTED client | (owned by #926 s5) |
| Host vault (keys, HMAC secrets) | TRUSTED | **exfiltration channel** (timing/error/receipt), not just placement |
| Derivation DATA oracle (HoloIndex / WSP index) | trusted-but-MUTABLE | poisoning (#927 5A) + **flooding/availability** + **in-band prompt injection of the derivation** |
| **Loaded-and-EXECUTED code (Skillz / deps / MCP tools)** | **assumed-trusted, actually mutable** | **NEW: the code that derives/signs/enforces is itself attackable and can reach the vault** |
| **Pattern-memory / adaptive-learning store** | trusted feedback loop | **NEW: poisoned learned pattern steers a future derivation/write** |
| Governance substrate (valve/gate/preamble/WSP source) | integrity-critical | self-modification (#927 5B) |
| **CABR / reward-scoring store** | write-only observability today | **NEW: the agent influences the score it is judged by** |
| **The human/DAO reviewer + 3-agent consensus** | trusted judgment | **NEW: RedDog authors the prose the reviewer reads (judgment capture, not identity)** |
| **Multiple concurrent RedDog instances** | per-instance identity | **NEW: distributed TOCTOU, worktree/chain races, mutating-quorum-membership** |

## 3. Threat classes (recursive self-governance)

### G1 -- Derivation-substrate poisoning (the agent corrupts what it derives governance FROM)
| ID | Attack | Owning control | Status |
|----|--------|----------------|--------|
| G1.1 | Oracle poisoning: write the HoloIndex/WSP index, then "derive" the attacker's preferred WSP and legitimately stamp it | #927 5A protected oracle (governance-denied; INDEX_GAP write-op = fail-closed; no derive-and-execute in an index-mutating context) | SPEC (5A) |
| G1.2 | WSP-index poisoning + HoloIndex poisoning (the two concrete substrates behind G1.1) | 5A denylist names both substrates explicitly | SPEC (5A) |
| G1.3 | **Pattern-memory / learned-derivation poisoning**: a poisoned `refactoring_patterns.json` / SQLite `pattern_memory` entry recalled by Qwen/Gemma steers a future write | **NEW: extend 5A protected set to the pattern-memory/adaptive-learning stores; treat recalled patterns as UNTRUSTED (re-derive from primary, never execute a recalled pattern as authority)** | RESIDUAL |
| G1.4 | **Derivation prompt/model injection**: the derivation is an LLM reading attacker-controlled task text / retrieved docs carrying "this file is governed by WSP-X; allowed_paths include Y" | **NEW: derive governance ONLY from a trusted WSP-framework path RedDog cannot write; treat retrieved evidence + task text as untrusted for derivation; ignore in-band directives** | RESIDUAL |

### G2 -- Self-governance mutation (the agent weakens the gate that judges it)
| ID | Attack | Owning control | Status |
|----|--------|----------------|--------|
| G2.1 | Governance-path self-modification (edit valve/gate/preamble/operator-loop enforcer) | #927 5B inv 1 | SPEC (5B) |
| G2.2 | Self-serving WSP rewrite (edit the WSP it derived from, in-loop) | #927 5B inv 2 | SPEC (5B) |
| G2.3 | Receipt / ledger disablement (disable/truncate the chain it is judged by) | #927 5B inv 5 | SPEC (5B) |
| G2.4 | Self-promotion (mark-ready / merge own draft PR) | #927 5B inv 7 + #925 draft-only | PARTIAL (draft-only yes; positive promotion authority unencoded) |
| G2.5 | **Meta-authority / governance capture**: who authorizes edits to the valve/WSP framework themselves? | **NEW: promotion-authority contract -- the promoter must be provably NOT the same principal; ties G2.4** | RESIDUAL |

### G3 -- Integrity mistaken for authenticity (self-assertion treated as authority)
| ID | Attack | Owning control | Status |
|----|--------|----------------|--------|
| G3.1 | Treat a self-asserted `derivation_source=REDDOG` stamp / digest chain as authority | #927 s5 boundary + #926 signature requirement (valve must not trust the unsigned label until E lands) | SPEC |
| G3.2 | Work-to-WSP substitution (derive WSP-X from benign text, do WSP-Y work) | #927 5C governance-coverage re-check at write boundary (`FAIL_WSP_WORK_MISMATCH`) | SPEC (5C) |

### G4 -- Replay, temporal + concurrency (multi-instance, continuous-run)
| ID | Attack | Owning control | Status |
|----|--------|----------------|--------|
| G4.1 | Operator-loop preamble / valve replay (reuse a prior accepted `preamble_digest`) | #927 5B inv 3 (single-use preamble nonce) | SPEC (5B) |
| G4.2 | **Distributed TOCTOU**: 2 honest instances; between preamble (T0) and write (T1) the SHARED world mutates (permission revoked, index changed, denied_path added). The bind holds (no replay, no retarget) but the world is stale | **NEW: extend #927 5C write-boundary re-check to EXTERNAL mutable state -- re-derive permission snapshot + oracle content-digest atomically at the write (optimistic-concurrency / CAS), fail-closed on drift** | RESIDUAL |
| G4.3 | **Concurrent worktree collision + receipt-chain fork**: 2 honest in-scope instances append the hash-linked chain concurrently (fork/lost-update) and race overlapping worktree writes (last-writer-wins) | **NEW: per-foundup/per-worktree exclusive write LEASE (single-writer) + monotonic append-only chain with CAS on predecessor-hash; lifts the "never 2 agents in 1 worktree" ops rule into an enforced control** | RESIDUAL |
| G4.4 | **Mutating-quorum-membership**: independent signers, but the signer/revocation set mutates DURING the round -> authority granted by a set that never simultaneously existed | **NEW: pin signer-set + revocation-list snapshot (digest) into the round; revocations effective only at round boundaries; concurrent mutation = round invalidated** | RESIDUAL |
| G4.5 | **Non-atomic multi-resource valve gate**: #926's 6-step verification makes only the nonce atomic; between step 2 (fresh snapshot) and step 6 (execute) a concurrent actor flips valve_state / invalidates snapshot / changes denied_paths | **NEW: evaluate the full precondition set in ONE critical section/transaction (pin permission+valve_state+denied_paths at step 2, CAS re-check at step 6), fail-closed on intra-pipeline drift** | RESIDUAL |
| G4.6 | **Tamper-preserving audit rewrite**: rewrite receipt history while keeping it self-consistent (receipts hash-linked UNSIGNED until F); delete nonces to reopen replay | **NEW: append-only, externally-anchored audit + nonce store (periodic hash-chain checkpoint to a surface RedDog cannot rewrite; off-host co-signer of nonce-consume)** | RESIDUAL |

### G5 -- Executable supply chain (the code that derives/signs/enforces is attackable)
| ID | Attack | Owning control | Status |
|----|--------|----------------|--------|
| G5.1 | **Skillz / dependency / MCP-tool poisoning reaching the vault**: malicious code loaded INTO RedDog's own process reaches the host vault holding the signing key -> emits a fully-VALID signed authority. #927's mutable-substrate rows cover DATA and SOURCE, never LOADED-AND-EXECUTED code | **NEW: code-provenance / supply-chain gate -- pinned+hash-verified deps; signed Skillz with a WSP 95 prototype->production promotion gate RedDog cannot self-approve; WSP 96 supply-chain gate fail-closed; key operations isolated from loaded plugin code** | RESIDUAL |

### G6 -- Economic / incentive (attack the value function, all artifacts authentic)
| ID | Attack | Owning control | Status |
|----|--------|----------------|--------|
| G6.1 | **Goodhart reward-farming**: maximize QUANTITY of correctly-signed, correctly-scoped, authentically-derived work orders/receipts (split one task into N trivial signed orders) rather than value | **NEW: reward-emission economic-integrity gate (#926 s12 step 5) -- value-weighted not count/compute-weighted accrual; receipt de-dup + minimum-substance threshold; per-principal rate cap** | RESIDUAL |
| G6.2 | **Collusive self-dealing**: a principal delegates its own RedDog to create low-value FoundUps (create_foundup now first-class) and accrue reward to a reward_account the SAME principal controls -- authentic throughout | **NEW: eligibility-separation invariant (reward_account independence-from-authorizing-principal, or a governance-gated self-dealing cap) + a FoundUp-value/maturity gate before reward eligibility** | RESIDUAL |
| G6.3 | **CABR-scoring-oracle poisoning**: the reward-earning RedDog influences the CABR store / scoring inputs it is judged BY (reward-side analogue of G1.1; 5A covers the governance oracle, not the CABR store) | **NEW: extend 5A protected-oracle set to the CABR/reward-scoring store + inputs; CABR scoring runs in an authority RedDog does not control** | RESIDUAL |

### G7 -- Availability + side-channel + social (the gate degrades or is bypassed around)
| ID | Attack | Owning control | Status |
|----|--------|----------------|--------|
| G7.1 | **Availability / DoS / budget exhaustion**: flood HoloIndex / wsp_protocol_lookup / permission probe / nonce store; exhaust agent-creation limits, worktree/disk, token budget -> sustained fail-closed (denial) or a fail-OPEN bug | **NEW: availability + fail-mode contract -- explicit fail-closed-not-fail-open per gate input under timeout/rate-limit/disk-full; alarm-on-sustained-fail-closed that RedDog cannot self-clear** | RESIDUAL |
| G7.2 | **Secret exfiltration side-channel**: non-constant-time HMAC/digest compare leaks the key by timing; secrets leak via error strings / receipts / telemetry / Copy-MD | **NEW: signature-verifier MUST use constant-time compare (`secrets.compare_digest`); failures MUST NOT include expected material; a redaction gate over ALL receipt/telemetry/Copy-MD/error surfaces** | RESIDUAL (verifier clause for E) |
| G7.3 | **Social-engineering the reviewer / consensus** (judgment integrity, not identity): RedDog authors the PR description, receipt narrative, and preamble the honest reviewer trusts | **NEW: promotion-authority contract -- reviewer sees a MACHINE-derived, RedDog-uncontrollable diff+scope summary as the source of truth (not RedDog's prose) + an adversarial-review checklist** | RESIDUAL |

## 4. Coverage matrix (summary)

- **SPEC-owned (by #927 5A/5B/5C + #926):** G1.1, G1.2, G2.1, G2.2, G2.3, G3.1, G3.2, G4.1.
- **PARTIAL:** G2.4 (draft-only yes; promotion authority no).
- **RESIDUAL -- newly surfaced, NO current owner (the real backlog):** G1.3, G1.4, G2.5, G4.2, G4.3, G4.4, G4.5, G4.6, G5.1, G6.1, G6.2, G6.3, G7.1, G7.2, G7.3.

Your 14-item coverage list maps as: oracle=G1.1, WSP-index=G1.2, HoloIndex=G1.2, self-serving-WSP-rewrite=G2.2, governance-path-self-mod=G2.1, valve/preamble-replay=G4.1, receipt-disablement=G2.3, self-consensus/Sybil=#926+G4.4(membership), self-promotion=G2.4, work-to-WSP=G3.2, integrity-vs-authenticity=G3.1, Skillz/pattern-memory=G5.1+G1.3, economic-gaming=G6.*, DoS/budget=G7.1. All 14 covered; the completeness sweep added G1.4, G4.2-G4.6, G6.2-G6.3, G7.2-G7.3.

## 5. Residual controls needed (prioritized for the D-implementation backlog)

1. **The signature scheme itself (E).** Until the work-order signature verifier exists, G3.1 and all of #926 Class A are open in practice. Highest priority; unblocks authenticity.
2. **Derivation hardening (G1.3, G1.4).** Protected pattern-memory + derive-from-trusted-path-only + treat retrieved/task text as untrusted. Without this, "active-derive" is defeated by poisoning/injection.
3. **Concurrency contract (G4.2-G4.5).** Write-boundary external-state re-check (CAS), per-worktree write lease, round-membership pin, atomic multi-resource gate. Required before ANY multi-instance continuous run.
4. **Executable supply-chain gate (G5.1).** Key isolation from loaded plugin code + signed Skillz (WSP 95/96). The signature layer is worthless if arbitrary loaded code can reach the key.
5. **Promotion-authority + judgment-integrity contract (G2.5, G7.3).** Machine-derived review summary; promoter provably-not-same-principal.
6. **Economic-integrity gate (G6.*).** Value-weighted reward, self-dealing separation, CABR-store protection. Blocks incentive gaming before settlement is ever unblocked.
7. **Availability + side-channel + audit-anchoring (G7.1, G7.2, G4.6).** Fail-closed-not-open contract, constant-time compare + redaction, externally-anchored audit/nonce store.

## 6. Truth boundaries

- OBSERVED: #926 s8 owns Class A; #927 5A-5C + s5 own G1.1/G1.2/G2.1-3/G3.1-2/G4.1; the ops rule "never 2 agents in 1 worktree" exists but is unmodeled as a control; receipts are hash-linked UNSIGNED today (#926 s2a/s2c).
- INFERRED: the RESIDUAL set (s5) is where recursive-self-governance safety is actually built; several items (G4.*, G5.1, G7.2) are BLOCKER-class for a 012-out-of-loop continuous multi-instance system.
- SPECIFIED_NOT_IMPLEMENTED: every control here is a spec; this doc adds NO code, NO authority, NO new WSP. It extends #927's invariant set and #926's threat model per WSP 64.

## 7. Verdict + next executable slice

Verdict: **CONSOLIDATE + EXTEND NOW; the RESIDUAL set is the recursive-safety backlog.** This threat model becomes the assertion target for #926 s12 step 2 (threat-model tests), now covering G1-G7.

**Next executable (only after this doc is finalized + reviewed):** `REDDOG_WORK_ORDER_SIGNATURE_VERIFIER_PHASE1` -- generalize the proven `intake_auth_provider.py` pattern: **verified subject NOT payload text; signed prefix; nonce; expiry; durable consume-once; fail-closed** -- and, from G7.2, **constant-time compare (`secrets.compare_digest`) + no expected-value material in failures**. Do NOT open verifier code until C is finalized.

## 8. Out of scope (this slice)
Any signing/crypto/keys; editing #925/#926/#927 or the valve/gate/WSP framework; running the live writer; opening authority; adding Skillz; re-indexing; building any control listed (all are specs/backlog).

---

*Central certification (extended from #926 s0): role text is never authority; a self-asserted derivation is never authority; a self-consistent digest chain is never authority. Authority input = signed identity + fresh permission (re-checked atomically at write) + scoped delegation + an oracle the agent cannot poison + governance the agent cannot self-modify + a value function the agent cannot game + keys the agent's loaded code cannot reach. Everything short of that is integrity, not authenticity.*
