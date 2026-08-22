# p.fMALL Tests

The suite verifies the Python shell/catalog surfaces, the Firebase/member Mall
contracts, and protected-decision boundaries. Tests are local and must not
mutate Holo replicas or trigger a Holo reindex.

## Test inventory

| File | Primary coverage |
|---|---|
| `test_shell_core.py` | Manifest validation/discovery, catalog, route, tile, shell boot |
| `test_api.py` | Dict adapter and default-shell behavior |
| `test_http_api.py` | FastAPI JSON routes |
| `test_shell_ui.py` | Static shell and route handoff |
| `test_member_catalog_export.py` | Canonical member projection/export |
| `test_catalog_foundup_truth_gate.py` | Catalog entity/status truth |
| `test_mall_video_catalog.py` | Video catalog shape and projections |
| `test_mall_video_player.py` | Player, gestures, queue, return, save/share/history |
| `test_video_mall_media_delivery.py` | Media paths, headers, embed and service-worker rules |
| `test_member_foundup_entry.py` | Member FoundUp entry flow |
| `test_member_pwa_hardening.py` | Manifest, service worker, restore, and wiring |
| `test_member_red_dog_concierge.py` | Shell-local FAQ concierge; no backend/AI claim |
| `test_gateway_roc_shell.py` | Gateway shell and phased runtime contracts |
| `test_gateway_terms_gate.py` | Terms/disclaimer/admission UI |
| `test_verification_gap_guard.py` | Protected decisions and advisory local-AI boundary |

The repository-level PFMall Tier-0 regression lives in
`holo_index/tests/test_tier0_retrieval_hardening.py` because it verifies the
shared Holo contract rather than PFMall runtime behavior.

## Commands

```powershell
python -m pytest modules/foundups/pfmall/tests -q
python -m pytest holo_index/tests/test_tier0_retrieval_hardening.py -q
python modules/infrastructure/wre_core/scripts/generate_test_registry.py --check
```

For focused work, execute the nearest test file first and expand to the full
module suite. A merged Holo documentation change additionally requires the
governed exact-main maintenance/activation flow and a digest-stable owner query;
pytest is not a substitute for that operational proof.

## Original pre-rebase baseline

At the original pre-rebase baseline
`f06ca1fcc4acc9e2645a3ed898bad844ac6df298`, the full module suite reported 588
passes and 19 failures. The candidate reproduced the same 19 node IDs. They are
inherited catalog enum/projection drift, member UI/concierge expectation drift,
one hard-coded `O:/Foundups-Agent` fixture, and missing tracked media
directories. They are not quarantined or claimed clean by this Tier-0 repair.
The exact post-#1538 Git parent is `69b7f073`; the focused Holo Tier-0 suite is
the acceptance surface for this slice.
