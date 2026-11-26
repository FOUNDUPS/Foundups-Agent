"""Offline WRE Lego block compiler, catalog reconciler, and conservative triage projection."""

from __future__ import annotations
import ast, hashlib, json, re, subprocess, warnings
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence
from .wre_test_registry import REGISTRY_PATH, TestRegistryEntry, load_canonical_test_registry
from .wre_test_registry_ast import import_aliases, module_effects, node_name
from .wre_test_registry_classification import owner_for_path

SCHEMA_VERSION, M2M_SCHEMA_VERSION = "wre_lego_block_projection.v1", "wre_lego_block_projection_m2m_v1"
AGI_SCAFFOLDING_HYPOTHESIS, FOUNDUP_REGISTRY_REL_PATH = "HYPOTHESIS_UNDER_TEST", "modules/foundups/foundup_registry.json"
BYTE_STATUSES = ("CLEAN_EXACT_MATCH", "EOL_CRLF_DRIFT", "MODIFIED_CONTENT", "UNTRACKED")
STATIC_TIERS = ("DOCUMENTED_ONLY", "STATICALLY_ANALYZED")
CAPABILITY_STATUSES = ("UNVERIFIED_STATIC_ONLY", "VERIFIED_CAPABILITY", "STALE_PROVENANCE_MISMATCH")
TRIAGE_CLASSIFICATIONS = ("ACTIVE_STATIC_CALLERS", "CANDIDATE_ZERO_STATIC_CALLERS", "INTENTIONAL_ENTRYPOINT_OR_STUB", "UNKNOWN_DYNAMIC_OR_EXTERNAL_CONSUMER")
CATALOG_RELATION_TYPES = ("FOUNDUP_TO_MODULE", "FOUNDUP_TO_MANIFEST", "MODULE_TO_TEST_SHARD", "SHARD_TO_TEST_FILE", "BLOCK_IMPORTS_BLOCK")
CATALOG_DIAGNOSTIC_CODES = ("DUPLICATE_MANIFEST_FOUNDUP_ID", "EXTERNAL_FOUNDUP_NO_LOCAL_MODULE", "MODULE_WITHOUT_FOUNDUP", "MODULE_WITHOUT_TEST_SHARD", "QUARANTINED_TEST_ENTRY")
_EXCLUDE_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}
_SUBBLOCK_SKIP_DIRS = {"src", "tests", "scripts", "docs", "memory"} | _EXCLUDE_DIRS
_ENTRYPOINT_NAMES = {"__init__.py", "__main__.py", "main.py", "cli.py", "dae.py", "daemon.py", "run_skill.py", "run_wre.py"}

def compute_git_blob_oid_sha1(raw_bytes: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw_bytes)}\0".encode("ascii") + raw_bytes).hexdigest()

def sha256_bytes(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()

@dataclass(frozen=True)
class ExactByteProvenance:
    git_blob_oid_sha1: str | None
    git_blob_sha256: str | None
    checkout_bytes_sha256: str
    byte_status: str
    def __post_init__(self) -> None:
        if self.byte_status not in BYTE_STATUSES or not self.checkout_bytes_sha256:
            raise ValueError("invalid_exact_byte_provenance")
        if self.byte_status == "UNTRACKED":
            if self.git_blob_oid_sha1 is not None or self.git_blob_sha256 is not None:
                raise ValueError("untracked_provenance_cannot_have_git_hashes")
        elif not self.git_blob_oid_sha1 or not self.git_blob_sha256 or self.git_blob_oid_sha1 == self.git_blob_sha256:
            raise ValueError("tracked_provenance_hashes_invalid")
        elif (self.byte_status == "CLEAN_EXACT_MATCH") != (self.checkout_bytes_sha256 == self.git_blob_sha256):
            raise ValueError("clean_exact_match_iff_identical_sha256")
@dataclass(frozen=True)
class RenameAliasRecord:
    prior_id_or_path: str
    source_kind: str
@dataclass(frozen=True)
class BlockIdentity:
    canonical_id: str
    current_posix_path: str
    parent_block_id: str | None = None
    aliases: tuple[RenameAliasRecord, ...] = ()
@dataclass(frozen=True)
class CatalogRelation:
    relation_type: str
    source_id: str
    target_id: str
    detail: str = ""
    def __post_init__(self) -> None:
        if self.relation_type not in CATALOG_RELATION_TYPES or not self.source_id or not self.target_id:
            raise ValueError(f"invalid_catalog_relation:{self.relation_type}")
@dataclass(frozen=True)
class CatalogDiagnostic:
    code: str
    subject_id: str
    related_paths: tuple[str, ...]
    detail: str
    def __post_init__(self) -> None:
        if self.code not in CATALOG_DIAGNOSTIC_CODES or not self.subject_id:
            raise ValueError(f"invalid_catalog_diagnostic:{self.code}")
@dataclass(frozen=True)
class VerifiedCapabilityReceipt:
    block_id: str
    capability_id: str
    source_git_blob_oid_sha1: str
    source_git_blob_sha256: str
    executed_checkout_sha256: str
    dependency_lock_sha256: str
    environment_fingerprint_sha256: str
    inputs_sha256: str
    verifier_receipt_id: str
    evidence_origin: str
    def __post_init__(self) -> None:
        if self.evidence_origin == "SIMULATED_TRANSITION_ONLY" or self.evidence_origin.startswith("SIMULATED"):
            raise ValueError("simulated_evidence_cannot_verify_runtime")
        vals = (self.block_id, self.capability_id, self.source_git_blob_oid_sha1, self.source_git_blob_sha256, self.executed_checkout_sha256, self.dependency_lock_sha256, self.environment_fingerprint_sha256, self.inputs_sha256, self.verifier_receipt_id, self.evidence_origin)
        if not all(isinstance(v, str) and v.strip() for v in vals):
            raise ValueError("verified_capability_receipt_missing_required_binding")
@dataclass(frozen=True)
class CapabilityVerificationState:
    capability_id: str
    status: str
    verifier_receipt_id: str | None = None
    reason: str = "static_analysis_only"
    def __post_init__(self) -> None:
        if self.status not in CAPABILITY_STATUSES or not self.capability_id:
            raise ValueError(f"invalid_capability_status:{self.status}")
@dataclass(frozen=True)
class AstBlockSummary:
    imported_modules: tuple[str, ...] = ()
    exported_symbols: tuple[str, ...] = ()
    module_effects_flags: tuple[str, ...] = ()
    has_dynamic_dispatch: bool = False
    parse_error: str | None = None
@dataclass(frozen=True)
class BlockTriageRecord:
    block_id: str
    classification: str
    static_caller_block_ids: tuple[str, ...] = ()
    contrary_evidence: tuple[str, ...] = ()
    consumer_scope_complete: bool = True
    is_dead_code_proven: bool = False
    deletion_authorized: bool = False
    def __post_init__(self) -> None:
        if self.deletion_authorized is not False or self.is_dead_code_proven is not False:
            raise ValueError("deletion_authorized_must_be_false")
        if self.classification not in TRIAGE_CLASSIFICATIONS:
            raise ValueError(f"invalid_triage_classification:{self.classification}")
@dataclass(frozen=True)
class LegoBlockRecord:
    identity: BlockIdentity
    block_kind: str
    provenance: ExactByteProvenance | None
    static_tier: str
    runtime_claims_enabled: bool
    ast_summary: AstBlockSummary | None
    declared_capabilities: tuple[str, ...]
    capability_statuses: tuple[CapabilityVerificationState, ...]
    depends_on_block_ids: tuple[str, ...]
    triage: BlockTriageRecord
    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "canonical_id": self.identity.canonical_id}
@dataclass(frozen=True)
class LegoProjectionReport:
    schema_version: str
    agi_scaffolding_hypothesis: str
    consumer_scope_complete: bool
    blocks: tuple[LegoBlockRecord, ...]
    catalog_relations: tuple[CatalogRelation, ...]
    catalog_diagnostics: tuple[CatalogDiagnostic, ...]
    admitted_receipts: tuple[VerifiedCapabilityReceipt, ...]
    projection_sha256: str

def compute_exact_byte_provenance(checkout_bytes: bytes, committed_blob_bytes: bytes | None = None) -> ExactByteProvenance:
    checkout_digest = sha256_bytes(checkout_bytes)
    if committed_blob_bytes is None:
        return ExactByteProvenance(None, None, checkout_digest, "UNTRACKED")
    status = "CLEAN_EXACT_MATCH" if checkout_bytes == committed_blob_bytes else ("EOL_CRLF_DRIFT" if checkout_bytes.replace(b"\r\n", b"\n") == committed_blob_bytes.replace(b"\r\n", b"\n") else "MODIFIED_CONTENT")
    return ExactByteProvenance(compute_git_blob_oid_sha1(committed_blob_bytes), sha256_bytes(committed_blob_bytes), checkout_digest, status)

def resolve_block_identity(current_posix_path: str, *, default_prefix: str = "block", parent_block_id: str | None = None, stable_external_id: tuple[str, str] | None = None, alias_map: Mapping[str, str] | None = None, git_rename_pairs: Sequence[tuple[str, str]] | None = None) -> BlockIdentity:
    norm = PurePosixPath(current_posix_path).as_posix()
    aliases, origin, seen, changed = [], norm, {norm}, True
    pairs = tuple((PurePosixPath(a).as_posix(), PurePosixPath(b).as_posix()) for a, b in (git_rename_pairs or ()))
    while changed:
        changed = False
        for old_p, new_p in reversed(pairs):
            cand = old_p if origin == new_p else (old_p + origin[len(new_p):] if origin.startswith(new_p + "/") else "")
            if cand and cand not in seen:
                aliases.append(RenameAliasRecord(cand, "git_rename"))
                seen.add(cand)
                origin, changed = cand, True
                break
    amap = dict(alias_map or {})
    mapped = amap.get(norm) or amap.get(origin)
    if mapped:
        aliases.append(RenameAliasRecord(origin, "alias_map"))
        cid = mapped
    elif stable_external_id is not None:
        aliases.append(RenameAliasRecord(stable_external_id[0], stable_external_id[1]))
        cid = stable_external_id[0]
    else:
        cid = f"{default_prefix}::{origin}"
    return BlockIdentity(cid, norm, parent_block_id, tuple(dict.fromkeys(aliases)))

def _coerce_receipt(receipt: VerifiedCapabilityReceipt | Mapping[str, Any]) -> VerifiedCapabilityReceipt:
    if not isinstance(receipt, Mapping):
        return receipt
    if receipt.get("runtime_verification_eligible") is False or str(receipt.get("evidence_origin", "")).startswith("SIMULATED"):
        raise ValueError("simulated_evidence_cannot_verify_runtime")
    keys = ("block_id", "capability_id", "source_git_blob_oid_sha1", "source_git_blob_sha256", "executed_checkout_sha256", "dependency_lock_sha256", "environment_fingerprint_sha256", "inputs_sha256", "verifier_receipt_id", "evidence_origin")
    return VerifiedCapabilityReceipt(**{k: str(receipt.get(k, "")) for k in keys})

def admit_verified_capability_receipt(block: LegoBlockRecord, receipt: VerifiedCapabilityReceipt | Mapping[str, Any], *, current_dependency_lock_sha256: str | None = None) -> LegoBlockRecord:
    rcpt = _coerce_receipt(receipt)
    if rcpt.block_id not in {block.identity.canonical_id, block.identity.current_posix_path}:
        raise ValueError("receipt_block_id_mismatch")
    prov = block.provenance
    checks = (
        (prov is None or prov.byte_status == "UNTRACKED", "untracked_or_container_block"),
        (prov is not None and prov.checkout_bytes_sha256 != rcpt.executed_checkout_sha256, "checkout_bytes_sha256_mismatch"),
        (prov is not None and prov.git_blob_sha256 != rcpt.source_git_blob_sha256, "git_blob_sha256_mismatch"),
        (prov is not None and prov.git_blob_oid_sha1 != rcpt.source_git_blob_oid_sha1, "git_blob_oid_sha1_mismatch"),
        (current_dependency_lock_sha256 is not None and current_dependency_lock_sha256 != rcpt.dependency_lock_sha256, "dependency_lock_sha256_mismatch"),
    )
    mismatch = next((reason for bad, reason in checks if bad), None)
    status, reason = ("STALE_PROVENANCE_MISMATCH", mismatch) if mismatch else ("VERIFIED_CAPABILITY", "exact_provenance_verified")
    by_cap = {cs.capability_id: cs for cs in block.capability_statuses}
    by_cap[rcpt.capability_id] = CapabilityVerificationState(rcpt.capability_id, status, rcpt.verifier_receipt_id, reason)
    declared = tuple(sorted(set(block.declared_capabilities) | {rcpt.capability_id}))
    ordered = tuple(by_cap[cid] for cid in sorted(by_cap))
    return LegoBlockRecord(block.identity, block.block_kind, block.provenance, block.static_tier, any(cs.status == "VERIFIED_CAPABILITY" for cs in ordered), block.ast_summary, declared, ordered, block.depends_on_block_ids, block.triage)

def _load_git_head_blobs(root: Path) -> dict[str, bytes]:
    if not (root / ".git").exists():
        return {}
    try:
        ls_res = subprocess.run(["git", "-C", str(root), "ls-tree", "-r", "-z", "HEAD"], capture_output=True, check=False, timeout=30)
        if ls_res.returncode != 0 or not ls_res.stdout:
            return {}
        oid_by_path = {PurePosixPath(r.split("\t", 1)[1]).as_posix(): r.split("\t", 1)[0].split()[2] for r in ls_res.stdout.decode("utf-8", errors="strict").split("\0") if "\t" in r and len(r.split("\t", 1)[0].split()) == 3 and r.split("\t", 1)[0].split()[1] == "blob"}
        oids = sorted(set(oid_by_path.values()))
        if not oids:
            return {}
        cat = subprocess.run(["git", "-C", str(root), "cat-file", "--batch"], input=("\n".join(oids) + "\n").encode("ascii"), capture_output=True, check=True, timeout=30).stdout
        pos, blobs = 0, {}
        for _ in oids:
            nl = cat.index(b"\n", pos)
            oid, _, size_s = cat[pos:nl].decode("ascii").split()[:3]
            start, size = nl + 1, int(size_s)
            blobs[oid] = cat[start:start + size]
            pos = start + size + 1
        return {rel: blobs[oid] for rel, oid in oid_by_path.items() if oid in blobs}
    except Exception:
        return {}

def _skill_frontmatter_name(raw: bytes) -> str | None:
    text = raw.decode("utf-8", errors="ignore")
    end = text.find("\n---", 3) if text.startswith("---") else -1
    return next((ln.split(":", 1)[1].strip().strip("\"'") or None for ln in (text[3:end].splitlines() if end != -1 else ()) if ln.strip().startswith("name:")), None)

def _analyze_python_ast(raw: bytes, rel: str) -> tuple[AstBlockSummary, ast.Module | None, set[str]]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(raw.decode("utf-8", errors="strict"), filename=rel)
    except UnicodeError:
        return AstBlockSummary(parse_error="non_utf8_source"), None, set()
    except SyntaxError:
        return AstBlockSummary(parse_error="syntax_error"), None, set()
    eff, aliases = module_effects(tree), import_aliases(tree)
    flags = tuple(sorted(n for ok, n in ((eff.stdout_mutated, "stdout_mutated"), (eff.environment_mutated, "environment_mutated"), (eff.module_raise, "module_raise"), (eff.file_write, "file_write")) if ok))
    imports, literals, dynamic = set(), set(), False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add("." * node.level + (node.module or ""))
        elif isinstance(node, ast.Call):
            called = node_name(node.func, aliases)
            dynamic |= called.startswith("importlib.") or called in {"__import__", "getattr"}
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) <= 240:
            literals.add(node.value)
    exported = tuple(sorted(n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not n.name.startswith("_")))
    return AstBlockSummary(tuple(sorted(imports)), exported, flags, dynamic, None), tree, literals

def _resolve_import_targets(importer_posix: str, tree: ast.Module, py_by_posix: Mapping[str, str]) -> set[str]:
    importer_dir, cands = PurePosixPath(importer_posix).parent, []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            cands.extend(PurePosixPath(*a.name.split(".")) for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = importer_dir
            for _ in range(max(0, node.level - 1)):
                base = base.parent
            parts = node.module.split(".") if node.module else []
            root_p = (base / PurePosixPath(*parts)) if node.level else PurePosixPath(*parts)
            cands.extend([root_p, *(root_p / a.name for a in node.names if a.name != "*")])
    return {py_by_posix[probe] for cand in cands for probe in (f"{cand.as_posix().lstrip('./')}.py", f"{cand.as_posix().lstrip('./')}/__init__.py") if probe in py_by_posix}

def _load_test_entries(root: Path) -> tuple[TestRegistryEntry, ...]:
    if not (root / REGISTRY_PATH).is_file():
        return ()
    try:
        return load_canonical_test_registry(root).entries
    except ValueError:
        raw = json.loads((root / REGISTRY_PATH).read_text(encoding="utf-8", errors="strict"))
        rows = raw.get("tests", []) if isinstance(raw, Mapping) else []
        return tuple(TestRegistryEntry(str(r["id"]), str(r["path"]), str(r.get("owner") or owner_for_path(PurePosixPath(str(r["path"])))), str(r.get("suite_class", "unit")), str(r["shard_id"]), tuple(r.get("capabilities", ())), str(r.get("execution_type", r.get("suite_class", "unit"))), bool(r.get("collectable", True)), int(r.get("timeout_s", 60)), tuple(r.get("quarantine_reasons", ())), str(r.get("description", ""))) for r in rows if isinstance(r, Mapping) and {"id", "path", "shard_id"} <= set(r))

def _matches_config_ref(rel: str, dotted: str, stem: str, cfg_rel: str, cfg_txt: str) -> bool:
    return cfg_rel != rel and ((rel in cfg_txt or dotted in cfg_txt or f"{stem}.py" in cfg_txt) or bool(not cfg_rel.endswith("foundup_registry.json") and len(stem) >= 4 and re.search(rf"\b{re.escape(stem)}\b", cfg_txt)))

def project_lego_blocks(repo_root: Path | str, *, committed_git_blobs: Mapping[str, bytes] | None = None, alias_map: Mapping[str, str] | None = None, git_rename_pairs: Sequence[tuple[str, str]] | None = None, capabilities_by_path: Mapping[str, Sequence[str]] | None = None, capability_receipts: Sequence[VerifiedCapabilityReceipt | Mapping[str, Any]] = (), consumer_scope_complete: bool = True, current_dependency_lock_sha256: str | None = None, deletion_authorized: bool = False) -> LegoProjectionReport:
    if deletion_authorized is not False:
        raise ValueError("deletion_authorized_must_be_false")
    root = Path(repo_root).resolve(strict=True)
    git_blobs = {PurePosixPath(k).as_posix(): v for k, v in committed_git_blobs.items()} if committed_git_blobs is not None else _load_git_head_blobs(root)
    all_files = tuple(p for p in sorted(root.rglob("*"), key=lambda x: x.relative_to(root).as_posix()) if p.is_file() and not any(pt in _EXCLUDE_DIRS for pt in p.relative_to(root).parts))
    relations, diagnostics, containers = set(), set(), {}
    reg_entities = [e for e in (json.loads((root / FOUNDUP_REGISTRY_REL_PATH).read_text(encoding="utf-8", errors="strict")).get("entities", []) if (root / FOUNDUP_REGISTRY_REL_PATH).is_file() else ()) if isinstance(e, Mapping) and e.get("foundup_id")]
    foundups_by_mod, external_mod_paths = {}, set()
    for ent in reg_entities:
        fid, mpath = str(ent["foundup_id"]), ent.get("module_path")
        if not mpath:
            diagnostics.add(CatalogDiagnostic("EXTERNAL_FOUNDUP_NO_LOCAL_MODULE", f"foundup::{fid}", (), "no_local_module_path"))
        else:
            norm_mod = PurePosixPath(str(mpath)).as_posix()
            foundups_by_mod.setdefault(norm_mod, []).append(ent)
            if ent.get("entity_type") == "external_foundup":
                external_mod_paths.add(norm_mod)
    mod_dirs: list[Path] = []
    if (root / "modules").is_dir():
        for dom in sorted(p for p in (root / "modules").iterdir() if p.is_dir() and p.name not in _EXCLUDE_DIRS):
            drel = dom.relative_to(root).as_posix()
            containers[drel] = (resolve_block_identity(drel, default_prefix="domain", alias_map=alias_map, git_rename_pairs=git_rename_pairs), "domain")
            mod_dirs.extend(sorted(p for p in dom.iterdir() if p.is_dir() and p.name not in _EXCLUDE_DIRS))
    if (root / "holo_index").is_dir():
        mod_dirs.append(root / "holo_index")
    for mdir in mod_dirs:
        mrel, parts = mdir.relative_to(root).as_posix(), PurePosixPath(mdir.relative_to(root).as_posix()).parts
        pid = containers[f"modules/{parts[1]}"][0].canonical_id if len(parts) >= 3 and parts[0] == "modules" else None
        fents = foundups_by_mod.get(mrel, [])
        ext_id = (f"foundup::{fents[0]['foundup_id']}", "foundup_registry") if len(fents) == 1 else None
        mident = resolve_block_identity(mrel, default_prefix="module", parent_block_id=pid, stable_external_id=ext_id, alias_map=alias_map, git_rename_pairs=git_rename_pairs)
        containers[mrel] = (mident, "module")
        for sub in sorted(p for p in mdir.iterdir() if p.is_dir() and p.name not in _SUBBLOCK_SKIP_DIRS):
            if any((sub / m).exists() for m in ("src", "SKILL.md", "SKILLz.md", "foundup_manifest.json")):
                srel = sub.relative_to(root).as_posix()
                containers[srel] = (resolve_block_identity(srel, default_prefix="subblock", parent_block_id=mident.canonical_id, alias_map=alias_map, git_rename_pairs=git_rename_pairs), "subblock")
    for ent in reg_entities:
        if ent.get("module_path"):
            nmod = PurePosixPath(str(ent["module_path"])).as_posix()
            relations.add(CatalogRelation("FOUNDUP_TO_MODULE", f"foundup::{ent['foundup_id']}", containers[nmod][0].canonical_id if nmod in containers else f"module::{nmod}"))
    manifests_by_fid, cfg_refs, raw_by_rel = {}, [], {}
    for fpath in all_files:
        rel = fpath.relative_to(root).as_posix()
        if rel == REGISTRY_PATH:
            continue
        raw = fpath.read_bytes()
        raw_by_rel[rel] = raw
        if fpath.name == "foundup_manifest.json":
            fid = str(json.loads(raw.decode("utf-8", errors="strict")).get("foundup_id", "")).strip()
            if fid:
                manifests_by_fid.setdefault(fid, []).append(rel)
                relations.add(CatalogRelation("FOUNDUP_TO_MANIFEST", f"foundup::{fid}", rel))
        if fpath.name in {"NAVIGATION.py", "foundup_registry.json", "SKILL.md", "SKILLz.md"} or ".github/workflows/" in rel or ".agents/workflows/" in rel:
            cfg_refs.append((rel, raw.decode("utf-8", errors="ignore")))
    diagnostics.update(CatalogDiagnostic("DUPLICATE_MANIFEST_FOUNDUP_ID", f"foundup::{fid}", tuple(sorted(mpaths)), "multiple_manifests_share_foundup_id") for fid, mpaths in sorted(manifests_by_fid.items()) if len(mpaths) > 1)
    mapped_mods = {r.target_id for r in relations if r.relation_type == "FOUNDUP_TO_MODULE"}
    manifest_dirs = {PurePosixPath(p).parent.as_posix() for paths in manifests_by_fid.values() for p in paths}
    diagnostics.update(CatalogDiagnostic("MODULE_WITHOUT_FOUNDUP", mident.canonical_id, (mrel,), "unmapped_local_module") for mrel, (mident, kind) in sorted(containers.items()) if kind == "module" and mident.canonical_id not in mapped_mods and mrel not in manifest_dirs)
    for entry in _load_test_entries(root):
        if not entry.collectable or entry.quarantine_reasons:
            diagnostics.add(CatalogDiagnostic("QUARANTINED_TEST_ENTRY", entry.id, (entry.path,), ",".join(entry.quarantine_reasons) or entry.suite_class))
        else:
            sref = f"shard::{entry.shard_id}"
            relations.add(CatalogRelation("SHARD_TO_TEST_FILE", sref, entry.path))
            if entry.owner in containers:
                relations.add(CatalogRelation("MODULE_TO_TEST_SHARD", containers[entry.owner][0].canonical_id, sref))
    tested_mods = {r.source_id for r in relations if r.relation_type == "MODULE_TO_TEST_SHARD"}
    diagnostics.update(CatalogDiagnostic("MODULE_WITHOUT_TEST_SHARD", mident.canonical_id, (mrel,), "no_automated_test_shard") for mrel, (mident, kind) in sorted(containers.items()) if kind == "module" and mident.canonical_id not in tested_mods)
    py_trees, py_summaries, dyn_lits, file_idents = {}, {}, [], {}
    for rel, raw in sorted(raw_by_rel.items()):
        fname = PurePosixPath(rel).name
        if fname.endswith(".py"):
            bkind, ext = "python_module", None
            summary, tree, lits = _analyze_python_ast(raw, rel)
            py_summaries[rel] = summary
            if tree is not None:
                py_trees[rel] = tree
            if summary.has_dynamic_dispatch:
                dyn_lits.append((rel, lits))
        elif fname in {"SKILL.md", "SKILLz.md"}:
            sname = _skill_frontmatter_name(raw)
            bkind, ext = "skill_doc", ((f"skill::{sname}", "skill_frontmatter") if sname else None)
        elif fname == "foundup_manifest.json":
            bkind, ext = "manifest", None
        else:
            continue
        pid = next((containers[a.as_posix()][0].canonical_id for a in PurePosixPath(rel).parents if a.as_posix() in containers), None)
        file_idents[rel] = (resolve_block_identity(rel, default_prefix="block", parent_block_id=pid, stable_external_id=ext, alias_map=alias_map, git_rename_pairs=git_rename_pairs), bkind)
    py_id_by_rel = {rel: ident.canonical_id for rel, (ident, kind) in file_idents.items() if kind == "python_module"}
    deps_by_id, callers_by_id = {bid: set() for bid in py_id_by_rel.values()}, {bid: set() for bid in py_id_by_rel.values()}
    for rel, tree in sorted(py_trees.items()):
        src_id = py_id_by_rel[rel]
        for dst_id in _resolve_import_targets(rel, tree, py_id_by_rel):
            if dst_id != src_id:
                deps_by_id[src_id].add(dst_id)
                callers_by_id[dst_id].add(src_id)
                relations.add(CatalogRelation("BLOCK_IMPORTS_BLOCK", src_id, dst_id))
    cap_overrides, built = dict(capabilities_by_path or {}), {}
    for crel, (cident, ckind) in sorted(containers.items()):
        contrary = (("external_foundup_consumer",) if crel in external_mod_paths else ()) + (() if consumer_scope_complete else ("consumer_scope_incomplete",))
        tcls = "UNKNOWN_DYNAMIC_OR_EXTERNAL_CONSUMER" if contrary else "INTENTIONAL_ENTRYPOINT_OR_STUB"
        triage = BlockTriageRecord(cident.canonical_id, tcls, (), contrary or (f"container_kind:{ckind}",), consumer_scope_complete)
        caps = tuple(sorted(set(cap_overrides.get(crel) or cap_overrides.get(cident.canonical_id) or ())))
        built[cident.canonical_id] = LegoBlockRecord(cident, ckind, None, "DOCUMENTED_ONLY", False, None, caps, tuple(CapabilityVerificationState(c, "UNVERIFIED_STATIC_ONLY") for c in caps), (), triage)
    for rel, (ident, bkind) in sorted(file_idents.items()):
        raw, summary = raw_by_rel[rel], py_summaries.get(rel)
        prov = compute_exact_byte_provenance(raw, git_blobs.get(rel))
        tier = "STATICALLY_ANALYZED" if bkind == "python_module" and summary and not summary.parse_error else "DOCUMENTED_ONLY"
        ovr = cap_overrides.get(rel) or cap_overrides.get(ident.canonical_id)
        caps = tuple(sorted(set(ovr))) if ovr is not None else (tuple(sorted(str(c) for c in json.loads(raw.decode("utf-8", errors="strict")).get("capabilities", ()) if c)) if bkind == "manifest" else (tuple(f"symbol::{s}" for s in summary.exported_symbols) if summary and summary.exported_symbols else ("module_surface",)))
        callers, deps = tuple(sorted(callers_by_id.get(ident.canonical_id, ()))), tuple(sorted(deps_by_id.get(ident.canonical_id, ())))
        stem, dotted, fname = PurePosixPath(rel).stem, rel.removesuffix(".py").replace("/", "."), PurePosixPath(rel).name
        contrary_l = ([] if consumer_scope_complete else ["consumer_scope_incomplete"]) + (["external_foundup_consumer"] if any(rel.startswith(ep + "/") for ep in external_mod_paths) else [])
        contrary_l.extend(f"dynamic_dispatch_reference:{dr}" for dr, lits in dyn_lits if dr != rel and any(t in lit for lit in lits for t in (rel, dotted, stem) if len(t) >= 3))
        contrary_l.extend(f"config_or_skill_reference:{cr}" for cr, ct in cfg_refs if _matches_config_ref(rel, dotted, stem, cr, ct))
        if callers:
            tcls = "ACTIVE_STATIC_CALLERS"
        elif contrary_l:
            tcls = "UNKNOWN_DYNAMIC_OR_EXTERNAL_CONSUMER"
        elif fname in _ENTRYPOINT_NAMES or fname.startswith("test_") or bkind != "python_module":
            tcls, _ = "INTENTIONAL_ENTRYPOINT_OR_STUB", contrary_l.append(f"entrypoint_or_declarative:{fname}")
        else:
            tcls = "CANDIDATE_ZERO_STATIC_CALLERS"
        built[ident.canonical_id] = LegoBlockRecord(ident, bkind, prov, tier, False, summary, caps, tuple(CapabilityVerificationState(c, "UNVERIFIED_STATIC_ONLY") for c in caps), deps, BlockTriageRecord(ident.canonical_id, tcls, callers, tuple(sorted(set(contrary_l))), consumer_scope_complete))
    by_path = {b.identity.current_posix_path: cid for cid, b in built.items()}
    admitted: list[VerifiedCapabilityReceipt] = []
    for raw_rcpt in capability_receipts:
        rcpt = _coerce_receipt(raw_rcpt)
        cid = rcpt.block_id if rcpt.block_id in built else by_path.get(rcpt.block_id, "")
        if not cid:
            raise ValueError(f"receipt_target_block_not_found:{rcpt.block_id}")
        built[cid] = admit_verified_capability_receipt(built[cid], rcpt, current_dependency_lock_sha256=current_dependency_lock_sha256)
        admitted.append(rcpt)
    blocks = tuple(built[k] for k in sorted(built))
    rels = tuple(sorted(relations, key=lambda r: (r.relation_type, r.source_id, r.target_id, r.detail)))
    diags = tuple(sorted(diagnostics, key=lambda d: (d.code, d.subject_id, d.related_paths, d.detail)))
    rcpts = tuple(sorted(admitted, key=lambda r: (r.block_id, r.capability_id, r.verifier_receipt_id)))
    prov_rep = LegoProjectionReport(SCHEMA_VERSION, AGI_SCAFFOLDING_HYPOTHESIS, consumer_scope_complete, blocks, rels, diags, rcpts, "")
    return LegoProjectionReport(SCHEMA_VERSION, AGI_SCAFFOLDING_HYPOTHESIS, consumer_scope_complete, blocks, rels, diags, rcpts, sha256_bytes(_canonical_payload_json(prov_rep, include_digest=False).encode("ascii")))

def _canonical_payload_json(projection: LegoProjectionReport, *, include_digest: bool) -> str:
    payload: dict[str, Any] = {"schema_version": projection.schema_version, "agi_scaffolding_hypothesis": projection.agi_scaffolding_hypothesis, "consumer_scope_complete": projection.consumer_scope_complete, "blocks": [b.to_dict() for b in projection.blocks], "catalog_relations": [asdict(r) for r in projection.catalog_relations], "catalog_diagnostics": [asdict(d) for d in projection.catalog_diagnostics], "admitted_receipts": [asdict(r) for r in projection.admitted_receipts], **({"projection_sha256": projection.projection_sha256} if include_digest else {})}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)

def to_canonical_json(projection: LegoProjectionReport) -> str:
    return _canonical_payload_json(projection, include_digest=True)

def to_m2m_compact(projection: LegoProjectionReport) -> str:
    b_cnt = {s: sum(1 for b in projection.blocks if b.provenance and b.provenance.byte_status == s) for s in BYTE_STATUSES}
    t_cnt = {c: sum(1 for b in projection.blocks if b.triage.classification == c) for c in TRIAGE_CLASSIFICATIONS}
    d_cnt = {c: sum(1 for d in projection.catalog_diagnostics if d.code == c) for c in CATALOG_DIAGNOSTIC_CODES}
    lines = [f"schema: {M2M_SCHEMA_VERSION}", f"HYPOTHESIS: {projection.agi_scaffolding_hypothesis}", f"PROJECTION_SHA256: {projection.projection_sha256}", f"SCOPE_COMPLETE: {str(projection.consumer_scope_complete).lower()}", f"COUNTS: blocks={len(projection.blocks)} relations={len(projection.catalog_relations)} diagnostics={len(projection.catalog_diagnostics)} receipts={len(projection.admitted_receipts)}", "BYTE_STATUS: " + " ".join(f"{k}={b_cnt[k]}" for k in BYTE_STATUSES), "TRIAGE: " + " ".join(f"{k}={t_cnt[k]}" for k in TRIAGE_CLASSIFICATIONS), "DIAGNOSTICS: " + " ".join(f"{k}={d_cnt[k]}" for k in CATALOG_DIAGNOSTIC_CODES), "BLOCKS:"]
    lines.extend(f"- {b.identity.canonical_id} | path={b.identity.current_posix_path} | parent={b.identity.parent_block_id or '-'} | byte={b.provenance.byte_status if b.provenance else 'CONTAINER'} | tier={b.static_tier} | triage={b.triage.classification} | caps={','.join(f'{cs.capability_id}:{cs.status}' for cs in b.capability_statuses) or '-'}" for b in projection.blocks)
    return "\n".join(lines) + "\n"
