# Session Closeout Schema - v1.0

**Format**: JSON (stdlib support, deterministic validation, no new dependency)

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | Schema version (e.g., `1.0.0`) |
| `record_type` | string | Must be `reddog_session_closeout` |
| `session_id` | string | UUID or date-stamp identifier |
| `source` | string | One of: `reddog_session`, `cursor`, `chatgpt`, `antigravity` |
| `captured_at` | string | ISO 8601 timestamp (e.g., `2026-05-27T14:30:00Z`) |
| `lane` | string | Worker/architect lane (e.g., `w6`, `w10`, `architect`) |
| `work_summary` | string | Curated summary, max 2000 chars, secret-redacted |

## Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `pr_refs` | array[int] | List of PR numbers referenced |
| `slice_refs` | array[string] | List of slice IDs completed |
| `decisions` | array[string] | One-line decisions made in session |
| `carry_forward` | array[string] | Next-slice IDs for follow-up work |
| `redaction_notes` | string | What was elided and why |
| `main_head_sha` | string | Main branch HEAD at session start |
| `gaps` | array[string] | Known gaps or incomplete items |

## Example

```json
{
  "schema_version": "1.0.0",
  "record_type": "reddog_session_closeout",
  "session_id": "2026-05-27__reddog-w6-01",
  "source": "reddog_session",
  "captured_at": "2026-05-27T14:30:00Z",
  "lane": "w6",
  "work_summary": "Completed IndexResult observability parity across all 6 HoloIndex indexers. Fixed test mock returning MagicMock instead of real IndexResult. Created main menu startup boundary fix removing ANTIFAFM_AUTO_START execution block.",
  "pr_refs": [708, 720, 721],
  "slice_refs": [
    "HOLOINDEX_INDEXER_ZERO_DOCS_OBSERVABILITY_PARITY_PHASE1",
    "MAIN_MENU_ANTIFAFM_STARTUP_BOUNDARY_FIX_PHASE1"
  ],
  "decisions": [
    "JSON over YAML for schema format - stdlib support, no dependency",
    "Delete auto-start block entirely rather than adding another gate"
  ],
  "carry_forward": [
    "REDDOG_SESSION_VALIDATOR_HARDENING_PHASE2"
  ],
  "redaction_notes": "No secrets present in session work",
  "main_head_sha": "84314016",
  "gaps": []
}
```

## Redaction Rules

### MUST Redact

1. **API Keys**: Any string matching `AIza*`, `sk-*`, `hf_*`, `ghp_*`, `gho_*`, `github_pat_*`
2. **OAuth/JWT**: Tokens, refresh tokens, bearer strings
3. **Env Vars**: `.env` key=value pairs, especially `*_SECRET`, `*_KEY`, `*_TOKEN`
4. **Credentials**: Database connection strings, passwords, stream keys
5. **Personal Data**: Email addresses (except committer's), real names beyond public PRs

### MUST NOT Include

1. **Raw Transcripts**: No role-by-role dialogue, no assistant/user message dumps
2. **Long Excerpts**: No multi-paragraph brain artifact copies
3. **DPO/SFT Examples**: No training data format in session files
4. **Local Paths**: No absolute paths to private directories (repo-relative OK)

## Validation

The validator at `modules/infrastructure/wre_core/scripts/validate_session_closeout.py`:

1. **Requires** all mandatory fields present
2. **Rejects** `work_summary` over 2000 characters
3. **Rejects** secret-pattern matches (see Redaction Rules)
4. **Rejects** raw transcript markers (`"assistant":`, `"user":`, `"role":`)
5. **Exits 0** on valid file, **non-zero** on failure

## Filename Convention

```
<captured_at>__<session_id>.json
```

Example: `2026-05-27T14-30-00Z__reddog-w6-01.json`

Note: Colons in ISO timestamps replaced with hyphens for filesystem compatibility.
