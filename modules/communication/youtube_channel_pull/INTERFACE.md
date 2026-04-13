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

## Dependencies

- `youtube_auth`: For `get_authenticated_service()`
- `googleapiclient`: YouTube Data API v3
