# Video provenance, agent identity, and reward collectibles — staged PoC

Status: PROPOSED / NOT IMPLEMENTED (2026-11-16). WSP_00 context; WSP_97 evidence-first; WSP_15 sequencing; WSP_48 RSI transfer; WSP_99 receipts; WSP_110 closure. This is a research/roadmap contract, not permission to mint, deploy, run paid models, or modify identity authority.

## Ownership and discovery
- Media authoring: `modules/communication/youtube_shorts/`; music-video assembly: `modules/communication/headless_video_orchestrator/`; indexing: existing `modules/ai_intelligence/video_indexer/`. Reuse existing rendering, uploader, rights checks and review.
- Existing WRE auto-researcher: `modules/infrastructure/wre_core/src/wre_auto_researcher.py` (injected dry-run runner; no live autonomous git writes). Inspect current WSP_48 and WRE admission before running agents. Research proposals are not RSI until independent verification and successful later reuse.
- Related experimental patent: `WSP_knowledge/docs/Papers/Patent_Series/04_rESP_Patent_Updated.md`, especially claims 12–14, figures 12–13, 19; prototype `modules/ai_intelligence/rESP_o1o2/src/quantum_cryptography_system.py`; corrected witness framing `WSP_framework/src/WSP_61_Theoretical_Physics_Foundation_Protocol.md`.
- This PoC is NOT a new NFT storefront, upload system, wallet authority, token economy, security principal or production cryptosystem.

## Staged evidence gates (WSP_15 order)

### P0 — Freeze one real LEGO-style video reference
Identify one already-produced, rights-cleared video and its canonical file bytes, source assets, renderer/version, creator authorization and SHA-256 digest. Record file/derivative identity separately from work identity and revision/parent IDs. Do not assume a prior video was independently reviewed or available on this worker. Baseline a byte-identical copy (same hash, no inherent copy event), re-encode (different hash), and unmodified playback. No public upload required.

### P1 — Standards-based provenance baseline
Create a canonical sidecar manifest with immutable work_id, artifact_id, revision_id, parent artifact IDs, source asset hashes, renderer/model parameters, rights evidence, issuer public key identifier, algorithm/version and timestamp. Use reviewed signing libraries and independent public-key signature verification; private keys remain in a managed signer, never in media, logs or browser. Bind signature to canonical manifest and exact media digest. Evaluate C2PA/Content Credentials for interoperable embedding, but maintain an external signed manifest when metadata is stripped. Embed only public verification material and a content locator, never a private key. Test tamper detection, wrong signer, substituted video, deleted manifest and key rotation/revocation. A digest alone is not an authenticated signature.

### P2 — Resilient identity and adversarial video lab
Compare metadata-only, signed sidecar, robust invisible watermark, and perceptual matching; these have different security properties. Measure watermark extraction after lossless copy, codec recompression, crop, resize, overlays, frame dropping, speed change, audio replacement and social-platform roundtrip when authorized. Independent attacker agents attempt removal, spoofing, collusion and false attribution; defender agents attempt detection. Keep immutable hidden test set and hold-out verifier. Metrics: detection precision/recall, false-positive rate, bit-error rate, perceptual quality, runtime, cost, key compromise and forgery success. Hard-to-find watermark is not stronger encryption. No claim of impossible copying or unbreakable ownership.

### P3 — WRE / Open Researcher measured improvement
Use existing WRE auto-researcher research/evaluator contracts; qualify actual runner and permissions separately. Fix baseline and independent scoring oracle before agent changes. Agent roles: proposer (new watermark/embedding scheme), attacker, verifier, cost/quality auditor. Each candidate records input hash, parameters, threat model, seeds, output hash, tests and rollback. Promote only statistically meaningful held-out improvement with independent re-test and later reuse (WSP_48); reject overfitting, broken verification and quality regressions. No live unattended edits or claims of autonomous RSI from a saved prompt.

### P4 — Cryptographic agent/DAE identity (separate authority lane)
A DAE cannot assert a role by prose alone. Require verified principal key, signed short-lived challenge/command, scoped capabilities, expiration, audience, nonce/replay protection, revocation and auditable delegation. Reuse existing WSP_27/DAE authentication and WRE/CABR authority contracts; inspect them before design. Signature proves key control, NOT authorization for the claimed role. Never allow a video token or embedded media key to confer security/merge/publishing permissions.

### P5 — Gifted video collectible, not a sale
Explore a non-sale reward object for verified participation. Wallet ownership and claim state must be authenticated; content identity and legal copyright/license must remain distinct. Define eligible award -> reserved/unclaimed -> claimed wallet -> optional transferable/retired states. An expired unclaimed reservation returns to the reward pool under explicit time, notice and audit policy; do NOT automatically confiscate a claimed wallet asset. Reuse existing UPS/FoundUp reward governance and ledger concepts only after reading their canonical rules. Prefer portable content-addressed media with replicated availability and on-chain digest/manifest references, not a single website URL. Do not mint or spend tokens in this PoC.

### P6 — Experimental geometry branch, strictly isolated
Compare the patent's geometric-path features against P1–P3 baseline under matched data, adversarial and statistical tests. Test repeatability, uniqueness, min-entropy, sensitivity, bias, extractability and independent reproduction. The current prototype hashes JSON geometric trajectories and checks hash length; that does not establish a secure digital signature, high entropy, quantum resistance or key unpredictability. WSP_61 now treats det(g) as a near-singularity/instability witness unless stronger mathematical conditions are proven. No geometry-derived material is a production secret or security primitive without external cryptographic review. Negative results are useful and retained.

## Test fixtures and acceptance
- Exact-copy fixture must preserve hash and embedded bytes; cannot infer who copied it.
- Derivative fixture must change exact hash but retain lineage only if explicitly signed/linked.
- Tampered signature, manifest, issuer and media must fail authentication.
- Watermark and perceptual matching are probabilistic and must report uncertainty.
- Wrong-role DAE with a valid but unauthorized signature must be denied.
- Expired unclaimed reward returns only by authorized policy; claimed token remains with owner absent separately authorized rules.
- Preserve rights, child-safety and YouTube platform requirements before publishing.
- Record baseline and independent verification; no success percentage without real runs.

## Next implementation slice (NOT executed by this document)
1. Resolve exact LEGO-video producer/asset and verify a rights-cleared sample.
2. Implement offline manifest/sign/verify prototype using vetted crypto; no NFT or network.
3. Add negative fixtures and independent checks; produce WSP_99 evidence receipt.
4. Admit bounded adversarial benchmark only after immutable oracle and runtime authorization.
5. Route lessons into existing WRE pattern memory, then assess reward prototype and experimental geometry.

## Open decisions
Choose canonical work/revision identifiers, signing trust roots and revocation policy, license rights conveyed by a gifted NFT, unclaimed expiration period, and which wallet/UPS ledger owns reward lifecycle. None is silently defaulted.

## Architectural correction: shared tool, not a channel-owned product (012, 2026-11-16)

Canonical intent: **producer of any kind -> reusable scene/asset LEGO composition (optional) -> shared video render/assembly tool -> provenance/signature service -> distribution adapter (optional) -> collectible/reward adapter (optional)**. A producer may supply code-built scenes, rendered frames, animation, filmed footage, or external licensed clips. The video tool must not require LEGO, antifaFM, Kids Episodes, or any particular FoundUp; those are consumers/adapters. Rendering and provenance should be reusable across the FoundUps ecosystem, not reimplemented per channel. Keep existing Shorts FFmpeg/editor and headless orchestrator as candidate implementation owners pending interface audit; no new engine is authorized by this document.

Boundary contracts to prototype: `VideoBuildRequest` (source type, assets/scene refs, timing, output profile, rights, producer identity), `VideoBuildResult` (artifact digest, render provenance, media URI, quality/review status), `ProvenanceEnvelope` (canonical manifest, signer, signature, parent references, verification), `RewardEligibility` (separate, policy-driven opt-in). Provenance verification is independent of distribution, NFT status and any single hosting URL. Signed manifests bind exact bytes; robust watermarks only provide probabilistic derivative recognition. Avoid encrypting publicly playable videos by default: encryption/access control is a separate optional tool mode.

**Mall gamification candidate**: a FoundUps Mall discovery event may produce a *proposed* rare video collectible award after independently verified eligibility and anti-abuse checks. Rarity must come from a declared edition/supply policy and auditable issuance, not arbitrary hidden claims. Reserve a reward; offer explicit claim to a verified wallet; expire unclaimed reservations back to the pool with notice and an auditable receipt. A claimed token does not return merely for inactivity. Never automatically mint, transfer, or assign assets to a browsing visitor; consent, privacy, age restrictions, and wallet safety apply. Reward distribution is not a sales storefront and confers no DAE authority. Reuse existing pfMALL, UPS and token governance after their interface/rights audits.

**Reuse/duplication gate**: before implementation, inspect the existing Shorts editor/uploader, headless video orchestration, antifaFM modular visual schemas, EDUIT shared scene/movie renderer, pfMALL discovery/rewards and WSP_26/WSP_27 identity/token contracts. Reuse their owners; do not introduce duplicate rendering, wallet, authorization, metadata, reward ledger or publisher services. antifaFM is an optional video-tool client, never the canonical owner. Record precise interface gaps before creating any new module.
