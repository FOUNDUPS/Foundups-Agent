from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

output = subprocess.check_output(
    [sys.executable, "scripts/generate_reddog_backend_manifest.py", "--write"],
    cwd=ROOT,
    text=True,
)
digest = output.splitlines()[0].strip()
if not re.fullmatch(r"[a-f0-9]{64}", digest):
    raise SystemExit(f"invalid manifest digest: {digest!r}")

test_path = ROOT / "scripts/tests/test_generate_reddog_backend_manifest.py"
test_text = test_path.read_text(encoding="utf-8")
test_text, count = re.subn(
    r'assert digest == "[a-f0-9]{64}"',
    f'assert digest == "{digest}"',
    test_text,
    count=1,
)
if count != 1:
    raise SystemExit("manifest test pin not found exactly once")
test_path.write_text(test_text, encoding="utf-8", newline="\n")

constants_path = ROOT / "extensions/reddog/backend_compatibility_constants.js"
constants = constants_path.read_text(encoding="utf-8")
constants, count = re.subn(
    r"EXPECTED_MANIFEST_SHA256 = '[a-f0-9]{64}'",
    f"EXPECTED_MANIFEST_SHA256 = '{digest}'",
    constants,
    count=1,
)
if count != 1:
    raise SystemExit("backend manifest constant not found exactly once")
constants_path.write_text(constants, encoding="utf-8", newline="\n")

subprocess.check_call(
    [sys.executable, "scripts/generate_reddog_backend_manifest.py", "--check"],
    cwd=ROOT,
)
subprocess.check_call(
    [sys.executable, "-m", "pytest", "scripts/tests/test_generate_reddog_backend_manifest.py", "-q"],
    cwd=ROOT,
)
print(digest)
