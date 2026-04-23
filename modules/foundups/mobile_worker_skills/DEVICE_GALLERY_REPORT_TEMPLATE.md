# Device Gallery Report Template

**Status:** SPECIFIED_NOT_IMPLEMENTED (WSP 97)  
**Purpose:** 012 fills this template during on-device AI Edge Gallery testing.

---

## Device Information

| Field | Value |
|-------|-------|
| **Date (UTC)** | `____-__-__T__:__Z` |
| **Device Model** | _________________________ |
| **OS Version** | Android __.__ / iOS __.__ |
| **AI Edge Gallery Version** | _________________________ |
| **Model Loaded** | Gemma __ / ________________ |
| **Tester** | 012 |

---

## Matrix A: Local Import Tests

Reference: [MATRIX_A_LOCAL_IMPORT_RUN.md](MATRIX_A_LOCAL_IMPORT_RUN.md)

### A1: foundups-edge-load-smoke

| Step | Check | Pass/Fail |
|------|-------|-----------|
| 1 | Skill folder copied to device | [ ] |
| 2 | Gallery > Skills > (+) > Import local skill | [ ] |
| 3 | Skill appears in list with correct name | [ ] |
| 4 | Skill enabled for chat session | [ ] |
| 5 | Sent exactly: `ping` | [ ] |
| 6 | Model replied exactly: `LOAD_OK` | [ ] |

**A1 Result:** [ ] PASS / [ ] FAIL

**A1 Failure Symptom (if FAIL):**  
`_______________________________________________________________`

---

### A2: foundups-code-task-parser

| Step | Check | Pass/Fail |
|------|-------|-----------|
| 1 | Skill folder copied to device | [ ] |
| 2 | Gallery > Skills > (+) > Import local skill | [ ] |
| 3 | Skill appears in list with correct name | [ ] |
| 4 | Skill enabled for chat session | [ ] |
| 5 | Sent prompt id `55108`: `fix swipe threshold in capture controller and run tests` | [ ] |

**A2 Output Validation:**

| Criterion | Check | Pass/Fail |
|-----------|-------|-----------|
| Response is parseable JSON | [ ] |
| `intent` is `edit` or `mixed` | [ ] |
| `summary` is one line, code-related | [ ] |
| `constraints` present (may be empty array) | [ ] |
| `open_questions` is NOT empty (no file path given) | [ ] |
| `suggested_next_skill` is `"foundups-scope-locker"` or `null` | [ ] |
| No invented file paths in any field | [ ] |

**A2 Result:** [ ] PASS / [ ] FAIL

**A2 Failure Symptom (if FAIL):**  
`_______________________________________________________________`

**A2 Model JSON Output (paste here if PASS):**
```json

```

---

## Matrix B-D: URL Loading Tests (Optional Phase 2)

Reference: [DEVICE_EDGE_GALLERY_VALIDATION.md](DEVICE_EDGE_GALLERY_VALIDATION.md)

### Test B: Load skill from URL

| Field | Value |
|-------|-------|
| **Skill Folder** | _________________________ |
| **URL Used** | _________________________ |

| Step | Check | Pass/Fail |
|------|-------|-----------|
| 1 | Gallery > Load skill from URL | [ ] |
| 2 | Entered folder base URL (not file URL) | [ ] |
| 3 | Skill appears in list | [ ] |
| 4 | Name + description match frontmatter | [ ] |
| 5 | Successful model turn using skill | [ ] |

**B Result:** [ ] PASS / [ ] FAIL / [ ] NOT_TESTED

**B Failure Symptom (if FAIL):**  
`_______________________________________________________________`

---

### Test C: Raw GitHub Sanity

| Field | Value |
|-------|-------|
| **Raw URL** | _________________________ |

| Step | Check | Pass/Fail |
|------|-------|-----------|
| 1 | Opened URL in mobile browser (not Gallery) | [ ] |
| 2 | File displays as markdown text | [ ] |
| 3 | Content starts with `---` frontmatter | [ ] |

**C Result:** [ ] PASS / [ ] FAIL / [ ] NOT_TESTED

---

### Test D: GitHub Pages Folder URL

| Field | Value |
|-------|-------|
| **Pages URL** | _________________________ |

| Step | Check | Pass/Fail |
|------|-------|-----------|
| 1 | Gallery > Load skill from URL | [ ] |
| 2 | Used Pages-deployed base URL | [ ] |
| 3 | Gallery URL load succeeded | [ ] |
| 4 | Skill functions same as local import | [ ] |

**D Result:** [ ] PASS / [ ] FAIL / [ ] NOT_TESTED

---

## Error Capture Section

### Import Errors

| Error | Observed |
|-------|----------|
| "Expected at least two `---` sections" | [ ] |
| Empty skill / crash | [ ] |
| Skill not listed after import | [ ] |
| 404 / timeout on URL load | [ ] |
| Wrong MIME / HTML error page | [ ] |
| Other: `________________________` | [ ] |

### Screenshot References

| Screenshot | Description | Filename/Location |
|------------|-------------|-------------------|
| Import screen | _________________________ | _________________________ |
| Skill list | _________________________ | _________________________ |
| Chat response | _________________________ | _________________________ |
| Error (if any) | _________________________ | _________________________ |

---

## Summary

| Test | Result |
|------|--------|
| A1 (edge-load-smoke) | [ ] PASS / [ ] FAIL |
| A2 (code-task-parser) | [ ] PASS / [ ] FAIL |
| B (URL load) | [ ] PASS / [ ] FAIL / [ ] NOT_TESTED |
| C (Raw GitHub sanity) | [ ] PASS / [ ] FAIL / [ ] NOT_TESTED |
| D (GitHub Pages) | [ ] PASS / [ ] FAIL / [ ] NOT_TESTED |

**Overall Matrix A Status:** [ ] PASS (A1 + A2 both pass) / [ ] FAIL

---

## 012 Sign-Off

**Date:** ____-__-__  
**Signature:** _________________________ (012)  
**Notes:**  
```

```

---

## Post-Test Actions (if PASS)

- [ ] Record outcome in `modules/foundups/ModLog.md`
- [ ] Pin Gallery app version in ModLog
- [ ] Pin model version (e.g., Gemma 4 E4B) in ModLog
- [ ] Attach screenshots to PR/issue if applicable

---

*Template version: 1.0.0 | Created: 2026-04-23 | WSP 97 compliant*
