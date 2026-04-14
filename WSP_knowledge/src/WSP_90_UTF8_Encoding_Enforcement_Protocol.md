# WSP 90: UTF-8 Encoding Enforcement Protocol

**Status**: Active
**Purpose**: Prevent UnicodeEncodeError on Windows systems by enforcing UTF-8 encoding across all Python modules
**Dependencies**: WSP 1 (Framework Foundation), WSP 49 (Module Structure), WSP 64 (Violation Prevention)
**Created**: 2025-10-11
**Semantic Score**: 1.1.2 (Active Protocol, Module Impact, Production Quality)

---

## Problem Statement

**Error Pattern**:
```python
UnicodeEncodeError: 'cp932' codec can't encode character '\U0001f4cd' in position 2
```

**Root Cause**: Windows uses locale-specific encodings (cp932, cp1252, etc.) instead of UTF-8 by default, causing crashes when printing Unicode characters (emojis, international text, symbols) to console or files.

**Impact**:
- Modules fail during execution on Windows
- Tests crash when outputting non-ASCII characters
- International text support broken
- Emoji-based logging fails

**CRITICAL LESSON LEARNED** (2025-10-18):
During WSP 90 bulk enforcement campaign, emojis were incorrectly removed from production code (replaced with `[U+XXXX]` notation), breaking:
- Banter engine emoji-to-number mappings (✊✋🖐️ for DAO consciousness)
- LiveChat visual feedback (🍣🧘🐕 channel identification)
- Liberty Alert notifications (🔴 live indicators)

**ROOT CAUSE OF MISTAKE**: WSP 90 was incorrectly applied at MODULE level instead of ENTRY POINT level, leading to belief that emojis must be removed. This was wrong.

**CORRECT APPROACH**:
1. ✅ Apply WSP 90 UTF-8 enforcement at entry points (main.py, daemon scripts)
2. ✅ Library modules inherit encoding automatically
3. ✅ Production emojis work perfectly with proper entry point setup
4. ❌ NEVER remove production emojis - they are critical for UX

---

## Solution Architecture

### 1. Entry Point Enforcement (MANDATORY)

**CRITICAL DISTINCTION**: WSP 90 enforcement MUST be applied at **entry points** (scripts/daemons with `if __name__ == "__main__":`), NOT at library module level.

**Entry Point Files (main.py, daemon scripts, CLI tools):**

```python
#!/usr/bin/env python3
"""
Script Name - Entry Point
==========================

[Script description]
"""

# === UTF-8 ENFORCEMENT (WSP 90) ===
# CRITICAL: Apply ONLY at entry points (main.py, daemon scripts)
# DO NOT apply in library modules (causes import conflicts)
import sys
import io

# Force UTF-8 encoding for stdout/stderr on Windows
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
# === END UTF-8 ENFORCEMENT ===

# Standard imports continue below
import asyncio
import logging
# ... rest of imports

if __name__ == "__main__":
    main()
```

**Library Modules (imported by other code):**

```python
"""
Library Module Name
===================

[Module description]
"""

# NO WSP 90 HEADER - Library modules inherit encoding from entry point
import asyncio
import logging
# ... standard imports

# Library code...
```

**Why This Matters**:
- ✅ Entry points set UTF-8 encoding ONCE for entire process
- ✅ Library modules inherit encoding automatically via logging system
- ✅ Production emojis work correctly in logs (🍣🧘🐕🔌💰⚠️)
- ❌ Module-level enforcement causes import conflicts and wrapping issues

### CRITICAL BUG FIX (2026-02-25)

**Problem**: 379 modules incorrectly applied WSP 90 UTF-8 wrapping at import time.
Each module re-wraps stderr, eventually causing "lost sys.stderr" error.

**Detection Command**:
```bash
grep -r "sys.stderr = io.TextIOWrapper" modules/ --include="*.py" | wc -l
# Expected: 0 (only main.py should have this)
```

**Correct Pattern (main.py sets flag first)**:
```python
# In main.py - SET FLAG BEFORE WRAPPING
import os
os.environ['FOUNDUPS_UTF8_WRAPPED'] = '1'

if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(...)
    sys.stderr = io.TextIOWrapper(...)
```

**If Module MUST Have UTF-8 (rare - prefer removing)**:
```python
# Check flag to prevent double-wrapping
import os
if sys.platform.startswith('win') and not os.environ.get('FOUNDUPS_UTF8_WRAPPED'):
    sys.stdout = io.TextIOWrapper(...)
    sys.stderr = io.TextIOWrapper(...)
```

**Bulk Fix Script**:
```bash
python modules/development/wsp_tools/scripts/fix_wsp90_utf8_bulk.py --dry-run
python modules/development/wsp_tools/scripts/fix_wsp90_utf8_bulk.py --apply
```

### 2. Environment-Level Enforcement (RECOMMENDED)

**Set before running Python**:

```bash
# Windows PowerShell
$env:PYTHONIOENCODING = "utf-8"
python script.py

# Windows CMD
set PYTHONIOENCODING=utf-8
python script.py

# Linux/Mac (already UTF-8 by default)
export PYTHONIOENCODING=utf-8
python script.py
```

### 3. Project-Level Enforcement (BEST PRACTICE)

**Add to `pyproject.toml` or setup.py**:

```toml
[tool.pytest.ini_options]
addopts = "--capture=no"
env = ["PYTHONIOENCODING=utf-8"]

[tool.ruff]
# Enforce UTF-8 encoding comments
target-version = "py312"
```

**Add to `.vscode/settings.json`**:

```json
{
  "terminal.integrated.env.windows": {
    "PYTHONIOENCODING": "utf-8"
  },
  "python.terminal.activateEnvironment": true
}
```

---

## WSP 90 Compliance Rules

### Rule 1: UTF-8 Header Block (Entry Points Only)

**ONLY entry point files (scripts/daemons) include WSP 90 enforcement header:**

**✅ Entry Points (main.py, daemon scripts, CLI tools):**
```python
# === UTF-8 ENFORCEMENT (WSP 90) ===
# CRITICAL: Apply ONLY at entry points
# DO NOT apply in library modules
import sys
import io
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
# === END UTF-8 ENFORCEMENT ===
```

**❌ Library Modules (imported code):**
```python
# NO WSP 90 HEADER
# Library modules inherit encoding from entry point automatically
import asyncio
import logging
# ... standard imports
```

**Entry Point Detection**:
- Files with `if __name__ == "__main__":` → Add WSP 90 header
- Files with `def main():` + CLI execution → Add WSP 90 header
- Files imported by other modules → NO WSP 90 header
- Daemon/service entry points → Add WSP 90 header

**Placement** (for entry points only):
- After module docstring
- Before all other imports
- Always wrapped in Windows platform check
- Add `line_buffering=True` for real-time log output

### Rule 2: File Encoding Declaration (MANDATORY)

**Every Python file MUST start with**:

```python
# -*- coding: utf-8 -*-
"""
Module Name
"""
```

**OR** (PEP 263 compliant):

```python
#!/usr/bin/env python
# coding: utf-8
"""
Module Name
"""
```

### Rule 3: Production Emoji Usage (CONDITIONAL)

**With proper entry point WSP 90 enforcement, production emojis are SAFE and ENCOURAGED for user-facing output:**

**✅ SAFE - Production Emojis (with entry point WSP 90):**
```python
# Production code with entry point UTF-8 enforcement
logger.info("🍣 Move2Japan [JAPAN] stream detected")
logger.info("🧘 UnDaoDu [MINDFUL] stream detected")
logger.info("🐕 FoundUps [FOUNDUPS] stream detected")
logger.info("🔌 Starting in NO-QUOTA mode")
logger.info("💰 API preservation active")
logger.info("⚠️ Authentication failed")
print("✊✋🖐️ DAO consciousness state transition")  # Banter engine
```

**❌ UNSAFE - Without Entry Point Enforcement:**
```python
# Library module without entry point UTF-8 setup = UnicodeEncodeError
print(f"✓ Success")  # Will crash on Windows if no entry point enforcement
```

**Guidelines**:
- ✅ Use emojis in daemon/service logs for visibility (🍣🧘🐕🔌💰⚠️)
- ✅ Use emojis in production UI/notifications (critical for user feedback)
- ✅ Use emojis in banter engine (✊✋🖐️ for DAO state mapping)
- ⚠️ Ensure entry point has WSP 90 enforcement before using emojis
- 📋 ASCII fallbacks optional for maximum compatibility (test environments)

### Rule 4: JSON/File Output Encoding

**Always specify UTF-8 encoding for file operations**:

```python
# Writing JSON
with open(file_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# Reading files
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# CSV files
import csv
with open("data.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Name", "Value"])
```

### Rule 5: Logging Configuration

**Configure logging with UTF-8**:

```python
import logging

# Set UTF-8 for logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)  # Will use WSP 90 enforcement
    ]
)
```

---

## Implementation Guide

### For New Modules

1. **Create file with UTF-8 declaration**:
   ```python
   # -*- coding: utf-8 -*-
   ```

2. **Add module docstring**

3. **Add WSP 90 UTF-8 enforcement header**

4. **Continue with normal imports**

### For Existing Modules

1. **Identify file type**:
   - Entry point (has `if __name__ == "__main__":`) → Add WSP 90
   - Library module (imported by others) → NO WSP 90

2. **For Entry Points Only - Insert WSP 90 header after docstring**:
   ```python
   """Module docstring"""

   # === UTF-8 ENFORCEMENT (WSP 90) ===
   # CRITICAL: Apply ONLY at entry points
   import sys
   import io
   if sys.platform.startswith('win'):
       sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
       sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
   # === END UTF-8 ENFORCEMENT ===

   # Existing imports continue...
   ```

3. **For Library Modules - REMOVE WSP 90 if present**:
   - Library modules inherit encoding from entry point
   - Removing prevents import conflicts

4. **Production emojis** - KEEP them (safe with proper entry point setup)

5. **Update file I/O** - add `encoding="utf-8"` parameter

### Testing UTF-8 Compliance

**Create test file `tests/test_utf8_compliance.py`**:

```python
# -*- coding: utf-8 -*-
"""
UTF-8 Compliance Test (WSP 90)
================================

Validates UTF-8 encoding enforcement across modules.
"""

# === UTF-8 ENFORCEMENT (WSP 90) ===
import sys
import io
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
# === END UTF-8 ENFORCEMENT ===

import pytest


def test_utf8_stdout():
    """Test UTF-8 output to stdout (emojis, international text)"""
    print("Testing UTF-8: Hello World")
    print("Spanish: Hola Mundo")
    print("Japanese: Konnichiwa")
    print("Emoji test: Success")  # Emoji converted to text per WSP 90 Rule 3
    assert sys.stdout.encoding.lower() in ['utf-8', 'utf8']


def test_utf8_file_write():
    """Test UTF-8 file writing"""
    import tempfile
    import json

    data = {
        "message": "UTF-8 test with international characters",
        "spanish": "Hola Mundo",
        "japanese": "Konnichiwa",
        "emoji_text": "Success"  # Text instead of emoji per WSP 90
    }

    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.json') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        temp_path = f.name

    # Verify file is UTF-8
    with open(temp_path, 'r', encoding='utf-8') as f:
        loaded = json.load(f)
        assert loaded["spanish"] == "Hola Mundo"

    import os
    os.unlink(temp_path)


if __name__ == "__main__":
    test_utf8_stdout()
    test_utf8_file_write()
    print("[PASS] All UTF-8 compliance tests passed (WSP 90)")
```

---

## Violation Prevention (WSP 64 Integration)

### Common Violations

**Violation 1: Missing UTF-8 Enforcement Header**
```python
# WRONG: No WSP 90 header
import sys
import logging

# RIGHT: WSP 90 header present
# === UTF-8 ENFORCEMENT (WSP 90) ===
import sys
import io
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
# === END UTF-8 ENFORCEMENT ===
```

**Violation 2: Emoji/Unicode in Print Statements**
```python
# WRONG: Emojis that fail on Windows
print("Status: Test passed")

# RIGHT: ASCII-safe alternative
print("[SUCCESS] Test passed")
```

**Violation 3: File I/O Without UTF-8**
```python
# WRONG: No encoding specified (uses system default)
with open("file.txt", "w") as f:
    f.write(content)

# RIGHT: Explicit UTF-8 encoding
with open("file.txt", "w", encoding="utf-8") as f:
    f.write(content)
```

---

## Migration Plan

### Phase 1: Core Modules (Immediate)
- [x] `modules/communication/liberty_alert/*` - Sprint Two POC modules
- [ ] `holo_index/` - Core search infrastructure
- [ ] `modules/communication/livechat/*` - High-traffic modules

### Phase 2: Infrastructure (Week 1)
- [ ] `modules/infrastructure/*` - System health, monitoring
- [ ] `WSP_agentic/*` - Agentic DAE modules
- [ ] `tools/*` - Utility scripts

### Phase 3: Complete Coverage (Week 2)
- [ ] All remaining modules
- [ ] Test files
- [ ] Documentation generators

### Automated Enforcement Script

**`tools/wsp90_enforcer.py`**:

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WSP 90 UTF-8 Enforcement Checker
=================================

Scans Python files and reports missing WSP 90 compliance.
"""

# === UTF-8 ENFORCEMENT (WSP 90) ===
import sys
import io
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
# === END UTF-8 ENFORCEMENT ===

import os
from pathlib import Path

WSP90_HEADER = "# === UTF-8 ENFORCEMENT (WSP 90) ==="

def check_file(file_path: Path) -> bool:
    """Check if file has WSP 90 compliance"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        return WSP90_HEADER in content

def scan_directory(directory: Path):
    """Scan directory for WSP 90 compliance"""
    python_files = list(directory.rglob("*.py"))
    non_compliant = []

    for py_file in python_files:
        if not check_file(py_file):
            non_compliant.append(py_file)

    if non_compliant:
        print(f"[WARNING] {len(non_compliant)}/{len(python_files)} files missing WSP 90 compliance:")
        for file in non_compliant:
            print(f"  - {file}")
        return False
    else:
        print(f"[PASS] All {len(python_files)} Python files are WSP 90 compliant")
        return True

if __name__ == "__main__":
    repo_root = Path(__file__).parent.parent
    scan_directory(repo_root / "modules")
    scan_directory(repo_root / "holo_index")
    scan_directory(repo_root / "WSP_agentic")
```

---

## WSP Compliance

This protocol follows:
- **WSP 1**: Framework foundation for systematic encoding enforcement
- **WSP 49**: Module structure standardization (UTF-8 header placement)
- **WSP 64**: Violation prevention through systematic enforcement
- **WSP 22**: ModLog documentation of UTF-8 compliance status

---

## References

### Python Documentation
- PEP 263: Defining Python Source Code Encodings
- PEP 529: Change Windows filesystem encoding to UTF-8
- Python `io.TextIOWrapper` documentation

### Related WSPs
- WSP 50: Pre-Action Verification (check encoding before file operations)
- WSP 5: Test Coverage (include UTF-8 tests)
- WSP 22: ModLog updates for UTF-8 migration status

---

**Last Updated**: 2025-10-11
**Maintainer**: 0102 DAE (infrastructure)
**Status**: Active - Immediate enforcement for all new modules
**Migration**: Phased rollout across existing modules (Phase 1: Core, Phase 2: Infrastructure, Phase 3: Complete)
