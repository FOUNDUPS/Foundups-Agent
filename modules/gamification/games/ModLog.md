# Games Module - ModLog

## 2026-10-27 — Cross-product review candidate

Linked EDUIT's prototype interactive-experience Skillz for audience, visible UI,
timing, incentives and state audits. Reused WRE ownership and evidence boundaries;
no game runtime, registry, admission or scheduler changes. First-use evidence
belongs to EDUIT. Cross-game transfer remains unverified. WSP 95/97; docs only.

## V1.0.0 (2026-03-05)

### Initial Release

**Features:**
- Chess game engine (python-chess wrapper)
- Checkers game engine (custom implementation)
- GameManager for matchmaking and turn management
- Random color assignment for fairness
- OBS Browser Source displays for visual boards
- Chat command integration (!chess, !checkers, !move, !resign, !board)

**Architecture:**
- `src/game_manager.py` - Singleton game orchestrator
- `src/chess_engine.py` - Chess logic via python-chess
- `src/checkers_engine.py` - Native checkers implementation
- `assets/chess_board.html` - OBS browser source for chess
- `assets/checkers_board.html` - OBS browser source for checkers
- `data/*.json` - State files for IPC with browser sources

**WSP Compliance:**
- WSP 3: gamification domain
- WSP 49: Standard module structure
- WSP 72: Independent of other modules (uses file IPC)

**Dependencies:**
- python-chess >= 1.9.0

**Integration:**
- Command routing via livechat/command_handler.py
- Command detection via livechat/message_processor.py

**Testing (V1.0.0)**:
- **17/17 tests passing** (see tests/TestModLog.md)
- Manual test runner (`run_tests.py`) bypasses web3 pytest plugin issues
- Chess: 5 tests (new_game, moves, board display, legal moves)
- Checkers: 5 tests (new_game, moves, jumps, king promotion)
- GameManager: 7 tests (matchmaking, turns, resign, state)
- Bug fixed: Checkers jump test used light squares instead of dark
