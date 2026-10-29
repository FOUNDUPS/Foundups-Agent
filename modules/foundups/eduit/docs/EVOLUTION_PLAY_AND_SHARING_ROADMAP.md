# Storytime: evolution play, replay and sharing

2026-10-28 JST. Latest 012 direction; complements
[SLOW_RESCUE_AND_AGENT_ROADMAP](SLOW_RESCUE_AND_AGENT_ROADMAP.md).
This file specifies the next product layers. It does **not** activate models,
recording, public uploads, accounts, quotas, membership or genetic simulation.
The existing green vine remains the destination; current cast/art and rescue
mechanics remain the mechanical reference until separately reviewed changes.

## Stages and current priority

| Stage | Deliverable | Exit evidence |
|---|---|---|
| Mechanical proof of concept | Video above game, clear Watch/Play/About/How navigation, short story line, touch/mouse/fullscreen controls and visible rescue score | Existing game remains playable; responsive bounds and state continuity inspected; no false AI/upload claim |
| AI prototype | Optional bounded per-creature policy, environmental needs, repeatable trait variation, learning experiments and five-mission sets | Actual model inference/status/failure fallback on supported devices; deterministic baseline and withheld-seed comparison; reviewed missions and generation explanation |
| Membership MVP | Adult-owned accounts, replay publishing, generated public aliases and server-enforced posting allowance | Authenticated entitlement, quota/idempotency/abuse/deletion tests, approved replay with verified channel, parent preview and explicit publication |

Do not build a parallel Mall, renderer, uploader or learning database. EDUIT is
the education sleeve; Storytime is its content experience. Extend current EDUIT
engine/scene and Shorts rendering/publishing owners. Existing WRE owns future
admission and RSI; a design document is not a worker. Implement the smallest
accepted layer, inspect it, retain defects/repairs, and promote only after review.

## Short educational framing

Child-facing opening: **“Long ago, tiny animals hid underground.”**
Immediate objective: notice a change, wake a creature, guide it to safety.
Post-game first lesson: **“You noticed. You helped!”**
Future inheritance lesson: **“Babies can be like their parents—and different.”**
Future learning lesson: **“Practice can help us learn.”**

These are proposed simple prompts for ages 3–4, not validated comprehension
claims. Keep detailed science in grown-up About/How; test with the intended age
before asserting learning efficacy. Do not infer age, intelligence or aptitude
from tap count, speed or score. A parent can later choose an explanation level;
no age collection is required for this proof of concept.

The shrews are fictional shrew-like mammals, not an identified direct human
ancestor. Avoid “you lived underground,” which would confuse an individual with
ancestry. Evolution branches across generations; it is not a ladder ending in
humans. Rescue, individual learning and inherited evolutionary change must be
presented as different processes. Survival in one mission alone is not a measure
of reproductive success or biological fitness.

## Proposed five-mission family set

SPECIFIED_NOT_IMPLEMENTED. One set comprises five **released, reviewed** missions;
there is currently one playable rescue, not a five-level campaign. Flooding is a
next-scene proposal, not a working Next destination. Each mission must establish
a visible cause, opportunity to respond, consequence and safe retry/practice path.

- Create a bounded seeded family profile when a **new set** begins. Preserve its
  seed, trait values, mission state and revision across pause, resize, reload and
  retry. “Random every load” would permit rerolling and break learning continuity;
  interpret that direction as a new-family action between sets. Versioned local
  saves need bounds, validation, delete/reset and migration before implementation.
- Parents' inherited profiles are fixed throughout the set. This is a gameplay
  rule, not a claim that parents or older animals cannot learn. Current slower
  parent travel and wake taps are authored fiction, not measured shrew biology.
- Earn points for completed rescues, not repeated tapping. Maintain the current
  base award and bounded speed bonus until balancing evidence supports a change.
  Keep untimed practice and distinguish earned score from learning success.
- Only after completing the set may points enable the **next generation/family**.
  Preserve 012's proposed automatic, seeded allocation instead of a child-facing
  shopping interface. It may select bounded fictional offspring trait variants;
  it must not rewrite the rescued animals' genes or turn memories into genes.
- Treat this allocation as a game progression rule. Real mutations do not occur
  because an animal earns points or needs a trait. Inheritance/variation and
  environment-dependent selection require their own explicit simulation model.
  No cash value, purchases, trade market or universal “better genes” claim.
- Any new-generation roll is committed once per completed set, reproducible from
  its seed and receipt. Reload/retry cannot grant duplicate points or reroll it.
  No midpoint spending or silently changing traits to rescue a failed mission.

Suggested simple labels: **Move**, **Notice**, **Remember**. They are pedagogical
labels for a game model, not three real genetic markers. Move concerns movement
pace; Notice concerns cue response. Remember represents learned policy/state,
not inherited factual knowledge. Actual limb growth is developmental and must
not be presented as synonymous with running speed. Keep tradeoffs explicit:
faster movement may need more energy; stronger caution may delay movement.
No trait is universally best in every environment.

## Creature behaviour and optional AI

Reuse the proposed observe → propose → validate → advance seam. The deterministic
engine owns time, hazards, legal actions, travel and scores. Each creature can
have its own state and policy while sharing one model worker. Keep three layers:

1. Stable fictional inherited profile: bounded pace, cue sensitivity and other
   reviewed tendencies, fixed for the current family/set.
2. Changing needs: fatigue, hunger, fear, curiosity and perceived hazard. A tap
   can cause a wake/look/sniff response followed by dozing; the response must be
   visible and repeatable enough for a child to understand.
3. Learned policy/memory: prior synthetic experiences, confidence and chosen
   actions, kept separate from genes and from the child's play record.

Increasing thumps, moving roots, progressive cracks and falling dirt provide
bounded observations to the policy, not arbitrary browser access. A loud cue may
raise perceived danger; fear can freeze or prompt escape according to a tested
profile. Compare scripted behaviours with a small-model candidate before paying
its latency, download and battery cost. Do not call scripted autonomy connected
AI. Show AI ready only after real load and bounded inference; unavailable/failed
models retain the manual fallback. No hidden cloud fallback or child telemetry.
Evaluate policy changes on synthetic traces with held-out seeds and rollback;
use the next actual episode for transfer evidence. Model self-rating is advisory.

## Replay above the game and YouTube sharing

The current top panel is an authored film. It is **not** a recording of the round.
Future explicit capture records a bounded event trace with episode/revision,
seed, locale, legal actions and simulation times. Replay the shared scene, then
render through the existing Shorts owner. Derive score from validated replay;
never trust a client-submitted score, arbitrary video, HTML, script or URL. A
simple animation recorder is not automatically a complete audio/video pipeline.
Retain exact media hash, timing, sound rights, review and render provenance.

Proposed adult flow: finish → preview replay → request posting → reviewed queue →
verified upload → returned video link. Do not show a working “Post” control until
that entire path exists. Keep child play separate from adult account/commerce.
Generated aliases replace free-form public names, but are pseudonyms, not proof
that all personal data has been eliminated. Default captures contain only game
art/audio/score: no camera, microphone, child face/name, drawings or free text.

Reuse `modules/communication/youtube_shorts/src/youtube_uploader.py` and hardened
`modules/platform_integration/youtube_auth/` as described in
[Kids local production](../../../communication/youtube_shorts/docs/KIDS_LOCAL_PRODUCTION.md).
Resolve the `us_story_time` role through existing host configuration; verify
`channels.list(mine=True)` matches the configured channel pin. The browser must
never receive the channel OAuth access/refresh token or client secret. Only the
server-held, bounded publishing job can invoke the publisher. Require explicit
privacy status, made-for-kids setting and separately assessed synthetic-media
setting. Start private/unlisted for review under the existing production skill.

“One free post, sign up for more” is a proposed allowance, not a working service.
A browser flag cannot enforce one post per person and must not be sold as such.
Choose an adult-owned account quota before public rollout; a device-local trial
would be resettable and must be described honestly. Do not add fingerprinting to
solve this. Before enabling the queue, require authenticated authorisation,
rate/resource limits, server reservation/settlement, idempotency across retries,
moderation, bounded metadata/aliases, cancellation and deletion/withdrawal.
Payments and extra quota belong to the existing entitlement/account plane.

YouTube made-for-kids videos do not provide comments, cards/end screens or channel
memberships. Website membership is a separate proposed product, not YouTube
channel membership. A generated alias does not by itself resolve children's
privacy obligations; future identifiable or persistent records need a defined
parental-consent, retention and deletion design before collection.

## EDUIT history and evidence labels

OBSERVED_REPOSITORY: existing EDUIT historical audit records a 2001 initiative
and a 2007 mission/presentation, followed by later adaptive-game proposals:
[historical lineage](../../../../docs/audits/pfmall_eduit/EDUIT_DISCOVERY_HISTORICAL_LINEAGE_2026-10-08.md).
CREATOR_RECOLLECTION: in this session 012 places first promotion in **2004**.
Retain this claim with attribution; no dated 2004 artifact was verified here.
Do not quietly replace established records or publish “first promoted in 2004”
as independently established fact. Public About can describe the monk's
long-running EDUIT vision without claiming an unverified first date.

## Source observations — read 2026-10-28 JST

Text/metadata inspected; no media watched, model run or platform upload performed.

- UC Berkeley, [misconceptions about evolution](https://evolution.berkeley.edu/teach-evolution/misconceptions-about-evolution/): populations evolve, lifetime change differs; no inevitable progress ladder; traits depend on environment.
- Smithsonian, [human evolution FAQ](https://humanorigins.si.edu/education/frequently-asked-questions): branching common ancestry, not modern species transforming directly into humans.
- NIA, [10 common misconceptions about aging](https://www.nia.nih.gov/health/healthy-aging/10-common-misconceptions-about-aging), dated 2024-04-10: older adults can learn new skills and memories. This is human evidence, not a shrew-specific parameter source; it rejects a blanket age stereotype, not a quantitative game model.
- YouTube, [videos.insert](https://developers.google.com/youtube/data/reference/rest/v3/videos/insert?hl=en): authenticated upload and explicit privacy/audience/synthetic-media fields. This design requires explicit private/unlisted review regardless of provider defaults.
- YouTube, [audience settings](https://support.google.com/youtube/answer/9527654?hl=en): made-for-kids feature restrictions. API capability is established by the API reference; the Help page also retains older transitional API wording.
- Google, [server OAuth](https://developers.google.com/youtube/data/guides/auth/server-side-web-apps): protect persistent credentials; keep client secrets outside source control.
- FTC, [COPPA FAQ](https://www.ftc.gov/business-guidance/resources/complying-coppa-frequently-asked-questions): persistent identifiers may be personal information. This architecture is not a compliance certification.
