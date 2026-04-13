# pfMALL YouTube Discovery

AI hook for exploratory YouTube video/channel discovery beyond known catalog channels.

## Purpose

This module provides the **discovery layer** for pfMALL - searching YouTube for content that might belong to existing FoundUps or represent new opportunities. It is separate from the deterministic channel-pull ingest path.

**Key distinction:**
- `youtube_channel_pull`: Deterministic pull from known channel IDs
- `pfmall_discovery`: Exploratory search for unknown content

## Usage

### Basic Discovery

```bash
python -m modules.ai_intelligence.pfmall_discovery.src.discovery_cli --query "FFCPLN music"
```

### Search for Channels

```bash
python -m modules.ai_intelligence.pfmall_discovery.src.discovery_cli --query "Japan expat" --type channel
```

### Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--query` | str | required | Search query |
| `--type` | str | video | "video" or "channel" |
| `--max-results` | int | 25 | Max results to return |
| `--include-channels` | flag | false | Also search channels when type=video |
| `--output` | path | auto | Output path for proposal JSON |

## Discovery Inputs Supported

Phase 1 supports:
- **Search query**: Free-text query (e.g., "FFCPLN music", "Japan relocation")
- **Search type**: Video or channel discovery

Future phases may add:
- FoundUp context (discover content related to an existing FoundUp)
- Topic expansion (AI-suggested related topics)

## Matching Policy

Discovered content is matched to existing FoundUps using this priority:

| Priority | Match Type | Confidence |
|----------|------------|------------|
| 1 | Exact channel_id match | 1.0 |
| 2 | Tag overlap (title/description vs catalog tags) | 0.3-0.7 |
| 3 | Category match | 0.2 |
| 4 | No match | 0.0 |

Unmatched content is still included in proposals - it may represent new FoundUp opportunities.

## Proposal Artifact

Proposals are written to:
```
docs/audits/pfmall_youtube_ingest/youtube_discovery_proposals.json
```

Each proposal includes:
- `query`: Original search query
- `candidate_type`: "video" or "channel"
- `video_id`, `channel_id`, `title`, etc.
- `matched_foundup_id`: Matched FoundUp (if any)
- `match_reason`: Why it matched
- `confidence`: Match confidence (0.0-1.0)
- `review_status`: Always "proposed" (human review required)

## Operator Workflow

1. **Run discovery**
   ```bash
   python -m modules.ai_intelligence.pfmall_discovery.src.discovery_cli --query "your topic"
   ```

2. **Review proposals**
   Open `docs/audits/pfmall_youtube_ingest/youtube_discovery_proposals.json`

3. **For matched proposals** (existing FoundUp):
   - Use channel-pull to get full video list
   - Apply reviewed delta via existing workflow

4. **For unmatched proposals** (potential new FoundUp):
   - Decide if a new FoundUp should be created
   - If yes, create via standard FoundUp creation process
   - Then add to catalog and run channel-pull

## What This Module Does NOT Do

- Does NOT mutate `mall-video-catalog.json`
- Does NOT auto-create new FoundUps
- Does NOT provide general "web search" (YouTube only)
- Does NOT bypass human review

## Prerequisites

### YouTube Data API Credentials

Reuses the existing `youtube_auth` credential system.

If credentials are unavailable:
- CLI reports the blocker explicitly
- Generates empty proposal artifact
- Tests still pass using fixture data

## Module Structure

```
pfmall_discovery/
├── src/
│   ├── __init__.py
│   ├── youtube_discovery.py    # YouTube search
│   ├── foundup_matcher.py      # Match to existing FoundUps
│   ├── proposal_generator.py   # Generate proposal artifacts
│   └── discovery_cli.py        # CLI entry point
├── tests/
│   └── test_discovery.py       # 18 tests
├── README.md
└── INTERFACE.md
```

## WSP References

- **WSP 3**: AI Intelligence domain placement
- **WSP 97**: Truthful discovery (no fake claims)
- **WSP 104**: FoundUp routing (matched proposals use existing routes)

## Related Modules

- `youtube_channel_pull`: Deterministic channel video pull
- `youtube_auth`: OAuth credential management
- `youtube_api_operations`: YouTube API utilities
