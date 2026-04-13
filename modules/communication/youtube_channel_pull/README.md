# YouTube Channel Pull

Fetch latest videos from YouTube channels and generate reviewable delta artifacts.

## Purpose

This module provides the first truthful YouTube-to-catalog ingest path for pfMALL. Instead of blind catalog mutation, it:

1. Reads channel identity from existing `source_id` fields in `mall-video-catalog.json`
2. Fetches latest N videos per channel via YouTube Data API
3. Compares against current catalog entries
4. Emits a reviewable delta artifact
5. Leaves actual catalog merge as a human-reviewed follow-up

## Usage

### Basic Pull (Dry-Run)

```bash
python -m modules.communication.youtube_channel_pull.src.pull_cli
```

This generates a delta artifact at:
```
docs/audits/pfmall_youtube_ingest/youtube_channel_pull_delta.json
```

### Pull Specific FoundUp

```bash
python -m modules.communication.youtube_channel_pull.src.pull_cli --foundup move2japan
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--dry-run` | `True` | Generate delta without mutation |
| `--foundup ID` | all | Pull only specified FoundUp |
| `--max-results N` | 50 | Max videos per channel |
| `--output PATH` | auto | Output path for delta JSON |

## Operator Workflow

### 1. Run the Pull

```bash
cd O:\Foundups-Agent
python -m modules.communication.youtube_channel_pull.src.pull_cli
```

### 2. Inspect the Delta

Open the generated delta file:
```
docs/audits/pfmall_youtube_ingest/youtube_channel_pull_delta.json
```

Review:
- `new_videos`: Candidates to add
- `skipped_ids`: Already present (no action needed)
- Video metadata: title, thumbnail_url, published_at

### 3. Decide What to Merge

For each FoundUp with new videos:
1. Review video titles for relevance
2. Check publish dates
3. Decide which videos to include

### 4. Manual Merge (Current Process)

Edit `public/member/mall-video-catalog.json`:
1. Find the FoundUp entry
2. Add new videos to the `videos` array
3. Update `video_count` field
4. Commit and deploy

### 5. Future: Merge Command (Not in Phase 1)

A future `--apply` mode may automate the merge step with review prompts.

## Prerequisites

### YouTube Data API Credentials

This module reuses the existing `youtube_auth` credential system:

1. Ensure `.env` has `YOUTUBE_SCOPES` configured
2. Ensure OAuth tokens exist for at least one credential set
3. Test with: `python -m modules.platform_integration.youtube_auth.src.quota_tester`

If credentials are missing, the CLI will:
- Report the blocker explicitly
- Generate an empty delta to verify workflow

### Quota Costs

Per YouTube Data API v3:
- `search.list`: ~100 units per request
- Default quota: 10,000 units/day per credential set

With 50 videos × 10 FoundUps = ~1,000 units per full pull.

## Module Structure

```
youtube_channel_pull/
├── src/
│   ├── __init__.py
│   ├── channel_puller.py    # Fetch videos from channel
│   ├── catalog_delta.py     # Compare and generate delta
│   └── pull_cli.py          # CLI entry point
├── tests/
│   └── test_catalog_delta.py
├── README.md
├── INTERFACE.md
└── requirements.txt
```

## WSP References

- **WSP 3**: Communication domain placement
- **WSP 97**: Truthful verification (no fake data)
- **WSP 49**: Module structure compliance

## Scheduled Refresh (Phase 2)

The refresh scheduler provides a triggerable entrypoint for routine channel refresh.

### Quick Start

```bash
# Manual refresh (all channels)
python -m modules.communication.youtube_channel_pull.src.refresh_scheduler

# Refresh specific FoundUp
python -m modules.communication.youtube_channel_pull.src.refresh_scheduler --foundup move2japan

# Mark as scheduled run (for logging)
python -m modules.communication.youtube_channel_pull.src.refresh_scheduler --scheduled
```

### Scheduler Options

| Flag | Default | Description |
|------|---------|-------------|
| `--foundup ID` | all | Refresh only specified FoundUp |
| `--max-results N` | 50 | Max videos per channel |
| `--scheduled` | false | Mark run as scheduled (vs manual) |
| `--no-log` | false | Skip logging to refresh_log.json |

### Output Artifacts

1. **Delta artifact**: `docs/audits/pfmall_youtube_ingest/youtube_channel_pull_delta.json`
2. **Refresh log**: `docs/audits/pfmall_youtube_ingest/refresh_log.json`

### Scheduling Options

#### Windows Task Scheduler

```powershell
# Create scheduled task (runs daily at 6 AM)
schtasks /create /tn "pfMALL YouTube Refresh" /tr "python -m modules.communication.youtube_channel_pull.src.refresh_scheduler --scheduled" /sc daily /st 06:00 /sd $(Get-Date -Format "MM/dd/yyyy")
```

#### Linux Cron

```bash
# Add to crontab (runs daily at 6 AM)
0 6 * * * cd /path/to/Foundups-Agent && python -m modules.communication.youtube_channel_pull.src.refresh_scheduler --scheduled
```

#### CI/CD Pipeline

```yaml
# GitHub Actions example
- name: Refresh YouTube channels
  run: python -m modules.communication.youtube_channel_pull.src.refresh_scheduler --scheduled
```

### Operator Workflow (Scheduled)

1. **Scheduler triggers refresh** (generates delta artifact)
2. **Operator reviews delta** (`docs/audits/pfmall_youtube_ingest/youtube_channel_pull_delta.json`)
3. **Operator applies approved videos** (manual or via future apply command)
4. **Commit changes** to catalog

### Review-First Guarantee

The scheduler NEVER mutates `mall-video-catalog.json` directly.
All catalog changes require explicit human review and apply step.

## Limitations (Current)

- No auto-commit or PR creation
- No thumbnail caching
- No cross-platform (YouTube only)
- Manual merge step required after review

## Related Modules

- `youtube_auth`: OAuth credential management
- `youtube_api_operations`: Enhanced API operations
- `youtube_channel_registry`: Channel metadata registry
