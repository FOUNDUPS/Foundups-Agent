"""Bounded Mode 1 inventory and structural hints; no source imports or writes."""
from dataclasses import dataclass
from pathlib import Path
import stat

from modules.infrastructure.wre_core.src.wre_git_bounded_io import (
    git_read_environment, run_bounded_stdout,
)

MAX_PATHS = 100000
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
ROOT_MANIFESTS = frozenset({'requirements.txt', 'package.json', 'package-lock.json'})
RESERVED = frozenset({'src', 'tests', 'docs', 'memory', 'skills', 'skillz'})


@dataclass(frozen=True)
class TrackedInventory:
    files: frozenset[str]
    incomplete: int
    excluded_environment: int


def environment_path(relative):
    return any(p.casefold() == '.env' or p.casefold().startswith('.env.')
               or p.casefold().endswith('.env') for p in relative.split('/'))


def valid_relative(relative):
    return (type(relative) is str and 0 < len(relative) <= 1024
            and not any(ord(c) < 32 or ord(c) == 127 or c in '\\:' for c in relative)
            and all(p not in {'', '.', '..'} and p == p.strip() and not p.endswith('.')
                    for p in relative.split('/')))


def regular_metadata(path, *, directory=False):
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, 'st_file_attributes', 0) & 0x400:
        raise ValueError('redirected_path')
    if not (stat.S_ISDIR if directory else stat.S_ISREG)(metadata.st_mode):
        raise ValueError('unsupported_file_type')
    return metadata


def source_metadata(root, relative):
    if not valid_relative(relative) or environment_path(relative):
        raise ValueError('unsupported_source_path')
    regular_metadata(root, directory=True)
    path = root
    parts = relative.split('/')
    for index, part in enumerate(parts):
        path = path / part
        metadata = regular_metadata(path, directory=index < len(parts) - 1)
    return metadata


def _git(root, *args, max_bytes=4 * 1024 * 1024):
    return run_bounded_stdout(
        ('git', '--no-optional-locks', '-C', str(root), *args), cwd=root,
        max_bytes=max_bytes, timeout_s=30, environment=git_read_environment(),
    ).decode('utf-8', errors='strict')


def read_tracked_inventory(root):
    """Require the exact Git root; never fall back to local traversal."""
    root = Path(root).absolute()
    regular_metadata(root, directory=True)
    top = Path(_git(root, 'rev-parse', '--show-toplevel', max_bytes=32768).strip())
    if top.resolve() != root.resolve():
        raise ValueError('repository_root_mismatch')
    raw = _git(root, 'ls-files', '--stage', '-z')
    if raw and not raw.endswith('\0'):
        raise ValueError('truncated_inventory')
    records = raw.split('\0')
    if len(records) > MAX_PATHS + 1:
        raise ValueError('inventory_limit')
    seen, files = set(), set()
    incomplete = environments = 0
    for record in filter(None, records):
        header, relative = record.split('\t', 1)
        mode, _oid, stage = header.split()
        if stage != '0' or not valid_relative(relative) or relative in seen:
            raise ValueError('invalid_inventory')
        seen.add(relative)
        if environment_path(relative):
            environments += 1
            continue
        if not relative.startswith('modules/') and relative not in ROOT_MANIFESTS:
            continue
        try:
            if mode not in {'100644', '100755'}:
                raise ValueError('unsupported_tracked_mode')
            metadata = source_metadata(root, relative)
            if relative in ROOT_MANIFESTS and metadata.st_size > MAX_MANIFEST_BYTES:
                raise ValueError('manifest_byte_limit')
            files.add(relative)
        except (OSError, ValueError):
            incomplete += 1
    return TrackedInventory(frozenset(files), incomplete, environments)


def module_roots(files, exceptions):
    roots = set()
    for relative in files:
        parts = relative.split('/')
        if parts[0] != 'modules' or len(parts) < 3:
            continue
        if parts[1] in exceptions:
            roots.add('/'.join(parts[:2]))
        elif len(parts) >= 4 and parts[2] not in RESERVED and not parts[2].startswith('.'):
            roots.add('/'.join(parts[:3]))
    return sorted(roots)


def structural_findings(inventory, domains, exceptions):
    """Tracked presence is a structural hint, never behavioral test coverage."""
    files, findings = inventory.files, []
    if inventory.incomplete:
        findings.append(f'ERROR: Tracked inspection incomplete ({inventory.incomplete} paths)')
    if inventory.excluded_environment:
        findings.append(f'WARNING: Environment paths excluded unread ({inventory.excluded_environment})')
    present = {p.split('/')[1] for p in files if p.startswith('modules/') and p.count('/') >= 2}
    if not present:
        findings.append('ERROR: No tracked module files available for structural inspection')
    for domain in sorted(present - domains - exceptions):
        findings.append(f"WARNING: Unknown Enterprise Domain '{domain}'")
    misplaced = {p.split('/')[1] + '/' + p.split('/')[2] for p in files
                 if p.startswith('modules/') and p.count('/') >= 3
                 and p.split('/')[1] not in exceptions and p.split('/')[2] in {'src', 'tests'}}
    findings.extend(f"WARNING: Domain-level source/tests need an owned block: '{p}'" for p in sorted(misplaced))
    roots = module_roots(files, exceptions)
    for module in roots:
        name = module.removeprefix('modules/')
        owned = {p.removeprefix(module + '/') for p in files if p.startswith(module + '/')}
        for directory in ('src', 'tests'):
            if not any(p.startswith(directory + '/') for p in owned):
                findings.append(f"ERROR: Module '{name}' has no tracked {directory}/ files")
        if 'tests/README.md' not in owned:
            findings.append(f"WARNING: Module '{name}' is missing tracked tests/README.md")
        if not any(p.startswith('src/') and p.count('/') == 1 and p.endswith('.py') for p in owned):
            findings.append(f"WARNING: Module '{name}' has no tracked Python files directly in src/")
        if not owned & {'module.json', 'requirements.txt'}:
            findings.append(f"WARNING: Module '{name}' is missing a tracked dependency manifest")
    return findings, len(roots)
