# Algorand module memory

## Retrieval and ownership — 2026-10-25

Canonical Holo query is degraded with `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`,
freshness UNKNOWN/index gap; no reindex or CURRENT semantic evidence is claimed.
Verified direct-source retrieval used NAVIGATION, platform domain structure,
placeholder blockchain and local mining/token utilities, FAM intent/persistence,
canonical test registry/CI and pinned SDK source. No existing unsigned ASA codec
was found. New module memory artifacts were absent before this allocated slice.

Retrieval evaluation: placeholder/simulator readiness was noise; source call paths
were prioritized over historical plans. Deduplicated owner/source documentation
and bounded SDK chunks supplied the missing format details. Historical branch and
source snapshots remain dated; this module creates no duplicate ledger/registry.
The concrete format boundary needs no Qwen/Gemma execution or model download.

SDK2.12.0 source observations: `transaction.py` SHA256
`400158a5f596bea8e5e342d8ef28dd72b0dcca4032dd92033f6231880dfe7d3e`;
`encoding.py` SHA256
`a2380d0f25b3514fb58313eb6716d4d0c659fcbca34fda386890ac7059dcfc45`.
The non-flat estimator generates an account/signs; use `flat_fee=True`. Generic
`msgpack_decode` dispatches signed/wrapper types; strict raw-map validation and
comparison against rebuilt expected bytes avoid that broader input surface.

Remember: declared source hash/auth/decimals are binding inputs, not verified
authority or ledger facts. Format validity is separate from funded issuance,
reward conversion, durable intent consumption, signing and network settlement.
Future execution must bind the exact source, dependencies and ordinary module
origins; do not copy/alias code around a repository import-denial profile.
