"""Tests for OBS WebSocket secret log redaction."""

from __future__ import annotations

import io
import logging

from modules.platform_integration.antifafm_broadcaster.src.obs_logging_guard import (
    OBSSecretRedactionFilter,
    create_obs_req_client,
    install_obs_logging_guard,
    redact_obs_log_message,
)


SYNTHETIC_PASSWORD = "synthetic-obs-password"
SYNTHETIC_AUTH = "synthetic-auth-token"
SYNTHETIC_STREAM_KEY = "synthetic-stream-key"


def test_redact_obs_log_message_masks_password_authentication_and_keys():
    message = (
        "ReqClient(host='localhost', password='synthetic-obs-password', "
        "authentication=\"synthetic-auth-token\", key='synthetic-stream-key', "
        "stream_key=\"synthetic-stream-key\")"
    )

    redacted = redact_obs_log_message(message)

    assert SYNTHETIC_PASSWORD not in redacted
    assert SYNTHETIC_AUTH not in redacted
    assert SYNTHETIC_STREAM_KEY not in redacted
    assert redacted.count("<redacted>") >= 4


def test_redaction_filter_masks_formatted_log_record():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(OBSSecretRedactionFilter())
    logger = logging.getLogger("tests.obs_redaction_filter")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    try:
        logger.info("OBS connect password='%s'", SYNTHETIC_PASSWORD)
    finally:
        logger.removeHandler(handler)

    output = stream.getvalue()
    assert SYNTHETIC_PASSWORD not in output
    assert "password='<redacted>'" in output


def test_install_obs_logging_guard_suppresses_known_obsws_info_loggers():
    install_obs_logging_guard()

    for logger_name in (
        "obsws_python",
        "obsws_python.baseclient",
        "obsws_python.reqs",
    ):
        assert logging.getLogger(logger_name).getEffectiveLevel() >= logging.WARNING


def test_create_obs_req_client_redacts_third_party_constructor_logs():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    obs_logger = logging.getLogger("obsws_python.baseclient")
    obs_logger.addHandler(handler)
    obs_logger.setLevel(logging.WARNING)
    obs_logger.propagate = False

    class FakeObsModule:
        class ReqClient:
            def __init__(self, *, host, port, password):
                self.host = host
                self.port = port
                self.password = password
                logging.getLogger("obsws_python.baseclient").warning(
                    "ReqClient(host='%s', port=%s, password='%s')",
                    host,
                    port,
                    password,
                )

    try:
        client = create_obs_req_client(
            FakeObsModule,
            host="localhost",
            port=4455,
            password=SYNTHETIC_PASSWORD,
        )
    finally:
        obs_logger.removeHandler(handler)

    output = stream.getvalue()
    assert client.password == SYNTHETIC_PASSWORD
    assert SYNTHETIC_PASSWORD not in output
    assert "password='<redacted>'" in output
