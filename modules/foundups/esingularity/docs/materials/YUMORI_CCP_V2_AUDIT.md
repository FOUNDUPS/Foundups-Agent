# YUMORI — CCP v2 intake audit — 2026-09-12

**Status: reviewed research intake, not publication approval.** Base repository commit: `3b74a04205b05fc0d84172d52b8862ff608b1d6e`. Scope: all 23 supplied document texts (11 language pairs plus README), current 03 text and the retrieved eSingularity ownership/publication documentation. Source identities are in [source_registry.json](source_registry.json). Originals remain unchanged.

## Decision

Do not concatenate the packet verbatim into 03. Its strongest reusable content is the research agenda: adaptive reuse, workload-specific local demand, useful heat, whole-life comparison and written feasibility gates. Its grant, financial, partnership and technical guarantees do not pass through simply because the packet calls itself verified.

03 should receive a short decision-relevant synthesis, not the academic manuscript, contact directory, investor pitch or correspondence. The proposed [Japanese-first integration source](YUMORI_03_RESEARCH_INTEGRATION.md) preserves the public/community onsen objective. CCP is an external analytical lens, not an adopted replacement for eSingularity/YUMORI or COG DC.

## Claim disposition

| ID | Packet claim or conflict | Decision / required evidence |
|---|---|---|
| A01 | City, academic and investor files call 8,901 m² the site area; some summaries assume free land. | Reject that premise. The city's property sheet gives 33,717.36 m², all leased [P1]. Keep site, building footprint and floor area separate; resolve the existing floor-area discrepancy before calculations. |
| A02 | “¥600M Fukui subsidy available/qualifies” appears beside an exclusion in the grants papers. | Current container concept is excluded from the cited AI-DC category; official rules also require at least ¥10B investment [P2]. Do not book it. Per-project and group caps must not be confused. |
| A03 | November 14, 2026 is presented as a confirmed city deadline. | Hold as unconfirmed. Grants paper §4.1 itself says it is extrapolated; the retrieved city overview links the R7 process, not a verified R8 deadline [P3]. Obtain the actual current notice or written response. |
| A04 | Prior proposals failed because of zoning/cost recovery. | No rejection-reason evidence was supplied in this packet review. Preserve the distinction between rejected proposals and documented reasons. |
| A05 | Article 34(14) “solves” permission. | Treat as a proposed consultation route, not an approval. The property sheet explicitly requires checking use restrictions and procedures [P1]. Obtain site-specific planning/legal review. |
| A06 | ~¥23M/year J-Credit income from assumed avoided emissions times a quoted price. | No project methodology, registration, certified issuance or sale evidence established here. Keep unverified carbon cash out of the base case; a market quote does not prove credit eligibility. |
| A07 | Grant amortization is included in the pitch's revenue and supports returns. | Separate commercial operating results from grant accounting and dated cash receipts. Reconcile with financing, taxes, replacements and working capital; do not carry the pitch's IRRs into FIN or 03. See arithmetic below. |
| A08 | “Same cost as demolition”, proven cost equivalence and automatic budget savings. | Comparisons use different scopes and unpriced assumptions. The demolition estimate, current preparation appropriation, project capex and future operating returns are different accounts. Obtain matched-scope quotations and the actual municipal budget source. |
| A09 | 72% site carbon reduction / demolition releases all historical embodied emissions. | The academic draft admits no site-specific LCA. Retain life-cycle assessment as a task, not an empirical project result. Compare future material, equipment, operation and end-of-life boundaries consistently. |
| A10 | 1 MW / PUE 1.11–1.12 / 850–900 kW useful heat / short heat payback. | Design assumptions, not measured results. Separate IT load, facility intake, utilization, recoverable heat and actually used heat. Obtain hourly demand, temperatures, losses, auxiliary power and installed cost. |
| A11 | 95–100 MW nearby grid availability and existing electrical maintenance imply available site power. | No load-connection reservation or current site capacity established. Obtain the utility's site-specific response, reinforcement cost, timing, redundancy and supply contract. Do not equate a map or old maintenance contract with a connection commitment. |
| A12 | “Zero local compute”; all clinical AI must avoid Tokyo/Osaka. | Reject blanket claims as unverified. Build workload-specific demand, latency, data and cost comparisons including existing providers/cloud. |
| A13 | Nearby universities/hospitals/JA are confirmed anchors or board partners. | Contact or geographic proximity is not an LOI, paid demand, membership or support. Correct institution/campus identity and attach evidence to each actual relationship state. |
| A14 | Tenant-only bath amenity and conversion of bathing halls replace the community onsen. | Do not adopt. Preserve the existing community-access mission and validate operating conditions with residents and engineers. |
| A15 | Japanese community brief guarantees privacy compliance, adequate power, no noise impact, jobs and no tax increase. | Remove unsupported guarantees. These additions are not equivalent to the English brief. Require independent technical, financial and legal review before public claims. |
| A16 | English/Japanese versions are fully equivalent. | Not established. Research brief is materially different in scope; Japanese academic abstract reverses the distribution argument, and versions differ in timelines, grants and partner status. Reconcile paragraph-level meaning and uncertainty, not only numbers. |
| A17 | Author/affiliation placeholders coexist with “manuscript submitted”. | Label research draft; no authorship, submission or peer-review receipt established. Source bibliography homepages do not verify each attributed result. |
| A18 | Contact appendices claim complete current verification. | They contain duplicate/conflicting identities, addresses and number variants. Stage for the existing private contact review; do not import into public Git or overwrite verified contacts in bulk. |
| A19 | National, local, tenant, tax and multi-year carbon amounts are one funding total. | Keep applicant, geography, expenditure, award state and receipt timing separate. Exclude other municipalities' aid from this site's funding and avoid stacking the same cost twice. |
| A20 | YUMORI.info and eSingularity.ai are independent information sites. | Principal correction: YUMORI.info is an alias/redirect to eSingularity.ai, not independent corroboration. No DNS change or redirect test performed. |

## Reproducible arithmetic on the supplied pitch only

Source: `investor-pitch-en`, §6.2, 10-year P&L; extracted text SHA-256 `350f19f3ed9603d31eef24b4d90d85a29924d4c1b2ee8c0a53c916f1c3cf612a`. Values below are millions of yen.

| Row | Y1 | Y2 | Y3 | Y4 | Y5 | Y6 | Y7 | Y8 | Y9 | Y10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Printed EBITDA | 5 | 19 | 63 | 88 | 103 | 92 | 76 | 58 | 42 | 25 |
| Printed subsidy amortization | 100 | 100 | 100 | 100 | 100 | 80 | 60 | 40 | 20 | 0 |
| Printed J-Credit revenue | 0 | 20 | 23 | 25 | 27 | 28 | 30 | 32 | 33 | 35 |
| EBITDA minus those two rows | -95 | -101 | -60 | -37 | -24 | -16 | -14 | -14 | -11 | -10 |

This subtraction is an audit diagnostic, not a corrected investment model, accounting opinion, project forecast or finding about the separate FIN workbook. Other inputs also require verification. The stated colocation arithmetic is `$196 × 1,000 kW × 0.70 = $137,200/month`, not approximately $164,000; colocation pricing must not be relabeled as GPU-service pricing without a business-model reconciliation. Grant-paper §7.1 listed range endpoints sum to 260–930 million yen, not 310–830; even the corrected sum is not direct available project funding because it mixes recipients and non-cash items.

## What to add to 03, and what stays elsewhere

**Add as proposed verification:** demand evidence by workload; hourly useful-heat test; matched-scope whole-life comparison; applicant/equipment/cash-flow funding checklist; written site, land, zoning, power and fiber conditions; language-parity and partner-status safeguards. Much of this already exists in 03, so integrate only the incremental detail rather than append duplicate explanations.

**Retain outside the 03 narrative:** academic literature leads and competing hypotheses; granular model reconciliation; unverified program discovery; contact records; outreach templates; correspondence provenance. JHR owns hyperscaler research; the existing FIN owner must govern finance; the contact lane keeps sensitive records private.

The packet does not supersede 03's current campaign sequence or the Japanese committee charter. This audit has not freshly verified the council date or the full set of grant windows already described in 03.

## Primary checks performed

[P1] Fukui City, former Sukatto Land property sheet, PDF pp. 2–4, accessed 2026-09-12: https://www.city.fukui.lg.jp/sisei/plan/reform/p071776_d/fil/SUKATTO.pdf

[P2] Fukui Prefecture, Growth Industry Location Promotion Subsidy, July 2026 rules, page dated 2026-08-13, accessed 2026-09-12: https://kigyoritti.pref.fukui.lg.jp/preferential/archives/1

[P3] Fukui City private-proposal overview, page dated 2026-02-24, accessed 2026-09-12: https://www.city.fukui.lg.jp/sisei/plan/reform/minkanteian_matome.html

The property PDF was parsed and relevant screenshots requested. Its Japanese glyphs did not render reliably in the available screenshot viewer; this is not a complete visual audit. No claim that all sources in the packet were independently verified is made. J-Credit eligibility remains unverified, not disproved for every conceivable future design.

## WSP retrieval / alternative comparison / execution boundary

Retrieved: WSP_00 operating contract, WSP_97 execution/reuse gates, repository operating instructions, module README/INTERFACE/ROADMAP/ModLog, existing public-claim ledger and JHR README. These establish the existing module and ownership boundaries. The selected move is a docs-only intake slice: preserve originals, consolidate accepted research questions and record rejected/held claims. A new repository, blanket Drive import, second claim ledger or new publisher would create unnecessary competing authority.

GitHub search/tree/file retrieval was the available fallback; no runnable checkout was obtained. WSP_00 runtime gate, HoloIndex owner-query, repository tests, complete WSP_15 allocation verification and full-project source migration are **not completed**. Do not represent this draft as fully WSP-executed, deployed or ready for automatic publication. No tests or runtime code are changed. Before promotion, the next governed checkout must complete required gates and assess the outstanding source/finance/privacy review.

See [remaining work](README.md#remaining-bounded-work) for ordered continuation. Existing Drive outputs and the public site were not changed by this intake.
