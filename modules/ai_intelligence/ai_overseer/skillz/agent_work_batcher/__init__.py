# agent_work_batcher - Batch 0102 agent work for LinkedIn posting
#
# Agent Gating:
#   - Qwen: ✓ ALLOWED (orchestration, generation)
#   - Gemma: ✗ NOT ALLOWED (pattern matching only - wrong skill type)
#   - Claude/OpenClaw: ✓ ALLOWED (direct invocation)
#
# Wardrobe Access:
#   - Discovery: OPEN to all via HoloIndex
#   - Execution: GATED by ALLOWED_AGENTS in executor.py

from .executor import AgentWorkBatcher, WorkItem, WorkBatch

__all__ = ["AgentWorkBatcher", "WorkItem", "WorkBatch"]
