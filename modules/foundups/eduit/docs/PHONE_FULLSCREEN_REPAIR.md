# Phone fullscreen repair — 2026-10-29 JST

## Baseline and scope
Repository main e5c700714f2ea73c251141f6377032d02da49610; published Site v12
4673a3110e7c1cdb1c6440f9545a0b80a805761d. Compare working Site v11
78904c8125350a06019222c6d0c41c7ba706846d. Audit issue #2252 is the retained
failure register. The earlier audit changed no live source; its findings were
still present when012 reported off-screen fullscreen entry again.

SOURCE-COMPARED: viewport sizing, resize/orientation listeners, safe-area metadata,
manifest identity and pinch adapter were retained in v12. There is no device-name
or iPhone-model detector to restore. The regressed CSS overrode responsive button
sizes, exposed both rails while marking, and reserved112px for captions even in
short landscape. The old viewport helper tracked width/height only; it did not
track visualViewport offsets or scroll. That is an existing robustness gap, not
proof of the physical iPhone failure's exact cause.

Only the Shorts-owned viewer layout/controller and UI cache version change here.
Film, scene/rig/cast, game/learning/replay logic, gesture implementation, manifest,
install ID/start URL/scope/icons, feedback namespace and stored records are locked.
Narration timing/replay/localization defects and the cached-version upgrade risk
in #2252 remain separate, open work; this does not claim to close that whole issue.

## Frozen acceptance and decision
Criteria reuse TILE_PRODUCTION_RSI: phone_tablet_controls, fullscreen_feedback,
touch_mouse_keyboard, launch_integration and continuity. Minimum64px on every
visible primary/annotation/exit target; no overlap or clipped/hit-blocked controls;
one rail in marking mode;16:9 scene; landscape video height at least60% of usable
viewport; both root and manifest start entry. Test320×568,390×844,568×320,844×390,
768×1024,1024×768 plus explicit safe-area fixtures. Native delivery is separate.

WSP15 allocation C2/I4/D4/Impact4=14/P1. Need: primary phone interaction regressed.
Affordable: repair existing CSS/controller instead of building a new device or
fullscreen subsystem. Cannot leave these reproducible primary-control defects.
Execution plane: local authoring, independent development review; no WRE/model
admission/activation. Governed lexical Holo at e5c7007 reported UNKNOWN freshness
and index gap; direct exact-source inspection supplied evidence. WSP00 invocation
failed missing torch; cached tracker state is not a new detector witness.

## Repair and evaluation cycles
1. **Reject baseline:** new browser oracle rejects published v12 at320×568 because
   its exit measures60px. Earlier audit also retained two visible whiteboard rails
   and568×320 video192×108. These failures are not erased by26 passing Node tests.
2. **One layout owner:** remove scattered expanded selectors; define one grid with
   an aspect-preserving scene, one state-specific rail, separately sized exit and
   safe-area padding. At narrow width game and annotation controls each use their
   own two-row layout; marking explicitly hides gameplay controls.
3. **Landscape:** place narrative beside the video on short landscape, retain it
   below in portrait. Controls keep CSS dimensions independent of art. At568×320
   the candidate video is384×216 without injected insets (v12 was192×108; v11
   398×224). With left/right32px and bottom16px fixtures it is356×200.25. Do not
   confuse that injected-inset comparison with a physical phone measurement.
4. **Viewport:** at normal zoom follow width/height AND offsetLeft/offsetTop;
   recalculate on visual viewport scroll/resize, orientation, pageshow and return
   to foreground. Changed bounds pause video and game; no automatic resume. When
   browser zoom is active, retain layout viewport and zero adapter offsets so
   ordinary page zoom remains available outside panel gestures.
5. **Recheck:**29 Node tests pass, including3 direct controller-viewport cases.
   The browser matrix passes296 checks for both entries/six sizes, including actual
   element bounds and elementFromPoint control hit tests. Retained35-check suite
   passes at390×844: drawing/Undo/Clear, frozen frame and saved marks through
   rotation, snapshot preparation, switch, practice/reset, repeat and child lock.
   Initial retained-suite attempt clicked before iframe API readiness; fixture
   reports that failure and now waits boundedly for readiness, without a production
   sleep. No application defect is inferred from that fixture race.
6. **Independent second pass:** reviewer requested real long-caption/picture and
   body-overlay coverage. Added12 actual paused cue-frame overflow checks and4
   options/unlock tests using a350×600 viewport at offset(20,80). Body-owned
   options/unlock now follow the same coordinates. Expanded296 checks pass.
   Reviewer accepted bounded source/state repair4/5; native coverage remains3/5.

The acceptance code deliberately checks useful image size and every visible
control, not merely a full-viewport outer box. Programmatic clicks and synthetic
pointers are identified as handler/state evidence; pointer-center hit tests add
reachability evidence but do not establish physical touch delivery.

## Independent review and grades
Independent reviewer fullscreen_audit reviews raw diff/controller tests and the
fixed acceptance criteria. Final findings and exact-source CI/publication receipts
belong in the milestone PR. No author-written receipt is runtime promotion proof.
Scoped grades after browser checks: phone layout4/5; fullscreen feedback4/5;
controller recovery4/5. Native iPhone/iPad Home Screen, real safe-area/keyboard
behavior, pinch delivery, OS Photos targets and actual narration audio remain
UNVERIFIED (input/platform coverage3/5). No aggregate or perfect rating.

## Retained RSI rule and remaining gates
Update existing interactive_experience_review candidate with deployed-baseline
comparison, negative control, useful scene-area floor, every-control bounds,
mutually exclusive rails and nonzero viewport-offset coverage. Forward-test on
next actual tile; this is a governed correction loop, not autonomous training or
an installed worker. Keep issue2252 open for other findings.

A new UI cache version advertises this asset set; install identity is unchanged.
Old clients may still wait for a new worker. Do not advise reinstalling or claim
an installed-upgrade pass without actual device evidence. Publication requires
PR checks, squash merge, exact-main checks, Site deploy and live root/inner smoke
checks separately. Baseline rollback is Site version12.

Official viewport semantics: https://developer.mozilla.org/en-US/docs/Web/API/VisualViewport
