# Video Comments Test ModLog

**Module:** communication/video_comments/tests
**WSP Reference:** WSP 34 (Test Documentation)

## 2026-08-09 - Context-Grounded Reply Regression Suite

Added `test_reply_context_pipeline.py` with seven isolated tests that do not load external models or call network services.

Coverage includes:

- Full original comment, semantic guidance, per-row video title, commenter context, and verified memory reaching embedded Qwen
- Qwen stop-token override that avoids false empty replies
- VoiceMemory queries combining the video title and comment
- #FFCPLN semantic handling without automatic troll classification
- Video title and target-channel propagation through both generator and processor boundaries
- Studio DOM result retention for video title, ID, and URL
- Context-source gate rejection of templates, stale/unknown sources, and stats-only replies

Validation receipts:

- `test_reply_context_pipeline.py`: 7 passed
- `test_ytr1_runtime_hardening.py`: 11 passed (2 upstream deprecation warnings)
