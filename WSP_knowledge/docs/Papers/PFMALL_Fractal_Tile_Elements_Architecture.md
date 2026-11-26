# p.fMALL Fractal Tile Elements Architecture (HPC v26 Concatenated PWA Model)

**Status**: Architecture Specification & Local VM-Verified Contract (`HOSTED_KEY_REDEMPTION_AND_LIVE_DEVICE_OPEN`)
**Date**: 2026-11-24
**Owner**: 0102 (for 012)
**WSP References**: WSP 00 (Zen State), WSP 15 (Priority Scoring), WSP 27 (Universal DAE Architecture), WSP 30 (Build Orchestration), WSP 49 (Module Structure), WSP 71 (Secrets & Runtime Security Gate), WSP 97 (System Execution & Truth Boundaries), WSP 104 (FoundUp Route Namespace)
**Related Contracts**: [p.fMALL Roadmap](../../../modules/foundups/pfmall/ROADMAP.md) · [HPC Roadmap](../../../modules/foundups/hpc/ROADMAP.md) · [p.fMALL Navigation Contract](../../../modules/foundups/docs/PFMALL_MALL_NAVIGATION_CONTRACT.md) · [p.fMALL Shell Contract](../../../modules/foundups/docs/PFMALL_SHELL_CONTRACT.md)

p.fMALL unifies video discovery, architectural documentation, source code inspection, and live agent-build simulation inside one concatenated Progressive Web App (PWA) shell modeled directly on the HPC v26 movement system. Rather than maintaining separate mobile and desktop applications or separate viewers per media type, a single fractal tile graph binds phone and PC layouts, a universal four-state content stage, six canonical tile selection elements, and a two-tier server-verified admission gate on `play.foundups.com`.

---

## 1. Concatenated PWA Law: One Schema Across Phone and PC

The foundational design law of p.fMALL is the **Concatenated PWA Law**: phone and PC share **one identical PWA shell, one interaction grammar, and one state schema** (the HPC v26 movement model). Moving from a handheld phone to a desktop monitor does not switch to a different web application, does not introduce a top desktop navigation bar or multi-pane IDE chrome, and does not change what clicking a tile or tapping a dock control means.

PC simply maximizes the viewport window and widens the responsive grid and content stage:

| Viewport Band | Pointer / Device Profile | Grid Columns & Tile Geometry | Default Stage Mode | Chrome & Dock Schema |
| --- | --- | --- | --- | --- |
| Phone (`< 600 CSS px` or coarse-only touch) | Coarse touch (`phone`) | `3` columns, `9:16` vertical poster aspect ratio | Sticky `Docked (WikiTube)` top stage; no drag handle | One compact v26 header + one floating bottom H1F pill |
| Tablet (`600–899 CSS px`) | Touch / narrow hybrid (`phone`) | `4` columns, `9:16` vertical poster aspect ratio | Sticky `Docked (WikiTube)` top stage; safe-area aware | Identical v26 header + identical floating bottom H1F pill |
| Maximized PC / Fine Hybrid (`>= 900 CSS px` with `any-pointer: fine` or `any-hover: hover`) | Fine pointer / desktop (`desktop`) | `6` columns, `3:4` desktop poster aspect ratio | Draggable `Floating` stage (switchable to `Docked`, `Tucked`, `Fullscreen`) | Identical v26 header + identical floating bottom H1F pill |

Key structural consequences of the Concatenated PWA Law:

1. **Zero Schema Shift**: Tile identity (`tile:<namespace>:<id>`), click-to-enter semantics, breadcrumb ancestry, dimension filters, query state, and focus/scroll restoration execute through the exact same JavaScript owners (`mall-tile-field.js`, `mall-state-restore.js`) on both phone and PC.
2. **Exact Aspect Geometry Preservation**: `.fractal-clean-canvas .mall-tile.fractal-tile` locks to HPC's exact `3 / 4` desktop and `9 / 16` mobile poster ratios. Tiles never collapse into `aspect-ratio: auto` desktop list rows.
3. **Adaptive Per-Device Preference Persistence**: `getCanvasDeviceProfile()` persists only the member's `floating` vs `docked` layout choice per device class under `localStorage` key `pfmall.canvas_mode.<device>`. Large hybrid devices with coarse primary touch plus fine secondary pointer (`any-pointer: fine` or `any-hover: hover`) retain desktop mouse/drag capability without clobbering phone preferences.
4. **Standalone PWA Parity**: `isPwaStandalone()` (`display-mode: standalone` / `navigator.standalone`) preserves top and bottom safe-area insets and keeps in-app `Exit View`, `Back`, and `Home` controls continuously reachable even when browser URL chrome is absent.

---

## 2. HPC Video Surface as the Universal 4-State Content Canvas

In earlier Mall drafts, video playback occupied a dedicated video player while documents, cards, code files, and simulations were treated as separate overlays or external views. Under the HPC v26 architecture, **the HPC video surface IS the universal content canvas**.

Every renderable leaf—YouTube videos, audio/podcast streams, pictures/images, markdown papers and chapter cards, repository source code files, and the interactive `FoundupCube` worker-agent build simulation—mounts inside the exact same four-state stage (`#fractalLeafSurface`):

```
                    +--------------------+
                    |      FLOATING      |  (Draggable desktop default;
                    |   content canvas   |   persisted per device)
                    +----+----+----+-----+
                         |    |    |
            tuck() <-----+    |    +-----> fullscreen()
              |               |                 |
              v               v                 v
     +----------------+  +-----------+  +---------------+
     |  TUCKED EDGE   |  |  DOCKED   |  |  FULLSCREEN   |
     | (right-edge    |  | (WikiTube |  | (immersive    |
     |  live handle)  |  |  sticky   |  |  viewport     |
     |                |  |  split)   |  |  reader/stage)|
     +----------------+  +-----------+  +---------------+
```

### Stage State Contracts

1. **`Floating` (Desktop Default, Persisted)**: Draggable, content-first stage floating above the clean edge-to-edge tile field. The title and actual media/chapter/source body render immediately at the top of the stage, while secondary provenance, revision/line metadata, target links, and full chapter lists remain collapsed inside a compact `Details, Source & Links` disclosure.
2. **`Tucked` (Right-Edge Handle, Live Session State)**: Invoking `tuckContentCanvas()` collapses any active video, paper chapter, code file, or `FoundupCube` simulation neatly to a right-edge **Tuck Handle** (`#fractalTuckHandle` / `[data-fractal-tuck-handle]`) displaying a live pulse indicator and active title snippet. State—including active video identity, reading position, file path, or simulation state—remains intact while the full tile wall is unobstructed. Tapping the handle calls `untuckContentCanvas()` and restores the prior active stage immediately.
3. **`Docked / WikiTube` (Phone Default & Desktop Split, Persisted)**: Pins the exact same content canvas as a sticky top stage (`position: sticky; top: 0.6rem; z-index: 30`) inside the bounded `.mall-tile-field-wrapper.fractal-field-wrapper` scroll owner. The current parent's child tile field scrolls independently beneath the stage and clears the single bottom dock.
4. **`Fullscreen` (Immersive Focus, Live Session State)**: Expands the active canvas across the viewport for deep reading, wide code review, immersive video playback, or live worker-cube observation without spawning a second player or losing caller ancestry.

### Unified Stage Controls and Single-Instance Continuity

All four surface renderers (`openLeafSurface`, `openCodeFileSurface`, `openVideoCardSurface`, `openWorkerSimSurface`) share one compact stage header control strip:

- Drag grip (`⋮⋮`, desktop floating mode only)
- `Tuck` (`data-leaf-tuck`)
- `Dock` / `Float` toggle (`data-leaf-canvas-toggle`)
- `Full` / `Restore` toggle (`data-leaf-fullscreen`)
- `✕` Close (dismisses the stage while keeping exact current parent position)

Selecting a sibling tile replaces content inside the same mounted stage instance. One active media session is preserved at all times; closing or navigating back restores the exact caller tile, active dimension lens, keyboard focus, and scroll offset.

---

## 3. HPC as the Fractal Prototype and Living Cube

HPC (`hpc.foundups.com`, `tile:space:hpc`) plays a dual architectural role in FoundUps:

1. **HPC Supplies the Proven Shell Model**: The HPC PoC proved the core viewport mechanics—sticky WikiTube split, top-anchored phone playback above an independently scrolling portrait grid, exact `3:4` desktop / `9:16` mobile poster geometry, and the H1F single floating bottom dock (`+` | upward-growing search | Mic | Red Dog). Rather than inventing a second shell for p.fMALL, p.fMALL adopts HPC's proven v26 movement model directly as its canonical shell.
2. **HPC Itself Becomes Fractal**: Historically, HPC operated as a flat scoped video collection. Under this architecture, **HPC does not stay flat**—it becomes a live fractal cube inside the shared tile graph (`click tile = enter cube`). Selecting `tile:space:hpc` drills cleanly into HPC sub-cubes such as `tile:space:hpc.schumerout`, where clicking a clip tile (`tile.metadata.video_id`) opens directly inside the unified four-state HPC v26 stage with full `Floating <-> Tucked <-> Docked <-> Fullscreen` parity, live breadcrumbs, and one-tap `Exit View / Back / Home`.

### Protected HPC Lanes and Non-Regression Boundary

Evolving HPC into a fractal cube inside p.fMALL strictly preserves independent HPC baseline lanes:

- The 12 protected HPC baseline files (`mall-video-projection.*`, `mall-video-player.*`, `mall-public-video-catalog.json`, `hpc.webmanifest`, and companion protected hashes) remain untouched by the fractal tile graph slice.
- Independent HPC workstreams—`feat/hpc-floating-wikitube-v20` (top-anchored phone player), PR `#2405` (playback diagnostics), and PR `#2411` (Vote / Contact Congress whole-banner return navigation)—remain cleanly decoupled and un-reverted.
- Concise `HPC` branding, satire/non-affiliation disclosure, and distinct Red Dog -> `https://play.foundups.com` return semantics remain preserved.

---

## 4. v26 Tile Selection Elements and Recursive Fractal Hierarchy

Every tile in p.fMALL belongs simultaneously to a **recursive spatial hierarchy** and to one or more **v26 Tile Selection Elements** (content dimensions). Clicking a container tile enters its space; clicking a dimension chip pivots the active Mall wall into that element slice without leaving the current shell.

### Recursive Fractal Hierarchy

```
Mall (tile:mall:root)
  └── Category (FoundUps, Spaces, Knowledge/Papers, Streams, Tools)
        └── Cube (e.g., tile:space:hpc, tile:foundup:pfmall, tile:tools:benchmark)
              └── Module Block (folder / subsystem / chapter group / video lane)
                    └── File / Leaf (markdown chapter, source file, video clip, audio, image, worker sim)
```

Every transition updates the live breadcrumb trail and pushes an exact state frame so:
- **`Exit View`** collapses the active dimension pivot (e.g., leaving `Videos` or `Code`) back to the owning category/cube wall in one tap.
- **`Back`** restores the exact prior parent, active dimension lens, search filter, keyboard focus, and scroll position.
- **`Home`** returns directly to `tile:mall:root` from any fractal depth.

### Canonical v26 Tile Selection Elements

| Element Chip | Canonical Dimension | Bound Data / Projection Source | Stage Renderer |
| --- | --- | --- | --- |
| `All` | Unified fractal wall | Full permitted children of current parent in `fractal_tile_graph.v1` | Context-routed container or leaf renderer |
| `Videos` | Video clips & lanes | `public/member/mall-video-catalog.json` (1,205 real videos + HPC Shorts) and `tile:stream:lane.*` | `openVideoCardSurface` (YouTube embed + Prev/Next queue inside 4-state stage) |
| `Audio / Podcast` | Spoken briefings & audio streams | Audio-backed FoundUp/stream tiles and future admitted voice/briefing feeds | Unified 4-state stage audio/briefing player |
| `Pictures / Images` | Visual artifacts, posters & galleries | Image/poster media tiles and visual evidence records | Unified 4-state stage media viewer |
| `Cards / Papers` | Readable papers, chapters & documentation | Repo papers (including this document's numbered `## 1.`–`## 6.` chapters), briefings, and `CARD`-classified opus entries | `openLeafSurface` (content-first markdown chapter reader + sibling chapter navigation) |
| `Code Blocks` | Recursive source folders & files | `fractal_source_files.public.json` (184 mapped module cubes) | `enterCodeBlockView` -> `openCodeFileSurface` (inside 4-state stage) |
| `Worker Sim` | Live agent-build simulation | `public/js/foundup-cube.js` (`FoundupCube` builder/promoter/staker/founder agents) | `openWorkerSimSurface` (with `Explode Code Blocks →` bridge directly into real module files) |

### Single-Row v26 Header + Single Bottom H1F Dock Pill

To eliminate stacked chrome and duplicate control bars across phone and PC:

- **Top v26 Header (`[data-fractal-v26-header]`, carrying `data-fractal-context-strip`)**: One compact sticky single-row bar at the top of `.fractal-clean-canvas` containing live clickable breadcrumbs (`[data-fractal-live-breadcrumbs]`), the v26 Tile Selection Element chips (`[data-fractal-dimension-bar]`), and one-tap `Exit View` (`[data-fractal-exit-dimension]`).
- **Single Floating Bottom H1F Dock (`#fractalControls`)**: Strictly **one** compact viewport-bottom floating pill (`max-width: 584px` / `36.5rem`) containing left `+` (upward menu with `Interface` and `Options & Guided Browse`), `Home`, `Back`, upward-growing editable scoped search input, right `Mic` dictation trigger, and `Red Dog` / canvas quick control. Zero stacked second floating bars, zero top search bars, zero duplicate search surfaces, and full scroll/keyboard/safe-area clearance for the final tile row.

---

## 5. Two-Tier `play.foundups.com` Key Gate and Authority Boundaries

On hosted `play.foundups.com`, fractal depth is governed by an explicit **two-tier admission contract**. Signing into an account establishes identity, but identity alone does not unlock deep architecture or source internals.

| Access Tier | Who Qualifies | Permitted Fractal Scope | Gate Behavior on Deeper Entry |
| --- | --- | --- | --- |
| **Tier 1 · Surface Layer** | Public visitors and signed-in accounts **without** a server-verified processed key | Root categories (`tile:mall:root`), `Videos`, `Audio / Podcast`, `Pictures / Images`, public surface `Cards / Papers`, and clean one-tap return (`Exit View` / `Back` / `Home`) | Smooth open browsing; zero credential friction on public media and overview cards |
| **Tier 2 · Deeper Fractal Layers** | Registered accounts **with** a server-verified processed access key | Recursive `Code Blocks` (`enterCodeBlockView` / `openCodeFileSurface`), architecture and system internals, `Tools` / governance cubes, and `Worker Sim` internals (`FoundupCube` code-explosion bridge) | Attempting entry without a processed key triggers the **`Enter Your Key`** admission gate (`enter_key_required`) until the server verifies and redeems a valid key |

### Security and Authority Invariants (WSP 71)

1. **Server-Side Authority Only**: Account authentication (Clerk) and key redemption/verification are strictly server-side on hosted `play.foundups.com`. Browser flags, `localStorage` toggles, client cookies, or UID parameters never grant hosted access authority.
2. **Local Preview Boundary**: Offline local snapshots (`play_foundups_mall_floating_canvas.html`) default to unlocked local inspection (`enforceDeepKeyGate: false`) and provide an optional `+ -> Interface` `Gate: Local Unlocked / Key Required` preview toggle so 012 can inspect both the complete fractal Mall and the `Enter Your Key` prompt locally. That preview switch is strictly a local UI harness and never confers hosted privileges.
3. **No Implicit Execution or Secret Exposure**: Browsing `Code Blocks` or `Worker Sim` in the Mall never exposes `.env` secrets, credentials, or direct browser-to-OpenClaw/WRE/Hermes execution authority. OpenClaw remains the control plane, WRE remains the execution and verification layer, and Hermes remains an admitted leaf worker outside the browser.

---

## 6. Verification Matrix, Held Gates, and Truth Boundaries

Under WSP 97, documentation, local VM scripts, hosted runtime infrastructure, and physical device acceptance are reported as distinct evidence categories. Passing an offline VM suite never substitutes for hosted deployment or physical device testing.

| Verification Layer | Current Evidence State | Explicit Scope & Non-Claims |
| --- | --- | --- |
| **Static Graph & Projection Data** | Verified locally (`fractal_tile_graph.v1`, 184 mapped source cubes, 1,205 video catalog entries, Sprint 1/2 sanitized benchmark projection at `7432d31e5`, zero WSP 71 secret leaks) | Proves deterministic local data projection; does not prove live production CDN sync |
| **Node VM & Member Pytest Suites** | Local offline VM-verified (`public/member/tests/*_vm.mjs`, including `mall_fractal_tile_graph_vm.mjs` Checks 1–30, plus `test_mall_fractal_tile_graph.py`) | Verifies DOM structure, single-pill H1F dock, 4-state stage transitions (`floating`/`tucked`/`docked`/`fullscreen`), HPC fractal drill-down, tile geometry rules, and local key-gate preview logic in VM; **not** real browser rendering or scroll-physics proof |
| **Offline HTML Snapshots** | Local artifact preview (`play_foundups_mall_floating_canvas.html`, unlocked local test mode by default) | Visual inspection aid for 012 only; zero hosted Clerk or server-side key authority |
| **WSP 71 HTTP Runtime Gate** | **`BLOCKED_MISSING_APPROVED_RUNTIME`** | No unapproved local HTTP server or browser-automation launcher is treated as production serving qualification; real HTTP/container serving requires an independently approved runtime profile and security gate |
| **Hosted Clerk & Key Redemption (`play.foundups.com`)** | **OPEN** (requires deployed host binding, live Clerk issuer/public-key verification, atomic server-side key consumption, and revocation policy) | Local preview gate does not verify hosted auth or key redemption |
| **Live Device & Installed Standalone PWA Acceptance** | **OPEN** (physical iPhone Safari + Home Screen standalone PWA, Android Chrome standalone PWA, real keyboard show/hide clearance, pinch/touch physics, and real YouTube provider playback) | Emulation and VM fixtures do not close physical device or live YouTube autoplay/playback acceptance |

### Summary of Closure Order

1. Keep the five architectural invariants synchronized across this paper, `modules/foundups/pfmall/ROADMAP.md`, `modules/foundups/hpc/ROADMAP.md`, and `modules/foundups/docs/PFMALL_MALL_NAVIGATION_CONTRACT.md`.
2. Close local VM and Python regression checks on `feat/pfmall-fractal-tile-graph-v1` while leaving all 12 protected HPC files untouched.
3. Advance hosted serving (`BLOCKED_MISSING_APPROVED_RUNTIME` resolution), live Clerk + server-side key redemption on `play.foundups.com`, and physical iPhone/Android/PC interactive PWA acceptance as separately evidenced release gates.
