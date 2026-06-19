"""what_should_i_schedule SKILLz package.

Read-only channel scheduling-priority ranking for the YouTube Shorts daemon.
See SKILLz.md for the WSP 95 micro chain-of-thought contract.
"""

from .executor import rank_channels_by_need, run_skill

__all__ = ["rank_channels_by_need", "run_skill"]
