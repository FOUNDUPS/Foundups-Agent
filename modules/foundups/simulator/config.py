"""Simulator configuration knobs.

All simulation parameters in one place for easy tuning.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SimulatorConfig:
    """Configuration for FoundUps simulator."""

    # Agent counts
    num_founder_agents: int = 3
    num_user_agents: int = 10

    # Timing
    tick_rate_hz: float = 2.0  # Ticks per second
    max_ticks: Optional[int] = None  # None = run forever

    # Epoch timing (tick-based intervals)
    mini_epoch_ticks: int = 10      # Demurrage cycle (bio-decay)
    epoch_ticks: int = 100          # Du pool distribution (passive)
    macro_epoch_ticks: int = 900    # BTC-F_i ratio snapshot (~15 min at 1Hz)
    # Note: Dao/Un payouts are EVENT-based (per 3V task), not epoch-based

    # Randomness
    seed: int = 42  # Deterministic seed for reproducibility

    # Token economics
    initial_agent_tokens: int = 1000
    epoch_funding_mode: str = "legacy_unfunded"  # Opt-in exact native simulation only
    foundup_creation_cost: int = 100
    like_cost: int = 1
    follow_cost: int = 5
    stake_min: int = 10
    stake_max: int = 100

    # FoundUp parameters
    max_token_supply: int = 21_000_000
    token_release_per_tick: int = 100
    founder_max_foundups: int = 3  # Per-founder cap for new FoundUps
    layer_d_anchor_enabled: bool = False
    layer_d_anchor_every_n_epochs: int = 1
    layer_d_anchor_force_republish: bool = False
    layer_d_anchor_mode: str = "mock"
    layer_d_anchor_db_path: Optional[str] = None

    # Agent behavior
    agent_action_probability: float = 0.3  # Chance to act each tick
    agent_cooldown_ticks: int = 5  # Ticks between actions

    # Viewport
    grid_width: int = 10
    grid_height: int = 6
    event_log_lines: int = 10

    # Render mode
    render_mode: str = "terminal"  # "terminal" or "pygame"

    # Debug
    verbose: bool = False
    show_debug_panel: bool = True

    # AI agents (Qwen founders, Gemma users)
    use_ai: bool = False  # Enable AI-driven agents
    ai_risk_tolerance: float = 0.5  # User agent risk tolerance (0-1)

    # Pure-step shadow parity (safe refactor gate; does not alter runtime path)
    pure_step_shadow_enabled: bool = False
    pure_step_shadow_log_interval: int = 25
    pure_step_shadow_max_actor_drift: float = 1e-6
    pure_step_shadow_max_pool_drift: float = 1e-6
    pure_step_shadow_max_fi_drift: float = 1e-6


# Default config instance
DEFAULT_CONFIG = SimulatorConfig()
