# Oversight direct-navigation audit — 2026-11-09

Owner: existing `voteballots/oversight` workstream. Continuation: [PR #2328](https://github.com/FOUNDUPS/Foundups-Agent/pull/2328). Current architecture: [Oversight README](../README.md#phase-one-landing-contract). This is a source/change audit, not a publication receipt.

## Frozen scope

012 requested highlighted destinations only, plain connecting lines, a dotted independent-state branch, and removal of every repeated connector-label/"Why this connection?"/"Requirements" control. Retain House, Senate, evidence/legal review, money tracing, evidence testing, witnesses, authorized decisions and both independent outcomes. Reuse the existing renderer, release projection, test file, source records and PWA. Do not change DNS, the historical archive, legal authority or the Vote runtime.

## Baseline and repair

Pinned prior PR head: `6f35d7f5bfe41a43684a3777448bc8a021b3a74c`. CI run [42555559113](https://github.com/FOUNDUPS/Foundups-Agent/actions/runs/42555559113), job `128960346770`, reported 411 Vote passes and one public-release failure. The new Vote anchor matched the existing internal-brand content scanner. The release test hid the builder's stderr behind a subprocess exception.

The repair keeps that scanner and the archive/inventory gates intact. Only one exact approved Vote anchor is allowed in each root/web landing scan. Other paths, duplicate anchors, altered hosts, suffixes, query/path variants, internal markers and malformed bytes still fail. Release subprocess failures now expose stdout/stderr while still failing the test.

The renderer retains ten destination boxes and draws twelve plain paths in five decorative SVG rows; only the independent-state branch is dotted. Connectors have no text, link, focus stop or pointer interaction. Choice cards contain only the destination. Existing node IDs and old `edge-*` fragment screens remain, including fictional exhibits and counterevidence. Machine records and legal templates are not deleted.

## Executed checks and limits

- Extended `test_oversight_public_release.py`, after reading the existing test README and TestModLog. Local focused cases against exact Git-blob-verified source: **17 passed, 1 integration test deselected**. The deselected test requires the complete archive and public dataset; it is not claimed as a local pass.
- The same new focused cases against the prior renderer/builder: **16 failed, 1 passed, 1 deselected**, establishing that the added assertions detect the changed behavior.
- Hosted integration for source commit `bc95cb3fec2c7961f75c79ed93ed033b0c663b36`: CI run [42557479077](https://github.com/FOUNDUPS/Foundups-Agent/actions/runs/42557479077), job `128966321986`, completed successfully. Its Vote suite, preserved-source verification and Node contact/cache checks all completed successfully. This result does not cover later commits until their own checks finish. The repository-wide test job was still running when inspected.
- Chromium in-memory component checks at **320×740, 390×844, 768×1024 and 1366×900** passed direct destination navigation, keyboard entry, heading focus, legacy fragments, minimum 44px node targets and no horizontal overflow. The mobile layout viewport was explicitly set and checked. The 390px screenshot was visually inspected. This used the actual renderer/CSS/focus script with an explicitly synthetic graph, **not** the full staged release, production CSP, service-worker installation or Safari. An HTTP preview was blocked by administrator policy; no policy was changed.
- Fresh read-only public fetches still showed the older deployed landing. The Vote destination responded with its existing informational page. The official DOJ biography supported the already-recorded leadership identity; this UI slice does not alter the legal materials or claim misconduct.

Local renderer SHA-256: `a40d60945a8845a8e838c2141c0a6b96811499688576240e687bb9508f8a23d2`.
Local map CSS SHA-256: `66ff757eeeb4f2bdffa1ddfacb32fde677f1da84437bedba86a41aa6e7874ce3`.

## Remaining release gates

1. Fresh final-head CI, including archive, release build, Node worker and security checks.
2. Whole staged-site phone/desktop, accessibility, root/web offline and source-index review by a separate verifier. The component audit is not independent acceptance.
3. Reconcile and publish through the existing Sites project and source mirror, then verify actual deployed pages/aliases. No supported native Sites publishing capability or mirror checkout was available in this connector session; no replacement host was created.
4. Record the final commit, stage inventory and publication receipt in the existing release accounting. Historical deployment observations remain historical.

WSP_00, WSP_97, WSP_91 and the repository/test instructions were read. Local WSP_00 bootstrap/strict tracker and HoloIndex were **not executed** because the full runtime checkout was unavailable. Direct pinned GitHub source and hosted CI supplied the bounded evidence. WSP_91's observability purpose is served here by explicit build diagnostics and revision-bound records; no new daemon or telemetry service is created. No claim of full WSP compliance, merge, legal adoption or live deployment follows from these checks.
