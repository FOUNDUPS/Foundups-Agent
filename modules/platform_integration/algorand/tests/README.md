# Unsigned probe test owner

Owner: `test_unsigned_asa_probe.py`,28 ordinary stdlib unittest methods in
`UnsignedASAProbeTests`; subtests are not additional standalone method IDs.
Use the canonical unit shard and the separately reviewed SDK qualification
adapter/profile. Generic discovery in an unadmitted environment is not evidence.
No skip, expected failure, fake package alias, signing or live provider is needed.

The tests use ordinary imports and the adapter's `assert_guarded()` in `setUp`.
Four explicit `expected_denial` controls cover socket, DNS, subprocess and account
generation. The build must succeed while account/sign/client and estimator paths
remain denied. The adapter/source admission is a separate owner and must itself be
reviewed and released before execution; its presence does not certify OS isolation.

Oracles include two independently prepared raw-hex/transaction-ID vectors, exact
SHA256 request bindings and standard-library transaction-hash calculation. Synthetic
public addresses make no account-control or ledger-state claim. Coverage includes
strict scalar/realm/address/fee/round bounds, trusted-expected mismatch, immutable
results, declarations absent from wire, hostile signed wrappers, duplicate/missing
keys, bool/int confusion, trailing/oversize data and noncanonical encodings.

Local qualification passes all 28 methods: four expected denied controls, zero
unexpected attempts/skips/failures/errors, and 245 loaded origins match the profile.
The immutable 1,505-file materialized candidate is unchanged. See TestModLog.md
for receipt hashes and the dedicated workflow for a distinct pip CI environment.
Missing-source collection before implementation would be a prerequisite failure,
not behavioral RED. No SDK/guard/oracle source changed after the passing run.
