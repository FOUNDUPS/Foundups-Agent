"""Isolated proposal ASGI factory using trusted server configuration only.

No default policy, dotenv, network/JWKS lookup, persistence or cloud deployment.
The existing draft verifier/handler retain all authentication and body semantics.
"""

import json
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from modules.ai_intelligence.ai_overseer.src.foundup_genesis.clerk_intake import ClerkIntakePolicy
from modules.foundups.pfmall.http_api import foundup_proposal

_CONFIG_BYTES = 16 * 1024


def _unique_fields(pairs: list) -> dict:
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("duplicate_configuration_field")
        result[name] = value
    return result


def create_app() -> FastAPI:
    """Construct only after a bounded, explicit operator-selected policy loads.

    PFMALL_CLERK_POLICY_FILE names an absolute regular file. Its public RSA key,
    issuer and allowed origins are administrative inputs, never HTTP input.
    Local file integrity/custody and deployment policy remain the host's duty.
    """
    try:
        path = Path(os.environ["PFMALL_CLERK_POLICY_FILE"])
        if not path.is_absolute() or not path.is_file():
            raise ValueError
        with path.open("rb") as source:
            raw = source.read(_CONFIG_BYTES + 1)
        if len(raw) > _CONFIG_BYTES:
            raise ValueError
        values = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_fields)
        if (type(values) is not dict
                or set(values) != {"issuer", "authorized_parties", "public_key_pem"}
                or type(values["authorized_parties"]) is not list):
            raise ValueError
        policy = ClerkIntakePolicy(values["issuer"], tuple(values["authorized_parties"]),
                                   values["public_key_pem"])
    except Exception:
        raise RuntimeError("intake_configuration_invalid") from None

    application = FastAPI(title="FoundUp draft intake", docs_url=None,
                          redoc_url=None, openapi_url=None)
    application.state.clerk_intake_policy = policy
    application.add_api_route("/pfmall/proposals", foundup_proposal, methods=["POST"])

    @application.get("/healthz")
    def health() -> JSONResponse:
        return JSONResponse({"status": "ready"}, headers={"Cache-Control": "no-store"})

    return application
