"""OBS logging guard for third-party WebSocket clients.

The obsws_python package can include connection parameters in log records and
object representations. This module installs a narrow redaction filter and
raises known obsws loggers above INFO before constructing any OBS client.
"""

from __future__ import annotations

import logging
import re
from typing import Any


_REDACTED = "<redacted>"
_OBS_LOGGER_NAMES = (
    "obsws_python",
    "obsws_python.baseclient",
    "obsws_python.baseclient.ObsClient",
    "obsws_python.reqs",
    "obsws_python.reqs.ReqClient",
)

_SECRET_PATTERNS = (
    re.compile(r"(?P<prefix>\bpassword\s*=\s*)'[^']*'", re.IGNORECASE),
    re.compile(r'(?P<prefix>\bpassword\s*=\s*)"[^"]*"', re.IGNORECASE),
    re.compile(r"(?P<prefix>\bpassword\s*=\s*)([^,\s)]+)", re.IGNORECASE),
    re.compile(r"(?P<prefix>['\"]password['\"]\s*:\s*)'[^']*'", re.IGNORECASE),
    re.compile(r'(?P<prefix>[\'"]password[\'"]\s*:\s*)"[^"]*"', re.IGNORECASE),
    re.compile(r"(?P<prefix>['\"]authentication['\"]\s*:\s*)'[^']*'", re.IGNORECASE),
    re.compile(r'(?P<prefix>[\'"]authentication[\'"]\s*:\s*)"[^"]*"', re.IGNORECASE),
    re.compile(r"(?P<prefix>\bauthentication\s*=\s*)'[^']*'", re.IGNORECASE),
    re.compile(r'(?P<prefix>\bauthentication\s*=\s*)"[^"]*"', re.IGNORECASE),
    re.compile(r"(?P<prefix>['\"]key['\"]\s*:\s*)'[^']+'", re.IGNORECASE),
    re.compile(r'(?P<prefix>[\'"]key[\'"]\s*:\s*)"[^"]+"', re.IGNORECASE),
    re.compile(r"(?P<prefix>\bkey\s*=\s*)'[^']+'", re.IGNORECASE),
    re.compile(r'(?P<prefix>\bkey\s*=\s*)"[^"]+"', re.IGNORECASE),
    re.compile(r"(?P<prefix>\bstream_key\s*=\s*)'[^']+'", re.IGNORECASE),
    re.compile(r'(?P<prefix>\bstream_key\s*=\s*)"[^"]+"', re.IGNORECASE),
)


def redact_obs_log_message(value: Any) -> str:
    """Return a log-safe string with OBS credentials redacted."""
    text = str(value)
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(lambda match: f"{match.group('prefix')}'{_REDACTED}'", text)
    return text


class OBSSecretRedactionFilter(logging.Filter):
    """Redact OBS/WebSocket secrets from log records before handlers emit them."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_obs_log_message(record.getMessage())
        record.args = ()
        return True


def _has_redaction_filter(target: Any) -> bool:
    return any(isinstance(filter_, OBSSecretRedactionFilter) for filter_ in target.filters)


def _attach_filter(target: Any) -> None:
    if not _has_redaction_filter(target):
        target.addFilter(OBSSecretRedactionFilter())


def install_obs_logging_guard() -> None:
    """Install OBS log redaction and suppress known verbose obsws loggers.

    This function is idempotent and safe to call before every OBS client
    construction.
    """
    root = logging.getLogger()
    _attach_filter(root)
    for handler in root.handlers:
        _attach_filter(handler)

    for logger_name in _OBS_LOGGER_NAMES:
        obs_logger = logging.getLogger(logger_name)
        obs_logger.setLevel(logging.WARNING)
        _attach_filter(obs_logger)
        for handler in obs_logger.handlers:
            _attach_filter(handler)


def create_obs_req_client(obs_module: Any, *, host: str, port: int, password: str) -> Any:
    """Create an obsws_python ReqClient after installing the logging guard."""
    install_obs_logging_guard()
    return obs_module.ReqClient(host=host, port=port, password=password)
