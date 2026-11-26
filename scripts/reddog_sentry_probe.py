#!/usr/bin/env python3
"""Submit one approved, content-free synthetic application error when opted in."""
from __future__ import annotations

import importlib.util
import argparse
import json
from pathlib import Path


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, '{"status":"INVALID_ARGUMENTS","delivery_verified":false}\n')


def main(argv=None):
    SafeParser(description=__doc__).parse_args(argv)
    source = Path(__file__).resolve().parents[1] / "modules/infrastructure/monitoring/src/sentry_error_telemetry.py"
    spec = importlib.util.spec_from_file_location("foundups_sentry_probe", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.report_application_error(component="telemetry_probe", reason="synthetic_probe")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "SUBMITTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
