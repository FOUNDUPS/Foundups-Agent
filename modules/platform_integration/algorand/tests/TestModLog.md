# Algorand test change log

## 2026-10-25 — first exact local execution passed

Committed code context: `444c9f147b6a603be57f4bfb51453cd99b1827a9`, after preserving
main e801 scheduler/registry changes. The original 28 test methods and product
source remain byte-identical to their authoring freeze. Adapter repairs were
statically reviewed before execution; initial/intermediate versions are retained.

Local materialized Windows CPython 3.12.10: child exit 0, stdout/stderr 0 bytes;
all 28 exact method IDs PASS, no skips/errors/failures/expected failures. Exactly
four expected denial events: account generation, DNS, process creation and socket
creation. Zero unexpected attempts or diagnostic overflow. All 245 loaded origins
and 5,263 frozen files rehash exactly; original 1,505 candidate files are unchanged.

SHA256 evidence bindings:

- Profile: `155cf0d9e341de82b6f61fedbf0092de345f076518f5dd4607254630e27bce65`.
- Separate execution release: `9e642ceccf1336cb6b64826024184bd0235d5531d3a6129a793dab9bf4c6e5b4`.
- Actual child receipt: `de4480b434555c9beb51117d48d3391a0fefa90230045657cec12c032ba5aa25`.
- Parent acceptance: `20fcb2c96b9dce5a8e2b079d33c23dc788459b94d00bcde449ad20e40dd290d2`.
- Independent prepared-profile review: `15ed6ce83cb4800bfeb7b1faa3c2533ad6f1e888c511c00ef63cbc6a441f4df2`.
- Independent run acceptance: `81ad5169c7f4da9d4be9aba15cbea3b6c758e3e130db6a7042e5c4b9a05aed0e`.

Local evidence root: `C:/Users/user/AppData/Local/Temp/foundups-asa-codec-qualification-v2-mvlraij9`.
These local artifacts are not bundled or a permanent public archive. The
[dedicated workflow](../../../../.github/workflows/algorand-probe-codec.yml) retains
its own distinct CI installation/profile/results for 14 days. CI has not yet run
for this candidate. Python hooks do not prove OS/native/concurrent-writer isolation;
no provider/node/account-generation/signing/mint/submission or paid state is admitted.

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
