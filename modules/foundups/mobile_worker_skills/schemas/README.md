# Mobile worker JSON schemas (v1)

| File | Purpose |
|------|---------|
| [`worker-handoff-pipeline.v1.schema.json`](worker-handoff-pipeline.v1.schema.json) | `$defs` for **ParserOutput**, **ScopeOutput**, **PacketOutput**, **ResultOutput**, **PipelineEnvelopeV1**, **HandoffValidationResult** |

**Usage:** Reference from `WSP_SKILL_BUILDER.md` and `foundups-handoff-validator`. Validate with any Draft 2020-12 capable tool (`ajv`, `jsonschema`, etc.).

**Note:** `$id` uses `https://foundups.org/schemas/...` as a stable logical URI; file is authoritative in-repo.
