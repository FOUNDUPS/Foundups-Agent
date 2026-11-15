# Kids Episodes tests

Run from repository root:

```bash
python -m pytest -q modules/foundups/kids_episodes/tests
```

`test_story_pipeline.py` uses injected fake assets, admission, generation, rendering and review to prove bounded state transitions. It does not prove live authority, education quality or provider execution. It checks source coverage, linked continuity, provider capability durations, stable IDs, input/runtime/artifact binding, interrupted-effect replay refusal, review completeness, bounded retry and resume re-review.

Provider adapter tests use fake clients. Actual FFmpeg integration tests, when present, are separate and require FFmpeg/ffprobe; their reviewer remains an explicit test double. No test reads credentials, pays a provider or uploads to YouTube.

`test_little_shrew.py` verifies canonical plan round-trip, complete nine-beat coverage, episode joins, supported provider durations, safe-family source content, portable asset hashes and identical SVG rig definitions. It does not verify live generation, audio or semantic video quality.


`test_tile_batch.py` also runs without third-party dependencies using
`python -B -m unittest modules.foundups.kids_episodes.tests.test_tile_batch -v`.
It checks five-tile dependency ordering, bounded repairs, identity binding,
self-review rejection and each missing/failed criterion. Record completeness
is not authenticated runtime acceptance or proof of educational quality.
