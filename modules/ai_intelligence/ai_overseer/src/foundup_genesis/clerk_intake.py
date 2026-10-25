"""Server-selected Clerk session authentication for draft proposals only.

No environment loading, cookies, HMAC downgrade, JWKS lookup, storage or grants.
The optional HTTP profile supplies PyJWT/cryptography. Legacy intake is unchanged.
Offline verification cannot establish remote revocation, membership or repo control.
This is the explicit server-only exception documented in the module INTERFACE;
legacy sole-provider comments describe the unchanged sess.v1/invite.v1 contract.
"""

from dataclasses import dataclass, field
import hashlib
import re
from urllib.parse import urlsplit

from .intake_transport import IntakeResult, intake_request
from .launch_request import LaunchRequestIntakeContext


def _https_origin(value: object) -> bool:
    if type(value) is not str or not value.isascii() or len(value) > 2048:
        return False
    parsed = urlsplit(value)
    return (parsed.scheme == "https" and bool(parsed.hostname)
            and parsed.username is None and parsed.password is None
            and not any((parsed.path, parsed.query, parsed.fragment))
            and not any(c.isspace() or c == "*" for c in value)
            and (parsed.port is None or 0 < parsed.port < 65536))


@dataclass(frozen=True, slots=True)
class ClerkIntakePolicy:
    """Trusted server configuration, never constructed from an HTTP payload."""

    issuer: str
    authorized_parties: tuple[str, ...]
    public_key_pem: str = field(repr=False)
    _public_key: object = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        try:
            if (not _https_origin(self.issuer)
                    or type(self.authorized_parties) is not tuple
                    or not 1 <= len(self.authorized_parties) <= 8
                    or not all(_https_origin(party) for party in self.authorized_parties)
                    or len(set(self.authorized_parties)) != len(self.authorized_parties)
                    or type(self.public_key_pem) is not str
                    or not 0 < len(self.public_key_pem) <= 8192):
                raise ValueError
            from cryptography.hazmat.primitives.serialization import load_pem_public_key
            from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
            key = load_pem_public_key(self.public_key_pem.encode("ascii"))
            if not isinstance(key, RSAPublicKey) or not 2048 <= key.key_size <= 4096:
                raise ValueError
            object.__setattr__(self, "_public_key", key)
        except Exception:
            raise ValueError("invalid_clerk_intake_policy") from None


def _header(headers: dict, name: str) -> str | None:
    values = [value for key, value in headers.items() if key.lower() == name]
    return values[0] if len(values) == 1 and type(values[0]) is str else None


def _verify_session(headers: dict, policy: ClerkIntakePolicy) -> LaunchRequestIntakeContext:
    """Fail closed with no diagnostic claims/token/key in the returned context."""
    try:
        auth, origin = _header(headers, "authorization"), _header(headers, "origin")
        if (type(policy) is not ClerkIntakePolicy or auth is None or len(auth) > 8192
                or origin not in policy.authorized_parties):
            return LaunchRequestIntakeContext()
        match = re.fullmatch(r"(?i:Bearer) ([A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)", auth)
        if match is None:
            return LaunchRequestIntakeContext()
        import jwt
        decoded = jwt.decode_complete(match[1], key=policy._public_key,
            algorithms=["RS256"], issuer=policy.issuer, leeway=0,
            options={"require": ["iss", "sub", "sid", "v", "azp", "iat", "nbf", "exp"]})
        header, claims = decoded["header"], decoded["payload"]
        if (header.get("typ") != "JWT" or any(k in header for k in ("crit", "jku", "jwk", "x5u"))
                or any(k in claims for k in ("aud", "sts", "act"))
                or type(claims["v"]) is not int or claims["v"] != 2
                or claims["azp"] != origin
                or type(claims["sub"]) is not str
                or re.fullmatch(r"user_[A-Za-z0-9]{1,128}", claims["sub"]) is None
                or type(claims["sid"]) is not str
                or re.fullmatch(r"sess_[A-Za-z0-9]{1,128}", claims["sid"]) is None
                or any(type(claims[k]) is not int for k in ("iat", "nbf", "exp"))
                or not 0 < claims["exp"] - claims["iat"] <= 120
                or not 0 <= claims["nbf"] <= claims["iat"]):
            return LaunchRequestIntakeContext()
        binding = hashlib.sha256((policy.issuer + "\0" + claims["sub"]).encode("utf-8")).hexdigest()
        return LaunchRequestIntakeContext(authenticated=True, requester_handle="clerk_" + binding)
    except Exception:
        return LaunchRequestIntakeContext()


def intake_clerk_request(headers, body, *, policy: ClerkIntakePolicy) -> IntakeResult:
    """Reuse complete legacy body preflight, with one explicit server-only provider.

    The old HMAC extractor may discard a JWT; this provider deliberately verifies
    the captured transport metadata instead. It never reads proposal auth fields.
    No invite is consumed and a bad bearer cannot fall back to another mechanism.
    """
    try:
        captured_headers = dict(headers)
    except Exception:
        return IntakeResult("rejected", None, "invalid_request", 400)

    def provider(_session, _invite, **_kwargs):
        return _verify_session(captured_headers, policy)

    return intake_request(captured_headers, body, _provider=provider)
