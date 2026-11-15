# Algorand unsigned probe codec

## Current security boundary — 2026-10-29

This component accepts unsigned ASA transfer format only. Algorand's current
[account signing documentation](https://dev.algorand.co/concepts/transactions/signing/)
distinguishes ordinary and Falcon accounts; State Proofs and consensus have
separate trust boundaries. This codec neither chooses nor verifies a signature
algorithm. A checksum address, source-binding digest or TestNet label does not
prove controller authority, quantum resistance, funded rewards or settlement.
The frozen Python3.12.10 qualification below is dated format evidence; it does
not qualify a patched production interpreter or a future signer.

### Canonical JSON framing

`format_unsigned_probe_request(request_json: bytes) -> bytes` exposes the same
unsigned format through bounded canonical ASCII JSON. It accepts the15 existing
request fields and returns six fields describing immutable bytes and their hashes.
It builds and generally validates the packet through the existing codec; it adds
no alternative wire decoder. See INTERFACE.md for exact byte and scalar bounds.

All52 methods pass in local and distinct hosted profiles; exact bindings are recorded
in tests/TestModLog.md. Old28-method results remain historical. Output hashes bind
declared request data and wire bytes; they grant no producer or account authority.
This API adds no FAM caller, process launch, durable artifact, signing or settlement.

## Original codec layer — historical28-method qualification

This module prepares and validates an unsigned ASA transfer **format** for
`TEST_TRANSPORT_PROBE` on the documented Algorand TestNet realm. It returns
immutable bytes, the SDK transaction ID and a separate digest of the declared
request. All 28 exact unittest methods pass in the independently reviewed local
Windows CPython 3.12.10 materialized profile. CI uses a distinct pip installation
and must qualify that environment separately; source authoring is not a test result.

Import the public functions from
`modules.platform_integration.algorand.src.unsigned_asa_probe`. Supply an exact
`UnsignedASAProbeRequest`; use `build_unsigned_asa_probe(request)` to build and
`validate_unsigned_asa_probe(raw_bytes, expected_request)` to compare against an
independently chosen expected request. See [INTERFACE.md](INTERFACE.md) for fields.
No SDK transaction object crosses this boundary.

The request binds declared asset decimals, expected authorization address and
source identity. Those declarations do not establish repository control, account
authority, current holdings, opt-in, freeze state, spendable balance, fee adequacy
or ledger authenticity. The unsigned wire format carries neither the declared
decimals nor the expected authorization address. There is no mint, reward,
account creation, signing, client, provider, database or chain interaction here.

The codec fixes `algorand-testnet`, `testnet-v1.0` and its documented genesis hash.
Reference: [official networks](https://dev.algorand.co/concepts/protocol/networks/),
checked 2026-10-25. The public hash is a realm identifier, not an authenticated
node snapshot. Exact integer amounts use ASA base units; no currency conversion
or FoundUps reward denomination is inferred.

Production dependency declarations are [requirements.txt](requirements.txt).
The dedicated qualification lock/profile additionally binds transitive wheels,
interpreter and execution controls. Root requirements and whole-FAM jobs are
unchanged under the allocated isolated-profile scope. The external seven-function
dependency experiment does not qualify this codec or ordinary pip/pytest use.

Next consumer: the existing FAM durable TestNet intent owner, after trusted ledger
facts and artifact/attempt/reissue ownership are specified. There is currently no
resident caller. UTC intent expiry does not become a wire expiry automatically;
round windows, current ledger rounds and any reissue must be checked separately.

See [tests/README.md](tests/README.md), [ROADMAP.md](ROADMAP.md) and
[memory/README.md](memory/README.md).
