# Algorand module change log

## 2026-10-25 — unsigned TestNet ASA format candidate

Preallocated WSP15 C3/I4/D4/Impact4=15/P1 in the existing FX delivery plan;
WSP3/6/12/22/49/50/62/84/97. Added one pure format owner, frozen scalar request
and immutable artifact. Validation restricts the exact realm/genesis, numeric and
address bounds, canonical ten-field wire format and separately named request
binding. Flat fee avoids the SDK estimator's account/signing behavior.

Authored and externally froze28 unittest IDs before product source existed.
Golden packets/txIDs were independently derived using only stdlib MessagePack
construction and SHA512/256. No candidate/SDK import or test execution has occurred
in this authoring lane; no behavioral RED/GREEN or runtime admission is claimed.
See tests/TestModLog.md for preimage evidence and qualification obligations.

No FAM/SQLA/intent/ledger/factory/resident imports, financial policy, reward, signing
or chain state changes. Module-only SDK/msgpack pins reuse the separately reviewed
dependency profile. Global dependency/CI/registry admission remains parent-owned.
