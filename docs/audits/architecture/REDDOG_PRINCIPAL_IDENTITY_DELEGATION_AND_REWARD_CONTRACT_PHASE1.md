# REDDOG_PRINCIPAL_IDENTITY_DELEGATION_AND_REWARD_CONTRACT_PHASE1

Status: DECISION-ONLY audit (no implementation, no keys, no chain, no permission change).
Base: 4094ed58e44f37fa66360c6e4a5ca7a04f250dc5 (origin/main HEAD at audit-write time)
Author-role: 0102 architect (synthesized from 4 read-only Explorer workers + WSP preflight worker)
WSP: WSP_97 (truth boundary), WSP_50 (pre-action), WSP_54, WSP_58, WSP_96, WSP_100, WSP_46, WSP_48, WSP_109

Truth-label legend (WSP_97):
- OBSERVED       = read directly from source at the cited file:line
- INFERRED       = concluded from OBSERVED evidence, not itself a literal
- SPECIFIED_NOT_IMPLEMENTED = proposed by this doc; does NOT exist in code yet
- NEEDS_VERIFICATION = asserted elsewhere, not confirmed by this audit

---

## 0. Driving question (verbatim)

"How should a RedDog move from advisory-only to governed executor for its
authenticated 012 principal, while preserving repo permission boundaries,
FoundUp ownership, work-order scope, receipts, and future F(i)/UPS allocation?"

The key architectural sentence this audit certifies:

    Role text is never authority.
    Signed identity + fresh permission + scoped delegation is authority input.

A pasted "I am 012" is prompt text. After this layer, that text means nothing
unless the work packet is signed by the authenticated principal / delegated
RedDog identity AND matches a fresh permission snapshot AND matches scope.

---

## 1. WSP governing protocols (OBSERVED from WSP preflight)

| WSP | Governs | Binding rule for this contract |
|-----|---------|-------------------------------|
| WSP_54 | Agent identity by state (Dormant/Active/Coordinating); DAEs carry declared identity | Identity is declared, not self-minted at runtime |
| WSP_58 | IP / tokenization: creator identity mandatory in IP metadata; token split 80/20 creator/treasury; amendments require governance approval; unique IP id FUP-YYYYMMDD-HASH | reward_account maps to the creator-identity + governance-gated split; RedDog cannot amend the split |
| WSP_96 | MCP governance: 3-agent consensus (0102/Qwen/Gemma); 0102 veto on high-risk; supply-chain security gate fail-closed | Broadening execution authority is a high-risk change -> consensus + veto gate |
| WSP_100 | DAE -> SmartDAO: payout_ready=False and cabr_ready=False enforced (DOCS_ONLY); no agent self-approves tier escalation; "sovereign internal agent consensus" is FUTURE_BLOCKED | Reward-to-receipt is SPECIFIED and FUTURE_BLOCKED; execution never implies payout |
| WSP_46 | WRE: DAE Gateway canonical routing; execution defaults dry_run_mode=True; AI Overseer=governance, WRE=execution; WRE does NOT handle payout/CABR | Delegated execution routes through the Gateway; payout is out of WRE scope |
| WSP_48 (Sec 8.3) | Recursive self-improvement: "0102/DAE proposes, does NOT self-approve. Builder agents construct, do NOT deploy without consensus." Agent-creation rate limits (5/min, max 50, depth 3) | Direct code ground for "RedDog never self-grants authority" |
| WSP_109 | FoundUp intake: framework canonical; NO token / NO wallet / NO chain activation in intake (TOKEN_DEFERRED); fork lineage explicit | Identity/reward layer is a SEPARATE concern from intake; must not smuggle wallet into intake |

WSP GAP (INFERRED): No existing WSP defines an agent cryptographic identity
(keypair / DID / fingerprint) nor a self-authority approval gate. This contract
fills a genuine WSP gap; it does not duplicate an existing protocol.

---

## 2. Direct-read evidence (OBSERVED)

### 2a. The work-order spine has scope FIELDS but ZERO signatures

`modules/communication/moltbot_bridge/src/reddog_governed_work_order_dryrun.py` (461L)
- RedDogGovernedWorkOrder carries: authenticated_principal (L124), principal_provider (L125),
  red_dog_instance_id (L123), repo_full_name (L126), allowed_paths (L130), nonce (L144),
  expiry (L143), evidence_digest (L145). FORBIDDEN_OPERATION_TOKENS + FORBIDDEN_PATH_GLOBS present.
- OBSERVED: every "digest" is a SHA256 hash = integrity (tamper-evidence), NOT a signature
  (authenticity). authenticated_principal is an UNSIGNED string. There is no key that proves
  the packet came from the claimed principal.

`modules/communication/moltbot_bridge/src/reddog_wre_execution_valve.py`
- OBSERVED: sovereign_worktree_token is a plain-text env-var non-empty check. No crypto, no
  expiry, no scope binding. A model that can emit the literal string satisfies the gate.
  This is a fabricatable authority token.

`modules/communication/moltbot_bridge/src/proof_of_compute_receipt.py` (L153-169)
- OBSERVED: receipt carries receipt_id, job_id, tenant_id, foundup_id, intent_id, worker_id,
  compute_used; payout_status=NOT_EVALUATED, cabr_status=NOT_SUBMITTED. Hash-linked, UNSIGNED.

### 2b. Intake already has the CORRECT signed-identity pattern (the asset to extend)

`modules/.../ai_overseer/.../intake_auth_provider.py` (750L) + launch_request.py
- OBSERVED: sess.v1 / invite.v1 tokens are HMAC-SHA256 signed over the whole token prefix
  (L413-416). Verified handle is extracted ONLY from the verified token subject, NEVER from
  payload (L505-528, L743-747). requester_handle is the verified principal (L152).
- OBSERVED: SQLiteNonceStore (L224-337) = durable single-use nonce = replay protection.
- OBSERVED: session TTL 1h, invite TTL 7d single-use. build_intake_context() (L670-750) is the
  ONLY function that sets authenticated / invite_token_verified / requester_handle.
- INFERRED: this is the "role text is never authority" pattern already implemented for intake.
  It is HMAC (symmetric shared secret), NOT a keypair; it does not yet cover work orders.

### 2c. Agent permission model (per-agent tiers, audit hashes not proofs)

`modules/ai_intelligence/agent_permissions/src/agent_permission_manager.py` (569L)
- OBSERVED: agent_id (L78) = agent identity; granted_by (L81) in {"0102","012","system_automatic"};
  tiers read_only < metrics_write < edit_access_tests < edit_access_src; confidence-based escalation
  + auto-downgrade (L330-342, L495-562); per-agent allow/forbid file lists (L306-328).
  Source of truth = .claude/skills/skills_registry.json; audit trail = SQLite permission_events.
- OBSERVED: approval_signature (L87, L181-200) is SHA256(json(approval_data)) = deterministic
  audit HASH, NOT a secret-key signature.

### 2d. Repo permission source of truth (fresh, TTL-bounded snapshot)

`.../reddog_github_permission_probe.py` (289L)
- OBSERVED: RepoPermissionProbeSnapshot (L47-64): principal_login (L50), principal_provider (L51),
  permission (L52), can_read/can_write/can_admin (L53-55), checked_at (L57), expires_at (L58, TTL
  default 300s L231), evidence_digest (L62 = sha256 of canonical snapshot_core). Read-only gh CLI.
- OBSERVED: is_snapshot_fresh() (L123-133) enforces now <= expires_at. Point-in-time, not a stream.
- INFERRED: this is the correct "fresh permission" input; it just needs to be BOUND INTO a signed
  payload rather than sitting beside an unsigned string.

### 2e. FoundUp ownership + reward accounting (identity keys exist, authority binding absent)

`modules/foundups/foundup_registry.schema.json`
- OBSERVED: owner_dae (L304, string|null), foundup_id (L162), tier F0..F5 (L186-191),
  token_symbol (L225-228), auditor (L339-341).
`modules/foundups/foundup_registry.json`
- OBSERVED: across gotjunk_001 / kosei / voteballots, owner_dae is DEFINED IN SCHEMA BUT
  UNPOPULATED in data. FoundUp ownership is metadata-only, unbound to a principal.

`modules/foundups/simulator/economics/epoch_ledger.py`
- OBSERVED: participant_rewards: Dict[str,float] maps participant_id -> amount (L49); Merkle proof
  per participant (L253-317). Participant identity is a bare STRING; no wallet / address / recipient.

`modules/communication/moltbot_bridge/src/cabr_store_export.py`
- OBSERVED: persists receipt_id/job_id/tenant_id (L173-175), decision (L188);
  verification_complete/cabr_ready/payout_ready = INTEGER, always FALSE (L207-209).
  Header (L50-57): "DOES NOT: Write to wallet / Trigger payouts / Issue tokens or UPS /
  Allocate rewards." Consensus/observability only, by design.
- OBSERVED (grep, 0 matches each): principal_wallet, reward_wallet, recipient_wallet,
  delegation_target, payout_address. No receipt->wallet mapping exists anywhere in the stack.

---

## 3. Current identity / authority map (INFERRED synthesis)

| Concern | Where it lives today | Authenticated? | Gap |
|---------|----------------------|----------------|-----|
| FoundUp-intake principal | requester_handle (intake_auth) | YES (HMAC token, subject-only, nonce) | Only covers intake, not work orders |
| Agent identity | agent_id (agent_permission_manager) | NO (string + audit hash) | Not a principal, not signed |
| Repo principal | principal_login (github probe) | YES (GitHub OAuth), TTL 300s | Fresh but bound to nothing signed |
| Work-order principal | authenticated_principal (work order) | NO (unsigned string) | Spoofable by any emitter |
| Execution gate | sovereign_worktree_token (valve) | NO (plain env var) | Fabricatable by the model |
| Reward earner | participant_id / tenant_id (ledger/CABR) | NO (bare string) | No wallet, no signature, no claim right |
| RedDog instance identity | (none) | -- | reddog_id / keypair / fingerprint ABSENT everywhere |

Core finding (INFERRED, decisive): the shape already exists (fields for principal, repo,
scope, nonce, expiry, receipts). What is absent is the cryptographic identity + signature
layer that turns those fields from CLAIMS into AUTHORITY INPUT. The one place that already
does it right is intake_auth (HMAC signed token, subject-not-payload, durable nonce). The
governed-executor contract is: generalize that proven pattern to work orders + receipts, add a
RedDog instance keypair, and bind fresh permission + FoundUp scope into the signed payload.

---

## 4. Proposed contract (SPECIFIED_NOT_IMPLEMENTED)

Schema is DEFINED here, not built. No keys, no signing code in this slice.

```yaml
RedDogPrincipalIdentity:
  principal_id:            # stable id of the authenticated 012 principal (e.g. github:<login>)
  principal_provider:      # "github" | "intake_session" | "intake_invite"
  principal_wallet:        # OPTIONAL public reward address; NEVER a private key; may be null pre-OPO
  reddog_id:               # stable public id of THIS RedDog instance (new; absent today)
  reddog_public_key:       # instance public key; private half never leaves host vault
  reddog_key_fingerprint:  # short public fingerprint for display / revocation lookup
  repo_scope:              # list of repo_full_name this RedDog may act within
  foundup_scope:           # list of foundup_id this RedDog may act for
  reward_account:          # public account/handle rewards accrue to; NEVER implies repo authority
  revocation_policy:       # how principal revokes this reddog_id (ttl, allowlist, kill-switch)
```

```yaml
RedDogDelegatedWorkAuthority:
  work_order_id:               # unique id
  principal_id:                # who authorized (must match a live RedDogPrincipalIdentity)
  reddog_id:                   # which instance is delegated
  repo_full_name:              # target repo (must be in repo_scope)
  foundup_id:                  # target FoundUp (must be in foundup_scope)
  allowed_paths:               # explicit allowlist
  denied_paths:                # explicit denylist (wins over allow)
  requested_operation:         # verb; must not hit FORBIDDEN_OPERATION_TOKENS
  permission_snapshot_digest:  # digest of a FRESH RepoPermissionProbeSnapshot, bound into payload
  nonce:                       # single-use; consumed via durable nonce store (per intake pattern)
  expires_at:                  # short TTL
  valve_state_required:        # required execution-valve state (replaces plain env-var token)
  signature:                   # signature over the canonical payload by principal / delegated reddog key
  receipt_chain:               # ordered signed receipts produced by executing this authority
```

Verification order (SPECIFIED_NOT_IMPLEMENTED, the "authority input" pipeline):
1. signature verifies against a known, non-revoked reddog_public_key / principal key.
2. permission_snapshot_digest resolves to a FRESH (unexpired) snapshot granting the op.
3. repo_full_name in repo_scope AND foundup_id in foundup_scope.
4. requested_operation not forbidden; allowed_paths minus denied_paths non-empty and in-scope.
5. nonce unconsumed (atomic consume) AND now < expires_at AND valve_state_required satisfied.
6. Only then does the work authority become executable. Any miss = fail-closed, no execution.

---

## 5. Placement recommendation

Options considered:
- PLACE_IDENTITY_IN_AGENT_PERMISSIONS   -- has tiers/audit but no keypair, no principal, no scope
- PLACE_IDENTITY_IN_AI_OVERSEER_INTAKE_AUTH -- has the RIGHT signing pattern but is intake-scoped
- PLACE_IDENTITY_IN_OPENCLAW_POLICY_GATE -- consumer of authority, not the source of truth
- CREATE_SHARED_REDDOG_IDENTITY_CONTRACT -- new shared contract consumed by all of the above
- DEFER_FOR_SOURCE_GAPS                  -- not needed; sources are sufficiently mapped

RECOMMENDATION (INFERRED): CREATE_SHARED_REDDOG_IDENTITY_CONTRACT.

Rationale:
- Identity is fragmented across 4 modules (intake handle, agent_id, github login, work-order string).
  No single existing module owns "RedDog principal + instance + scope + reward" together.
- The correct crypto pattern already exists in intake_auth (HMAC token, subject-not-payload, nonce);
  the shared contract GENERALIZES that pattern rather than reinventing it.
- Consumers (OpenClaw policy gate, WRE valve, Hermes, receipt chain, reward accounting) should each
  DEPEND ON the shared contract, not re-implement identity. This keeps one source of truth.
- NOT in the extension: the VS Code / Cursor extension is an untrusted client surface. Identity,
  keys, and signature verification must live server/host-side; the extension only PRESENTS a packet
  to be verified. Putting identity in the extension would make role text into authority again.

---

## 6. On-chain / off-chain boundary (hard rule)

OFF-CHAIN (host vault / server only), NEVER on-chain, NEVER in repo/prompt/Copy-MD/receipt:
- reddog private signing key, principal private key, HMAC secrets, any wallet private key.

ON-CHAIN is PERMITTED to store (public, future, WSP_58/WSP_100 gated):
- public reddog_id / reddog_public_key / fingerprint, capability commitments (hashes),
  receipt-chain hashes, reward allocations (public amounts to public accounts).

Boundary invariant (INFERRED): the chain may anchor PUBLIC commitments and hashes; it never
holds a secret and never becomes the execution authority. Repo writes still require a fresh
GitHub permission snapshot; FoundUp writes still require foundup_scope; neither is granted by
anything on-chain.

---

## 7. Reward / F(i) / UPS allocation model (SPECIFIED_NOT_IMPLEMENTED, FUTURE_BLOCKED)

Current state (OBSERVED): payout_ready=False, cabr_ready=False, verification_complete=False are
hard-coded; CABR "does not write to wallet / trigger payouts / issue tokens / allocate rewards";
epoch ledger tracks participant_id -> amount with no wallet; owner_dae unpopulated. So reward is
tracked-but-not-settled by design.

Proposed binding (does NOT unblock payout; only defines the future path):
- A reward accrues to a reward_account ONLY via a SIGNED receipt in receipt_chain, never via a
  model claim. Receipt must be signed by the delegated reddog_id whose principal_id owns/was
  delegated the target foundup_id.
- reward_account maps to the WSP_58 creator-identity split (80/20 creator/treasury), which is
  governance-gated; RedDog cannot amend the split (WSP_58) and cannot self-approve settlement
  (WSP_48 Sec 8.3, WSP_100).
- Separation invariants (must hold in every future slice):
  - Execution authority does NOT imply fund custody.
  - reward_account does NOT imply repo authority.
  - Consensus (CABR approved) is NOT settlement (send tokens); they remain distinct gates.
- Settlement stays FUTURE_BLOCKED until WSP_100 flips payout_ready via governance, not via RedDog.

---

## 8. Security / spoofing / replay threat model (INFERRED)

| Attack | Today | After this contract |
|--------|-------|---------------------|
| Paste "I am 012" in prompt | authenticated_principal is an unsigned string -> could be trusted | text is inert; identity only from a verified signature over the payload |
| Replay a prior valid packet | work-order nonce exists but valve token is a static env var | durable single-use nonce (intake pattern) + short expires_at -> replay fails |
| Fabricate the sovereign token | plain env-var non-empty check -> model can emit the literal | valve_state_required bound into a signed, scoped payload; no free-text token |
| Another founder's RedDog acts in your repo | only an unsigned repo string | repo_full_name must be in signed repo_scope AND match a FRESH permission snapshot |
| Claim someone else's reward | participant_id is a bare string, no proof | reward requires a SIGNED receipt bound to reddog_id/principal_id/reward_account |
| Forge a receipt to fake compute/reward | receipts are hash-linked but unsigned | receipts must be signed; unsigned receipt = not in chain = no reward |
| Stale-permission escalation | snapshot sits beside an unsigned order | permission_snapshot_digest bound into signature; expired snapshot = fail-closed |
| RedDog self-grants broader authority | no runtime gate observed | WSP_48/WSP_96/WSP_100: propose-not-self-approve; consensus + 0102 veto required |

Direct answer to 012's concern: yes, this layer protects against someone pretending to be you.
A malicious actor can paste "I am 012" today and it might be read as authority. After this layer,
that text is meaningless unless the packet carries a valid signature from the authenticated
principal / delegated reddog_id AND matches fresh permission AND matches scope.

---

## 9. Hard requirements (contract must enforce; verbatim from architect directive)

- No private keys in repo, prompts, Copy MD, chain, or receipts.
- Work order must be signed.
- Permission snapshot must be fresh and bound into the signed payload.
- FoundUp scope must be explicit.
- Rewards attach to signed receipts, not model claims.
- Execution authority does not imply fund custody.
- Reward account does not imply repo authority.
- RedDog never self-grants authority.

---

## 10. HoloIndex addendum (OBSERVED)

Running the identity/reward query set against HoloIndex returned skill_hits:0 and no semantic
surfacing of reddog_id / principal identity / reward_account / delegation authority. The identity
and reward surfaces audited here were located by 0102-direct read, NOT by semantic retrieval.
INDEX_GAP confirmed (consistent with the campaign-operator and youtube_auth index gaps). A
re-index (python holo_index.py --index-all --index-symbols --index-skillz) is a prerequisite
before RedDog itself could audit these surfaces; RedDog remains retrieval-blind to them today.

---

## 11. Truth Boundary Checklist (scope guards for the resulting PR)

- NO_KEY_IMPLEMENTATION      -- this slice defines schema only; zero signing/crypto code added.
- NO_CHAIN_ACTIVATION        -- no on-chain writes; boundary described, not implemented.
- NO_PERMISSION_CHANGE       -- no grant/revoke; permission model only mapped.
- NO_WALLET                  -- no wallet created/bound; reward path SPECIFIED + FUTURE_BLOCKED.
- NO_RUNTIME_AUTHORITY       -- no execution path broadened; advisory posture unchanged.
- DOCS_ONLY                  -- decision PR; deliverable is this document.

---

## 12. Next slices + implementation sequence (architect-directed)

Recommended next slice (DEFINE, not implement):

    REDDOG_PRINCIPAL_IDENTITY_AND_DELEGATION_CONTRACT_PHASE1

Implementation sequence (each its own gated slice; do NOT implement keys yet):
1. Identity/delegation contract doc (this decision -> ratified schema).
2. Threat-model tests / static contract checks (assert the Section 8 invariants).
3. Signature verifier for work orders (generalize the intake HMAC/subject-not-payload pattern).
4. Signed receipt chain (replace unsigned hash-linked receipts).
5. Reward-account mapping (bind signed receipt -> reward_account; still FUTURE_BLOCKED settlement).
6. Only then broaden RedDog execution authority (WSP_96 consensus + 0102 veto gated).

Governance note: broadening execution authority (step 6) is a high-risk change under WSP_96;
it requires 3-agent consensus with 0102 veto and MUST NOT be self-approved by RedDog (WSP_48 Sec 8.3).
