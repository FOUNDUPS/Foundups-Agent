"""reschedule_plan SKILLz package.

Dry-run REBALANCE PLAN for over-crowded schedule days (move count>cap excess onto
under-target upcoming days, into US-ET peak slots per channel tz). Read-only; the
mutating DOM apply is an explicit Phase-2 follow-up. See SKILLz.md for the WSP 95
micro chain-of-thought contract.
"""

from .executor import DRY_RUN, run_skill

__all__ = ["run_skill", "DRY_RUN"]
