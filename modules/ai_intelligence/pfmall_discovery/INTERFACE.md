# pfMALL Discovery Interface

## Public API

### youtube_discovery.py

#### `search_youtube(youtube_service, query, max_results=25, search_type="video")`

Search YouTube for videos or channels.

**Parameters:**
- `youtube_service`: Authenticated googleapiclient YouTube service
- `query`: Search query string
- `max_results`: Maximum results (default 25)
- `search_type`: "video" or "channel"

**Returns:** `List[DiscoveryProposal]`

#### `search_by_topic(youtube_service, topic, include_videos=True, include_channels=False, max_results=25)`

Search by topic with optional channel inclusion.

**Returns:** `List[DiscoveryProposal]`

### foundup_matcher.py

#### `load_catalog_targets(catalog_path=None)`

Load YouTube-backed FoundUps from catalog.

**Returns:** `List[CatalogTarget]`

#### `match_to_foundup(channel_id, title, description, targets)`

Match discovered content to existing FoundUp with disambiguation.

**Matching Policy (priority order):**
1. Exact channel_id match (confidence: 1.0)
2. Ambiguous shared-topic match (confidence: 0.3-0.5, returns candidates)
3. Single tag overlap match (confidence: 0.3-0.7)
4. Category match (confidence: 0.2)
5. Unmatched (confidence: 0.0)

**Returns:** `Tuple[Optional[str], str, float, List[str]]` - (foundup_id, reason, confidence, ambiguous_candidates)

**Match Reasons:**
- `channel_id_match`: Exact channel identity match
- `ambiguous_shared_topic`: Multiple FoundUps share tag space (e.g., #FFCPLN)
- `tag_overlap:N.NN`: Single FoundUp tag match with score
- `category_match`: Category-based match
- `no_match`: No viable match found

#### `match_proposals(proposals, targets=None)`

Batch match proposals to FoundUps.

**Returns:** `List[DiscoveryProposal]` with match fields populated

### proposal_generator.py

#### `generate_discovery_proposals(youtube_service, query, search_type="video", max_results=25, include_channels=False)`

Generate complete proposal report.

**Returns:** Proposal report dict:
```python
{
    "generated_at": "2026-04-13T...",
    "query": "FFCPLN music",
    "search_type": "video",
    "summary": {
        "total_proposals": 25,
        "matched_to_foundup": 5,
        "unmatched": 20,
        "catalog_targets": 4,
    },
    "proposals": [...]
}
```

#### `write_proposal_artifact(report, output_path=None)`

Write proposal to JSON file.

**Returns:** Path written to

#### `format_proposal_summary(report)`

Format report for terminal display.

**Returns:** Formatted string

## Data Structures

### DiscoveryProposal

```python
@dataclass
class DiscoveryProposal:
    query: str
    candidate_type: str  # "video" or "channel"
    video_id: Optional[str] = None
    channel_id: str = ""
    channel_title: str = ""
    title: str = ""
    description: str = ""
    thumbnail_url: str = ""
    embed_url: str = ""
    source_url: str = ""
    published_at: str = ""
    # Matching results
    matched_foundup_id: Optional[str] = None
    match_reason: str = ""
    confidence: float = 0.0
    ambiguous_candidates: List[str] = []  # FoundUp IDs when ambiguous
    review_status: str = "proposed"
```

**Ambiguity Handling:**
When `match_reason == "ambiguous_shared_topic"`:
- `matched_foundup_id` is `None` (no single match)
- `ambiguous_candidates` contains all viable FoundUp IDs
- `confidence` is reduced (0.3-0.5) to reflect uncertainty

### CatalogTarget

```python
@dataclass
class CatalogTarget:
    foundup_id: str
    source_id: str  # YouTube channel ID
    source_handle: str
    tags: List[str]
    category: str
```

## CLI Interface

```bash
python -m modules.ai_intelligence.pfmall_discovery.src.discovery_cli [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--query` | str | required | Search query |
| `--type` | str | video | "video" or "channel" |
| `--max-results` | int | 25 | Max results |
| `--include-channels` | flag | false | Also search channels |
| `--output` | path | auto | Output path |

## Dependencies

- `youtube_auth`: For `get_authenticated_service()`
- `googleapiclient`: YouTube Data API v3
