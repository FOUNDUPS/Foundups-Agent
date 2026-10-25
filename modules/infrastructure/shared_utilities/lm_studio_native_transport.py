"""Bounded loopback transport and exact native LM Studio inventory parsing."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


DEFAULT_LM_STUDIO_BASE_URL = "http://localhost:1234"
MAX_CONFIG_BYTES = 16_384
MAX_CONTROL_RESPONSE_BYTES = 65_536
MAX_INVENTORY_BYTES = 1_048_576
MAX_INSTANCES_PER_MODEL = 16
MAX_MODELS = 512
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


class _RejectRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class LMStudioAuthenticationError(RuntimeError):
    """LM Studio rejected or requires an API token."""


class LMStudioResidencyState(str, Enum):
    SERVER_UNREACHABLE = "server_unreachable"
    NOT_INSTALLED = "not_installed"
    INSTALLED_NOT_RESIDENT = "installed_not_resident"
    RESIDENT = "resident"


@dataclass(frozen=True)
class LMStudioLoadedInstance:
    instance_id: str
    config: Mapping[str, Any]


@dataclass(frozen=True)
class LMStudioModelState:
    model_key: str
    state: LMStudioResidencyState
    loaded_instances: tuple[LMStudioLoadedInstance, ...]
    total_resident_instances: int = 0
    max_context_length: int | None = None
    model_size_bytes: int | None = None


def inspect_lm_studio_model(
    model_key: str,
    *,
    base_url: str = DEFAULT_LM_STUDIO_BASE_URL,
    api_token: str | None = None,
    timeout: float = 2.0,
) -> LMStudioModelState:
    """Return installed, exact residency, and node-capacity facts without loading."""

    key = required_text("model_key", model_key)
    root = normalize_lm_studio_base_url(base_url)
    try:
        payload = request_lm_studio_json(
            f"{root}/api/v1/models",
            method="GET",
            api_token=api_token,
            timeout=bounded_timeout(timeout),
            max_response_bytes=MAX_INVENTORY_BYTES,
        )
    except LMStudioAuthenticationError:
        raise
    except (OSError, TimeoutError, urllib.error.URLError):
        return LMStudioModelState(
            key, LMStudioResidencyState.SERVER_UNREACHABLE, ()
        )
    return _model_state_from_inventory(key, payload)


def normalize_lm_studio_base_url(value: str) -> str:
    """Normalize an HTTP loopback-only LM Studio server root."""

    parsed = urllib.parse.urlsplit(str(value or "").strip())
    try:
        port = parsed.port or 1234
    except ValueError as exc:
        raise ValueError("lm_studio_base_url_invalid") from exc
    if (
        parsed.scheme != "http"
        or parsed.hostname not in _LOOPBACK_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path.rstrip("/") not in {"", "/v1"}
        or not 1 <= port <= 65_535
    ):
        raise ValueError("lm_studio_base_url_invalid")
    host = f"[{parsed.hostname}]" if parsed.hostname == "::1" else parsed.hostname
    return f"http://{host}:{port}"


def lm_studio_node_identity(base_url: str) -> str:
    """Collapse loopback aliases to one physical-node/port capacity identity."""

    parsed = urllib.parse.urlsplit(normalize_lm_studio_base_url(base_url))
    return f"loopback:{parsed.port or 1234}"


def request_lm_studio_json(
    url: str,
    *,
    method: str,
    api_token: str | None,
    timeout: float,
    max_response_bytes: int,
    payload: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    """Issue one bounded, redirect-rejecting native request."""

    headers = {"Content-Type": "application/json"}
    token = validate_api_token(api_token)
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    data = None if payload is None else json_bytes(payload, MAX_CONFIG_BYTES)
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with _open_no_redirect(request, timeout=timeout) as response:
            if hasattr(response, "geturl") and response.geturl() != url:
                raise ValueError("lm_studio_redirect_rejected")
            raw = response.read(max_response_bytes + 1)
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            raise LMStudioAuthenticationError(
                "lm_studio_authentication_failed"
            ) from None
        raise RuntimeError(f"lm_studio_http_status_{exc.code}") from None
    if len(raw) > max_response_bytes:
        raise ValueError("lm_studio_response_too_large")
    try:
        decoded = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("lm_studio_response_json_invalid") from exc
    if not isinstance(decoded, Mapping):
        raise ValueError("lm_studio_response_shape_invalid")
    return decoded


def validate_api_token(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value or len(value) > 8192:
        raise ValueError("lm_studio_api_token_invalid")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError("lm_studio_api_token_invalid")
    return value


def bounded_timeout(value: float) -> float:
    timeout = float(value)
    if not 0.1 <= timeout <= 600.0:
        raise ValueError("lm_studio_timeout_invalid")
    return timeout


def required_text(name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError(f"lm_studio_{name}_invalid")
    text = value.strip()
    if not text or len(text.encode("utf-8")) > 512 or any(ord(c) < 32 for c in text):
        raise ValueError(f"lm_studio_{name}_invalid")
    return text


def canonical_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"lm_studio_{name}_invalid")
    encoded = json_bytes(value, MAX_CONFIG_BYTES)
    decoded = json.loads(encoded)
    if not isinstance(decoded, dict):
        raise ValueError(f"lm_studio_{name}_invalid")
    return decoded


def json_bytes(value: Any, cap: int) -> bytes:
    try:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("lm_studio_json_invalid") from exc
    if len(encoded) > cap:
        raise ValueError("lm_studio_json_too_large")
    return encoded


def _model_state_from_inventory(
    model_key: str, payload: Mapping[str, Any]
) -> LMStudioModelState:
    models = payload.get("models")
    if not isinstance(models, list) or len(models) > MAX_MODELS:
        raise ValueError("lm_studio_inventory_invalid")
    total_resident = _count_resident_instances(models)
    matches = [
        item
        for item in models
        if isinstance(item, Mapping) and item.get("key") == model_key
    ]
    if not matches:
        return LMStudioModelState(
            model_key,
            LMStudioResidencyState.NOT_INSTALLED,
            (),
            total_resident,
        )
    if len(matches) != 1 or matches[0].get("type") != "llm":
        raise ValueError("lm_studio_model_identity_ambiguous")
    model = matches[0]
    instances = _parse_instances(model.get("loaded_instances"))
    maximum = _positive_integer_or_none(model.get("max_context_length"))
    size_bytes = _positive_integer_or_none(model.get("size_bytes"))
    status = (
        LMStudioResidencyState.RESIDENT
        if instances
        else LMStudioResidencyState.INSTALLED_NOT_RESIDENT
    )
    return LMStudioModelState(
        model_key, status, instances, total_resident, maximum, size_bytes
    )


def _count_resident_instances(models: list[Any]) -> int:
    count = 0
    for item in models:
        if not isinstance(item, Mapping):
            raise ValueError("lm_studio_inventory_model_invalid")
        instances = item.get("loaded_instances")
        if not isinstance(instances, list) or len(instances) > MAX_INSTANCES_PER_MODEL:
            raise ValueError("lm_studio_loaded_instances_invalid")
        count += len(instances)
    return count


def _parse_instances(value: Any) -> tuple[LMStudioLoadedInstance, ...]:
    if not isinstance(value, list) or len(value) > MAX_INSTANCES_PER_MODEL:
        raise ValueError("lm_studio_loaded_instances_invalid")
    result: list[LMStudioLoadedInstance] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError("lm_studio_loaded_instance_invalid")
        instance_id = required_text("instance_id", item.get("id"))
        config = canonical_mapping(item.get("config"), "observed_config")
        if instance_id in seen:
            raise ValueError("lm_studio_loaded_instance_duplicate")
        seen.add(instance_id)
        result.append(LMStudioLoadedInstance(instance_id, config))
    return tuple(result)


def _positive_integer_or_none(value: Any) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 1:
        raise ValueError("lm_studio_inventory_capacity_invalid")
    return value


def _open_no_redirect(request: urllib.request.Request, *, timeout: float) -> Any:
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), _RejectRedirectHandler()
    )
    return opener.open(request, timeout=timeout)


__all__ = [
    "DEFAULT_LM_STUDIO_BASE_URL",
    "LMStudioAuthenticationError",
    "LMStudioLoadedInstance",
    "LMStudioModelState",
    "LMStudioResidencyState",
    "bounded_timeout",
    "canonical_mapping",
    "inspect_lm_studio_model",
    "json_bytes",
    "lm_studio_node_identity",
    "normalize_lm_studio_base_url",
    "request_lm_studio_json",
    "required_text",
    "validate_api_token",
]
