# YouTube Channel Pull Interface

## Public API

### channel_puller.py

#### `fetch_channel_videos(youtube_service, channel_id, max_results=50)`

Fetch latest videos from a YouTube channel.

**Parameters:**
- `youtube_service`: Authenticated googleapiclient YouTube service
- `channel_id`: YouTube channel ID (e.g., "UC-LSSlOZwpGIRIYihaz8zCw")
- `max_results`: Maximum videos to fetch (default 50)

**Returns:** `List[Dict]` with keys:
- `video_id`: YouTube video ID
- `title`: Video title
- `thumbnail_url`: Thumbnail URL
- `embed_url`: Embeddable URL
- `source_url`: Watch URL
- `published_at`: ISO timestamp
- `channel_id`: Channel ID

#### `get_channel_ids_from_catalog(catalog)`

Extract YouTube channel IDs from catalog.

**Parameters:**
- `catalog`: List of catalog entries

**Returns:** `Dict[str, str]` mapping foundup_id → channel_id

### catalog_delta.py

#### `generate_full_delta(catalog, pulled_by_foundup)`

Generate delta report for all FoundUps.

**Parameters:**
- `catalog`: Full mall-video-catalog.json content
- `pulled_by_foundup`: Dict mapping foundup_id → pulled videos list

**Returns:** Delta report dict:
```python
{
    "generated_at": "2026-04-13T...",
    "summary": {
        "foundups_checked": 10,
        "total_new_videos": 25,
        "total_skipped": 150,
    },
    "deltas": [
        {
            "foundup_id": "move2japan",
            "existing_count": 573,
            "pulled_count": 50,
            "new_count": 3,
            "skipped_count": 47,
            "new_videos": [...],
            "skipped_ids": [...]
        }
    ]
}
```

#### `write_delta_artifact(delta, output_path)`

Write delta to JSON file.

**Parameters:**
- `delta`: Delta report dict
- `output_path`: Path to write

**Returns:** Path written to

#### `format_delta_summary(delta)`

Format delta for terminal display.

**Parameters:**
- `delta`: Delta report dict

**Returns:** Formatted string

## CLI Interface

```bash
python -m modules.communication.youtube_channel_pull.src.pull_cli [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--dry-run` | flag | True | No catalog mutation |
| `--foundup` | str | all | Filter to one FoundUp |
| `--max-results` | int | 50 | Videos per channel |
| `--output` | path | auto | Delta output path |

### refresh_scheduler.py

#### `run_refresh(foundup_filter=None, max_results=50, trigger_mode="manual")`

Run the channel refresh workflow. Main entrypoint for scheduled/triggered refresh.

**Parameters:**
- `foundup_filter`: Optional FoundUp ID to filter (default: all)
- `max_results`: Max videos per channel (default: 50)
- `trigger_mode`: How triggered ("manual", "scheduled", "ci")

**Returns:** `RefreshResult` with:
```python
{
    "success": bool,
    "foundups_checked": int,
    "new_videos_found": int,
    "delta_path": str,
    "error": str | None,
    "triggered_at": str,  # ISO timestamp
    "trigger_mode": str,
}
```

**Review-First Guarantee:** This function NEVER mutates the catalog.
It only generates delta artifacts for human review.

## Scheduler CLI

```bash
python -m modules.communication.youtube_channel_pull.src.refresh_scheduler [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--foundup` | str | all | Refresh only specified FoundUp |
| `--max-results` | int | 50 | Videos per channel |
| `--scheduled` | flag | false | Mark as scheduled run |
| `--no-log` | flag | false | Skip refresh log |

## Output Artifacts

| Artifact | Path | Purpose |
|----------|------|---------|
| Delta | `docs/audits/pfmall_youtube_ingest/youtube_channel_pull_delta.json` | New videos for review |
| Refresh Log | `docs/audits/pfmall_youtube_ingest/refresh_log.json` | Scheduler run history |

### status_summary.py

Read-only status summary generator. Aggregates catalog, delta, refresh log,
discovery proposals, and the latest discovery review into a single operator
artifact. Performs no catalog mutation and requires no live API access.

#### `generate_status_summary(repo_root=REPO_ROOT) -> Dict`

Return a status summary dict with fields:
- `generated_at`, `read_only`
- `sources`: relative paths to each parsed artifact (or `null` if missing)
- `catalog`: foundup counts, declared-vs-actual totals, mismatches, per-entry rows
- `delta`: latest known-channel refresh (generated_at, per-foundup deltas)
- `refresh_log`: run count + last run, or `{available: False, note: ...}` if missing
- `proposals`: latest discovery proposals metadata
- `review`: latest discovery review result (auto-selects most recent `youtube_discovery_review_result_*.json` by sorted order)
- `blockers`: list of strings
- `next_actions`: list of strings

#### `render_markdown(summary: Dict) -> str`

Render the summary dict as operator-facing markdown. Safe on fully-missing
artifact sets (reports absences honestly).

#### `write_status_summary(summary, markdown_path, json_path) -> Dict[str, Path]`

Write markdown and JSON artifacts. Only writes to the provided output paths;
never mutates source artifacts.

#### CLI

```bash
python -m modules.communication.youtube_channel_pull.src.status_summary [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--repo-root` | path | inferred | Repo root to scan for artifacts |
| `--markdown-out` | path | `docs/audits/pfmall_youtube_ingest/pipeline_status_summary.md` | Markdown output |
| `--json-out` | path | `docs/audits/pfmall_youtube_ingest/pipeline_status_summary.json` | JSON output |
| `--stdout` | flag | false | Print markdown to stdout instead of writing files |

#### Output Artifacts

| Artifact | Path | Purpose |
|----------|------|---------|
| Status Summary (MD) | `docs/audits/pfmall_youtube_ingest/pipeline_status_summary.md` | Operator-facing status view |
| Status Summary (JSON) | `docs/audits/pfmall_youtube_ingest/pipeline_status_summary.json` | Machine-readable status contract |

## Dependencies

- `youtube_auth`: For `get_authenticated_service()`
- `googleapiclient`: YouTube Data API v3
- `status_summary`: standard library only (json, pathlib, datetime, argparse)
