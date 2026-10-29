"""Pure unsigned TestNet ASA format boundary, without ledger or signing authority."""

import base64
from dataclasses import asdict, dataclass
import hashlib
import json
import re

import msgpack
from algosdk import encoding, transaction


_GENESIS_HASH = "4863b518a4b3c84ec810f22d4f1081cb0f71f059a7ac20dec62f7f70e5093a22"
_WIRE_FIELDS = frozenset(("type", "snd", "arcv", "xaid", "aamt", "fee", "fv", "lv", "gh", "gen"))
_INTEGER_FIELDS = ("asset_id", "amount_atoms", "fee_microalgos", "fee_cap_microalgos",
                   "first_valid_round", "last_valid_round")
_BINDING_DOMAIN = b"foundups:unsigned-asa-probe:request:v1\0"


@dataclass(frozen=True, slots=True)
class UnsignedASAProbeRequest:
    """Declared facts for one format-only probe; no field grants authority."""

    purpose: str
    network: str
    genesis_id: str
    genesis_hash_hex: str
    sender_address: str
    expected_auth_address: str
    recipient_address: str
    asset_id: int
    asset_decimals: int
    amount_atoms: int
    fee_microalgos: int
    fee_cap_microalgos: int
    first_valid_round: int
    last_valid_round: int
    source_identity_sha256: str


@dataclass(frozen=True, slots=True)
class UnsignedASAProbe:
    """Unsigned bytes, the SDK transaction ID and a separate declared-fact binding."""

    unsigned_bytes: bytes
    transaction_id: str
    source_binding_sha256: str


def _address(value, field):
    if type(value) is not str or len(value) != 58:
        raise ValueError(field)
    try:
        decoded = encoding.decode_address(value)
        canonical = encoding.encode_address(decoded)
    except Exception:
        raise ValueError(field) from None
    if type(decoded) is not bytes or len(decoded) != 32 or not any(decoded) or canonical != value:
        raise ValueError(field)


def _check_request(request):
    if type(request) is not UnsignedASAProbeRequest:
        raise ValueError("request")
    for field in _INTEGER_FIELDS:
        value = getattr(request, field)
        if type(value) is not int or not 1 <= value <= 2**63 - 1:
            raise ValueError(field)
    if type(request.asset_decimals) is not int or not 0 <= request.asset_decimals <= 19:
        raise ValueError("asset_decimals")
    if not request.first_valid_round <= request.last_valid_round <= request.first_valid_round + 1000:
        raise ValueError("last_valid_round")
    if request.fee_microalgos > request.fee_cap_microalgos:
        raise ValueError("fee_microalgos")
    for field, expected in (("purpose", "TEST_TRANSPORT_PROBE"), ("network", "algorand-testnet"),
                            ("genesis_id", "testnet-v1.0"), ("genesis_hash_hex", _GENESIS_HASH)):
        value = getattr(request, field)
        if type(value) is not str or value != expected:
            raise ValueError(field)
    value = request.source_identity_sha256
    if type(value) is not str or re.fullmatch("[0-9a-f]{64}", value) is None:
        raise ValueError("source_identity_sha256")
    for field in ("sender_address", "recipient_address", "expected_auth_address"):
        _address(getattr(request, field), field)


def _artifact(request):
    # The SDK's non-flat estimator generates an account and signs. Never invoke it.
    params = transaction.SuggestedParams(
        fee=request.fee_microalgos, first=request.first_valid_round,
        last=request.last_valid_round,
        gh=base64.b64encode(bytes.fromhex(request.genesis_hash_hex)).decode("ascii"),
        gen=request.genesis_id, flat_fee=True,
    )
    txn = transaction.AssetTransferTxn(
        sender=request.sender_address, sp=params, receiver=request.recipient_address,
        amt=request.amount_atoms, index=request.asset_id,
    )
    raw = base64.b64decode(encoding.msgpack_encode(txn), validate=True)
    canonical_request = json.dumps(asdict(request), sort_keys=True, separators=(",", ":"),
                                   ensure_ascii=True).encode("ascii")
    binding = hashlib.sha256(_BINDING_DOMAIN + canonical_request).hexdigest()
    return UnsignedASAProbe(raw, txn.get_txid(), binding)


def build_unsigned_asa_probe(request):
    """Build a canonical unsigned packet from exact scalar declarations.

    Rounds and fees are declared format bounds, not current ledger facts.
    Decimals and expected authorization address are bound only in the digest.
    """
    _check_request(request)
    return _artifact(request)


def _unique_map(pairs):
    result = {}
    for key, value in pairs:
        if type(key) is not str or key in result:
            raise ValueError("unsigned_bytes")
        result[key] = value
    return result


def _decode_wire(raw):
    if type(raw) is not bytes or not 1 <= len(raw) <= 1024:
        raise ValueError("unsigned_bytes")
    try:
        wire = msgpack.unpackb(raw, raw=False, strict_map_key=True, object_pairs_hook=_unique_map,
                               max_map_len=10, max_array_len=0, max_str_len=64,
                               max_bin_len=32, max_ext_len=0)
    except Exception:
        raise ValueError("unsigned_bytes") from None
    if type(wire) is not dict or wire.keys() != _WIRE_FIELDS:
        raise ValueError("unsigned_bytes")
    for field in ("xaid", "aamt", "fee", "fv", "lv"):
        value = wire[field]
        if type(value) is not int or not 1 <= value <= 2**63 - 1:
            raise ValueError(field)
    for field in ("snd", "arcv", "gh"):
        value = wire[field]
        if type(value) is not bytes or len(value) != 32 or not any(value):
            raise ValueError(field)
    for field, expected in (("type", "axfer"), ("gen", "testnet-v1.0")):
        if type(wire[field]) is not str or wire[field] != expected:
            raise ValueError(field)
    return wire


def validate_unsigned_asa_probe(unsigned_bytes, expected_request):
    """Validate strict canonical bytes against a separately supplied expected request.

    Unknown fields, signed wrappers, duplicate keys, trailing objects and alternate
    encodings fail. This performs no host snapshot or on-chain admission check.
    """
    _check_request(expected_request)
    _decode_wire(unsigned_bytes)
    expected = _artifact(expected_request)
    if unsigned_bytes != expected.unsigned_bytes:
        raise ValueError("unsigned_bytes")
    return expected
