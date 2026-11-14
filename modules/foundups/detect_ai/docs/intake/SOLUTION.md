# AmIBot - Solution Definition

## Core Solution
A mobile-friendly browser game with a neutral chat surface. Before joining, participants know their partner may be human or AI and consent to the game. The server holds the assignment, runs a short text conversation, accepts a locked verdict plus probability, then reveals the assigned class and approved model configuration. Participation scores and three separate leaderboard families support learning and comparison.

## Key Capabilities
1. Human participant vs an undisclosed human-controlled or AI partner.
2. Human detector and registered agent-detector tracks, with separate live-interaction and transcript-only results.
3. Versioned conversational-model comparisons, including small open checkpoints, approved frontier services, and Red Dog configurations.
4. Server-authoritative scoring, provisional practice points, moderated accounts and fraud-resistant ranked play.
5. Separate, revocable permission for evaluation reuse, model training, and public transcript publication.

## Differentiation
Human or Not already implements the central game. Our proposed distinction is the combination of small-model quality/cost comparisons, agent judges, reproducible conditions, FoundUps contribution governance, and a Red Dog behavior-evaluation loop. This is a product hypothesis, not a claim that no competitor offers any component.

## Technical Approach
Build the product experience in `modules/foundups/detect_ai`. Reuse existing platform authentication, the AI gateway, WRE, evaluation and ledger owners only after their actual interfaces are inspected. Do not create a competing orchestrator or assume a catalog-discovery module can execute inference.

Proposed application services: match/round coordinator; server-only assignment store; message relay and moderation; approved model adapter; verdict/scoring service; separate leaderboard projections; consent/export service. These are logical responsibilities, not a demand for seven deployments. One small service is enough for the POC.

Flow: consent -> join -> server randomization -> matched chat -> locked verdict/confidence -> reveal -> score -> optional explanation -> rematch. Use 120 seconds as the initial declared conversation window, starting only when both endpoints are ready. Permit early verdict lock without revealing truth to an active partner. Exact timeout and disconnect handling must be tested.

Start with an independently sampled 50/50 target assignment for each focal round. A missing human must not be secretly replaced by AI. Offer waiting or clearly labeled AI practice; exclude practice from the randomized benchmark. Record all assignments and attrition, not only completed games. Human partner recruitment and judge sampling are documented separately.

## Browser vs Discord Decision
Browser-first. A public landing can explain the game without an account; the POC gates actual play with invites. Use Discord to recruit synchronized pilot cohorts and later optionally wrap the web app as an Activity. Do not use ordinary bot-tagged messages as a blinded experimental interface. One backend and scoring authority serve both surfaces.

## POC -> Prototype -> MVP
POC proves actual human/AI round handling, truth isolation and score integrity. Prototype adds multi-model comparisons, agent judges, ranked identities and consented exports. MVP adds public operation, durable moderation, published methodology and approved reward integration. See POC_SCOPE and PROTOTYPE_GATE; none is implemented by this intake.

## Reward Design Boundary
Keep practice XP, statistical skill scores and economic rewards separate. Free POC points have no transferability or promised token conversion. A later authorized reward adapter submits verified contribution evidence to existing FoundUps governance/ledger owners. Rate limits, duplicate prevention, independent verification, a funded budget, disputes and applicable review precede activation. No token symbol, supply or price is assigned here.

## AmIBot technical decision - chat, PWA and content modes

Use [CHAT_PWA_SAFETY_RESEARCH.md](../CHAT_PWA_SAFETY_RESEARCH.md) as the current technical selection record. Recommend Socket.IO plus a minimal application-specific round coordinator, rather than adopting an unsupported random-chat application or introducing both Socket.IO and Colyseus. Reuse a suitable existing transport/auth owner if preflight proves one; no integration compatibility is certified here.

The browser/PWA runs the interface. The trusted server owns login admission, queue policy, assignment, moderation, clocks, verdicts and scores; one approved small model runs behind the existing inference boundary. The POC has only clean-chat adult participants and mandatory safety controls. Mature/NSFW access is a separate, disabled future queue with age-assurance and jurisdiction/provider gates. A later local-model practice mode is opt-in and excluded from verified rankings.
