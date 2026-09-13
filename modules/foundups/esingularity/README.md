# Project eSingularity FoundUp

Project eSingularity is a Japanese-first community campaign and public-information PWA for preserving Sukatto Land Kuzuryu and testing a community-owned green data center (COG DC) alternative for Fukui.

**FoundUp ID**: `esingularity_001`

**Canonical module**: `modules/foundups/esingularity`

**Public site**: https://esingularity.ai/

**Lifecycle**: Internal Proto
**Deployment**: OpenAI Sites

## Public architecture — one project, two focused sites

The module deliberately publishes two different public experiences from one canonical frontend and one existing Sites project. Shared hosting does **not** mean a shared homepage.

| Public entry | Focus | Homepage owner |
| --- | --- | --- |
| `https://esingularity.ai/` | Project vision: preserve and regenerate Sukatto Land Kuzuryu through the eSingularity/COG DC proposal | `frontend/app/page.tsx` |
| `https://yumori.me/` and `https://www.yumori.me/` | YUMORI movement: understand the wider case, join the preparatory committee, and reach the supporting evidence | `frontend/app/yumori/page.tsx` via the hostname-only root rewrite |
| `https://yumori.info/` | Existing external redirect to eSingularity.ai | Outside this frontend; do not modify here |

Non-negotiable invariants:

- Never replace either homepage with the other, and never redirect YUMORI.me to eSingularity.ai.
- Reuse the same application, components, assets, reports, and hosting project without creating a drifting second copy of YUMORI content.
- A redesign of `app/page.tsx` is an eSingularity.ai change. It must not overwrite, absorb, or repurpose `app/yumori/page.tsx`.
- A YUMORI movement-page change is confined to `app/yumori/page.tsx` unless a shared dependency is intentionally required. It must not alter the eSingularity.ai homepage.
- Treat Git merge completion as source integration only. Production acceptance requires fresh-host verification against both domains.

The executable routing and publication contract is in [INTERFACE.md](INTERFACE.md). The permanent regression and production-verification gates are in [tests/README.md](tests/README.md).

## eSingularity.ai project surface

The current public journey is deliberately simple. The existing hero is followed by a ten-slide YUMORI presentation, while the existing campaign ticker carries one `NEW` notification linking to it:

1. Understand what is at risk.
2. See the alternative to demolition.
3. Understand the potential benefit to Fukui.
4. Understand how students and FoundUps could use our COG DC compute.
5. Become a YUMORI or join the LINE community without financial obligation.

The financial models, engineering research, and source audits support the public claims but are not the main public experience.

## Campaign ticker updates

Use [esingularity-ticker](../../../.agents/skills/esingularity-ticker/SKILL.md) for field-status updates. Edit `frontend/content/current-field-status.ts`; the shared `CampaignTicker.tsx` renders it. Date and time-limit each invitation in Japan time.

## Japan Hyperscaler Report (JHR)

JHR is the eSingularity research/publication lane for tracking Japan's hyperscale data-center expansion, policy, grid constraints, land-use effects, community response, and implications for Fukui and distributed COG DC infrastructure.

- Runtime: `jhr/src/jhr_agent.py`
- Launch adapter: `jhr/scripts/launch.py`
- Agent skill: `.agents/skills/japan_hyperscaler_report/SKILL.md`
- Public route: `/reports/jhr`
- First report: `jhr/reports/JHR_001_2026-09_JAPAN_HYPERSCALER_REPORT.md`

JHR is significance-gated. A research cycle may return `NO_REPORT`; no publication is implied merely because a cycle ran. Public claims require provenance and WSP_97 evidence.

## Module structure

```text
modules/foundups/esingularity/
├── frontend/               # Live Japanese-first Vinext/Sites PWA
│   ├── content/            # Canonical Japanese deck and derived language states
│   ├── audit/              # Public-claim evidence ledger
│   └── app/reports/jhr/    # Public Japan Hyperscaler Report route
├── jhr/                    # Japan Hyperscaler Report research + publish gate
│   ├── src/                # Significance and truth-boundary logic
│   ├── scripts/            # Launch adapter
│   ├── reports/            # Verified reference reports
│   └── tests/              # Publish/no-publish gate tests
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

JHR assessment only:

```powershell
python modules/foundups/esingularity/jhr/scripts/launch.py
```

With no research retriever connected, JHR fails closed and returns `NO_REPORT` rather than pretending research occurred.

## Architectural boundaries

- `esingularity.ai` is the project/vision surface; YUMORI.me is the movement/join surface. They are peers with different jobs, not aliases for the same homepage.
- Foundups.com discovers the project through the registry and `/f/esingularity_001` namespace.
- The Foundups.com shell does not own or duplicate eSingularity product logic.
- The site remains inside the monorepo until it passes the FoundUp exfoliation readiness gate.
- No token, investment offer, or fundraising claim is created by this module registration.
- The deck is additive: it does not replace the existing hero, ticker, campaign actions, or deeper public sections.
- Contact candidates remain in the ignored RedDog manual-alpha store until a governed Contact Memory runtime exists.
- JHR public publication remains fail-closed until retrieval, verification, drafting, image provenance, and publication adapters are verified together.

## WSP alignment

- WSP 3: FoundUp ownership under `modules/foundups/`
- WSP 22: module change documentation
- WSP 49/60: module structure and memory
- WSP 97: truth-boundary labels, evidence gates, and no implied activation
- WSP 104: stable `/f/{foundup_id}` namespace and tenant isolation
