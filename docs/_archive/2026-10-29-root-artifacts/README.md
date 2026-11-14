# Preserved root artifacts — 2026-10-29

These artifacts were relocated from the repository root after source/hash review.
They remain historical evidence; relocation does not validate their instructions,
runtime claims, credentials, deployment settings or readiness. Current execution
instructions remain in [CLAUDE.md](../../../CLAUDE.md). No shared-PC files were
cleaned or overwritten by these tracked relocations.

| Original Git path | Destination | Bytes | SHA-256 before relocation |
| --- | --- | ---: | --- |
| `.prompt_reddog_always_holoindex_grounding_phase1.md` | `extensions/reddog/docs/prompts/always_holoindex_grounding_phase1.md` | 11946 | `b4650ae7fcd27148755bc8eb4d2b14b79dec834494a1b246a4a702fddbd0a492` |
| `.prompt_reddog_context_target_content_inclusion_phase1.md` | `extensions/reddog/docs/prompts/context_target_content_inclusion_phase1.md` | 15183 | `7d65c71457810b5b97da6aa41c5a12bbfc2b9101f15ca92752454c92ef126dda` |
| `OFoundups-Agentfirestore.indexes.json` | `docs/_archive/2026-10-29-root-artifacts/firestore.indexes.malformed.json.txt` | 182 | `100d266006d25cc79c4a17d3db9e8fad10b39662fd2a7adc17d2dc76ebd9826c` |
| `SUPERADMIN_ONBOARDING.md` | `docs/SUPERADMIN_ONBOARDING.md` | 5055 | `0789e43969c43bf065a0663dfcd838a8326f94fc726e326193b9936fd094a25d` |
| `WRE_COT_DEEP_ANALYSIS.md` | `modules/infrastructure/wre_core/docs/WRE_COT_DEEP_ANALYSIS.md` | 7938 | `839e2dca01212a803403dccb2bdecc0fe29dacd5bba12b1d14b2c569934c2ee8` |
| `image.png` | `docs/_archive/2026-10-29-root-artifacts/verify-filenames.png` | 5656 | `37201a361f6851d08baf759a6b8bdb287fe18f0b8a2a22b5e06ab9c9a996e823` |

Source comparison: main `cb227122828f60d58b50de1046abb09ae31a0929`. Five files retain exact Git bytes.
The onboarding runbook retains its original body with six relative link corrections
and an explicit historical-status notice. Hashes above describe Git blob bytes;
Windows checkout CRLF conversion was checked separately. The screenshot is not edited.
The escaped-name Firestore text was already tracked and is malformed JSON; it is
preserved as text, not installed as a Firebase deployment configuration. Root
`firebase.json` bindings are unchanged. Git history retains all original paths.

## Escaped E-drive snapshot

The additional `E\uf03a` directory was tracked, not untracked clutter. Its six
files are preserved under `escaped-drive-e/HoloIndex/`. Vector files last changed
in commit `329123fb64aac377dc2fa2f32eda6fded1f74f0b` (2025-11-12); the WSP summary
last changed in `3791fb7928c0f4ed35ec255b51ae55ca416118bb` (2026-02-20).
A literal tracked-text reference scan found only `.dockerignore`; that exclusion
is retained. This is historical data, not the active `E:/HoloIndex` store or an
accepted semantic generation. No pickle deserialization, vector loading, live
index replacement or configuration change was performed. External consumers
are not established by the repository reference scan.

| Original Git path | Bytes | SHA-256 |
| --- | ---: | --- |
| `E/HoloIndex/indexes/wsp_summary.json` | 179330 | `9871b03a9a01ca8459e074e24c30c5247641e326f5b7b56f5a5493a86c76f50e` |
| `E/HoloIndex/vectors/ac0901fb-0ee1-46bc-980a-ee4447f43801/data_level0.bin` | 2205616 | `42636a9ea314eaf2d2fb3602fd2efd3e266633a76a38612b172d57f28d858fb9` |
| `E/HoloIndex/vectors/ac0901fb-0ee1-46bc-980a-ee4447f43801/header.bin` | 100 | `9bcc34d0a534ea5c3a0228304633f5290d068c1f711c12e461e98f83d18a5ea9` |
| `E/HoloIndex/vectors/ac0901fb-0ee1-46bc-980a-ee4447f43801/index_metadata.pickle` | 45304 | `4b3e16d449f119a7832732d30259bb0687d99113bea195f9f3c8a6c42c836547` |
| `E/HoloIndex/vectors/ac0901fb-0ee1-46bc-980a-ee4447f43801/length.bin` | 5264 | `ed3aabd805ecdc1af726ff3b4e214bdb2da85d4e1cd20da86dbca1f040c23eaf` |
| `E/HoloIndex/vectors/ac0901fb-0ee1-46bc-980a-ee4447f43801/link_lists.bin` | 11384 | `e120a5983bbb47d5e382dfdbe639547be42daca7fb377711e42c509ed4b033a3` |

All six Git blobs (2446998 bytes total) and the Windows filesystem
bytes are preserved. The directory move was limited to the verified owned
checkout and rejected extra files, reparse entries and destination collisions.
