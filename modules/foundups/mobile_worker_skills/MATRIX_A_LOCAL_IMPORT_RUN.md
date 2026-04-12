# Matrix A — local import only (device)

**Prerequisite:** AI Edge Gallery installed; skill folders available on device (USB push, zip extract, or sync).

**Do not use Load skill from URL** in this session.

---

## A1 — `foundups-edge-load-smoke` (fastest proof)

**Prompt id (tracking):** `38214`

1. Copy the entire folder `foundups-edge-load-smoke/` (must contain `SKILL.md`) onto the device.
2. Gallery → Skills → (+) → **Import local skill** → select that folder.
3. Enable the skill for a chat session.
4. Send exactly: `ping` (any case per skill rules).

**Pass:** Model replies exactly `LOAD_OK` (plain text, one line).  
**Fail:** Import error, wrong reply, or skill not applied.

---

## A2 — `foundups-code-task-parser`

**Prompt id (tracking):** `84726`

1. Import `foundups-code-task-parser/` the same way as A1.
2. Enable the skill.
3. Send **exactly** this user message (prompt id `55108`):

```text
fix swipe threshold in capture controller and run tests
```

**Pass criteria (structured output):**

- Single JSON object (no markdown fence required by 012 for copy-paste, but body should be parseable JSON).
- **`intent`** is one of `read` | `edit` | `mixed` | `unclear` — for this message expect **`edit`** or **`mixed`** (code change + tests).
- **`summary`** is one line, code-related.
- **`constraints`**: only what the user said (may be empty).
- **`open_questions`**: must **not** be empty unless the user already named a **verified** file path (they did **not** here) — at minimum ask **which file** holds the capture controller / swipe threshold.
- **`suggested_next_skill`**: JSON `null` or `"foundups-scope-locker"`; for edit/mixed should be **`"foundups-scope-locker"`**.
- **No invented file paths** in any field (no fake `src/foo.ts` unless user typed it).

**Fail:** Prose only, invalid JSON, invented paths, empty `open_questions` when no path given, `intent` `read` only.

---

## Desk reference — example compliant parser output (model may vary)

For input `55108` only; valid if it meets the pass criteria above.

```json
{
  "intent": "mixed",
  "summary": "Fix swipe threshold in capture controller and run tests",
  "constraints": [],
  "open_questions": [
    "Which file or module contains the capture controller and swipe threshold logic?",
    "Which test command or directory should run (e.g. pytest path)?"
  ],
  "suggested_next_skill": "foundups-scope-locker"
}
```

---

## 012 report back (after A1 + A2)

Use the block in `DEVICE_EDGE_GALLERY_VALIDATION.md` (`DEVICE_GALLERY_REPORT`) with `test_row: A` and attach parser JSON if A2 passed.
