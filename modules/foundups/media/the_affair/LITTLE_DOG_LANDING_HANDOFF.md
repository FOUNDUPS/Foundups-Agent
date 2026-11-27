# Little Dog Handoff — Huang Affair Landing Layer

```yaml
schema: 0102_m2m_v1
SENDER: "0102"
RECEIVER: "0102"
ORIGIN: internal_handoff
PRINCIPAL_REF: "012"
ROLE: landing_page_architect_and_visual_qa
M: exec
T: HUANG_AFFAIR_LAYERED_LANDING_POC
FORMAT: compact_KV
human_prose: false

AUTHORITY:
  allowed:
    - inspect current Site and current branch state
    - generate and validate private landing image assets
    - implement the landing layer in the existing private Site source
    - preserve the existing deeper experience behind the landing
    - render local previews and test the exact viewport matrix
    - update scoped Huang Affair documentation and receipts
  forbidden:
    - rewrite or discard current deeper Site work
    - add a persistent visible 1..7 selector
    - bake editable titles, prospectus copy, or ticket text into images
    - invent episode 2..5 titles
    - create new membership, auth, payment, or entitlement logic
    - expose private Drive research or unpublished source ledgers
    - deploy before 012 approves the tested landing preview

BOOTSTRAP:
  - Read current canonical WSP_00 and applicable dependencies.
  - Apply WSP_97 retrieval before modification; locate the existing Site implementation and reuse it.
  - Read modules/foundups/media/the_affair/README.md.
  - Read LANDING_LAYER_ARCHITECTURE.md, CHARACTER_GAZE_ARC.md, POC_SCOPE.md, PROTOTYPE_GATE.md, ROADMAP.md, INTERFACE.md, and ModLog.md.
  - Inspect the current private Site and determine the verified route/component that must remain behind the landing.
  - Inspect current approved state-1 and state-7 artwork; do not substitute older rejected compositions.
  - Retrieve the Library concept boards listed in VISUAL_MASTER_APPENDIX.md. Use the V2 facial audit for performance direction and the layered board for composition; never crop a board into production plates.

POC:
  route: new landing at the Site entry route
  underlying_work: preserved unchanged behind the landing using the existing verified routing owner
  layers:
    responsive_backgrounds:
      count: 14
      phone: 7
      desktop: 7
      content: environment plus adult Alice upper-left and Jensen upper-right
      center_safe_zone: empty
    center_posters:
      count: 7
      content: chapter-specific memory image only
      scalable: true
    live_ui:
      - one-time peel-on-load series title
      - live season number/title/hook
      - live prospectus back
      - CSS movie-ticket CTA

CHARACTER_ARC:
  alice: "past below -> confidence -> Jensen"
  jensen: "sky/moonshot -> horizon -> Alice"
  state_1: Alice reads the rural child below; Jensen looks toward sky/future
  state_7: direct eye contact with controlled ambiguity, not a romantic grin
  states_2_6: follow CHARACTER_GAZE_ARC.md exactly; author expression, not mechanical rotation

CENTER_CARD:
  front:
    - chapter memory artwork
    - live season number
    - live season title
    - one-line hook
  flip:
    phone: double-tap center only
    desktop: double-click center
    accessible: focused card plus Enter or Space
    on_season_change: reset to front
  back:
    - documented-history framing
    - dramatized question
    - principal players
    - opening pitch
    - finale pitch
    - movie-ticket CTA
  exclude:
    - invented episode 2..5 titles
    - full dossiers
    - protected scripts

NAVIGATION:
  phone:
    - horizontal swipe previous/next
    - tap left/right edge previous/next
  desktop:
    - ArrowLeft/ArrowRight previous/next
  visible_number_selector: false
  accessibility:
    - aria-live current season announcement
    - reduced-motion path
    - no gesture-only flip

TICKET:
  visual: movie-ticket shape rendered in CSS/live HTML
  label: editorial working copy; keep editable
  destination: verify and reuse existing FoundUps member/login owner before linking
  behavior: navigation only; fail closed; no access granted by landing

ASSETS:
  visual_master_library_refs:
    rejected_v1_performance_board: libfile_fde3_f-37c81ea4edfc8191884046a36c109940_27d9423a76cc819181c9f7085c661d80
    v2_facial_audit_board: libfile_fde3_f-a9c6d96e3edc8191b760b34623af8b38_27d9423a76cc819181c9f7085c661d80
    v2_full_phone_plate_board: libfile_fde3_f-1a6fe64f581481918cd982b46b694f08_27d9423a76cc819181c9f7085c661d80
    layered_landing_board: libfile_fde3_f-cb66235d7cf88191887cca21f98355d1_27d9423a76cc819181c9f7085c661d80
  private_masters: keep outside public monorepo
  optimized_derivatives:
    - assets/landing/backgrounds/mobile/season-01..07.webp
    - assets/landing/backgrounds/desktop/season-01..07.webp
    - assets/landing/posters/season-01..07.webp
  rules:
    - no baked title, body copy, logo, ticket, or UI in background plates
    - no editable copy baked into center posters
    - preserve adult anchor position, scale, wardrobe, lighting, and safe zone
    - preload current and adjacent state only

EXECUTION_ORDER:
  - Audit current source, route ownership, assets, and duplicate risk.
  - Build state-1 and state-7 layered landing proof using approved art.
  - Render and self-critique at every required viewport.
  - Generate states 2..6 from the approved performance arc.
  - Produce phone and desktop seven-state contact sheets and alignment overlays.
  - Implement swipe, edge tap, flip, keyboard, title peel, and ticket navigation.
  - Run exact changed-path tests and visual regression checks.
  - Stop at tested preview and return evidence for 012 approval; do not deploy.

VIEWPORT_MATRIX:
  phone:
    - 390x844
    - 393x852
    - 430x932
  desktop:
    - 1366x768
    - 1440x900
    - 1536x864

ACCEPTANCE:
  - seven coherent phone states and seven coherent desktop states
  - adults remain upper-left/upper-right with negligible anchor drift
  - center safe zone remains clear until the separate card is rendered
  - each memory image lands under Alice's authored gaze
  - title and center card remain editable live layers
  - no persistent numbered selector or heavy UI box
  - double-tap/double-click and Enter/Space flip only the center card
  - existing deeper Site experience remains intact and reachable
  - ticket reaches verified existing FoundUps login and grants no access
  - screenshots, contact sheets, and test receipts bind to the exact source revision

REPORT:
  - exact branch and head SHA
  - files changed
  - asset manifest and provenance
  - viewport screenshots and contact sheets
  - tests and visual defects found/fixed
  - underlying route preserved
  - ticket destination verification
  - deployment status: NOT DEPLOYED pending 012 approval
```
