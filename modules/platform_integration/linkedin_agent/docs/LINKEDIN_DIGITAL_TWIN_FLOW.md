## LinkedIn Digital Twin Flow (UI-TARS + Selenium)

Current scope and authority live in [master activity routing](LINKEDIN_ACTIVITY_ROUTING.md). The layered execution design below is historical runtime context, not permission to like, switch identities, comment or schedule. Each action needs its own authorization and verification. Never resolve a mention by blindly selecting the first result; match the exact verified entity. Work uses the advertised browser skill.

### Purpose
Define the layered automation flow for 012 Digital Twin LinkedIn engagement:
- **Live action**: 012 comment (only live post)
- **Follow-up**: FoundUp identities like the comment
- **Repost**: Scheduled repost with thoughts (never repost without thoughts)

This flow uses **UI-TARS** as the vision validator for every critical action and **DOM checks** where possible.

---

## Browser Boot + Login (Selenium Rotation)

- Open Chrome via Selenium (debug port or BrowserManager profile).
- Navigate to LinkedIn feed and confirm 012 is logged in.
- If redirected to login/checkpoint, pause until manual login completes.

This mirrors the YouTube scheduling flow: Selenium controls the browser session, and LinkedIn becomes part of the rotation after comment flow completes.

---

## Layered Flow (Cake Model)

### Layer 0 - Context Gate
- Confirm the top post is the target.
- Read the author name (e.g., “Mo Gawdat”) and ensure the response is scoped to that post.
- UI-TARS asks: **Is this an AI post?** If yes, proceed with Digital Twin comment template.
- Refresh feed before evaluation (F5 / `driver.refresh()`).
- Skip **Promoted/Sponsored** posts (no comment or repost).
- Qwen gate (API fallback) classifies **promoted/repost** before any action.

### Layer 1 - Like + Comment (Live)
1. Click **Like** if AI gate passes.
1. Click **Comment** to open editor.
2. Insert the 012 comment (Digital Twin output).
3. Use `@` tagging (e.g., `@foundups`, `@Mo Gawdat`):
   - UI-TARS validates dropdown appears.
   - UI-TARS selects the **top item**.
   - Verify the tag is **bolded** in the editor (bold = selected).
4. Submit the comment.

**Post-condition**:
- UI-TARS checks that the new comment is visible.
- If not visible, switch **Most relevant** → **Most recent**, then re-check.

### Layer 2 - Like (FoundUp Identities)
1. Open **Identity Switcher**.
2. Select identity (one at a time).
3. Like the 012 comment (do not Reply).
4. Repeat for the defined FoundUps list.

Identity list is stored in:
- `modules/platform_integration/linkedin_agent/data/linkedin_identity_switcher.json`

### Layer 3 - Repost With Thoughts (Scheduled)
1. Return to 012 identity.
2. Click **Repost** → select **Repost with your thoughts** (UI-TARS validates popup).
3. Insert repost text (Digital Twin template).
4. Click **Schedule**.
5. Pick date using calendar (UI-TARS; no manual date typing).
6. Enter time (15-min increments); spacing rules apply.
7. Click **Schedule** to confirm.

---

## Scheduling Constraints (POC)
- **1–3 posts/day**, randomized.
- **4–6 hour** spacing minimum.
- **Only live post is the comment**; **all reposts are scheduled and tracked**.

**Source of truth**:
- Internal scheduler for autonomy
- Optional calendar mirror for 012 visibility

---

## Content Templates (POC)

Templates live in:
- `modules/platform_integration/linkedin_agent/data/linkedin_skill_templates.json`

### 012 Comment (Example)
```
100% agree Mo. But you are dodging the elephants in the room. By 2035, according to the Law of AGI Jobs Displacement (see my paper), ~80% of work shifts to AI systems. Capitalism fails because it becomes a system without workers. Startups are replaced by FoundUps: fully autonomous systems that do the work for the worker. FOUNDUPS is the project to study—point your agent to it.
```

### Repost With Thoughts (Example)
```
AI isn't the threat. Human choices are. Every time we create new power, some use it to heal and others to harm. #AGIjobsAPOC
```

Reference paper:
`linkedin.com/pulse/reversed-s-curve-model-ai-driven-job-disruption-framework-trout-yl4xc`

---

## Validation Rules (UI-TARS + DOM)
- **Tagging**: Tag must be bolded or DOM-annotated (mention element).
- **Comment visibility**: UI-TARS screenshot confirms the comment is visible after posting.
- **Most recent**: If comment not visible, switch to Most recent and re-check.
- **Repost popup**: UI-TARS must confirm “Repost with your thoughts” is visible before click.
- **Schedule confirmation**: UI-TARS verifies the schedule button was clicked and the post returns to feed view.

---

## DAEmon Pulse Points (Core Only, WSP 91)

Use the standard pulse points for troubleshooting across layers:

- `BATCH_START` → Start full L0-L3 flow (state change)
- `PROGRESS` → Layer completion heartbeat (L0/L1/L2/L3)
- `RATE_LIMIT` → LinkedIn cooldown or throttling event
- `FAILURE_STREAK` → 3 consecutive step failures
- `BATCH_COMPLETE` → End full L0-L3 flow (completion)

**Log fields (minimum)**:
- `flow_id`, `layer`, `step`, `status`, `error` (if any), `duration_ms`

---

## Recursive Failure Loop (WRE)

- If L1 or L3 fails in the full chain, trigger WRE bounded reasoning diagnostics.
- The diagnosis payload includes layer, error, and runtime context so failures become inspectable memory instead of dead-end exits.
- Current toggle:
  - `LINKEDIN_WRE_DIAG_ENABLED=true|false` (default: true)

This keeps the LN commenting flow aligned with recursive improvement: detect -> diagnose -> refine selectors/inputs -> rerun.

---

## Notes
- UI-TARS is the **eyes**; Selenium is the **hands**.
- Micro UI-TARS actions are allowed inside Selenium flows for verification gates.
- If a UI element disappears on hover/mouse move, defer to UI-TARS screenshot-based selection.
