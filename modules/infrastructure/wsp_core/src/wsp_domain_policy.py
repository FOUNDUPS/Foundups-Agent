"""Pure WSP 3 policy over already-admitted repository-relative file paths.

Callers own Git generation, metadata validation and content-read boundaries.
Root contracts or direct src/tests descendants identify a module; other tracked
containers remain explicit ownership debt. No filesystem or application imports.
"""

CORE_DOMAINS = frozenset({
    'ai_intelligence', 'communication', 'platform_integration', 'infrastructure',
    'foundups', 'gamification', 'blockchain', 'development', 'aggregation', 'monitoring',
})
ARCHITECTURAL_EXCEPTIONS = frozenset({'wre_core'})  # WSP 3 section 5.1
RESERVED_BLOCK_NAMES = frozenset({'src', 'tests', 'docs', 'memory', 'skills', 'skillz'})
ROOT_CONTRACTS = frozenset({'README.md', 'INTERFACE.md'})


def _classify(paths, exceptions):
    roots, containers = set(), set()
    for relative in paths:
        parts = relative.split('/')
        if len(parts) < 3 or parts[0] != 'modules':
            continue
        if parts[1] in exceptions:
            roots.add('/'.join(parts[:2]))
        elif (len(parts) >= 4 and parts[2] not in RESERVED_BLOCK_NAMES
              and not parts[2].startswith('.')):
            root = '/'.join(parts[:3])
            containers.add(root)
            if ((len(parts) >= 5 and parts[3] in {'src', 'tests'})
                    or (len(parts) == 4 and parts[3] in ROOT_CONTRACTS)):
                roots.add(root)
    return roots, containers


def evidenced_module_roots(paths, exceptions=ARCHITECTURAL_EXCEPTIONS):
    """Return sorted immutable module roots without deciding domain validity."""
    roots, _ = _classify(paths, exceptions)
    return tuple(sorted(roots))


def unqualified_module_containers(paths, exceptions=ARCHITECTURAL_EXCEPTIONS):
    """Keep non-module containers visible without inventing module contracts."""
    roots, containers = _classify(paths, exceptions)
    return tuple(sorted(containers - roots))
