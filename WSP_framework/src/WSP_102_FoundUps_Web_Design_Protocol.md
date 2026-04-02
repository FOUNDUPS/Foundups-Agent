# WSP 102: FoundUps Web Design Protocol

**Version**: 1.0.0
**Status**: Active
**Created**: 2026-02-18
**Author**: 012 (canonical insight)

## 1. Purpose

Define standards for designing FoundUps web interfaces including landing pages, member areas, and authentication flows. Prioritizes user efficiency, mobile-first design, and regulatory compliance.

## 2. Click Economy (012 Principle)

> "You can rate a system by how many clicks it takes you to do something"

### 2.1 Grading Scale

| Grade | Clicks | Rating | Example |
|-------|--------|--------|---------|
| A | 1 | Excellent | Dashboard access when authenticated |
| B | 2 | Good | ENTER → Sign in → Member area |
| C | 3 | Acceptable | Requires justification |
| D/F | 4+ | Fail | Redesign required |

### 2.2 Target Grades by Action

| Action | Target | Max Clicks |
|--------|--------|------------|
| Sign up/Sign in | B | 2 |
| View dashboard | A | 1 |
| Launch FoundUP | B | 2 |
| Send invite | B | 2 |
| View wallet | B | 2 |

### 2.3 Implementation Pattern

Combine related actions into single screens:
- Disclaimer + Auth buttons on same modal
- Clicking sign-in = implicit confirmation of terms

## 3. Authentication Flow

### 3.1 The Curtain Pattern

Legal disclaimer (the "curtain") must appear BEFORE authentication:

```
Landing → ENTER → Disclaimer Modal (with embedded auth) → Sign in → Member Area
```

**Grade: B** (2 clicks to member area)

### 3.2 Embedded Auth Buttons

Auth buttons appear directly on disclaimer modal:
- "I Confirm — Sign in with Google"
- "I Confirm — Sign in with LinkedIn"
- Escape hatch: "I am an accredited investor"

Clicking sign-in button implicitly confirms:
- User is NOT accredited investor
- User is NOT company representative
- User agrees to Terms of Access and NDA

### 3.3 Mobile Touch Targets

- Minimum button size: 44x44px (Apple HIG)
- Minimum spacing: 8px between targets
- Full-width buttons on mobile for easy thumb reach

## 4. Visual Design Standards

### 4.1 Color Palette

```css
--bg-primary: #08080f;      /* Dark background */
--accent: #7c5cfc;          /* Purple accent */
--accent-hover: #6b4ce0;    /* Purple hover */
--text-primary: #ffffff;    /* White text */
--text-dim: #9ca3af;        /* Gray text */
--border: rgba(255,255,255,0.1);
--card-bg: rgba(255,255,255,0.05);
```

### 4.2 Typography

- Font: Geist Sans (primary), Geist Mono (code)
- Headings: Bold, high contrast
- Body: Regular weight, sufficient line height

### 4.3 Components

**Stat Cards**: Icon + Value + Label + Action Button
```html
<div class="stat-card">
  <span class="icon">💰</span>
  <div class="content">
    <div class="value">--</div>
    <div class="label">UPS Balance</div>
  </div>
  <button class="action">Wallet</button>
</div>
```

**Action Buttons**: Full-width on mobile, icon + label
```html
<button class="action-button">
  <span class="icon">🚀</span>
  <span class="label">Launch a FoundUP</span>
</button>
```

## 5. Regulatory Compliance

### 5.1 Required Disclaimers

Every auth flow must verify:
- User is NOT accredited investor (SEC definition)
- User is NOT company representative
- User agrees to Terms of Access
- User agrees to NDA

### 5.2 Legal Links

Required links on disclaimer:
- Terms of Access: `/legal/terms-of-access.html`
- NDA: `/legal/alpha-nda.html`

Links must be visible, clickable, and open in new tab.

## 6. Responsive Design

### 6.1 Breakpoints

```css
/* Mobile first */
@media (min-width: 768px) { /* Tablet */ }
@media (min-width: 1024px) { /* Desktop */ }
```

### 6.2 Grid Patterns

- Stats: 1 column mobile → 4 columns desktop
- Content: 1 column mobile → 2 columns desktop
- Full-width cards on mobile

## 7. Folder Structure

```
public/
├── index.html          # Landing page
├── member/
│   └── index.html      # Member dashboard
├── legal/
│   ├── terms-of-access.html
│   └── alpha-nda.html
└── css/
    └── styles.css      # Shared styles
```

## 8. SoftProto Direction

FoundUps interfaces are moving toward a schema-driven UI operating layer.

Direction lock:
- layout should become user-owned, not hard-coded
- gestures should become user-owned, not hard-coded
- future AI edits and direct user edits must mutate the same underlying state

Current implementation note:
- `modules/foundups/docs/SOFTPROTO_FOUNDATION_ARCHITECTURE_2026-04-01.md`
- `modules/foundups/docs/SOFTPROTO_ROLLOUT_PLAN_2026-04-01.md`

Interpretation:
- `WSP 102` remains the governing web design protocol
- `SoftProto` is the active implementation direction for configurable FoundUps surfaces
- `Svelte` may be used as the rendering layer for SoftProto, but the system itself is the schema/registry/store/command model, not the framework alone

Adoption order:
1. architecture contract
2. surface audits
3. isolated spike inside `/member/`
4. phased rollout across gateway, Mall, user panel, and FoundUp views

Nested interaction requirement:
- gesture resolution must eventually support recursive scopes across:
  - app
  - plane
  - module
  - submodule
  - object
- local overrides must be able to fall back to parent defaults

## 8A. Mall / FoundUp Runtime Boundary

FoundUps web surfaces must preserve the runtime split between the shell and the
product experience.

Canonical model:

```text
Mall PWA = control shell
FoundUp = external product/app
Connection = metadata + task API + deep link
```

Direction lock:
- the Mall owns discovery, auth context, navigation, and shared shell controls
- the FoundUp owns its own product logic, task surface, and product UI
- separate FoundUp repos are compatible with one installed app experience when
  deployment stays inside the shell route scope

Current runtime note:
- `modules/foundups/docs/PFMALL_EXTERNAL_FOUNDUP_ROUTE_CONTRACT.md`

Preferred route family:
- `/f/{foundup_id}`
- `/f/{foundup_id}/{path}`

Implication:
- route navigation is the experience pipe
- metadata/task/status contracts are the control pipe
- UI customization work such as SoftProto belongs to the shell-side interface
  layer and must not erase the Mall-vs-FoundUp boundary

## 9. Testing Checklist

- [ ] Click count audit (target Grade B or better)
- [ ] Mobile touch target verification (44px minimum)
- [ ] Disclaimer visible before auth
- [ ] Legal links functional
- [ ] Auth flow completes in 2 clicks
- [ ] Responsive on mobile/tablet/desktop

---

*WSP 102: Every click costs trust. Spend wisely.*
