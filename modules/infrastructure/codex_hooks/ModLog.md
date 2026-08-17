# Codex Hooks ModLog

## 0.1.0 - Codex WSP lifecycle hooks Phase 1

**WSP Protocol**: WSP 00, 3, 5, 22, 49, 50, 84, 97

**Phase**: Initial Creation

**Agent**: 0102

### Changes

- Added repository-local ChatGPT/Codex hook discovery configuration.
- Added deterministic WSP_00, prompt-secret, tool-safety, and Stop gates.
- Added cross-platform command routing with a Windows-specific override.
- Added focused hook wire-shape and policy regression tests.
- Kept emitted hook messages independent of prompt and session metadata so
  secret-bearing wire input cannot flow to process output.

### Impact

Trusted FoundUps sessions can now discover executable lifecycle guards directly
from the checkout. This does not claim MCP availability or remote transport.

### WSP Compliance

- Reuses canonical WSP_00 and tracker implementations rather than duplicating them.
- Fails closed for session identity and repository-edit ambiguity.
- Keeps transcripts, raw prompts, and credential values out of persistence/output.
