# Kosei AI Systems - Public Landing PWA

**Type**: Public landing page (no auth required)
**Phase**: 1 (MVP)

---

## Overview

This is the public landing PWA for Kosei AI Systems. It handles:
- Service explanation and value props
- EN/JP language toggle
- Pre-audit intake form (writes to Firestore)
- PWA installability

## Surfaces

| Route | Purpose | Auth |
|-------|---------|------|
| `/kosei/` | Landing page | None |
| `/kosei/#audit` | Intake form anchor | None |
| `/kosei/#pricing` | Pricing teaser anchor | None |
| `/kosei/login` | Auth redirect (future) | None → redirect |

**NOT in this surface**:
- `/kosei/app/*` — Client workspace (separate build)
- `/kosei/admin/*` — Operator workspace (separate build)

## Files

```
frontend/
├── index.html          # Main landing page
├── manifest.json       # PWA manifest
├── sw.js               # Service worker
├── css/
│   └── kosei.css       # All styles
├── js/
│   ├── kosei-i18n.js   # EN/JP (vanilla JS, used by index.html)
│   ├── kosei-intake.js # Form → Firestore (vanilla JS)
│   ├── i18n.js         # EN/JP (ES6 module, for future Vite)
│   ├── firebase-init.js # Firebase (ES6 module, for future Vite)
│   └── intake-form.js  # Form handler (ES6 module, for future Vite)
├── assets/             # Icons (placeholder)
└── README.md           # This file
```

**Two JS implementations exist**:
- `kosei-*.js` — vanilla JS with `window.*` globals (Phase 1 static HTML)
- Non-prefixed files — ES6 modules (for future Vite/React migration)

## i18n System

**Implementation**: `js/kosei-i18n.js`

Centralized string management:
- All strings defined in `KOSEI_STRINGS` object (EN + JA)
- DOM elements use `data-i18n="key"` attribute
- `applyKoseiStrings()` applies all translations
- Locale persisted in `localStorage('kosei_locale')`
- Browser language detection on first visit

**Usage**:
```html
<h1 data-i18n="hero_title">AI-Powered Content...</h1>
```

**Toggle**:
```javascript
window.koseiI18n.toggle(); // EN ↔ JA
```

## Firebase Integration

**Pattern**: Reuses shared Firebase project (`gen-lang-client-0061781628`)

**Collection**: `kosei_audit_requests` (per KOSEI_DATA_MODEL.md)

**Submission flow**:
1. Form submit → `submitAuditRequest(formData)`
2. Try Firestore write to `kosei_audit_requests`
3. Fallback: localStorage (`kosei_pending_audits`) if Firestore unavailable
4. Show success/error message

**No auth required** for intake form — public create per Firestore rules.

## PWA Support

**Manifest**: `manifest.json`
- Name: "Kosei AI Systems"
- Theme: #6366f1 (indigo)
- Display: standalone
- Scope: `/kosei/`

**Service Worker**: `sw.js`
- Static asset caching
- Network-first for HTML
- NEVER caches Firebase SDK, auth, or API calls

**Install**: Browser prompts install on supported platforms.

## Development

**Local testing**:
```bash
# From repo root, serve with any static server
npx serve modules/foundups/kosei/frontend -p 3000
```

**Firebase Hosting** (production):
- Add `kosei` site target to `.firebaserc`
- Deploy: `firebase deploy --only hosting:kosei`

## Boundaries

| Concern | This Surface | Other |
|---------|-------------|-------|
| Lead capture | YES | — |
| EN/JP toggle | YES | — |
| PWA install | YES | — |
| Client dashboard | NO | `/kosei/app/*` |
| Admin console | NO | `/kosei/admin/*` |
| AutoPost UI | NO | External repo |

---

*Phase 1 MVP — Worker H*
