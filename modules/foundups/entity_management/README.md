# Corp Mgmt

Review-only WSP_15 PoC. Primary purpose is legal-entity obligation evidence for
individual FoundUp instances, hence WSP_3 `modules/foundups/entity_management`,
not a new domain, messaging transport or external agency connector.

`src/corp_mgmt.py` evaluates one synthetic obligation record offline. It does not
select an entity automatically, verify documents, determine legal eligibility,
calculate taxes/deadlines, send messages, file, pay, sign, persist or schedule.
Always returns `can_execute: False`. RECONCILED means only the supplied Boolean
gates passed, never official acceptance or permission.

The adjacent wardrobe skill contains the human/agent reconciliation procedure.
Reuse existing correspondence-state, recipient-preflight, private Mosh Pit and
local-procedure skills rather than duplicating their transports or ledgers.
No automatic registry/HoloIndex admission, activation or external action is included.

Validation from repo root: `python -B -m unittest discover -s modules/foundups/entity_management/tests -v`.
See INTERFACE.md for deliberate limitations and ROADMAP.md for admission gates.
