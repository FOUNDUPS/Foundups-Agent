"""Explicit issuer-only wire role; legacy target projection stays byte stable."""
SCHEMA_VERSION_V2 = "foundup-root-revocation-anchor-service.v2"
SIGNING_PREFIX_V2 = "foundup-root-revocation-anchor-request.v2."
TARGET_ROLE = "target_signer"
GRANT_ROLE = "grant_issuer"
GRANT_PEER_PRINCIPAL = "reddog-root-grant-issuer"
ROLE_FIELDS = {"requester_role", "requester_principal_id", "requester_key_epoch"}


def request_payload(value):
    payload = dict(value)
    if payload.get("requester_role", TARGET_ROLE) == TARGET_ROLE:
        for field in ROLE_FIELDS:
            payload.pop(field, None)
    return payload


def require_request_role(value):
    if value.requester_role == TARGET_ROLE:
        if value.requester_principal_id is not None or value.requester_key_epoch is not None:
            raise ValueError("root_revocation_request_role_invalid")
    elif (value.requester_role != GRANT_ROLE or value.operation != "REVOCATION_ANCHOR_LOAD"
          or any(type(item) is not str or not item or not item.isascii()
                 for item in (value.requester_principal_id, value.requester_key_epoch))):
        raise ValueError("root_revocation_request_role_invalid")
