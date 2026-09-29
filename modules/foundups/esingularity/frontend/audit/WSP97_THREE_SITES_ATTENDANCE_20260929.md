# WSP 97 audit and Prometheus M-to-M execution prompt — 2026-09-29

## Observed evidence and decision

- Source: `frontend/app/page.tsx` shows only FY2018 use (129,649); `app/yumori/page.tsx` is the separate movement home. The shared ticker and host rewrite must remain mounted. Current Git main was clean before edits; the Sites source was deployed as v54.
- Fukui City's full-period monitoring PDF reports FY2005 142,484; FY2006–2010 mean 150,187; FY2011–2015 mean 133,014; FY2016 135,782; FY2017 133,421; FY2018 129,649. These yield 1,957,341 uses across FY2005–2018. Document 03 adds FY2019 124,561 from the city's 2020 municipal report, yielding 2,081,902 across FY2005–2019. The latter report URL failed in the web retriever and requires separate verification before elevating the 15-year subtotal to a primary-sourced website fact.
- Document 03 labels “over three million since opening” a reasonable **estimate**, not a verified lifetime total: FY1994–2004 annual records are missing. It needs 918,098 earlier uses (83,464 per year on average) to cross three million by FY2019. FY2020 should not be assumed to be a full operating year. The public function ended in June 2021; the city's current facility page still describes gym use.
- Document 07 and the repo candidate registry describe three distinct roles: Sukatto human-facing hub under a separate PPP/PFI comparison route; Hanyu initial-priority, grid-first school candidate; Shimousaka second/future expansion school candidate. Neither school has verified deliverable power or fiber; the school property-proposal route does not automatically apply to Sukatto.
- Micro: insert one compact three-site panel after the project hero; preserve the hero, deck, current-position section and navigation. Add an evidence note near the existing FY2018 fact instead of replacing a verified statistic. Macro: translate every new text and accessible label into English and Brazilian Portuguese; scope CSS to the project panel so the YUMORI homepage and ticker are unaffected. Challenge: a prominent unqualified three-million claim would confuse estimated lifetime use with recorded attendance, so label it explicitly and explain the missing years.

## Prometheus M-to-M prompt (authored before implementation)

**Mission:** Make the smallest evidence-led eSingularity.ai update that makes the three-site Fukui proposal visible and accurately presents historical use, with Japanese as the source and complete English and pt-BR equivalents.

**Method:** Inspect WSP 97, the website skill, repo contracts, source documents 03/05/07, primary Fukui records, live site and adjacent YUMORI consumer. Work in two small patches: (1) project-only panel with candidate roles, status and route distinction; (2) historic-use note with verified years and explicitly estimated lifetime threshold. Review each diff and render before the next patch. Do not turn candidate nodes into approved projects or assign unverified MW.

**Verification:** Check Japanese content and responsive placement first, then English and Brazilian Portuguese text, controls, semantics and overflow. Run contract/domain tests, lint and build. Confirm both homepages, shared ticker, project links and host routing. Document actual merge and deployment status; never equate build or Git merge with live publication.
