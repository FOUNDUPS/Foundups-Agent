# WSP compliance checker tests

`test_wsp_compliance_checker.py` exercises the real scanner against temporary Git
repositories. It checks tracked-only scope, no imported application source or
database creation, environment exclusion, malformed/conflicted/truncated inventory,
link/reparse rejection, missing files, per-file/total byte limits, caller Git
environment isolation, repeated scans and unchanged files/index. Structural cases
cover current size thresholds, direct component counts, real duplicate block
names, domain-level source/tests, monitoring and WSP 3's wre_core exception.

Two constructor cases execute the GitHub adapter's real constructor body with
inert dependency objects. They prove default/explicit checkout binding without
importing network clients or initiating any GitHub action.

```text
python -B -m pytest -q -c NUL --noconftest --import-mode=importlib -p no:cacheprovider modules/infrastructure/wsp_core/tests/test_wsp_compliance_checker.py
```

On POSIX use `/dev/null` in place of `NUL`. Disable automatic pytest plugins and
bytecode generation, and use `PYTHON_DOTENV_DISABLED=1`. CI includes this exact
test owner in its existing audit contract selection. Do not collect unrelated
operational test directories. No live browser, provider or database is required.

The frozen candidate has 39 passing cases; the same acceptance on main3ad has
31 failures and 8 passing controls. Baseline reproduction explicitly denies the
old PatternMemory constructor so it cannot create a real database. See
[TestModLog.md](TestModLog.md). These tests do not validate other WSP core engines.

The subsequent F6a policy layer adds ten cases in the same test owner (49 total).
These bind the shared constants to both WSP 3 mirrors and exercise real scanner
behavior for data-only containers and suppressions, immutable compatibility
aliases, root-contract/src/tests evidence, reserved names, generator inputs and
pure-policy no-IO calls. They do not authorize physical directory migrations.
