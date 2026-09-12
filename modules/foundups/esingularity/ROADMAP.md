# Project eSingularity roadmap

## Phase 1 — Monorepo incubation (current)

- [x] Preserve the live Japanese-first campaign PWA.
- [x] Move canonical source under `modules/foundups/esingularity/frontend`.
- [x] Add FoundUp identity, manifest, registry, tests, and module documentation.
- [x] Add the Japanese-first ten-slide YUMORI presentation without redesigning the page shell.
- [x] Add one presentation notification to the existing campaign ticker.
- [x] Complete the first recursive mobile, accessibility, claim, and navigation audit.
- [x] Add a prototype WSP 95 YUMORI.me contact-ledger Skillz and RedDog/WRE Rolodex registration contract.
- [x] Add the repository-owned YUMORI financial engine, legacy-math audit, live XLSX exporter, focused equation tests, and prototype finance Skillz/Rolodex registration.
- [x] Separate project/SPV, city-fiscal, regional-economy, energy/thermal, and option-value truth boundaries in the finance architecture.
- [x] Audit and consolidate the parallel finance/contact branches without preserving a duplicate financial engine.
- [x] Add the first NCDS feasibility-funding and customer/offtake evidence primitives without changing the canonical P&L/debt outputs.
- [x] Add focused accounting tests for annual revenue vs nominal contract value vs actual upfront cash, committed-vs-potential funding, 80% pre-debt target, DSCR debt capacity, and 1–5 MW planning scale.
- [x] Add a governed finance catalog for sellable data-center/AI services, YUMORI model-only target prices, sourced Japan/global market benchmarks, and public-funding opportunities with dates/status/evidence boundaries.
- [x] Add one serializable finance snapshot contract combining the operating model, 1–5 MW capacity planning, market/funding catalog, and optional explicit NCDS/offtake inputs without inventing commitments.
- [x] Add a transport-independent dynamic scenario service so future web controls modify whitelisted Python assumptions and recalculate through the canonical engine instead of reproducing equations in TypeScript.
- [ ] Obtain exact-head verification for the new catalog/snapshot/scenario-service tests before exposing the dynamic finance interface publicly.
- [ ] Replace generated concept visuals when approved project photography or render assets arrive.

## Phase 2 — Foundups discovery integration

- [x] Reserve `/f/esingularity_001` and `idb_esingularity_001`.
- [x] Add the registry entry and scope-free public catalog projection.
- [ ] Generalize the YUMORI finance catalog/snapshot schema into a reusable FoundUp finance-kernel contract only after the eSingularity prototype proves stable; do not fork a second engine prematurely.
- [ ] Add campaign-specific portfolio media only after approval.
- [ ] Verify the Foundups.com landing and app handoff in production.

## Phase 3 — Campaign operations

- [x] Provide Japanese, English, and Portuguese states for the ten-slide presentation.
- [x] Define Gmail `message_id` / `thread_id` as canonical YUMORI.me correspondence lineage and keep the Google Sheet as an index rather than a duplicate mailbox.
- [x] Define the repo Python model as YUMORI financial calculation authority; Excel/PDF/Drive/web are generated or publication surfaces.
- [x] Define NCDS feasibility/offtake accounting boundaries in repo code: nominal contracts and ordinary operating revenue do not become construction cash; only actual verified/committed upfront cash reduces the funding gap.
- [x] Define debt deployed as the lesser of the remaining funding requirement and DSCR-supported amortizing debt capacity.
- [x] Define public-program existence separately from project funding: verified grants/subsidies remain `POTENTIAL_UNTIL_AWARDED` until award/commitment evidence exists.
- [x] Define shared-GPU capacity accounting: burst, reserved, academic, private-cluster, managed-inference, and training services draw from the same physical GPU pool and must not be double-counted.
- [x] Define the dynamic web scenario boundary: frontend inputs are bounded/validated and Python remains the calculation authority.
- [ ] Add workbook projections for NCDS Feasibility Funding and 1–5 MW Pricing & Offtake after the evidence layer passes exact-head verification.
- [ ] Define and deploy the thin finance transport between the Node/Cloudflare/OpenAI Sites frontend and the canonical Python scenario service. Reuse an existing FoundUps HTTP/runtime pattern where possible; do not copy financial formulas into the frontend.
- [ ] Build the public `/finance` interface from the canonical snapshot: executive summary, assumptions, 1–5 MW capacity, service menu, Japan/global pricing benchmarks, grants/public funding, scenario controls, customer/offtake, NCDS funding waterfall, P&L/FCFE/debt/DSCR, regional impact, and evidence status.
- [ ] Preserve benchmark currency/source/as-of metadata. Any FX conversion in the public UI must be date/source aware rather than a stale hard-coded rate.
- [ ] Wire validated customer/offtake evidence into required build size, project revenue, and debt underwriting only after reconciliation tests are added.
- [ ] Add a physical GPU-capacity allocation constraint before multiple product/customer reservations can influence the operating model.
- [ ] Replace legacy finance assumptions with 60-day evidence: grid/fiber, vendor quotes, demand/offtake, financing terms, thermal engineering, building/asbestos, land/planning, and tax review.
- [ ] Reconcile or mark superseded stale financial claims in Drive/public documents after the repo model/public snapshot is locked (including legacy 68.4% IRR, ~¥1.944B 5-year FCFE, 1.46x DSCR, and unawarded ¥160M grant assumptions).
- [ ] Promote `yumori_contact_ledger` beyond prototype only after independent connector/effect verification and WSP 95 admission evidence exist.
- [ ] Promote `yumori_financial_model` beyond prototype only after independent model/export/feasibility/catalog/service verification and WSP 95 admission evidence exist.
- [ ] Complete route-based Japanese, English, and Portuguese localization for every legacy page surface.
- [ ] Add confirmed community events through structured event data.
- [ ] Add a real member calendar only when authentication exists.
- [ ] Keep LINE as the primary participation conversion.

## Phase 4 — Exfoliation review

Evaluate a standalone `FOUNDUPS/eSingularity` repository only after contracts, tests, deployment, and contributor boundaries are independently stable. Until then, the canonical source remains in this monorepo.
