"""Bounded exact-row injections for HoloIndex collection search."""

from __future__ import annotations

from typing import Sequence

from holo_index.tier0_retrieval import module_tier0_paths


def _remove_initial_tier0_rows(
    docs: list, metas: list, dists: list, expected: set[str]
) -> None:
    """Force strict owners to replace vector Tier-0 rows with exact reads."""
    if not (len(docs) == len(metas) == len(dists)):
        raise RuntimeError("HOLOINDEX_STRICT_TIER0_LOOKUP_FAILED")
    keep = [
        index for index, meta in enumerate(metas)
        if str((meta or {}).get("path") or "").replace("\\", "/").lower()
        not in expected
    ]
    docs[:] = [docs[index] for index in keep]
    metas[:] = [metas[index] for index in keep]
    dists[:] = [dists[index] for index in keep]


def inject_module_tier0_candidates(
    collection, docs: list, metas: list, dists: list, module_path: str, *,
    strict: bool = False,
) -> tuple[str, ...]:
    """Inject exactly one authoritative README and INTERFACE collection row."""
    required = module_tier0_paths(module_path)
    expected = {path.lower() for path in required}
    if strict:
        _remove_initial_tier0_rows(docs, metas, dists, expected)
    existing = {
        str((meta or {}).get("path") or "").replace("\\", "/").lower()
        for meta in metas
    }
    missing: list[str] = []
    for path in required:
        if path.lower() in existing:
            continue
        try:
            result = collection.get(
                where={"path": path}, include=["documents", "metadatas"]
            )
            found_docs = list(result.get("documents") or [])
            found_metas = list(result.get("metadatas") or [])
            if not found_docs and not found_metas:
                missing.append(path)
                continue
            if len(found_docs) != 1 or len(found_metas) != 1:
                raise ValueError("tier0_lookup_cardinality_invalid")
            meta = dict(found_metas[0] or {})
            found_path = str(meta.get("path") or "").replace("\\", "/")
            if found_path != path:
                raise ValueError("tier0_lookup_path_mismatch")
        except Exception as exc:
            missing.append(path)
            if strict:
                raise RuntimeError("HOLOINDEX_STRICT_TIER0_LOOKUP_FAILED") from exc
            continue
        docs.append(found_docs[0])
        meta["_retrieval_provenance"] = "exact_metadata"
        metas.append(meta)
        dists.append(None)
        existing.add(path.lower())
    if strict and missing:
        raise RuntimeError("HOLOINDEX_STRICT_TIER0_INCOMPLETE")
    return tuple(missing)


def inject_wsp_alias_candidates(
    collection, docs: list, metas: list, dists: list,
    alias_wsps: Sequence[str], extract_wsp_numbers,
) -> None:
    """Append exact WSP alias rows absent from the vector candidate set."""
    if not alias_wsps:
        return
    existing = {(meta.get("path") or "").lower() for meta in metas}
    try:
        all_data = collection.get(include=["documents", "metadatas"])
        all_docs = all_data.get("documents", [])
        alias_set = set(alias_wsps)
        for index, meta in enumerate(all_data.get("metadatas", [])):
            path = (meta.get("path") or "").lower()
            title = (meta.get("title") or "").lower()
            targets = set(extract_wsp_numbers(path) + extract_wsp_numbers(title))
            if path not in existing and alias_set & targets:
                docs.append(all_docs[index])
                metas.append(meta)
                dists.append(1.5)
                existing.add(path)
    except Exception:
        return


__all__ = ["inject_module_tier0_candidates", "inject_wsp_alias_candidates"]
