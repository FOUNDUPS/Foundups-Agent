# pAVS MCP Server Interface

**Version**: 0.1.0
**Protocol**: MCP (Model Context Protocol)
**Transport**: WebSocket (wss://)

## Authentication

All MCP connections require API key authentication:

```
Authorization: Bearer fp_xxxxxxxxxxxx
```

API keys are scoped per-FoundUp and obtained via `foundup_register` tool.

## Tools

### cabr_validate

Validates content through CABR V1/V2/V3 pipeline.

**Input Schema**:
```json
{
  "content": "string (required) - Content to validate",
  "context": {
    "platform": "string - Target platform (instagram, twitter, linkedin)",
    "audience": "string - Target audience descriptor",
    "foundup_id": "string - Calling FoundUp identifier"
  }
}
```

**Output Schema**:
```json
{
  "score": "number 0.0-1.0 - CABR validation score",
  "passed": "boolean - Whether content passes gate (score >= 0.6)",
  "feedback": "string - Improvement suggestions if not passed",
  "v1_result": "object - V1 (Validation) details",
  "v2_result": "object - V2 (Verification) details",
  "v3_result": "object - V3 (Valuation) details"
}
```

### gemma_classify

Binary or multi-class classification via Gemma.

**Input Schema**:
```json
{
  "text": "string (required) - Text to classify",
  "categories": ["array of strings (required) - Category labels"]
}
```

**Output Schema**:
```json
{
  "classification": "string - Best matching category",
  "confidence": "number 0.0-1.0 - Classification confidence",
  "all_scores": {
    "category1": 0.85,
    "category2": 0.15
  }
}
```

### qwen_plan

Strategic planning via Qwen.

**Input Schema**:
```json
{
  "objective": "string (required) - What to achieve",
  "constraints": {
    "platform": "string - Target platform",
    "timing": "string - Timing preference (optimal, immediate, scheduled)",
    "budget_ups": "number - UPs budget limit",
    "audience": "string - Target audience"
  }
}
```

**Output Schema**:
```json
{
  "plan": [
    {"step": 1, "action": "string", "rationale": "string"},
    {"step": 2, "action": "string", "rationale": "string"}
  ],
  "reasoning": "string - Strategic explanation",
  "alternatives": ["array of alternative approaches"],
  "recommended_platform": "string",
  "optimal_time": "ISO datetime"
}
```

### fam_emit

Emit event to FAM DAEmon for tracking.

**Input Schema**:
```json
{
  "foundup_id": "string (required) - FoundUp identifier",
  "event_type": "string (required) - Event category",
  "payload": "object - Event-specific data"
}
```

**Event Types**:
- `post_created` - Content created
- `post_published` - Content published to platform
- `engagement_received` - Likes, comments, shares
- `task_completed` - Agent task finished
- `error_occurred` - Error in processing

**Output Schema**:
```json
{
  "event_id": "string - Unique event identifier (sha256 hash)",
  "timestamp": "ISO datetime",
  "persisted": "boolean - Whether event was durably stored"
}
```

### pattern_recall

Recall successful patterns from Pattern Memory.

**Input Schema**:
```json
{
  "skill": "string (required) - Skill/action type",
  "min_fidelity": "number 0.0-1.0 (default 0.7) - Minimum success rate"
}
```

**Output Schema**:
```json
{
  "patterns": [
    {
      "pattern_id": "string",
      "skill": "string",
      "input_context": "object",
      "successful_output": "object",
      "fidelity": "number 0.0-1.0",
      "uses": "number"
    }
  ]
}
```

### pattern_store

Store execution outcome for learning.

**Input Schema**:
```json
{
  "skill": "string (required) - Skill that was executed",
  "outcome": {
    "success": "boolean",
    "input": "object - Input that was provided",
    "output": "object - Output that was produced",
    "context": "object - Environmental context",
    "feedback": "string - Optional feedback"
  }
}
```

**Output Schema**:
```json
{
  "pattern_id": "string - Stored pattern identifier",
  "updated_fidelity": "number - New fidelity score for this skill"
}
```

### holo_search

Semantic search via HoloIndex.

**Input Schema**:
```json
{
  "query": "string (required) - Natural language query",
  "domain": "string (optional) - Domain filter (foundups, ai_intelligence, etc.)",
  "limit": "number (default 10) - Max results"
}
```

**Output Schema**:
```json
{
  "matches": [
    {
      "file": "string - File path",
      "line": "number - Line number",
      "content": "string - Matching content",
      "score": "number - Relevance score"
    }
  ]
}
```

### foundup_register

Register a FoundUp for pAVS access.

**Input Schema**:
```json
{
  "foundup_id": "string (required) - Unique FoundUp identifier",
  "repo_url": "string (required) - GitHub repo URL",
  "owner_pubkey": "string (required) - Owner's Ed25519 public key"
}
```

**Output Schema**:
```json
{
  "api_key": "string - Encrypted API key (fp_xxxx)",
  "endpoint": "string - MCP server endpoint URL",
  "registered_at": "ISO datetime",
  "tier": "string - Access tier (free, pro, enterprise)"
}
```

## Error Handling

All errors follow MCP error format:

```json
{
  "error": {
    "code": "string - Error code",
    "message": "string - Human readable message",
    "details": "object - Additional context"
  }
}
```

**Error Codes**:
- `AUTH_FAILED` - Invalid or expired API key
- `RATE_LIMITED` - Too many requests
- `VALIDATION_FAILED` - Invalid input schema
- `INTERNAL_ERROR` - Server-side error
- `FOUNDUP_NOT_REGISTERED` - FoundUp not registered

## Rate Limits

| Tier | Requests/min | Requests/day |
|------|--------------|--------------|
| Free | 10 | 1,000 |
| Pro | 100 | 50,000 |
| Enterprise | 1,000 | Unlimited |
