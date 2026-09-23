# Browser Actions TestModLog

## 2026-09-24: Manager admission guard

- WSP 00/15/22/34/50/62/84/97; C3/I3/D4/Impact3 = 13/P1. The existing action owner now requires no prior pending/connected target, the actual PENDING enum, a matching target and identity with the currently stored pending object before Connect. Rejections return `connection_request_not_admitted` without invitation UI or success credit. Existing policy denials, previews, navigation failures and manager bookkeeping are preserved.
- Frozen acceptance: baseline 11 fail/25 pass; repaired and independent runs each pass the same 36 unique cases. All 23 earlier compatibility cases remain; four legacy constructor cases are deselected and two known plugin warnings remain. Seven malformed/state controls supplement the six manager outcomes. File/class/method shrink; no new module or skill.
- Backend binding changes one source digest among 1401 unchanged members and updates two existing pins. Eight manifest tests, the 67-file package and unchanged 1659-file test registry pass. Two premature manifest preparations each yielded 1 fail/7 pass: an old loaded pin, then a partially staged index. Both are preserved; the completed, coherently staged candidate passes the sequential rerun.
- Evidence: `O:/Foundups-Agent-audits/20260924-rsi-manager-guard`; exact publication/closure is recorded there and in the canonical system backlog. This proves a local admission guard, not live delivery, bookkeeping rollback, quota repair, concurrent exactly-once execution, OS confinement or retained native RSI.

## 2026-09-24: Manager-result to UI admission qualification

- WSP00/15/22/34/50/62/84/97; C3/I3/D3/Impact3=12/P2. Extended the existing policy test owner with six fixed current-behavior cases; all23 prior cases and original test AST/fixtures preserved. Production source, backend manifest and registry remain unchanged.
- Same29 cases pass locally and independently, four legacy constructor cases deselected, two known config warnings. Quota WITHDRAWN, already CONNECTED, prior PENDING and simulator-failure WITHDRAWN still reach fake Connect/Send and gain credit; freshPENDING and policyBLOCKED controls distinguish admission.
- Returned/stored object identity is checked: under the fixed test clock, exception fallback shares the storedPENDING request_id but is a different object; priorPENDING reuses the exact existing object. Canonical workflow records a prospective13/P1 fresh-work guard, not a completed repair. No live delivery, rollback, concurrent exactly-once or retained-RSI claim.
- Test inventory reconciled against six actual files; established required canonical tests/TestModLog. Source-only instruction hygiene was separately discovered/scored13/P1 without reproducing or using credential-shaped values. Exact evidence/closure and next selection are in the system backlog.

## Current test inventory

| File | Existing scope |
|---|---|
| `test_linkedin_connection_policy.py` |36 inert acceptance cases: policy/preview/note, manager admission and malformed results; four legacy constructor cases excluded. |
| `test_linkedin_actions_unit.py` |Other action behaviors with fake router; not run in this qualification. |
| `test_autonomous_gemini_heart.py` |Existing-Chrome Gemini heart integration harness; not run. |
| `test_final_autonomous_gemini.py` |Standalone Chrome/Gemini integration harness; not run. |
| `test_gemini_studio_heart.py` |Gemini Studio heart targeting harness; not run. |
| `test_gemini_js_click.py` |Gemini/JavaScript click integration harness; not run. |

The inventory describes retrieved source, not fresh pass claims. Reuse existing fixtures before creating a new file. Historical phantom filenames in tests/README were replaced with this actual six-file inventory.
