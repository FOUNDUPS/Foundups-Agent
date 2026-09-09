# Project eSingularity FoundUp

Project eSingularity is a Japanese-first community campaign and public-information PWA for preserving Sukatto Land Kuzuryu and testing a community-owned green data center (COG DC) alternative for Fukui.

**FoundUp ID**: `esingularity_001`

**Canonical module**: `modules/foundups/esingularity`

**Public site**: https://esingularity.ai/

**Lifecycle**: Internal Proto
**Deployment**: OpenAI Sites

## Purpose

The current public journey is deliberately simple. The existing hero is followed by a ten-slide YUMORI presentation, while the existing campaign ticker carries one `NEW` notification linking to it:

1. Understand what is at risk.
2. See the alternative to demolition.
3. Understand the potential benefit to Fukui.
4. Understand how students and FoundUps could use our COG DC compute.
5. Become a YUMORI or join the LINE community without financial obligation.

The financial models, engineering research, and source audits support the public claims but are not the main public experience.

## Module structure

```text
modules/foundups/esingularity/
├── frontend/               # Live Japanese-first Vinext/Sites PWA
│   ├── content/            # Canonical Japanese deck and derived language states
│   └── audit/              # Public-claim evidence ledger
├── skillz/                 # WSP 95 module-owned operational Skillz
│   └── yumori_contact_ledger/
├── src/                    # Stable FoundUp identity contract
├── tests/                  # Manifest, registry, route, hosting, and Skillz checks
├── docs/                   # Migration, architecture, and external-context contracts
├── memory/                 # WSP 60 module memory documentation
├── foundup_manifest.json   # p.fMALL/FoundUps discovery contract
├── module.json             # Module discovery metadata
├── README.md
├── INTERFACE.md
├── ROADMAP.md
└── ModLog.md
```

## YUMORI.me communications ledger

The operational YUMORI.me contact system lives in connected Google services,
not in public Git:

- Gmail is the canonical message/thread record.
- `YUMORI.me Contacts` is the Google Sheet contact and Email Log index.
- `YUMORI.me Moshpit` is the dated campaign milestone record.
- `YUMORI.me Contacts Pics` preserves contact-source imagery such as business cards.

The repo stores the reconciliation contract and RedDog/WRE discovery hook at
`skillz/yumori_contact_ledger/SKILLz.md`, with source/schema context in
`docs/YUMORI_CONTACT_LEDGER_CONTEXT.md`. The Skillz uses Gmail `message_id` and
`thread_id` rather than inventing a second tracking signature.

## Local workflow

```powershell
cd modules/foundups/esingularity/frontend
npm ci
npm run lint
npm run build
npm run dev -- --host 127.0.0.1
```

## Architectural boundaries

- `esingularity.ai` remains the primary campaign domain.
- Foundups.com discovers the project through the registry and `/f/esingularity_001` namespace.
- The Foundups.com shell does not own or duplicate eSingularity product logic.
- The site remains inside the monorepo until it passes the FoundUp exfoliation readiness gate.
- No token, investment offer, or fundraising claim is created by this module registration.
- The deck is additive: it does not replace the existing hero, ticker, campaign actions, or deeper public sections.
- Public-site contact candidates remain in the ignored RedDog manual-alpha store until a governed Contact Memory runtime exists.
- Private operational correspondence/contact rows remain in connected Gmail/Drive; the repo contains workflow contracts, not a private contact dump.
- A Skillz file grants no Gmail/Drive mutation authority. Live state must be read from the connected sources before current-state claims or actions.

## WSP alignment

- WSP 3: FoundUp ownership under `modules/foundups/`
- WSP 22: module change documentation
- WSP 49/60: module structure and memory
- WSP 95: module-owned Skillz and Rolodex registry discovery
- WSP 97: truth-boundary labels and no implied activation
- WSP 104: stable `/f/{foundup_id}` namespace and tenant isolation
