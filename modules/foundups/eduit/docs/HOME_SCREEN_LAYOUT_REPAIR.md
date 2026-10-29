# Home Screen layout repair — 2026-10-26 JST

## Evidence and cause boundary

012 supplied an installed-iPhone screenshot: tiny external controls, large unused
space, no per-panel expand buttons. The deployed root was a meta-refresh page
without viewport or manifest. This is an observed entry-point defect consistent
with desktop-width launch scaling; exact iOS internal cause is not proven.
Testing only `/review/director` had missed the actual launch document.

## Implemented scope

- `storytime_site.mount_storytime_root` projects the same Shorts-owned viewer
  into root with viewport, manifest and correctly resolved module/media paths.
- `build_site.py --storytime-root` explicitly selects this standalone projection;
  default EDUIT build and shared Mall owners are preserved. No duplicate UI owner.
- Both panel shells own48px expand/collapse buttons. Video stays contained; game
  iframe, captured scene and annotation canvas share a single aspect-ratio surface.
- CSS viewport focus works without browser-native fullscreen permission, including
  the installed web-app surface. Safe-area insets and visualViewport resize data
  keep expanded surfaces within the available viewport after rotation.
- Game timing pauses on expand/collapse and viewport changes. Expanded game keeps
  Play/Feedback controls; feedback returns to the combined page before drawing.
- Existing Mall gestureZone remains owner. Small adapter also handles iOS WebKit
  gesturestart/change/end; two-finger gestures suppress accidental rescue clicks.
- Pinch-out expands, pinch-in collapses. Explicit controls and Escape remain
  available; inert background/focus restoration keeps keyboard input on the panel.
- Worker v2 caches the root and new input adapter under the existing bounded
  allowlist. Media and rescue mechanics are unchanged. No new YouTube upload.

## Checks and limits

Fourteen Node checks cover game, locale, PWA, gesture callback bounds/cancellation,
root projection and the actual standalone CLI using a fake-media packaging fixture.
The fixture does not claim to render or review video. Browser viewport harness
exercised390x844,844x390,768x1024 and1024x768; panel buttons remain48px and no
horizontal overflow was observed. Expanded game surface maintained16:9 after
rotation; explicit video/game collapse returns to the combined view.

Independent review caught a missing CLI flag declaration and missing resize pause;
repaired before publication. Actual iPhone Home Screen launch, native WebKit touch
delivery and nonzero hardware safe-area values remain unverified in this browser.
Do not present viewport simulation or event tests as physical-device acceptance.
The real follow-up check is to reopen the existing saved app after deployment.

## WSP/RSI lesson

Audit every entry path: site root, manifest start URL and existing installed
shortcut, not just the inner review page. Keep per-panel actions spatially bound
to their content. Preserve a single layout source and put standalone projection
in the existing builder. Proposed learning is recorded here, not autonomous model
training or a WRE activation. WSP15 priority is fixing launch/input correctness
before adding episodes, gestures or decorative filler.


## Applied skill receipt — same milestone, not a new implementation lane

Canonical skill: `youtube_shorts/skillz/kids_episode_production/SKILLz.md` v0.2.4
and `references/viewer-iteration.md`, under the existing production skill.
The earlier gap was incomplete viewer routing plus stale perspective notes;
those are corrected rather than creating a second skill/module/registry owner.

| Skill check | Evidence / result |
|---|---|
| Retrieve before edit | EDUIT architecture/interface/deployment and actual launch/viewer/worker/Mall code read; governed lexical receipt UNKNOWN/index gap retained |
| Lock approved story | No diff in engine, scene, rig, learning-events or MP4; original15s media retained |
| Reproduce entry path | Old root meta-refresh lacked viewport; root projection test and live browser harness exercise root, not only inner route |
| Physics/causality | Game pauses during focus/resize; fixed world timeline regression checks pass;14 tests total |
| Continuity | Same16:9 scene and normalized whiteboard surface; media identity unchanged |
| Education | Existing words/audio/locale mappings unchanged; panel controls overlay safe corners rather than replacing labels |
| Art/readability |48px controls at390x844 and tablet bounds; no observed horizontal overflow; source screenshot retained by012 |
| Independent repair | CLI flag and resize pause findings repaired; keyboard background made inert; final recheck required before merge |
| Bound claims | Browser/event proofs separate from actual iOS Home Screen/native touch; listening not rerun for unchanged audio |
| Milestone closure | One PR covers source, evidence and skill corrections; merge/deploy receipts recorded separately |

Scope rubric (engineering judgment, not WSP15 priority score): launch-path
coverage, spatially bound controls and callback/rotation recovery are the three
criteria. Baseline screenshot/source FAIL; candidate browser checks PASS.
Physical-device acceptance stays UNVERIFIED, so no overall perfect rating or
claim of proven iOS behavior. No autonomous RSI promotion or learning-outcome claim.


## Current diagnostic grades and autonomous findings

Rubric: viewer-iteration v0.2.4. These engineering judgments were introduced
as a diagnostic after the current repair, not a preregistered improvement study.
Freeze them for the next iteration; do not claim a measured learning effect.

| Criterion | Current scoped grade | Evidence / remaining gap |
|---|---|---|
| Launch/fit |4/5 browser scope | Direct live root and four viewport dimensions checked; actual installed iOS acceptance UNVERIFIED |
| Panel entry/exit |3/5 | Both live units fill viewport and return;48px controls; keyboard Escape/focus and real-device safe areas need explicit acceptance |
| Input parity |3/5 | Mouse and gesture callback/cancellation checks pass; native iOS touch delivery UNVERIFIED |
| State/feedback continuity |3/5 | Source/test pause and normalized canvas retained; installed-device resume/marks after rotation need acceptance |
| Educational readability |3/5 | Scene/words/media identities unchanged; direct word/control overlap checks in the new expanded layout remain needed |

No overall average, completion percentage or physical-iPhone PASS is assigned.
No speculative new code is justified solely to raise an unverified device score.
Independent reviewer confirmed14 checks, ownership and repaired findings; merge
and deployment receipts remain separate evidence.

Autonomous inspection caught the missing builder CLI option, missing timer pause
on viewport resize, off-panel keyboard focus and accidental rescue taps during
pinch. Those were repaired without waiting for012 to identify each defect.
The source audit also found stale perspective notes and a missing viewer route
in the skill. This is a manually governed contribution to RSI, not an installed
autonomous production line. Next actual episode remains the forward test.


Independent score review: `/root/touch_review` evaluated local source8bacd37a
(tree19c5bd002cf20da41358764bd62a13303f34590b), confirmed14/14 source checks,
and requested lowering panel-entry and educational-readability grades because
source invariants alone do not prove keyboard or visual cue acceptance. Those
corrections are retained above. This identifies a reviewed source tree, not an
authenticated WRE reviewer or automatic skill-promotion receipt.
