# CLI Module

This module provides the command-line interface for the FoundUps Agent system.

Japanese STT: set `OPENCLAW_VOICE_STT_LANGUAGE=ja`; the Whisper, Cohere and Google
adapters receive the selected language. Explicit adapter arguments override the
environment. Cohere decoding supports current `decode` and older `batch_decode`
processors. Desktop TTS is unchanged. Speech imports no longer boot the main menu.
The [Japanese message-call prototype](../../platform_integration/elevenlabs_calls/README.md)
reuses microphone capture with a dedicated local command; general RedDog voice
routing has no newly registered telephone action.

## Purpose

Extracted from `main.py` per WSP 62 (file size enforcement) to maintain compliant module sizes.

## Structure

```
cli/
├── src/
│   ├── utilities.py        # Common helpers, env functions, holo controls
│   ├── youtube_controls.py # YT control planes and scheduler controls
│   ├── youtube_menu.py     # YouTube DAEs submenu handlers
│   ├── indexing_menu.py    # YouTube indexing submenu
│   ├── holodae_menu.py     # HoloDAE menu handlers
│   ├── git_menu.py         # Git operations submenu
│   └── main_menu.py        # Argument parsing, dispatch, main loop
├── tests/
├── memory/
└── README.md
```

## Usage

The CLI module is imported by the root `main.py` which serves as a thin router:

```python
from modules.infrastructure.cli.src.main_menu import run_main_menu
run_main_menu()
```

You can also run the package directly:

```bash
python -m modules.infrastructure.cli --chat
python -m modules.infrastructure.cli --voice
python -m modules.infrastructure.cli --agent-command "linkedin action read_feed max_posts=2"
```

## WSP Compliance

- **WSP 62**: All files under 600 lines (well below 1200-line OK threshold)
- **WSP 49**: Standard module structure with src/, tests/, memory/
- **WSP 60**: Memory directory included for future state persistence
