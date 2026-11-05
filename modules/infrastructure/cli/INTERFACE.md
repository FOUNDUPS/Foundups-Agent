# CLI Module Interface

## Public API

### main_menu.py
- `run_main_menu()` - Entry point for interactive CLI

### utilities.py
- `console_input(prompt: str = "") -> str` - Main-menu input with temporary
  calling-thread filters on existing stdout/stderr logging handlers. File sinks
  and preexisting filters are preserved; EOF/KeyboardInterrupt propagate after
  cleanup. This is a logging boundary, not capture of native or arbitrary output.
- `env_truthy(name: str, default: str = "false") -> bool`
- `env_flag(name: str, default_on: bool = True) -> bool`
- `maybe_clear_screen() -> None`
- `update_env_file(key: str, value: str) -> None`
- `set_env_bool(key: str, enabled: bool) -> None`
- `select_channel() -> str`
- `holo_controls_menu() -> None`
- `holo_advanced_controls_menu() -> None`

### youtube_controls.py
- `yt_switch_summary() -> str`
- `yt_scheduler_controls_menu() -> None`
- `yt_controls_menu() -> None`

### youtube_menu.py
- `handle_youtube_menu(args, should_skip, pm) -> None`

### indexing_menu.py
- `handle_indexing_menu() -> None`

### holodae_menu.py
- `handle_holodae_menu() -> None`

### git_menu.py
- `handle_git_menu() -> None`

## Dependencies

- `modules.infrastructure.instance_lock`
- `modules.ai_intelligence.holo_dae`
- `modules.communication.livechat`
- `modules.platform_integration.youtube_shorts_scheduler`
