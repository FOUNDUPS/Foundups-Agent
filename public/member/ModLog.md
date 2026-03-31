# Member Area Module Change Log

## [2026-03-31] FoundUp Entry Page (Phase 1)

**Who**: 0102 (Claude Opus 4.6)
**Type**: Feature Addition
**Slice**: `pfmall_member_foundup_entry_phase1`

**What**: Card taps now navigate to a dedicated entry page instead of an in-page overlay.

**Files Created**:
- `public/member/foundup.html` — dedicated FoundUp entry view

**Files Modified**:
- `public/member/index.html` — card click navigates to `foundup.html?id={id}` instead of `openFoundupOverlay()`
- `public/member/README.md` — added `foundup.html` to runtime shape
- `public/member/INTERFACE.md` — updated hosted assets and UI contract
- `public/member/ModLog.md` — this entry

**Behavior Change**:
1. Tapping a FoundUp card navigates to `/member/foundup.html?id={foundup_id}`.
2. Entry page is deep-linkable (share URL, bookmark, back button works).
3. Shows readiness posture, detail rows, what-happens-next copy, and description.
4. Not-found state for unknown IDs. Back-to-Mall navigation.
5. Red Dog button present (currently returns to Mall).

**Why**: In-page overlays are not deep-linkable and break browser history. Dedicated page enables sharing, bookmarks, and proper back-button behavior.

---

## [2026-03-31] Invite-Gated Mall Cutover

**Who**: 0102 (Codex)
**Type**: Experience Cutover

**What**: Replaced the admitted `/member/` shell with a Firebase-hosted p.fMALL experience while preserving the existing invite/auth gateway.

**Files Modified**:
- `public/member/index.html`
- `public/member/css/member.css`
- `public/member/README.md`
- `public/member/INTERFACE.md`
- `public/member/ModLog.md`

**Files Created**:
- `public/member/mall-catalog.json`

**Behavior Change**:
1. Invite validation and username claim remain unchanged.
2. Authenticated admitted users now land in a swipe-first Mall shell instead of the legacy member shell.
3. Invite codes moved into the Red Dog concierge sheet.
4. No gateway rewrite or landing-page redirect surgery was required.

**Why**:
- `foundups.com` gateway behavior was already working and had to stay stable.
- The operational bug was the admitted `/member/` destination, not the invite gate itself.

---

## [2026-02-18] Layer 1: Shell Implementation

**Who**: 0102 (Claude Opus 4.5)
**Type**: New Module Creation
**WSP**: WSP 49 (Structure), WSP 72 (Independence)

**What**: Created member area shell with authentication and navigation.

**Files Created**:
- `public/member/index.html` - Main member area with auth state, navigation, placeholders
- `public/member/css/member.css` - Shared styles (dark theme, glassmorphism)
- `public/member/README.md` - Module documentation
- `public/member/INTERFACE.md` - Public API definition
- `public/member/ROADMAP.md` - Layer progression plan
- `public/member/ModLog.md` - This file

**Files Modified**:
- `public/index.html` - Added redirect to `/member/` after successful signup

**Architecture Decisions**:
1. **Occam's Layered** - Build one layer at a time, test, then next
2. **No God Modules** - Each section (wallet, foundups, agents) is independent
3. **Same Design Language** - Matches landing page (CSS variables, glassmorphism)
4. **Firebase Auth** - Uses same Firebase project as landing page
5. **Hash-based Routing** - Simple, no additional dependencies

**Layer 1 Features**:
- Firebase auth state listener
- Redirect to landing if not authenticated
- Sidebar navigation with section routing
- Mobile responsive (collapsible sidebar)
- User info display (name, avatar)
- Invite codes display with copy functionality
- Placeholder sections for all future modules
- Sign out functionality

**Next Layer**: Dashboard (Layer 2) - Real data integration

**WSP References**:
- WSP 49: Module structure compliance
- WSP 72: Module independence (no cross-dependencies)
- WSP 22: Change logging (this file)
- WSP 50: Searched HoloIndex before creating

---

*Created: 2026-02-18*
