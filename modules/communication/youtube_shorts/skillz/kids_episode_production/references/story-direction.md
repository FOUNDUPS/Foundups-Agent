# Direct an educational micro-story

Use before shot planning, and after creator corrections. Write a short observable
story contract, not hidden reasoning or a list of animation effects.

1. State the event in one sentence: because X changes, the character notices Y,
   acts Z, and the visible outcome differs. Identify the intended feeling and one
   learning objective. Distinguish fictional events from verified factual teaching.
2. Separate locked creator intent, negotiable staging, and unknown facts. Apply
   latest corrections over older drafts, without silently rewriting the stakes.
   Ask only when unresolved intent blocks the next concrete decision.
3. Sketch two compact staging options. Choose the one whose cause and consequence
   are clearest with the fewest characters, objects, cuts and words. Do not choose
   based only on what the current renderer already makes convenient.
4. Write a state table: time, cue, character location/pose, action, world change,
   visible evidence, sound and intended learner observation. Assign stable IDs,
   size relationships, ground plane and camera angle. Show travel, not teleporting.
5. Allocate 15 seconds to cue → decision/action → consequence/reveal. Three five-
   second clips are an editing boundary, not three disconnected ideas. Hold key
   cues and the final evidence long enough to read; speed up empty waiting first.
6. Check the counterfactual: if the character did nothing, would the outcome
   change? If not, do not imply its action caused success. Make the chosen path
   and relevant environmental constraint visible before the payoff.
7. Review a simple storyboard silently. Can a reviewer identify who noticed what,
   where they moved, what changed and why the result followed? Do not rely on
   captions or sound to conceal ambiguous geometry. Freeze a material palette and reuse each material color across intact, moving and final states. Check sampled pixels in actual rendered frames, not just color names. Reject inconsistent counts,
   unexplained scale changes, floating props and incomplete world-state changes.
8. Add original music/foley only after the event reads visually. Align each sound
   to its physical cause. For vocabulary learning, assign each target word a visible referent, synchronized sound and legible text window. Review whether a learner can match the word to the event, not merely whether a caption exists. Use the creator-approved vocabulary rather than incidental foley labels. Keep instructional cues intelligible; music supports
   attention and emotional timing. Do not imitate a named song's melody.
9. Turn the same observation/action into the optional game: cue → relevant input
   → visible consequence → gentle retry. Define one observable learning success
   separate from speed, and leave an untimed path. Do not infer ability from taps.
10. Render, inspect the actual transitions and listen to actual audio. Have an
    independent reviewer describe causality without supplying the intended answer.
    Inspect anticipation, contact, occlusion and reveal frames as well as playback. Give every affected character a visible response before occlusion; do not leave a living cast frozen while the environment changes. Preserve discrepancies and revise the responsible beat. Technical encoding
    checks and a written plan do not prove audience comprehension.

## Ordered output audits — run on every preview revision

Run these passes in order on the rendered outcome, not only the code. Keep each
pass bounded to the changed beat and its dependencies. Record PASS, FAIL or
UNVERIFIED with revision, timestamp/frame, observation and repair. If physics
fails, repair it before polishing typography. After a repair rerun that pass
and dependent passes; do not repeat unrelated repository suites per preview.

1. **Physics / causal staging:** establish support, gravity direction, contact,
   travel, collision and occlusion. Follow anticipation → contact → compression
   → release. A descending roof must visibly cover space and characters, not
   merely change their visibility. Explain what supports the surviving pocket.
   Stagger reactions plausibly by character and cue; arbitrary random timing is
   not physics. Show turns with solid intermediate poses rather than identity swaps or profile/front crossfades. Inspect the midpoint: blended faces can pass endpoint checks yet fail continuity.
   Use readable stylized mechanics; do not claim a geotechnical simulation or
   add a physics engine when the existing deterministic scene can express it.
2. **Continuity:** lock cast IDs, relative scale, geography, material colors,
   root/pocket geometry and camera. Compare before/during/after and shot joins.
   Check rendered pixels for material identity; account for codec variation.
   Verify the full affected chamber disappears with no residual floor or props.
3. **Education:** name one observable learning objective. For every learning
   event bind a stable event ID to its visible action, actual sound onset,
   displayed word and readable duration. For repeated actions, repeat the
   synchronized word at each occurrence. A sniff must show a nose/body sniff
   motion, its sound and SNIFF together; sound alone is insufficient. Distinguish
   sound-word association from spoken pronunciation, reading mastery or proven
   learning outcomes. Listen to the mix; sample/peak checks alone cannot pass
   auditory clarity. If listening is unavailable mark that subcheck UNVERIFIED.
4. **Art direction / readability:** place a large word near its cause (nose,
   fissure, impact) without covering the action, eyes or essential geography.
   Use a consistent readable font; vary weight, modest motion or shape only
   where it reinforces meaning. A crack-like treatment must not break letter
   recognition. Verify phone-size frames, contrast against each actual background, timing and safe margins. A support or foreground fix must be rechecked against every character below/behind it; solving one physical gap can obscure another learning object.
   Keep one visible text owner across scene/export/subtitles; avoid double-print.
   Recheck the whole scene silently, then sound+image together when available.

### Language-ready learning events

Keep event identity, timing, action anchor and sound reference separate from
locale text, font and optional spoken audio. English is the video prototype. Game display variants for English, Japanese,
Portuguese and Spanish are implemented; native-language and spoken-audio review
remain separate. Chinese and translated videos are future work. Onomatopoeia is language-specific: do not assume a
literal translation or the same spelling represents the natural local sound.
Test glyph coverage, line length and readability; use a defined English fallback
rather than claiming unsupported languages work. Reuse the existing episode
locale contract when implementing; do not build a second translation service.

### Fast creative loop and milestone integration

Preserve each meaningful revision and correction locally with its source/asset
identity. Preview → ordered audits → repair → preview is the creative loop.
Bundle software, skill and documentation changes into a PR at an agreed
milestone; do not push a new PR or broad CI run for every visual adjustment.
YouTube publication is a separate authorized media workflow, not a Git merge.
Changes to authentication, publishing or execution boundaries still require
appropriate review before use. Store successful corrections as candidate skill
improvements and test transfer on the next actual episode. This is a manual,
versioned contribution to RSI, not evidence of an installed autonomous worker.

## Little Shrew: correction-to-principle record

| Earlier limitation | Creator correction | Transferable rule |
|---|---|---|
| Generic waking/sniffing animation | Tremor wakes one small shrew | Give movement a visible cause |
| Oversized/extra shrew obscured roles | Two parents, three equally sized young; one active hero | Lock cast and size before rendering |
| Motion lacked a consequential destination | Hero shuffles to root pocket before impact | Establish geography and travel before payoff |
| Burrow remained visually legible after crushing | Chamber, floor and other figures disappear into uniform dark soil; only pocket remains | Recompute the whole affected world state |
| Foot/shape ambiguous | Side-view foot descends, lifts, leaves readable imprint | Reveal evidence of the event from a consistent camera |
| One generic impact noise | Stomp → crunch → squish tied to contact/compaction | Separate sound causes and synchronize them |
| Soil changed hue during collapse | Keep roof, floor and compacted earth the same dark brown | Bind material identity across state changes; verify rendered pixels |
| Family slept through an abrupt scene swap | Cracks travel with the falling roof; family wakes and starts moving before occlusion | Stage anticipation → reaction → occlusion → aftermath; inspect transitions, not only endpoints |
| Sound cue had no learning word | Show THUMP at the first shake | Pair the visible word with its actual sound onset; assign one text owner so scene and subtitles never double-print |
| Passive scene only | Tap shrew, then root, with retry | Derive interaction from the same causal sequence |

Latest Little Shrew direction is a fictional sole-survivor scene, not the older
family-escape draft. Preserve that authored choice; no visible injuries. Do not
infer that collapse/death is a template for every preschool story. Review tone
and emotional intensity for the audience; the current scene is not validated
for preschool comprehension. No claims of proven evolutionary ancestry.

## Required output before expensive production

Deliver: event sentence; one learning objective and observable success; locked
cast/world; chosen staging with alternative; timed state table; continuity/join
checks; sound/caption plan; unresolved facts; review questions. Label plan,
rendered, watched, listened, reviewed and published separately.

Retain each useful correction as failure → creator intent → general rule →
changed artifact → review result. Apply the candidate rule to the next actual episode in the current series before
claiming it transfers. A prompt update is not model training or autonomous RSI.

## Collaborative RSI / autoresearch cycle

Treat each material creator correction as an experiment candidate, not an order
to expand the skill indefinitely. Record the previous observable failure, creator
intent, proposed general rule, changed skill version, and expected improvement.
Keep story-specific facts in the series bible and reusable rules in this skill.
Do not copy family details, private correspondence or child data into learning
records. Apply this same separation to other workflows such as Gmail.

Before evaluation, freeze the baseline and rubric: causal clarity, spatial
continuity, objective/action correspondence, age-appropriate tone, timing, and
production cost. Compare baseline and candidate on the same bounded task, then
use the next actual story episode as the forward test, not an unrelated exercise.
Present the proposed next episode to 012 before rendering; distinguish the agent
proposal from accepted story canon. Preserve 012 feedback as the next iteration. Ask an independent reviewer to identify the event from the
output without the intended answer. Preserve failures as well as successes.
Reject regressions, ambiguous improvements and score-gaming; preserve the prior
version for rollback. Retain only independently supported improvements and check
them again on later real use. Do not add more rules when a clearer existing rule
would fix the failure. No paid experiment or external effect without its existing
budget/admission binding.

Use existing WRE measurement, pattern-memory and admission owners. Repository
`modules/infrastructure/wre_core/README.md` classifies current AutoResearcher
feedback as execution_feedback; independent held-out verification, rollback and
retained-generation evidence are separate requirements. The legacy recursive
learning interface generates proposals and apply_improvement currently fails
closed. Do not claim an automatic production loop merely by calling that API.
A manually versioned and tested skill is a bounded learning artifact; continual
execution needs the admitted WRE worker. No new scheduled ChatGPT scout.


### Video-to-game review correction — 2026-10-26

The world event must occur on its own timeline even when no input is given. Test
no action, partial success, full success, late action and retry against the same
scene. A game's alternative survivors do not rewrite the film's authored outcome.
Review captured feedback visually: sanitization must preserve safe local character
references. Keep child-facing play free of creator prose; use explicit review mode.
These are candidate improvements; next actual episode remains the transfer test.

For viewer/PWA feedback use [viewer iteration](viewer-iteration.md). Preserve
stylized depth: the approved parents-above/babies-below composition is not a
floating-body error solely because screen coordinates differ.
