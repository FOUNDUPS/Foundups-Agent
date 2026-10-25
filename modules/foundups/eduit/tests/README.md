# Story Time verification

Run from the repository root:

```powershell
node --test modules/foundups/eduit/tests/*.test.mjs
python -B -m unittest discover -s modules/foundups/eduit/tests -p "test_*.py"
node --test modules/communication/youtube_shorts/tests/kids_review.test.mjs
```

The Node suite exercises the real engine/scene, lifecycle, page controller and
worker in controlled DOM/worker harnesses. Python packaging tests stub the
renderer; the full build separately exercises Cairo/FFmpeg rendering.
See `TestModLog.md` and `../DEPLOYMENT.md` for actual browser/hosting results.
Automated input/controller checks do not prove physical touch-device acceptance
or that the rendered audio has been listened to.
