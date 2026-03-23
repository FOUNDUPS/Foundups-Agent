"""
GitHub Orchestrator - 0102 Management Layer

Re-exports from src module.
"""

from .src import (
    GitHubOrchestrator,
    get_github_orchestrator,
    create_fam_listener,
    wire_github_to_fam,
)

__all__ = [
    "GitHubOrchestrator",
    "get_github_orchestrator",
    "create_fam_listener",
    "wire_github_to_fam",
]
__version__ = "0.4.0"
