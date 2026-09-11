# video_comments Test Suite

**Test Coverage:** Partial (existing tests available)
**Framework:** pytest + unittest

## [EXISTING] Available Tests

| Test File | Purpose | Status |
|-----------|---------|--------|
| `test_llm_integration.py` | WSP FMAS tests for LLM comment generation | ✅ Available |
| `test_reply_to_comment.py` | YouTube API reply capability demo | ✅ Available |
| `test_classifier_pipeline.py` | Commenter classification tests | ✅ Available |
| `test_like_single_comment.py` | Single comment like/heart test | ✅ Available |
| `test_poc_dialogue.py` | PoC dialogue flow test | ✅ Available |
| `test_post_comment.py` | Comment posting test | ✅ Available |
| `test_move2japan_access.py` | Move2Japan channel access test | ✅ Available |
| `test_reply_context_pipeline.py` | Per-row video context, full-prompt Qwen routing, and source-gate regressions | ✅ 7 passing |
| `test_ytr1_runtime_hardening.py` | Text-model selection and reply runtime hardening | ✅ 11 passing |

## [TEST] Test Categories

### Unit Tests (test_*.py)
- test_[module_name].py - Core functionality tests
- test_integration.py - Integration tests (when applicable)

### Test Structure
```
tests/
������ __init__.py              # Test package
������ README.md               # This file
������ test_[module_name].py   # Main test file
������ TestModLog.md          # Test evolution log
```

## [RUN] Running Tests

### All Tests
```bash
cd modules/communication/video_comments
python -m pytest tests/
```

### Specific Test
```bash
cd modules/communication/video_comments
python -m pytest tests/test_[module_name].py
```

### Context Pipeline Regression
```bash
python -m pytest modules/communication/video_comments/tests/test_reply_context_pipeline.py -q
python -m pytest modules/communication/video_comments/tests/test_ytr1_runtime_hardening.py -q
```

### With Coverage
```bash
cd modules/communication/video_comments
python -m pytest --cov=src --cov-report=html tests/
```

## [COVERAGE] Coverage Requirements

**WSP 13 Compliance Target:** >=90% coverage

### Current Status
- **Lines:** 0%
- **Functions:** 0%
- **Branches:** 0%

### Coverage Areas Required
- [ ] Core functionality
- [ ] Error handling
- [ ] Edge cases
- [ ] Integration points

## [CONFIG] Test Configuration

### pytest.ini (if needed)
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
```

## [CASES] Test Cases (TODO)

### Basic Functionality
- [ ] Test initialization
- [ ] Test main methods
- [ ] Test configuration handling

### Error Conditions
- [ ] Test invalid inputs
- [ ] Test missing dependencies
- [ ] Test network failures (if applicable)

### Integration Tests
- [ ] Test with dependent modules
- [ ] Test end-to-end workflows
- [ ] Test performance requirements

## [EVOLUTION] Test Evolution Log

See TestModLog.md for detailed test development history.

---

**WSP 13 Testing Compliance:** Structure Complete, Implementation Pending
