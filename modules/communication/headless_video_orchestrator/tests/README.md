# Headless Video Orchestrator Offline Tests

Run from the checkout root using the vetted repository virtualenv:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
& "O:/Foundups-Agent/.venv/Scripts/python.exe" -B -m pytest modules/communication/headless_video_orchestrator/tests/test_headless_video_orchestrator.py -o addopts=""
```

Tests synthesize small local PNG/audio/MP4 fixtures via `ffmpeg`/`ffprobe` in `tmp_path` with zero network, browser, OAuth, or paid provider calls. Synthetic fixtures prove deterministic pipeline contracts, crop-ratio math, motion-label honesty, decode verification, and dry-run gating — not creative comedy quality.
