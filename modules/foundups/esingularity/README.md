# Project eSingularity FoundUp

Project eSingularity is a Japanese-first community campaign and public-information PWA for preserving Sukatto Land Kuzuryu and demonstrating a community-focused AI infrastructure alternative for Fukui.

**FoundUp ID**: `esingularity_001`

**Canonical module**: `modules/foundups/esingularity`

**Public site**: https://esingularity.ai/

**Lifecycle**: Internal Proto
**Deployment**: OpenAI Sites

## Purpose

The current public journey is deliberately simple:

1. Understand what is at risk.
2. See the alternative to demolition.
3. Understand the potential benefit to Fukui.
4. Join the LINE community.

The financial models, engineering research, and source audits support the public claims but are not the main public experience.

## Module structure

```text
modules/foundups/esingularity/
├── frontend/               # Live Japanese-first Vinext/Sites PWA
├── src/                    # Stable FoundUp identity contract
├── tests/                  # Manifest, registry, route, and hosting checks
├── docs/                   # Migration and architecture records
├── memory/                 # WSP 60 module memory documentation
├── foundup_manifest.json   # p.fMALL/FoundUps discovery contract
├── module.json             # Module discovery metadata
├── README.md
├── INTERFACE.md
├── ROADMAP.md
└── ModLog.md
```

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

## WSP alignment

- WSP 3: FoundUp ownership under `modules/foundups/`
- WSP 22: module change documentation
- WSP 49/60: module structure and memory
- WSP 97: truth-boundary labels and no implied activation
- WSP 104: stable `/f/{foundup_id}` namespace and tenant isolation
