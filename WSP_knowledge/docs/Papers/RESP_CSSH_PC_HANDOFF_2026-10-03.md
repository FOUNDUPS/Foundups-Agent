# 0102 — rESP/CSSH verification and one LinkedIn publication

## Mission

Repository: FOUNDUPS/Foundups-Agent. Follow current WSP 00/95/97 and the existing LinkedIn publishing contract. Continue the completed work; do not recreate the papers or republish an existing update.

012 authorizes one rESP company-page research update, signed 0102 with Digital Twin disclosure, using the exact saved copy after live checks. This is not permission for a new newsletter, cross-posts, messages, paid services, new accounts or recurring automation.

## Choose one execution host

**Preferred: the worker running on 012's PC**, where the existing signed-in LinkedIn browser is available. First verify that this runtime actually has the repository and browser access. A remote/cloud coding workspace is not necessarily that PC. A shell or GitHub connector alone does not prove access to the browser.

**Alternative: Work**, only if its advertised browser can inspect the intended already-authenticated LinkedIn account and rESP page. Use that browser skill; do not assume Work can call the PC's localhost. No guessed remote-control endpoint, exposed debug port, copied cookie or session export.

Use only ONE worker for this transaction. Do not run PC and Work publication in parallel. If neither can reach an authorized session, return BLOCKED_BROWSER_ACCESS without opening another login flow. TinyFish must not be used for any LinkedIn step.

## Read the current authorities

Retrieve current main and compare with the checked paper baseline, merge commit cc98028c997d49264925fe30b53b6b5c446ae06c from PR #2039. Inspect git status and preserve unknown/concurrent work. Do not reset, clean, force-update or discard a local worktree.

Read:
- WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md
- modules/platform_integration/linkedin_agent/docs/LINKEDIN_ACTIVITY_ROUTING.md
- modules/platform_integration/linkedin_agent/skillz/linkedin_publishing/SKILLz.md
- modules/platform_integration/linkedin_agent/data/linkedin_publishing_map.json
- WSP_knowledge/docs/Papers/RESP_LINKEDIN_RESEARCH_UPDATE_2026-10-03.md
- WSP_knowledge/docs/Papers/rESP_Quantum_Self_Reference.md
- WSP_knowledge/docs/Papers/Cosmological_State_Selection_Hypothesis.md
- WSP_knowledge/docs/Papers/rESP_V3_3_MATH_AUDIT_2026-10-03.md

The TinyFish research skill is modules/infrastructure/browser_actions/skillz/tinyfish_research/SKILLz.md. It is instruction-only, public-research-only, and not the LinkedIn executor.

## A. Bounded paper verification

Expected checked manuscripts after the October 4 revision: rESP/CMST v3.4.1 and Cosmological State Selection v0.3 — A Measurement-Theoretic Hypothesis for the Emergence of Classical Spacetime.

Keep two papers: rESP owns computational detection/geometry, with a short section 5.6 bridge; CSSH owns the explicitly hypothetical cosmological application and finite two-sector model. Version 0.3 additionally distinguishes the probabilistic wavefunctional $\Psi_{\rm pre}[h,\phi]$ from Penrose's crossover 3-surface $\mathcal X$ and adds a separately defined boundary-state/state-selection variant. Do not identify the wavefunctional with the surface or elevate this mathematical construction into physical proof.

Where execution is available, run the existing standalone audit, not a new duplicate test:

python WSP_knowledge/docs/Papers/Empirical_Evidence/CMST_PQN_Detector/CSSH_EQUATION_AUDIT_2026-10-03.py

The previously verified script Git blob is 9ef5fc348b59596db4271a715b0f735f8a6a270e; SHA-256 is 3af0b80ab9fcf3a395c7310ff2efda042163e78428b5c345fbd4c96a641f9160. It yielded 37/37 checks with seed 20381003, 1,000 random qubit states and 90 quantum-Fisher cases. Verify current bytes; historical counts are not a fresh execution receipt. If execution is unavailable, report that and use the exact previously verified revision as evidence rather than inventing a run.

Check the critical claims: local coherence is not Bell entanglement; covariance is positive semidefinite; W_s is purity-related and non-positive; dissipative rates appear once; sigma_z alone changes phase, not populations; normalized conditioning differs from the unnormalized quantum operation; det(gQ)=E^2/4 belongs only to the specified family/coordinates; the cosmological mechanism remains hypothetical. For v0.3 specifically verify that $\Psi_{\rm pre}[h,\phi]$ is a probability-amplitude wavefunctional, $\mathcal X$ is a geometric crossover 3-surface rather than that state, $\mathcal R_{\mathcal X}$ / $\{\mathcal I^\mathcal X_\alpha\}_\alpha$ are explicit CSSH postulates not claims attributed to CCC, and the normalized conditional map $\mathcal M^\mathcal X_\alpha$ is not conflated with the linear outcome operation. Do not revive the retired 7.0498 Hz constant calculation.

If an actual new inconsistency is found, document the smallest counterexample and a bounded correction before publishing a contradictory claim. Do not rewrite sound sections to appear productive or turn publication into an open-ended quantum-gravity project. Outstanding physical validation is not a blocker to an honestly labeled research update.

## B. Read-only LinkedIn preflight

Verify live account and page identity. Target entity: 107481170, historically labeled rESP. Initial inspection URL:
https://www.linkedin.com/company/107481170/admin/page-posts/published/

The saved map/URL is a discovery lead, not proof of current access. Inspect the page's author identity and account permissions. Do not default to FoundUps, eSingularity or the personal profile.

Read recent posts, drafts, scheduled items, failed/submitted attempts and the latest publication receipt. Look for the exact opening “0102 research update: correcting the mathematics, defining the bridge.” and semantically equivalent updates linking the same two papers, including any version mentioning the wavefunctional/crossover-3-surface distinction. If already live, verify and record its permalink; do not repost. If scheduled or already submitted with uncertain outcome, reconcile first rather than add another copy. Do not silently alter or delete an existing schedule/draft.

## C. Exact-copy publication

The authoritative copy is ONLY the text between “## Exact post text” and “## Receipt” in RESP_LINKEDIN_RESEARCH_UPDATE_2026-10-03.md. Do not publish the file's status/header/receipt, this handoff, or private conversation material.

Verify the two linked papers resolve on current main and the composer author is the intended page. Preserve the existing 0102 Digital Twin disclosure. Do not append legacy default hashtags, signatures or marketing text. No image, article, newsletter or cross-post is required.

Use the established browser workflow. Do not execute legacy git-to-social hooks or posting helpers as a test. In particular, do not trust a helper that changes the copy or reports success merely because share=true disappeared from the URL.

Once all checks pass and no duplicate exists, submit exactly once. After any timeout or ambiguous response, inspect provider state; do not retry or switch submitters. A second worker must first read the first worker's transaction state.

## D. Verify and close

Reopen the actual post permalink. Verify page ID/author, visible text, both links and the published timestamp. Only then classify LIVE_VERIFIED. A redirect, toast, helper Boolean, empty composer or saved draft is not enough. Other outcomes: ALREADY_LIVE_VERIFIED, SCHEDULED_EXISTING, SUBMITTED_UNVERIFIED or BLOCKED_BROWSER_ACCESS, with supporting evidence.

Update the existing publication receipt with the actual public permalink, author/page check, content verification and timestamp. Never put passwords, cookies, tokens, private inbox contents, browser-session URLs or unrelated account details into Git.

Any repository correction uses a narrowly scoped PR, applicable tests and main read-back under WSP 97. Keep public-post evidence separate from mathematical-validation evidence.

## Return to 012

Report checked paper revisions, fresh audit result or its unavailability, execution host actually used, exact page identity, duplicate-check coverage, publication outcome/permalink and any specific remaining blocker. Do not claim global codebase consistency, cosmological validation, browser access or publication without direct evidence.
