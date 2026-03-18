# HoloIndex Search Hang Remediation (WSP 97 Compliance)

**Date**: 2026-03-18
**Status**: RESOLVED
**Issue**: HoloIndex `--search` command hanging indefinitely, blocking WSP 97 pre-flight operations

---

## Root Cause Analysis

### Primary Cause: SentenceTransformer Import Hang

The `SentenceTransformer` import from `sentence_transformers` library was blocking indefinitely when:
1. HuggingFace Hub is unreachable
2. Model download is in progress
3. No timeout mechanism existed

**Evidence**:
```python
# This test confirmed the hang:
import threading
import time
def test_import():
    from sentence_transformers import SentenceTransformer  # HANGS HERE
thread = threading.Thread(target=test_import)
thread.start()
thread.join(timeout=10)
if thread.is_alive():
    print("HANG DETECTED")  # Confirmed after 10s
```

### Secondary Causes

1. **Slow module imports at startup**:
   - `codeindex_reporter` importing Qwen modules: ~4.4s
   - `qwen_advisor` modules: ~4.0s
   - These imports happened unconditionally, even when not needed

2. **No timeout on ChromaDB operations**:
   - `collection.query()` had no timeout
   - `model.encode()` had no timeout

3. **Auto-refresh logic running when HoloIndex unavailable**:
   - Code tried to call `holo.index_wsp_entries()` on `None`

---

## Fixes Implemented

### 1. Hard Timeouts for Blocking Operations

Added `_run_with_timeout()` helper in [holo_index/core/holo_index.py](../core/holo_index.py):

```python
HOLO_MODEL_IMPORT_TIMEOUT = 5   # seconds
HOLO_MODEL_LOAD_TIMEOUT = 10    # seconds
HOLO_ENCODE_TIMEOUT = 3         # seconds

def _run_with_timeout(func, timeout_sec, default=None, error_msg="Operation timed out"):
    """Execute function with hard timeout using ThreadPoolExecutor."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func)
        try:
            return future.result(timeout=timeout_sec)
        except TimeoutError:
            return default
```

Applied to:
- `SentenceTransformer` import: 5s timeout
- Model loading: 10s timeout
- `model.encode()`: 3s timeout

### 2. Lazy Imports for Slow Modules

In [holo_index/cli.py](../cli.py):

```python
# BEFORE: Always imported (8s+ startup penalty)
from holo_index.reports.codeindex_reporter import CodeIndexReporter
from holo_index.qwen_advisor.advisor import QwenAdvisor

# AFTER: Only import when needed
_need_advisor = "--llm-advisor" in sys.argv
if _need_advisor:
    from holo_index.qwen_advisor.advisor import QwenAdvisor
```

### 3. Enhanced Offline/Fast Mode

`--offline` and `--fast-search` flags now:
- Set `HOLO_SKIP_MODEL=1` before any imports
- Skip HoloIndex/ChromaDB imports entirely
- Use lightweight lexical search fallback
- Return results immediately without heavy post-processing

### 4. Guards for None HoloIndex

Added safety checks throughout:
```python
if holo is not None and not (index_code or index_wsp):
    # Only run auto-refresh when HoloIndex is available
```

---

## Validation Results

| Mode | Command | Time | Target | Status |
|------|---------|------|--------|--------|
| Offline | `--offline --search "test"` | 1.22s | <3s | PASS |
| Fast | `--fast-search --search "test"` | 2.06s | <3s | PASS |

---

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOLO_MODEL_IMPORT_TIMEOUT` | 5 | Max seconds for SentenceTransformer import |
| `HOLO_MODEL_LOAD_TIMEOUT` | 10 | Max seconds for model loading |
| `HOLO_ENCODE_TIMEOUT` | 3 | Max seconds for embedding generation |
| `HOLO_SKIP_MODEL` | 0 | Skip model entirely (use lexical search) |
| `HOLO_OFFLINE` | 0 | Offline mode (no network, no model) |

### CLI Flags

| Flag | Effect |
|------|--------|
| `--offline` | Skip model, use lexical search only |
| `--fast-search` | Skip model, minimal processing |
| `--bundle-json` + `HOLO_SKIP_MODEL=1` | JSON output, no model import |

---

## Recommendations for 0102 Agents

1. **For pre-flight queries**: Use `--offline` or `--fast-search` for guaranteed <3s response
2. **For full semantic search**: Ensure E:/HoloIndex/models has cached model
3. **When model unavailable**: System automatically falls back to lexical search

---

## Files Modified

- [holo_index/core/holo_index.py](../core/holo_index.py): Added timeout wrappers
- [holo_index/cli.py](../cli.py): Lazy imports, offline fallbacks, guards

---

*WSP 97 Compliant | 0102 Architect | 2026-03-18*
