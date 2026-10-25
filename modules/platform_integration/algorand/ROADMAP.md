# Algorand module roadmap

1. **Locally qualified layer:** strict scalar-to-unsigned-byte codec and test-first
   independent vectors; all 28 exact methods pass in the reviewed materialized
   profile. Source authoring and local qualification grant no network authority.
2. **Hosted layer qualified:** run40173561283 passes all28 exact methods in the
   distinct Windows pip installation; see tests/TestModLog.md for source/profile
   bindings and retained earlier failures. Canonical unit shard has no skips,
   import aliases or dependency stubs. Publication security gates remain open.
3. Allocate a consumer in the existing durable FAM TestNet intent owner. Bind
   admitted intent identity to immutable artifact, attempt and explicit reissue;
   do not add a second ledger or infer reward units from generic payout amounts.
4. Separately admit authenticated ledger facts: realm/snapshot provenance, current
   rounds, address/rekey authority, ASA decimals, holdings/opt-in/freeze, spendable
   balance and exact fee policy. Address checksum alone proves none of these.
5. Only a later explicitly authorized signer/transport layer may consider signing
   or submission. UTC expiry, confirmation, replay and paid-state gates remain
   independent. No SDK account, key or client capability is admitted by this module.
