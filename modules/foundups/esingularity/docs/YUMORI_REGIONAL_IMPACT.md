# Regional economic impact — executable financial-model extension

Audit: 2026-09-29 JST. WSP 00/15/50/97. MPS C3/I5/D4/Impact4 = 16/P0.

## Ownership and integration

This extends [YUMORI economic-model authority](YUMORI_ECONOMIC_MODEL.md).
Calculation owner: `../src/yumori_regional_impact.py`, exported by the existing
`../src/__init__.py` package. Numerical regression owner remains
`../tests/test_yumori_economic_model.py`; no competing test file or financial workbook.

The native Google FIN workbook remains
`1w00eZcfUMyaNu_wwQEf_GVNHpQamYScRdpB_QGecFJ0`.
The existing **Regional Impact** tab, sheet ID 92001, is retained. The 18-tab
structure is unchanged. No new workbook, tab, contact ledger, or campaign log
was created. The legacy integrated XLSX remains reference-only.

`calculate_regional_impact()` produces separately labeled history, visitor-spend,
innovation-payroll, and public/asset-reference outputs. `regional_projection_values()`
returns the 41 numerical expected values at existing Regional Impact cell addresses.
This is a rebuildable parity contract, not a live synchronization service or permission
to overwrite changed human assumptions.

Commercial demand sizing, the three-site CapEx model, financing, CFADS, investor
returns and cash reinvestment remain unchanged. No regional output is injected
into those cash flows. In particular, Hanyu's current planning cash and its gate
remain independent of the regional onsen scenario.

## Source reconciliation

- [City monitoring, p.1](https://www.city.fukui.lg.jp/fukusi/kfukusi/ikigai/p015196_d/fil/monitoring-30sukatto.pdf)
  was re-read, including the rendered table. FY2005–FY2018 uses sum to **1,957,341**
  using the six published annual/period rows. Two five-year averages are multiplied
  by five; preserve this precision boundary. These are uses, not unique people.
- FY2018: 114,028 day uses + 15,621 overnight uses = 129,649 total uses.
  The same table records **124,886 thousand JPY in user fees**. This is neither
  lodging-only receipts nor full revenue, profit or regional spending.
- FY2019's inherited 124,561 reference is preserved, and the expanded reference
  sum remains 2,081,902. Its original aramasi2.pdf URL returned 404 on this audit;
  obtain the archived original before promoting the expanded sum as freshly
  verified. A broken URL does not establish that a historical number was false.
- Lifetime attendance remains unverified. The future 100,000/year × 30 years =
  3,000,000 uses is a different, explicitly conditional planning illustration.
- [Fukui 2025 tourism report, printed p.7](https://www.pref.fukui.lg.jp/doc/kankou/fukuiken-kankoukyakusu_d/fil/024.pdf)
  gives 5,546 JPY/day-trip visitor and 30,221 JPY/overnight visitor. The day total
  comprises 1,786 souvenirs plus 3,760 other spending. Other includes food and
  local transport; fuel/food cannot simply be added on top of the whole-trip total.
  Trip averages are not measured spending per repeat onsen use.
- Historic construction, floor/site area, MLIT index and City reuse-cost inputs
  are inherited reference inputs. SUKATTO.pdf is now unavailable at the recorded
  URL; preserve those values with archival-source-recheck notes rather than
  inventing replacement evidence. Indexing construction cost is not an appraisal.

## Calculation contracts

| Layer | Formula | Interpretation |
| --- | --- | --- |
| Gross visitor spending | annual uses × spending per use | Sensitivity, not project income or GDP |
| Incremental local spending | gross × local capture × additionality | Both shares remain scenario inputs, not observations |
| Present value | sum of end-year annual stream / (1+r)^year | Constant nominal stream; zero discount rate supported; not welfare NPV |
| Innovation payroll | firms × FTE/firm × annual pay/FTE | Gross scenario, not verified or net-new jobs |
| Indexed construction reference | historic cost × current index / historic index | Not market value or certified replacement cost |
| Deferred demolition PV | estimate × ((1+cost growth)/(1+discount))^years | Timing-only sensitivity; not full reuse benefit |
| Listed operating hurdle | listed maintenance + site area × land rate | Not complete Opex or current City net cost |

The three innovation cases remain 20/30/60 firms × 2 FTE × 4M JPY =
160M/240M/480M JPY annual gross payroll. Occupancy, survival, displacement, hiring
and compensation require market-test evidence. Removed on-site accommodation
revenue is not silently retained; external hotels need a separate demand case.

I-O total output, indirect/induced effects, actual market value, actual demolition
contract price and aggregate Community ROI return **None / HOLD**, not zero estimates.
An aggregate multiplier is not a substitute for the official sector model.
Total output = direct × multiplier; indirect plus induced alone = direct ×
(multiplier−1). Do not apply local supply leakage twice when the official I-O
method already includes it. The official tool covers Fukui Prefecture, not an
unsupported Fukui-City-only effect.

A welfare benefit-cost ratio needs non-overlapping benefits and costs against
an explicit counterfactual. Sales, wages, private investment, fiscal savings,
and construction cost cannot simply be summed as community benefits. No such
headline ROI is admitted by this extension.

## Existing FIN cell ownership

- Regional Impact 5–18: history/benchmark summaries, now linked to source rows.
- 20–41: visitor and payroll sensitivities; PV handles zero rates.
- 43–70: asset/cost references and unresolved methods. Index/area/rate/horizon
  constants are linked to explicit controls rather than repeated inside formulas.
- 74–89: underlying annual/period history, retained FY2019 reference, recorded
  user fees and tourism-source boundaries.
- 91–109: explicit controls, source-recheck notes, calculation owner and cash boundary.
- 129–176: 41 Python expected values, live formula readbacks, PASS/DRIFT/ERROR and
  expected/passed counts. Values were generated from model version regional-impact/1.0.0.
- Dashboard 27–34: linked regional summaries, kept out of commercial cash rows.
  The newer capacity rule at Dashboard row 26 is preserved.
- Audit & Checks 31–33: live parity count, history reconciliation and I-O/BCR HOLD.
  Existing portfolio checks from row 34 onward are preserved.

## Verification and change receipt

Initial main was b34c483cdaa84253961dd58f9b4878b9841f9cd0, including #1962's
costed three-site planning model. Stale #1935 was documentation-only and did
not implement these regional calculations; this extension supersedes that
incomplete calculation claim without reverting intervening portfolio work.

Eight isolated local new-model cases passed. The existing repository test owner
adds those tests plus a portfolio-before/after equality regression. Full exact-head
CI and main integration are separate PR gates, not inferred from local tests.

Native Google Sheets readback on 2026-09-29 returned **41 expected / 41 PASS**.
The receipt is a dated baseline comparison. Intentional later assumption changes
must rebuild/review expected values; PASS is not proof of source verification,
commercial viability, investment authority or automatic synchronization.

No government filing, email, fundraising solicitation, website publication or
investment commitment occurred in this reconciliation.
