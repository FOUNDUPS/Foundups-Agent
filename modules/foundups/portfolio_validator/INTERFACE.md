# Portfolio validator interface

The package [exports](__init__.py) `Violation`, `ValidationReport`, `load_sources`
and `run_validation` from [src/validator.py](src/validator.py). This is an
observation-only Phase 1 validator; it does not generate or repair the portfolio.

`load_sources(repo_root, registry_path=None, catalog_path=None,
projection_path=None, manifest_dir=None) -> Sources` reads the registry, runtime
catalog, derived portfolio and per-FoundUp manifests. Missing/malformed required
JSON and handled read failures raise `SourceError`; malformed or missing optional
manifests are skipped. Registry/projection must contain `entities`, and catalog
must be an array. This is not full nested schema validation or a sealed-path
security boundary. Optional overrides use ordinary Path joining semantics.

`run_validation(sources) -> ValidationReport` runs the ordered R1–R11 and C1–C4
rules and returns violations plus supplementary inventory counts. Ordinary
violations do not raise; unexpected rule exceptions can. A violation includes
rule_id, severity, entity, field, expected, actual, source and message. Report
`to_dict()` emits `violations`, `stats` and error/warning/total summary counts.

The [CLI](__main__.py) supports `--check`, `--json` and `--repo-root`. It exits
0 for no findings, **1 for errors or warnings**, and 2 for caught `SourceError`.
The implementation's warning exit behavior takes precedence over the stale
`Violation` docstring saying warnings do not cause failure. Repo-root discovery
walks parents for modules/WSP_framework/public markers. No fix/update action or
CI-gate activation is exposed by this interface. Existing tests remain in
`tests/test_validator.py`; this documentation review did not rerun them or claim
deployment, endpoint availability, or current portfolio correctness.
