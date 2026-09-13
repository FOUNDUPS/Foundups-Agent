# YUMORI / eSingularity — Grants, Subsidies, and PPP Support Registry

Last verified: 2026-09-13 JST

## Purpose and truth boundary

This file is the repository-side canonical registry for external grant/subsidy/PPP-support programs relevant to YUMORI / former Sukatto Land Kuzuryu. Google Drive financial models and grant-audit sheets are working/derived evidence; this repository record controls project status labels.

Never describe a program as project funding merely because the program exists. Track each item as: `VERIFIED PROGRAM`, `ELIGIBILITY INQUIRY`, `ELIGIBLE`, `APPLICATION`, `SELECTED`, `AWARDED`, or `CLOSED`. Only `AWARDED` may be booked as committed subsidy revenue.

## Authority map: repository ↔ Google Drive

Use this section to prevent drift between codebase truth and Drive working documents.

### Canonical repository authority

- **Grant / subsidy / PPP-support status:** this file, `modules/foundups/esingularity/docs/GRANTS_AND_SUBSIDIES.md`.
- **Public-claim admission:** `modules/foundups/esingularity/frontend/audit/SOURCE_OF_TRUTH.md`.
- **Module direction / discoverability:** `README.md`, `ROADMAP.md`, `ModLog.md`.

### Drive working/derived documents

1. **PPP/PFI Private Proposal Master Draft**  
   Drive ID: `1QgnX9-2XE1wXtn2vg1d3zh3SmXDZyiEjKhSVJuSUOPc`  
   Purpose: formal PPP/PFI mechanics, legal/submission framing, City-facing proposal structure.  
   Rule: may consume grant-status facts from this repo registry; must not independently promote program status.

2. **City / Prefecture / Council Support Brief**  
   Drive ID: `1yeO6-6_mTLW8QswosVKmCVCHSRgWiacq-7FL7-9clsE`  
   Purpose: policy alignment, economics, public-asset reuse evidence, decision-maker support material.  
   Rule: may cite only the current status labels recorded here for grants/PPP support.

3. **Project Prospectus / Case for Support**  
   Drive ID: `1-wxF_I39svQH8AGvF2sryIk6ReAz2ctHe0-5-HypypM`  
   Purpose: integrated explanatory/project narrative.  
   Rule: explanatory only; not the authority for live grant eligibility or award status.

4. **Phase 1 Functional Financial Model & Grant Audit**  
   Drive ID: `1w00eZcfUMyaNu_wwQEf_GVNHpQamYScRdpB_QGecFJ0`  
   Tab: `Grants & Subsidies`  
   Purpose: scenario analysis, caps/rates, timing, model integration, audit notes.  
   Rule: analysis layer only. Maximum caps, model placeholders, or candidate programs are not committed funding unless this repo registry reaches `AWARDED`.

### Cross-reference rule

The three core Drive documents above now begin with an `AUTHORITY INDEX / 権威インデックス` that points readers back to this repository registry. Future agents starting in the repo should use the Drive IDs above to inspect supporting working documents when more detail is needed; future agents starting in Drive should return here before asserting current program status.

If repo and Drive disagree, **do not choose the more favorable number**. Re-verify the primary government source, update this registry first, then reconcile Drive.

## Current highest-priority program

### F-01 — 地域共生を目指したデータセンター脱炭素化設備導入支援事業

- Agency: 環境省 / 一般社団法人 地域循環共生社会連携協会 (RCESPA)
- Status: **VERIFIED PROGRAM / FORMAL ELIGIBILITY INQUIRY SENT 2026-09-13**
- Current round: FY2025 supplementary budget, third call
- Deadline: 2026-10-09 12:00 JST
- Support: generally 1/2 of eligible costs; storage equipment 1/3; project cap up to ¥1,000,000,000 subject to the official guide
- Primary source: https://www.env.go.jp/press/press_05495.html
- Program desk: https://rcespa.jp/r07hosei-datacenter/

Relevant official scope includes data-center decarbonization, high-efficiency cooling and thermal-use equipment. The current project hypothesis is a regional data center with liquid cooling / CDU / heat exchangers / heat pumps / pumps / thermal piping / storage and controls, exporting recovered server heat to the onsen, domestic hot water, showers, kitchen hot water and building heating. River/onsen/ambient heat on the cooling side is also under investigation.

**Critical unresolved eligibility question:** former Sukatto Land Kuzuryu is currently closed and Fukui City has not approved YUMORI reuse. YUMORI is preparing a PPP/public-asset reuse proposal. The formal inquiry asks whether, if Fukui City accepts a lawful PPP/lease/use structure and an eligible private/SPC/operator applicant obtains the required rights before the program's required milestone, the new data-center/heat-reuse equipment can qualify notwithstanding the facility's current closed status.

Do not state that Fukui City is participating in the project, that the project qualifies, or that ¥1B is available to YUMORI until the administering body answers and the applicant/equipment/use-right structure is confirmed.

## F-07A — SHIFT: 省CO2型システムへの改修支援事業

- Agency: 環境省 / 温室効果ガス審査協会 (GAJ)
- Status: **VERIFIED LIVE PROGRAM / FIT REQUIRES BASELINE ELIGIBILITY CHECK**
- Third-round opening: 2026-09-11
- Deadlines: 2026-10-01 12:00 JST and 2026-10-15 12:00 JST
- Rate: 1/3
- Cap: up to ¥100M or ¥500M depending on verified annual CO2 reduction and official guide conditions
- Primary source: https://www.env.go.jp/press/press_05521.html

Potential YUMORI uses: heat recovery, heat exchangers, heat pumps, hot-water/HVAC electrification, fuel switching, pumps, circulation and related thermal retrofit. However SHIFT relies on qualifying existing-facility/baseline emissions and operating conditions. Because Sukatto Land is closed, this must not be presented as a current eligible funding line until the baseline/closure rules are resolved.

## Other tracked programs

- MOE zero-emission / regional-coexistence data-center rounds: monitor for new rounds; potentially relevant to modular/container DC phases.
- METI GX regional-co-creation / decarbonized-power-region investment programs: monitor for scale, regional and applicant fit; potentially relevant to later DC expansion, not assumed for Phase 1.
- Fukui Prefecture 成長産業立地促進補助金 AI型データセンター区分: policy-relevant but current Phase 1 does not meet the presently identified ¥10B-scale / facility-form conditions; do not book.
- Cabinet Office PPP/PFI support: procedural rather than project CAPEX. Fukui City can potentially use national PPP/PFI expert/one-stop support to evaluate public-asset reuse and private proposals.

## Financial-model integration

The Google Sheet `YUMORI — eSingularity Phase 1 Functional Financial Model & Grant Audit — 2026-09-12` contains a `Grants & Subsidies` working tab. On 2026-09-13 F-01 was updated to `LIVE / FORMAL ELIGIBILITY INQUIRY SENT` with the closed-facility + future PPP/SPC question. Model placeholders such as “METI/NEDO Regional DC Decentralization Grant,” “MOE Decarbonized & Symbiotic DC Grant,” or a Fukui dormant-property grant remain **unverified model assumptions** unless mapped to an official program here.

No financial model may double-count overlapping eligible equipment or treat a maximum statutory cap as the expected award. Funding scenarios should be calculated only after: applicant identity, property/use rights, eligible equipment ownership, eligible-cost basis, subsidy stacking rules, CO2 methodology, award probability, and timing are documented.

## Outreach objective

The immediate objective is not to ask a ministry to endorse YUMORI. It is to obtain a technically useful eligibility pathway that can be shown to Fukui City engineers and council:

> If Fukui City accepts a PPP/public-asset reuse structure and grants lawful use rights for former Sukatto Land Kuzuryu, what applicant, ownership, equipment, timing, CO2 and contractual conditions would the project need to satisfy to qualify for national support?

Outreach is issued in the name of the **すかっとランド九頭竜 グリーンAI・地域再生設立準備委員会 / YUMORI Preparatory Committee**, not as a personal project of 012. City approval is never implied.

Operational distribution rule from 2026-09-13: Councilman Sano should be BCC'd on YUMORI operational outreach unless there is a specific legal/privacy reason not to. Media should not be silently BCC'd on routine grant/process emails; send media a direct, concise update when a substantive answer, filing, decision, or other reportable development exists.
