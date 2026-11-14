# System health tool tests

[`test_wsp_85_validator.py`](test_wsp_85_validator.py) is the bounded offline
root-validator owner. Its disposable directories cover foundational configuration,
misplaced scripts, temporary/prompt artifacts and escaped Windows drive names.
Content-preservation assertions check that classification does not delete work.

From the repository root with the existing qualified Python and pytest:

```text
python -B -m pytest -q -c NUL --noconftest --import-mode=importlib -o pythonpath=. -p no:cacheprovider modules/infrastructure/system_health_monitor/tests/test_wsp_85_validator.py
```

Use `/dev/null` instead of `NUL` on POSIX and disable automatic pytest plugin
loading in the caller environment. This selection does not establish analyzer
coverage, live service health, whole-repository compliance or deletion safety.

`system_integration_test.py` and `detailed_workflow_test.py` are legacy manual
drivers with authentication, stream/chat and social-publishing paths. Do not run
them as an incidental part of root cleanup. Their existence is not passing
offline test evidence. Historical generated coverage percentages and placeholder
test filenames have been replaced with this actual test scope.
