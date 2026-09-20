---
name: yumori_funding_ppp_intelligence
description: Verify live grant, subsidy, GX, PPP/PFI and public-asset reuse opportunities for YUMORI.me and synchronize City-facing evidence
version: 0.1
author: 0102
agents: [0102, qwen, gemma]
primary_agent: 0102
intent_type: RESEARCH
promotion_state: candidate
category: workflow
domain: foundup_campaign_operations
pattern_fidelity_threshold: 0.95
wsp_chain: [WSP_00, WSP_15, WSP_22, WSP_50, WSP_95, WSP_97]
evals:
  - official_primary_source_required
  - canonical_registry_updated_before_drive
  - no_unawarded_funding_booked
  - city_facing_claims_preserve_eligibility_boundary
---

# YUMORI.me Funding / PPP Intelligence

## Purpose

Maintain one evidence-backed funding and PPP intelligence lane for YUMORI.me / former Sukatto Land Kuzuryu. The skill converts changing national, Fukui Prefecture and Fukui City programs into accurate project evidence without turning a live program into a false funding commitment.

## Trigger

Run this workflow when any of the following occurs:

- a grant, subsidy, GX, data-center, energy-efficiency, heat-reuse, regional-infrastructure, PPP/PFI or public-asset reuse program opens, closes or materially changes;
- 012 asks what public funding/support could apply to YUMORI.me;
- a City/Prefecture/council communication will mention grants, subsidy, PPP/PFI or public funding;
- document 03, document 05 or the financial model is being updated on funding;
- a ministry, implementing body, Fukui City or Fukui Prefecture gives an eligibility answer.

## Authority order

1. Official primary source: ministry, agency, Fukui Prefecture, Fukui City, or the officially appointed program administrator.
2. Canonical repository registry: `modules/foundups/esingularity/docs/GRANTS_AND_SUBSIDIES.md`.
3. Drive document 03: City/Prefecture/Council evidence and education surface.
4. Drive document 05: PPP/PFI mechanics, applicant/ownership/contracting and funding-stack implementation.
5. Financial/grant audit models: scenario analysis only.
6. Mosh Pit / Email Log: operational receipts, not grant-status authority.

If sources conflict, re-verify the primary source and update the repository registry first.

## Status contract

Use only these meanings:

- `VERIFIED PROGRAM`: official program exists.
- `ELIGIBILITY INQUIRY`: a specific project-fit question has been sent.
- `ELIGIBLE`: program administrator or controlling rule establishes project/applicant fit.
- `APPLICATION`: application actually submitted.
- `SELECTED`: selected/adopted, but funding terms may still require completion.
- `AWARDED`: committed subsidy/award supported by primary documentation.
- `CLOSED`: no longer open.

A maximum cap is never expected funding. Only `AWARDED` may be treated as committed subsidy revenue.

## Workflow

### 1. Detect and verify

For every candidate program capture:

- official program name and agency;
- current round and opening/closing dates;
- applicant class;
- subsidy rate and cap;
- eligible and excluded costs/equipment;
- site/property/use-right requirements;
- ownership/operator requirements;
- CO2, renewable-energy, heat-use or performance methodology;
- procurement/contract-before-award restrictions;
- stacking / duplicate-subsidy rules;
- application method and inquiry contact;
- exact primary-source URLs.

### 2. Map to YUMORI.me components

Do not ask only “does YUMORI.me qualify?” Map the program to the actual component:

- modular/container COGDC;
- new-build or later DC expansion;
- renewable power / storage / UPS / receiving equipment;
- cooling / CDU / heat exchanger / heat pump / pumps;
- onsen/thermal retrofit / DHW / HVAC / controls;
- existing-building retrofit;
- public infrastructure and PPP feasibility;
- education/research use;
- public-asset reuse / lease / concession / private proposal.

Record unresolved applicant, ownership, land, closure/baseline and timing questions.

### 3. Synchronize project documents

**Registry first.**

Then update Drive **03** with the detailed public/city-facing funding evidence:
- live status;
- official dates;
- rate/cap;
- what it could support;
- what it does not prove;
- the specific question Fukui City should evaluate.

Update Drive **05** only with the PPP implementation consequence:
- who would apply;
- who owns funded equipment;
- City/SPC/operator roles;
- procurement timing;
- public/private funding split;
- VFM/PSC treatment;
- subsidy stacking and failure case.

Do not maintain two independent detailed grant registries in 03 and 05. 03 is the readable evidence surface; 05 consumes it for transaction mechanics.

### 4. City education packet

When a live program materially changes the reuse case, prepare a concise Japanese City Funding Notice:

1. official program and agency;
2. what changed and deadline;
3. published rate/cap;
4. YUMORI.me/Sukatto component that may fit;
5. unresolved eligibility boundary;
6. request to identify the responsible Fukui City department and assess eligibility before irreversible disposition;
7. official source links.

The purpose is education and eligibility determination, not a claim that the City or YUMORI.me has secured funding.

### 5. Outreach and receipts

Use the canonical YUMORI.me contact/Gmail routing rules. After sending:

- verify Sent;
- capture Gmail MID/TID;
- update Email Log / Contacts as required;
- add the material event to the Mosh Pit;
- record any reply as evidence and update the registry only if it changes program status.

## 03 / 05 decision rule

**03 answers:** “What support exists now, why does it matter, and what should the City verify?”

**05 answers:** “If a support route is usable, how does it change applicant structure, PPP/PFI mechanics, procurement, ownership, VFM, risk and the funding stack?”

When unsure where a grant fact belongs, put the full verified program fact in the registry + 03 and only its transaction consequence in 05.

## Boundaries

- Do not describe open programs as secured project funding.
- Do not imply Fukui City, Fukui Prefecture or a ministry supports YUMORI.me unless primary evidence says so.
- Do not book subsidy revenue before AWARDED.
- Do not double-count the same equipment across grants.
- Do not infer that a closed facility satisfies baseline requirements.
- Do not infer that a public asset is eligible merely because a City reuse program exists.
- Do not use secondary articles when the current primary program source is available.
