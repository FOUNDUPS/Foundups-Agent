"""Unsigned probe format contracts; execute only in the admitted SDK profile.

Golden packets use a separate stdlib-only MessagePack/SHA512-256 derivation.
Synthetic public addresses have no asserted private-key or ledger identity.
"""

import base64
import dataclasses
import hashlib
import json
import socket
import subprocess
import unittest
from unittest import mock

import msgpack
from algosdk import account

from modules.platform_integration.algorand.src.unsigned_asa_probe import (
    UnsignedASAProbe,
    UnsignedASAProbeRequest,
    build_unsigned_asa_probe,
    validate_unsigned_asa_probe,
)
from .qualify_sdk import assert_guarded, expected_denial
from modules.platform_integration.algorand.src import unsigned_asa_probe as codec


SENDER = "AEBAGBAFAYDQQCIKBMGA2DQPCAIREEYUCULBOGAZDINRYHI6D4QDTYK3BA"
RECEIVER = "EERCGJBFEYTSQKJKFMWC2LRPGAYTEMZUGU3DOOBZHI5TYPJ6H5APQGQK7A"
AUTH = "IFBEGRCFIZDUQSKKJNGE2TSPKBIVEU2UKVLFOWCZLJNVYXK6L5QDK3LAIY"
GENESIS = "4863b518a4b3c84ec810f22d4f1081cb0f71f059a7ac20dec62f7f70e5093a22"
GOLDEN = bytes.fromhex(
    "8aa461616d7411a461726376c4202122232425262728292a2b2c2d2e2f303132333435"
    "363738393a3b3c3d3e3f40a3666565cd03e8a26676ce000f4240a367656eac746573"
    "746e65742d76312e30a26768c4204863b518a4b3c84ec810f22d4f1081cb0f71f059"
    "a7ac20dec62f7f70e5093a22a26c76ce000f4434a3736e64c4200102030405060708"
    "090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20a474797065a561786665"
    "72a478616964cd1092"
)
BOUNDARY = bytes.fromhex(
    "8aa461616d74cf7fffffffffffffffa461726376c4202122232425262728292a2b2c2d"
    "2e2f303132333435363738393a3b3c3d3e3f40a366656501a2667601a367656eac74"
    "6573746e65742d76312e30a26768c4204863b518a4b3c84ec810f22d4f1081cb0f71"
    "f059a7ac20dec62f7f70e5093a22a26c76cd03e9a3736e64c4200102030405060708"
    "090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20a474797065a561786665"
    "72a47861696401"
)


def request(**changes):
    values = dict(purpose="TEST_TRANSPORT_PROBE", network="algorand-testnet",
                  genesis_id="testnet-v1.0", genesis_hash_hex=GENESIS,
                  sender_address=SENDER, expected_auth_address=AUTH,
                  recipient_address=RECEIVER, asset_id=4242, asset_decimals=6,
                  amount_atoms=17, fee_microalgos=1000, fee_cap_microalgos=2000,
                  first_valid_round=1000000, last_valid_round=1000500,
                  source_identity_sha256="a" * 64)
    return UnsignedASAProbeRequest(**(values | changes))


def packet(**changes):
    return msgpack.packb(msgpack.unpackb(GOLDEN, raw=False) | changes, use_bin_type=True)


class IntSubclass(int):
    pass


class StrSubclass(str):
    pass


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def request_json(**changes):
    return canonical_json(dataclasses.asdict(request(**changes)))


class UnsignedASAProbeTests(unittest.TestCase):
    def setUp(self):
        assert_guarded()

    def reject_request(self, field, value):
        candidate = request(**{field: value})
        for operation in (lambda: build_unsigned_asa_probe(candidate),
                          lambda: validate_unsigned_asa_probe(GOLDEN, candidate)):
            with self.assertRaises(ValueError) as caught:
                operation()
            self.assertEqual(str(caught.exception), field)

    def reject_packet(self, raw):
        with self.assertRaises(ValueError):
            validate_unsigned_asa_probe(raw, request())

    def test_golden_packet_and_actual_sdk_transaction_id(self):
        result = build_unsigned_asa_probe(request())
        self.assertEqual(result.unsigned_bytes, GOLDEN)
        self.assertEqual(result.transaction_id, "N3GLERTNMD6GC443Q67RAVH7SCKB7EDEMY55W3T6QIPG7ZOAIMXQ")
        self.assertEqual(result.source_binding_sha256, "9a88e8909de608735f94c61724a278e869b816e6389dbb520d74fde20f994686")
        self.assertEqual(validate_unsigned_asa_probe(GOLDEN, request()), result)

    def test_independent_boundary_vector(self):
        candidate = request(asset_id=1, asset_decimals=19, amount_atoms=2**63-1,
                            fee_microalgos=1, first_valid_round=1, last_valid_round=1001)
        result = build_unsigned_asa_probe(candidate)
        self.assertEqual(result.unsigned_bytes, BOUNDARY)
        self.assertEqual(result.transaction_id, "RVE2KBMHTH3H3GCJTH5JNXKMH6LW5OD4N77UGIVH7QSPBK3BXMTQ")
        self.assertEqual(result.source_binding_sha256, "5f2eec7d9759af3b5d71408e7130e78c07d502376db3531926ef31740f5cf3a9")
        self.assertEqual(validate_unsigned_asa_probe(BOUNDARY, candidate), result)

    def test_txid_is_transaction_hash_not_request_digest(self):
        result = build_unsigned_asa_probe(request())
        calculated = base64.b32encode(hashlib.new("sha512_256", b"TX" + GOLDEN).digest()).decode().rstrip("=")
        self.assertEqual(result.transaction_id, calculated)
        self.assertNotEqual(result.source_binding_sha256, hashlib.sha256(GOLDEN).hexdigest())

    def test_request_and_artifact_are_immutable_scalar_records(self):
        candidate = request()
        result = build_unsigned_asa_probe(candidate)
        self.assertIs(type(result), UnsignedASAProbe)
        self.assertIs(type(result.unsigned_bytes), bytes)
        self.assertEqual([f.name for f in dataclasses.fields(result)],
                         ["unsigned_bytes", "transaction_id", "source_binding_sha256"])
        for obj, field, value in ((candidate, "amount_atoms", 99), (result, "unsigned_bytes", b"")):
            with self.assertRaises(dataclasses.FrozenInstanceError):
                setattr(obj, field, value)
            self.assertFalse(hasattr(obj, "__dict__"))

    def test_declared_metadata_changes_binding_not_wire_authority(self):
        original = build_unsigned_asa_probe(request())
        for change in (dict(expected_auth_address=RECEIVER), dict(asset_decimals=0),
                       dict(source_identity_sha256="b" * 64), dict(fee_cap_microalgos=3000)):
            with self.subTest(change=next(iter(change))):
                candidate = request(**change)
                result = validate_unsigned_asa_probe(GOLDEN, candidate)
                self.assertEqual(result.unsigned_bytes, original.unsigned_bytes)
                self.assertEqual(result.transaction_id, original.transaction_id)
                self.assertNotEqual(result.source_binding_sha256, original.source_binding_sha256)

    def test_exact_request_type_required(self):
        class Derived(UnsignedASAProbeRequest):
            pass
        for candidate in (None, dataclasses.asdict(request()), Derived(**dataclasses.asdict(request()))):
            with self.subTest(kind=type(candidate).__name__):
                with self.assertRaises(ValueError):
                    build_unsigned_asa_probe(candidate)
                with self.assertRaises(ValueError):
                    validate_unsigned_asa_probe(GOLDEN, candidate)

    def test_positive_integer_fields_reject_coercion_and_overflow(self):
        for field in ("asset_id", "amount_atoms", "fee_microalgos", "fee_cap_microalgos",
                      "first_valid_round", "last_valid_round"):
            for value in (0, -1, True, False, 1.0, IntSubclass(1), 2**63, "1", None):
                with self.subTest(field=field, kind=type(value).__name__):
                    self.reject_request(field, value)

    def test_asset_decimals_exact_bounds(self):
        for value in (-1, 20, True, 1.0, IntSubclass(6), "6", None):
            with self.subTest(kind=type(value).__name__):
                self.reject_request("asset_decimals", value)
        self.assertEqual(build_unsigned_asa_probe(request(asset_decimals=0)).unsigned_bytes, GOLDEN)

    def test_round_span_and_fee_cap(self):
        self.reject_request("last_valid_round", 999999)
        self.reject_request("last_valid_round", 1001001)
        self.reject_request("fee_microalgos", 2001)
        self.assertEqual(build_unsigned_asa_probe(request(fee_cap_microalgos=1000)).unsigned_bytes, GOLDEN)
        build_unsigned_asa_probe(request(last_valid_round=1000000))

    def test_exact_probe_realm_and_public_genesis(self):
        for field, values in (("purpose", ["PAYOUT", ""]), ("network", ["algorand-mainnet", ""]),
                              ("genesis_id", ["mainnet-v1.0", "testnet-v1.0 "]),
                              ("genesis_hash_hex", ["0" * 64, GENESIS.upper(), GENESIS[:-1]])):
            for value in values:
                with self.subTest(field=field):
                    self.reject_request(field, value)

    def test_canonical_nonzero_checksum_addresses(self):
        zero = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAY5HFKQ"
        for field in ("sender_address", "recipient_address", "expected_auth_address"):
            for value in ("", zero, SENDER.lower(), SENDER[:-1] + "X", SENDER + "=", b"x" * 58, None):
                with self.subTest(field=field, kind=type(value).__name__):
                    self.reject_request(field, value)

    def test_declared_source_hash_requires_lowercase_hex(self):
        for value in ("A" * 64, "g" * 64, "a" * 63, "a" * 65, b"a" * 64, None):
            self.reject_request("source_identity_sha256", value)

    def test_string_subclasses_are_not_scalar_contract_values(self):
        for field in ("purpose", "network", "genesis_id", "genesis_hash_hex", "sender_address",
                      "recipient_address", "expected_auth_address", "source_identity_sha256"):
            self.reject_request(field, StrSubclass(getattr(request(), field)))

    def test_expected_request_wire_mismatch(self):
        for changes in (dict(asset_id=4243), dict(amount_atoms=18), dict(fee_microalgos=1001),
                        dict(first_valid_round=1000001), dict(last_valid_round=1000501),
                        dict(sender_address=RECEIVER), dict(recipient_address=SENDER)):
            with self.subTest(field=next(iter(changes))):
                with self.assertRaises(ValueError):
                    validate_unsigned_asa_probe(GOLDEN, request(**changes))

    def test_forbidden_and_unknown_wire_fields(self):
        for field in ("rekey", "close", "aclose", "asnd", "grp", "note", "lx", "lease", "unknown"):
            with self.subTest(field=field):
                self.reject_packet(packet(**{field: b"x" * 32}))

    def test_signed_and_nested_wrappers_rejected(self):
        inner = msgpack.unpackb(GOLDEN, raw=False)
        for wrapper in ({"txn": inner}, {"sig": b"x" * 64, "txn": inner},
                        {"lsig": {}, "txn": inner}, [inner], None):
            self.reject_packet(msgpack.packb(wrapper, use_bin_type=True))

    def test_every_wire_field_required(self):
        wire = msgpack.unpackb(GOLDEN, raw=False)
        for field in wire:
            self.reject_packet(msgpack.packb({k: v for k, v in wire.items() if k != field}, use_bin_type=True))

    def test_wire_integer_types_before_equality(self):
        for field in ("aamt", "fee", "fv", "lv", "xaid"):
            for value in (True, False, 0, -1, 17.0, "17", None, 2**63):
                with self.subTest(field=field, kind=type(value).__name__):
                    self.reject_packet(packet(**{field: value}))

    def test_wire_binary_and_realm_types(self):
        for field in ("snd", "arcv", "gh"):
            for value in (b"", b"x" * 31, b"x" * 33, "x" * 32, [1] * 32, b"\0" * 32):
                self.reject_packet(packet(**{field: value}))
        for field, value in (("type", b"axfer"), ("type", "pay"), ("gen", b"testnet-v1.0"),
                             ("gen", "mainnet-v1.0"), ("gh", b"x" * 32)):
            self.reject_packet(packet(**{field: value}))

    def test_duplicate_keys_even_when_equal_rejected(self):
        pairs = list(msgpack.unpackb(GOLDEN, raw=False).items())
        pairs[-1] = ("fee", 1000)
        duplicate = b"\x8a" + b"".join(msgpack.packb(k) + msgpack.packb(v, use_bin_type=True) for k, v in pairs)
        self.reject_packet(duplicate)

    def test_noncanonical_order_width_and_bin_forms_rejected(self):
        wire = msgpack.unpackb(GOLDEN, raw=False)
        self.reject_packet(msgpack.packb(dict(reversed(list(wire.items()))), use_bin_type=True))
        self.reject_packet(GOLDEN.replace(bytes.fromhex("a461616d7411"), bytes.fromhex("a461616d74cc11"), 1))
        self.reject_packet(GOLDEN.replace(b"\xc4\x20", b"\xc5\x00\x20", 1))

    def test_nonstring_map_key_rejected(self):
        wire = msgpack.unpackb(GOLDEN, raw=False)
        del wire["fee"]
        self.reject_packet(msgpack.packb(wire | {1: 1000}, use_bin_type=True))

    def test_trailing_truncated_oversize_and_nonbytes_rejected(self):
        for raw in (GOLDEN + b"\0", GOLDEN[:-1], b"", b"x" * 1025, bytearray(GOLDEN),
                    memoryview(GOLDEN), GOLDEN.hex(), None, b"\xc1"):
            with self.subTest(kind=type(raw).__name__):
                self.reject_packet(raw)

    def test_errors_never_echo_supplied_values(self):
        marker = "private-value-must-not-appear"
        with self.assertRaises(ValueError) as caught:
            build_unsigned_asa_probe(request(source_identity_sha256=marker))
        self.assertEqual(str(caught.exception), "source_identity_sha256")
        self.assertNotIn(marker, str(caught.exception))

    def test_socket_negative_control(self):
        expected_denial("socket", lambda: socket.socket())

    def test_dns_negative_control(self):
        expected_denial("dns", lambda: socket.getaddrinfo("invalid.example", 443))

    def test_process_negative_control(self):
        expected_denial("subprocess", lambda: subprocess.Popen(["forbidden-codec-probe"]))

    def test_account_negative_control_and_flat_fee_build(self):
        expected_denial("account_sign_client", account.generate_account)
        self.assertEqual(build_unsigned_asa_probe(request()).unsigned_bytes, GOLDEN)


    def format_result(self, candidate=None):
        candidate = request() if candidate is None else candidate
        raw_request = canonical_json(dataclasses.asdict(candidate))
        output = codec.format_unsigned_probe_request(raw_request)
        self.assertIs(type(output), bytes)
        self.assertLessEqual(len(output), 16384)
        body = json.loads(output.decode("ascii"))
        self.assertEqual(set(body), {"schema", "request_sha256", "unsigned_hex",
                                   "unsigned_sha256", "transaction_id", "source_binding_sha256"})
        self.assertTrue(all(type(value) is str for value in body.values()))
        self.assertEqual(output, canonical_json(body))
        self.assertEqual(body["schema"], "foundups-unsigned-probe-worker-result-v1")
        self.assertEqual(body["request_sha256"], hashlib.sha256(raw_request).hexdigest())
        self.assertRegex(body["unsigned_hex"], r"\A(?:[0-9a-f]{2})+\Z")
        wire = bytes.fromhex(body["unsigned_hex"])
        self.assertTrue(1 <= len(wire) <= 1024)
        self.assertEqual(body["unsigned_sha256"], hashlib.sha256(wire).hexdigest())
        self.assertRegex(body["transaction_id"], r"\A[A-Z2-7]{52}\Z")
        self.assertEqual(body["transaction_id"], base64.b32encode(
            hashlib.new("sha512_256", b"TX" + wire).digest()).decode().rstrip("="))
        self.assertEqual(body["source_binding_sha256"], hashlib.sha256(
            b"foundups:unsigned-asa-probe:request:v1\0" + raw_request).hexdigest())
        return output, body

    def reject_json(self, raw):
        with self.assertRaises(ValueError):
            codec.format_unsigned_probe_request(raw)

    def test_format_golden_six_field_output(self):
        _, body = self.format_result()
        self.assertEqual(bytes.fromhex(body["unsigned_hex"]), GOLDEN)
        self.assertEqual(body["transaction_id"], "N3GLERTNMD6GC443Q67RAVH7SCKB7EDEMY55W3T6QIPG7ZOAIMXQ")
        self.assertEqual(body["source_binding_sha256"], "9a88e8909de608735f94c61724a278e869b816e6389dbb520d74fde20f994686")

    def test_format_independent_boundary_six_field_output(self):
        candidate = request(asset_id=1, asset_decimals=19, amount_atoms=2**63-1,
                            fee_microalgos=1, first_valid_round=1, last_valid_round=1001)
        _, body = self.format_result(candidate)
        self.assertEqual(bytes.fromhex(body["unsigned_hex"]), BOUNDARY)
        self.assertEqual(body["transaction_id"], "RVE2KBMHTH3H3GCJTH5JNXKMH6LW5OD4N77UGIVH7QSPBK3BXMTQ")
        self.assertEqual(body["source_binding_sha256"], "5f2eec7d9759af3b5d71408e7130e78c07d502376db3531926ef31740f5cf3a9")

    def test_format_changed_request_not_fixed_golden(self):
        candidate = request(asset_id=4243, amount_atoms=18, fee_microalgos=1001,
                            first_valid_round=1000001, last_valid_round=1000999)
        _, body = self.format_result(candidate)
        wire = bytes.fromhex(body["unsigned_hex"])
        self.assertNotIn(wire, (GOLDEN, BOUNDARY))
        self.assertEqual(validate_unsigned_asa_probe(wire, candidate),
                         build_unsigned_asa_probe(candidate))

    def test_format_declaration_binding_does_not_authorize_wire(self):
        _, original = self.format_result()
        for changes in (dict(expected_auth_address=RECEIVER), dict(asset_decimals=0),
                        dict(source_identity_sha256="b" * 64), dict(fee_cap_microalgos=3000)):
            with self.subTest(field=next(iter(changes))):
                _, body = self.format_result(request(**changes))
                self.assertEqual(body["unsigned_hex"], original["unsigned_hex"])
                self.assertEqual(body["transaction_id"], original["transaction_id"])
                self.assertNotEqual(body["request_sha256"], original["request_sha256"])
                self.assertNotEqual(body["source_binding_sha256"], original["source_binding_sha256"])

    def test_format_deterministic_immutable_bytes_and_exact_request_hash(self):
        raw = request_json()
        before = bytes(raw)
        first, body = self.format_result()
        second = codec.format_unsigned_probe_request(raw)
        self.assertEqual(first, second)
        self.assertIs(type(second), bytes)
        self.assertEqual(raw, before)
        self.assertEqual(body["request_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertNotEqual(body["request_sha256"], body["unsigned_sha256"])

    def test_format_exact_bytes_input_type(self):
        class Derived(bytes):
            pass
        class Coercible:
            def __bytes__(self):
                raise AssertionError("coercion")
            def __len__(self):
                raise AssertionError("length")
        raw = request_json()
        for candidate in (None, raw.decode(), bytearray(raw), memoryview(raw),
                          Derived(raw), Coercible()):
            with self.subTest(kind=type(candidate).__name__):
                self.reject_json(candidate)

    def test_format_input_size_checked_before_parse(self):
        with mock.patch.object(codec.json, "loads", side_effect=AssertionError("parser_called")):
            for raw in (b"", b"x" * 4097):
                with self.subTest(length=len(raw)):
                    self.reject_json(raw)
        self.reject_json(b"x" * 4096)

    def test_format_nonascii_bom_and_nul_input(self):
        raw = request_json()
        for candidate in (b"\xef\xbb\xbf" + raw, b"\xff\xfe" + raw.decode().encode("utf-16-le"),
                          raw.replace(b"TEST_TRANSPORT_PROBE", "probe\u00e9".encode()),
                          raw.replace(b"TEST_TRANSPORT_PROBE", b"probe\0")):
            self.reject_json(candidate)

    def test_format_malformed_truncated_and_trailing_input(self):
        raw = request_json()
        for candidate in (raw[:-1], b"{", raw + b"{}", raw + b"false", raw[:-1] + b",}",
                          b'{"amount_atoms":' + b"[" * 1500 + b"]" * 1500 + b"}"):
            self.reject_json(candidate)

    def test_format_exact_top_level_object(self):
        for value in (None, [], [dataclasses.asdict(request())], True, 17, "request"):
            self.reject_json(canonical_json(value))

    def test_format_duplicate_equal_conflicting_and_escaped_keys(self):
        raw = request_json()
        for tail in (b',"amount_atoms":17}', b',"amount_atoms":18}',
                     b',"amount\\u005fatoms":17}', b',"unknown":1,"unknown":1}'):
            self.reject_json(raw[:-1] + tail)

    def test_format_exact_fifteen_fields(self):
        values = dataclasses.asdict(request())
        self.assertEqual(len(values), 15)
        for field in values:
            with self.subTest(missing=field):
                self.reject_json(canonical_json({k: v for k, v in values.items() if k != field}))
        for field in ("unknown", "authorization", "profile", "producer_grant_sha256"):
            self.reject_json(canonical_json(values | {field: "untrusted"}))

    def test_format_canonical_key_order_and_whitespace(self):
        values = dataclasses.asdict(request())
        raw = request_json()
        reordered = dict(reversed(sorted(values.items())))
        for candidate in (b" " + raw, raw + b" ", raw + b"\n",
                          json.dumps(values, sort_keys=True).encode(),
                          json.dumps(reordered, separators=(",", ":")).encode()):
            self.reject_json(candidate)

    def test_format_canonical_escapes_and_negative_zero(self):
        raw = request_json()
        for candidate in (raw.replace(b'"purpose"', b'"\\u0070urpose"', 1),
                          raw.replace(SENDER.encode(), b"\\u0041" + SENDER[1:].encode(), 1),
                          request_json(asset_decimals=0).replace(
                              b'"asset_decimals":0', b'"asset_decimals":-0', 1)):
            self.reject_json(candidate)

    def test_format_bool_float_and_numeric_strings(self):
        for field in ("asset_id", "amount_atoms", "fee_microalgos", "fee_cap_microalgos",
                      "first_valid_round", "last_valid_round", "asset_decimals"):
            for value in (True, False, 1.0, "1"):
                with self.subTest(field=field, kind=type(value).__name__):
                    values = dataclasses.asdict(request()) | {field: value}
                    self.reject_json(canonical_json(values))

    def test_format_null_nested_and_wrong_scalar_kinds(self):
        values = dataclasses.asdict(request())
        for field, original in values.items():
            wrong = (None, [], {}) + ((1, True) if type(original) is str else ())
            for value in wrong:
                with self.subTest(field=field, kind=type(value).__name__):
                    self.reject_json(canonical_json(values | {field: value}))

    def test_format_nonfinite_literals_and_exponent_overflow(self):
        raw = request_json()
        for value in (b"NaN", b"Infinity", b"-Infinity", b"1e999"):
            self.reject_json(raw.replace(b'"amount_atoms":17', b'"amount_atoms":' + value, 1))

    def test_format_exact_integer_and_decimal_bounds(self):
        for field in ("asset_id", "amount_atoms", "fee_microalgos", "fee_cap_microalgos",
                      "first_valid_round", "last_valid_round"):
            for value in (0, -1, 2**63, 10**100):
                self.reject_json(request_json(**{field: value}))
        for value in (-1, 20):
            self.reject_json(request_json(asset_decimals=value))
        self.format_result(request(asset_decimals=0))

    def test_format_existing_realm_address_fee_round_rules(self):
        for field, value in (("purpose", "PAYOUT"), ("network", "algorand-mainnet"),
                             ("genesis_id", "mainnet-v1.0"), ("genesis_hash_hex", "0" * 64),
                             ("sender_address", SENDER.lower()),
                             ("recipient_address", SENDER[:-1] + "X"),
                             ("expected_auth_address", AUTH.lower()),
                             ("source_identity_sha256", "g" * 64),
                             ("fee_microalgos", 2001), ("last_valid_round", 999999),
                             ("last_valid_round", 1001001)):
            with self.subTest(field=field):
                self.reject_json(request_json(**{field: value}))

    def test_format_wrong_expected_request_wire_rejected(self):
        other = build_unsigned_asa_probe(request(amount_atoms=18))
        with mock.patch.object(codec, "build_unsigned_asa_probe", return_value=other):
            self.reject_json(request_json())

    def test_format_malformed_and_unbounded_emitted_wire_rejected(self):
        original = build_unsigned_asa_probe(request())
        inner = msgpack.unpackb(GOLDEN, raw=False)
        duplicate = b"\x8b" + GOLDEN[1:] + msgpack.packb("fee") + msgpack.packb(1000)
        malformed = (b"", b"x" * 1025, bytearray(GOLDEN), GOLDEN + b"\0", duplicate,
                     packet(unknown=b"x"), msgpack.packb({"sig": b"x" * 64, "txn": inner}, use_bin_type=True),
                     msgpack.packb(dict(reversed(list(inner.items()))), use_bin_type=True))
        for raw in malformed:
            poisoned = dataclasses.replace(original, unsigned_bytes=raw)
            with mock.patch.object(codec, "build_unsigned_asa_probe", return_value=poisoned):
                self.reject_json(request_json())

    def test_format_validated_artifact_sidecars_are_used(self):
        original = build_unsigned_asa_probe(request())
        poisoned = dataclasses.replace(original, transaction_id="unvalidated",
                                       source_binding_sha256="f" * 64)
        with mock.patch.object(codec, "build_unsigned_asa_probe", return_value=poisoned):
            _, body = self.format_result()
        self.assertEqual(body["transaction_id"], original.transaction_id)
        self.assertEqual(body["source_binding_sha256"], original.source_binding_sha256)

    def test_format_maximum_real_valid_output_bounds(self):
        largest = 2**63 - 1
        candidate = request(asset_id=largest, amount_atoms=largest, asset_decimals=19,
                            fee_microalgos=largest, fee_cap_microalgos=largest,
                            first_valid_round=largest, last_valid_round=largest)
        output, body = self.format_result(candidate)
        self.assertLessEqual(len(request_json(**dataclasses.asdict(candidate))), 4096)
        self.assertLessEqual(len(bytes.fromhex(body["unsigned_hex"])), 1024)
        self.assertLessEqual(len(output), 16384)

    def test_format_errors_do_not_echo_input(self):
        marker = "submitted-value-must-not-appear"
        for raw in (canonical_json(dataclasses.asdict(request()) | {marker: marker}),
                    request_json(source_identity_sha256=marker),
                    b'{"' + marker.encode() + b'":'):
            with self.assertRaises(ValueError) as caught:
                codec.format_unsigned_probe_request(raw)
            self.assertIn(str(caught.exception), ("request_json", "source_identity_sha256"))
            self.assertNotIn(marker, str(caught.exception))
            self.assertIsNone(caught.exception.__cause__)
            if caught.exception.__context__ is not None:
                self.assertTrue(caught.exception.__suppress_context__)
