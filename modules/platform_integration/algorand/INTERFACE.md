# Unsigned ASA probe interface

Public owner: `src/unsigned_asa_probe.py`. Both functions require the exact
`UnsignedASAProbeRequest` class; subclasses, mappings and implicit coercions fail.
Records are frozen, slotted dataclasses containing only scalar fields or bytes.

| Request field | Accepted declaration |
| --- | --- |
| `purpose` | Exact string `TEST_TRANSPORT_PROBE` |
| `network` | Exact string `algorand-testnet` |
| `genesis_id` | Exact string `testnet-v1.0` |
| `genesis_hash_hex` | `4863b518a4b3c84ec810f22d4f1081cb0f71f059a7ac20dec62f7f70e5093a22` |
| `sender_address`, `recipient_address`, `expected_auth_address` | Canonical checksum addresses representing nonzero32-byte public identifiers |
| `asset_id`, `amount_atoms` | Built-in integers1 through `2**63-1`; amount is exact ASA base units |
| `fee_microalgos`, `fee_cap_microalgos` | Built-in integers1 through `2**63-1`; exact fee cannot exceed declared cap |
| `first_valid_round`, `last_valid_round` | Built-in integers1 through `2**63-1`; last >=first and last-first <=1000 |
| `asset_decimals` | Built-in integer0 through19; declared metadata only |
| `source_identity_sha256` | Exact64 lowercase hexadecimal characters; declared identity only |

Booleans, floats, custom scalar subclasses and nonfinite values are rejected.
No minimum network fee, current ledger round or economic unit policy is inferred.
An equal first/last round and a difference of1000 are valid format bounds; this
does not assert inclusion or acceptance on a live network.

`build_unsigned_asa_probe(request) -> UnsignedASAProbe` validates declarations and
uses `SuggestedParams(flat_fee=True)` and `AssetTransferTxn`. It never invokes
the SDK's non-flat fee estimator, which generates an account and signs.

`validate_unsigned_asa_probe(unsigned_bytes, expected_request) -> UnsignedASAProbe`
requires exact `bytes`, length1..1024. It rejects duplicate/nonstring keys, missing
or unknown fields, signed/nested wrappers, extra objects, malformed values and
noncanonical ordering, integer widths or binary encodings. Types are checked
before comparison. Its only permitted wire keys are `type`, `snd`, `arcv`, `xaid`,
`aamt`, `fee`, `fv`, `lv`, `gh`, `gen`; expected SDK serialization must match exactly.
Generic SDK packet deserialization is deliberately unnecessary at this boundary.

The result contains exactly:

- `unsigned_bytes`: immutable canonical raw MessagePack bytes.
- `transaction_id`: actual SDK `get_txid()` result, binding the wire bytes.
- `source_binding_sha256`: SHA256 of domain bytes
  `foundups:unsigned-asa-probe:request:v1` followed by one NUL byte and canonical
  ASCII JSON of every request field (`sort_keys=True`, separators comma/colon,
  `ensure_ascii=True`). This is distinct from a wire hash or authorization proof.

Changing declared auth/decimals/source identity/fee cap changes the binding while
the transaction ID may remain the same. The caller must supply trusted expected
declarations; validation does not make them trusted. Errors are `ValueError`
containing field names only and do not echo supplied values. This is a new format
contract without a persisted artifact migration or a settlement state transition.

### Canonical JSON entrypoint

`format_unsigned_probe_request(request_json: bytes) -> bytes` accepts exact
builtin bytes, length1..4096: one ASCII JSON object with exactly the15 fields
above. Duplicate keys (including escaped collisions), missing/unknown keys,
nonfinite numbers and wrong builtin scalar kinds reject before DTO construction.
Existing request validation retains semantic ownership of all field bounds.
Canonical input/output uses sorted keys, compact comma/colon separators,
`ensure_ascii=True`, `allow_nan=False`, and no terminal whitespace or newline.
Equivalent parsed values do not make differently spelled input canonical.

Build through `build_unsigned_asa_probe`, then pass its wire and the parsed
expected request to the unchanged `validate_unsigned_asa_probe`. Use the
validated artifact's sidecars. Output is exact immutable ASCII bytes<=16384:

- `schema`: `foundups-unsigned-probe-worker-result-v1`.
- `request_sha256`: SHA256 of the exact canonical input bytes.
- `unsigned_hex`: lowercase hex of canonical unsigned wire, length1..1024 bytes.
- `unsigned_sha256`: SHA256 of that raw wire.
- `transaction_id`: actual SDK transaction ID for that wire.
- `source_binding_sha256`: existing domain+all15-request digest described above.

Errors are field-name-only `ValueError`, with parser diagnostics suppressed.
The envelope supplies no executable/profile/grant authority or current ledger fact.
