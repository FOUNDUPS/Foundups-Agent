# INTERFACE - Public FoundUp Catalog Projector

WSP 11 public interface. The projection path depends ONLY on the canonical
registry; it never reads `public/member/mall-video-catalog.json`.

## Public API (`modules.foundups.public_catalog_projector`)

### Constants
- `PUBLIC_ALLOWLIST: tuple[str, ...]` - the only fields permitted in a
  projection entry.
- `KNOWN_MEMBER_SCOPED_FIELDS: tuple[str, ...]` - the named forbidden set
  (member-scoped keys observed in the runtime catalog).

### `load_registry(repo_root: Path, registry_path: Optional[Path] = None) -> dict`
Loads + structurally validates the canonical registry. Raises `SourceError`
(fail-closed) on missing/malformed input. Does NOT load the runtime catalog.

### `generate_projection(registry: dict) -> dict`
Derives the scope-free public catalog: filters to portfolio-eligible entries,
projects ONLY allowlisted fields, sets `is_dual_identity` for holoindex, sorts
deterministically. Never invents fields/entries. Pure.
Before filtering, validates every explicit `public_discovery_alias` against all
canonical IDs and aliases. Malformed slugs, duplicate target IDs and collisions
raise `SourceError`. Emits the optional alias only when portfolio-eligible and
explicitly discoverable/listed/promoted. No alias preserves prior output.

### `validate_projection(projection: dict, registry: dict) -> ValidationReport`
Runs fail-closed safety rules (A allowlist-only, B derived-from-registry, B
filter-completeness). Pure - never mutates inputs, never writes.
`ValidationReport.is_safe` is `True` only when zero errors.
Also checks exact alias presence/value (`B_alias` violations), including missing
required aliases or injected null/hidden aliases. Invalid registry reservations
raise `SourceError`, even when the colliding record would be filtered out.

### `write_projection(projection: dict, repo_root: Path, projection_path=None) -> Path`
The ONLY side-effecting function. Writes the derived artifact as stable JSON.

### Errors / data classes
- `SourceError` - fail-closed input error (CLI exit 2).
- `Violation` - `{rule_id, severity, entity, field, expected, actual, message}`.
- `ValidationReport` - `violations`, `stats`, `is_safe`, `error_count`, `to_dict()`.

## CLI (`python -m modules.foundups.public_catalog_projector`)
`--generate` | `--validate` | `--check` (default) | `--json` | `--repo-root PATH`.
Exit: `0` safe, `1` violation, `2` source error. `--generate` refuses to write
an unsafe projection.

## Derived artifact
`public/f/public_catalog.json` - DERIVED, never hand-authored. Shape-compatible
with the public page's `portfolio.entities[]` consumption (same field names:
`foundup_id`, `display_name`, `public_summary`, `poc_url`, `portfolio_priority`,
`portfolio_status`, etc.).

## Public shell consumption

The optional alias is shell-owned discovery input, not a tenant identity.
`window.entryRedDog.getContext().foundupId` is null while catalog resolution is
pending or rejected, and becomes the validated canonical ID before landing
rendering. This intentionally withholds speculative IDs for canonical requests
too; successful legacy canonical context stays unchanged. Alias requests must
replace the URL successfully before exposing identity or rendering.
