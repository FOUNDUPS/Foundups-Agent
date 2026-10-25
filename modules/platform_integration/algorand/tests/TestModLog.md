# Algorand test change log

## 2026-10-25 — test-first authoring freeze

Authored28 unittest method IDs/265 lines before `src/unsigned_asa_probe.py` existed.
Test raw SHA256: `b25b8cbbcd04c27baa7600fb1336601d9d17bace1fb371a41227322296a3a5a7`.
External preimage, exact ID inventory and independent golden oracle receipt:
`C:/Users/user/AppData/Local/Temp/foundups-asa-codec-authoring-iqm8nmka/test_preimage.json`.
The golden JSON raw SHA256 is
`6592a2a8c9827570fb1f087cb887beabd164956f46b12a52428bab896c3bb4e6`.
This path is local evidence; preserve a parent-reviewed portable result before
claiming reproducible publication evidence.

Only stdlib AST parsing/hashing and independent oracle construction ran. Candidate
and SDK imports, unittest execution, RED/GREEN and effect-control qualification are
pending a separately released profile. The dependency experiment's seven assertions
do not count as these28 tests. Later qualification must retain every method/oracle,
all actual failures and the four explicit guard-negative outcomes.
