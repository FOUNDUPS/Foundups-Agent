# Assumption Audit: HoloIndex declared runtime ABI phase 1

## Boundary

The exact base and dependency generations and their inert composition prove
bytes and topology, but not that Windows can safely load the selected native
images into CPython 3.12. This transaction adds only an offline, inert,
composition-bound static ABI attestation. Its ABI source remains outside the
executable backend manifest and VSIX. A shared Windows publication repair does
change the backend manifest and therefore rebinds the 0.4.139 thin-client
release without adding ABI authority. The transaction may not load a DLL/PYD,
start an owner, alter a route, sign artifacts, change ACLs, register a Skill,
claim Windows loader closure, or claim A-grade/retrieval RSI.

## Governed retrieval evaluation

The canonical owner query returned `CURRENT` at exact base
`6b06a3ba909e5dea9c72aae68114b376282107cd`, with no index gap and no reindex.
Results correctly found the existing composition and runtime security family,
but generic test records displaced adjacent ABI-specific sources. Because the
candidate overlay was uncommitted and therefore outside committed retrieval
authority, exact direct reads completed the audit. No maintenance, route, or
owner mutation was performed.

## External primary-source reconciliation

Microsoft's PE format documentation describes delay-import fields as RVAs and
also says the Attributes field must be zero. Microsoft's current MSVC delay
helper documentation instead defines `dlattrRva` and says that attribute marks
the descriptor fields as RVAs. Real installed MSVC-built PE32+ samples use
`dlattrRva=1`. The phase-1 parser therefore admits only the unambiguous modern
RVA subset and rejects attribute zero rather than interpreting two dialects
identically. It validates the normal and delay lookup/address tables, delay
HMOD virtual storage, bounded optional tables, terminators, and forwarders.

Python's Stable ABI guidance says Windows stable-ABI extensions link to
`python3.dll`, while version-specific CPython 3.12 extensions link to the
versioned DLL. Wheel compatibility is separately derived from the standardized
Python/ABI/platform tag tuple. These sources support static compatibility
checks; none describes actual Windows loader search-order proof.

- Microsoft PE format: <https://learn.microsoft.com/en-us/windows/win32/debug/pe-format>
- Microsoft delay-load helper: <https://learn.microsoft.com/en-us/cpp/build/reference/understanding-the-helper-function?view=msvc-170>
- Python Stable ABI: <https://docs.python.org/3.12/c-api/stable.html>
- Python packaging compatibility tags: <https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/>

## WSP_15 allocation and dialectic

| Candidate | C/I/D/Im | MPS | Decision |
|---|---:|---:|---|
| Repair and publish inert declared ABI evidence | 5/5/5/5 | 20 / P0 | **GO now** |
| Bind an explicit executable dependency closure | 5/5/5/5 | 20 / P0 | Next separate slice |
| Actual Windows loader/dynamic-load closure | 5/5/4/5 | 19 / P0 | Blocked on executable closure |
| Signer, empirical write denial, deterministic pre-import | 5/5/4/5 | 19 / P0 | Blocked on loader closure |
| Owner/route/VSIX propagation | 4/4/2/4 | 14 / P1 | Must remain deferred |

The rejected alternative was to scan every `.exe`, `.dll`, and `.pyd` in the
entire 72,261-file dependency payload and then ignore incompatible utilities
by filename. That would encode host accidents as policy. The accepted phase
attests every native member of its supplied composition and truthfully fails
the current broad production shape; a future content-bound executable-closure
manifest must define the smaller relevant set without weakening byte hashing.

## Assumptions and falsifiers

| ID | Assumption | Falsifier and result |
|---|---|---|
| A1 | PE parsing is inert and bounded. | Malformed headers, overlaps, null RVAs, missing tables, repeated thunks, exhaustion, and unsupported dialects reject without loading. |
| A2 | Declared imports are structurally loadable metadata. | Normal IAT and delay HMOD/IAT/INT zero or length mismatch reject; every present optional delay table must match the lookup count. |
| A3 | Export presence is not enough when forwarded. | Forwarded Python exports and forwarded `PyInit_*` entries cannot earn CPython-link evidence. |
| A4 | Wheel metadata owns every dependency-native byte exactly once. | Traversal, duplicate normalized RECORD paths, absent hashes, wrong hashes/sizes, multiple owners, and incompatible tags reject. |
| A5 | Static graph reachability is not loader routing. | Duplicate local and nonlocal Python-DLL basename cases reject; all external loader-resolution authority remains false. |
| A6 | Aggregate work cannot multiply across images/descriptors. | Repeated thunk and name RVAs are cached; every EAT slot plus decoded name byte counts toward aggregate descriptor/thunk/export/name/edge budgets. |
| A7 | Publication errors do not disclose private paths. | Injected OS exceptions surface only stable ABI error codes. |
| A8 | Windows long paths preserve failed evidence safely. | Extended-path no-replace publication followed by injected final rejection quarantines the canonical generation and leaves no visible success name. |
| A9 | Passing static evidence is not activation. | Schema validation forces loader, determinism, bootstrap, signature, write denial, activation, and exact closure false. |

## Independent hostile review

Three WSP_00/WSP_97 reviewers independently returned NO-GO on the initial
green suite. Their reproduced counterexamples caused the delay-dialect,
null-table, paired-table, aggregate-budget, forwarder, RECORD, error-channel,
long-path, and WSP_62 repairs. The graph was extracted into its own module;
every new infrastructure source is below 600 lines and every touched/new
function is at or below 50 lines. Final closure review additionally reproduced
unmapped export targets, zero-slot EAT undercounting, repeated name-RVA work,
optional delay-table undercounting, and collision error drift; each now has a
focused fail-closed regression. The final first-principles pass also confined
every NUL-terminated name to its mapped raw span and every forwarder string to
the declared export-directory range.

## Production-shaped falsification

A read-only scan of the active O:-backed repository virtual environment found
396 native-suffix artifacts. The repaired parser accepted 388 PE32+ images: 384
AMD64 and four ARM64. It rejected eight PE32 images. Separate metadata review
also found duplicate RECORD ownership. Therefore the current whole-environment
composition does not satisfy this AMD64/CP312 phase. This is the correct
outcome and is not a parser defect or permission to create exceptions.

## Decision

Proceed only with the inert declared-ABI modules and the shared Windows
extended-path no-replace repair. Preserve all activation-grade fields false.
The next focused transaction must define and content-bind the exact executable
dependency closure (or build a clean pinned query-only environment), then
repeat this attestation over that closure. Actual loader behavior, dynamic
loads, signatures, deterministic pre-import execution, empirical write denial,
resident owner selection, route-v2, and A-grade remain later independent gates.
