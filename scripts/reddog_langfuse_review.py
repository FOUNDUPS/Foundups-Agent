#!/usr/bin/env python3
"""Read a bounded, content-free Langfuse diagnostic packet without task execution."""
from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
from pathlib import Path


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, '{"ok":false,"reason":"invalid_arguments"}\n')


class CredentialError(ValueError):
    """Fixed errors that never include credential values or private paths."""


def credential_pair(env_file=None):
    source = os.environ
    if env_file is not None:
        try:
            from dotenv import dotenv_values
            from dotenv.parser import parse_stream

            with Path(env_file).open(encoding="utf-8-sig") as stream:
                contents = stream.read(65537)
            if len(contents) > 65536:
                raise ValueError
            if any(binding.error for binding in parse_stream(io.StringIO(contents))):
                raise ValueError
            source = dotenv_values(stream=io.StringIO(contents), interpolate=False)
        except Exception:
            raise CredentialError("env_file_unavailable") from None
    names = ("LANGFUSE_VIEWER_PUBLIC_KEY", "LANGFUSE_VIEWER_SECRET_KEY")
    if not any(name in source for name in names):
        names = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")
    pair = tuple(source.get(name) for name in names)
    if any(not isinstance(value, str) or not value.strip() for value in pair):
        raise CredentialError("credentials_incomplete")
    return pair


def _report_error(reason):
    if os.environ.get("FOUNDUPS_SENTRY_ENABLED") != "1":
        return
    try:
        source = Path(__file__).resolve().parents[1] / "modules/infrastructure/monitoring/src/sentry_error_telemetry.py"
        spec = importlib.util.spec_from_file_location("foundups_sentry_cli", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.report_application_error(component="langfuse_review", reason=reason)
    except Exception:
        pass


def main(argv=None) -> int:
    parser = SafeParser(description=__doc__)
    parser.add_argument("--from-time", required=True, help="Inclusive UTC ISO-8601 timestamp")
    parser.add_argument("--to-time", required=True, help="Exclusive UTC ISO-8601 timestamp (range <=7 days)")
    parser.add_argument("--base-url", default="https://jp.cloud.langfuse.com")
    parser.add_argument("--trace-id", help="Optional OTel 32-character lowercase hexadecimal trace ID")
    parser.add_argument("--max-pages", type=int, default=5, help="1-5 pages of <=100 rows")
    parser.add_argument("--timeout", type=float, default=10, help="Per-request socket timeout, >0 to15 seconds")
    parser.add_argument("--env-file", help="Explicit credential source; no discovery or process-environment merging")
    args = parser.parse_args(argv)
    source = Path(__file__).resolve().parents[1] / "modules/communication/moltbot_bridge/src/reddog_langfuse_telemetry.py"
    spec = importlib.util.spec_from_file_location("reddog_langfuse_lookup", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        public_key, secret_key = credential_pair(args.env_file)
        options = vars(args).copy()
        options.pop("env_file")
        result = module.read_review(public_key=public_key, secret_key=secret_key, **options)
    except (CredentialError, module.TelemetryError) as exc:
        _report_error(str(exc))
        print(json.dumps({"ok": False, "reason": str(exc)}))
        return 2
    print(json.dumps({"ok": True, **result}, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
