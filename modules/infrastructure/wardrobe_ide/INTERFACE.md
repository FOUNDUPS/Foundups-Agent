# Wardrobe IDE — Public API (INTERFACE)

**WSP 11** · **Module**: `modules/infrastructure/wardrobe_ide`  
**Status**: Foundation PoC (`README.md`); APIs match `src/` as implemented.

---

## Purpose

Record short browser interactions as reusable **skills** (JSON + index), replay via **Playwright** or **Selenium** backends. See `README.md` for CLI and architecture.

---

## Exported symbols

Import from the package root:

```python
from modules.infrastructure.wardrobe_ide import (
    WardrobeSkill,
    record_new_skill,
    replay_skill_by_name,
    show_skills_library,
    save_skill,
    load_skill,
    list_skills,
    import_skill_file,
)
```

---

## Types

### `WardrobeSkill` (`src/skill.py`)

Dataclass representing one recorded skill.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Skill identifier (e.g. `yt_like_and_reply`) |
| `backend` | `Literal["playwright", "selenium"]` | Backend used for record/replay |
| `steps` | `list[dict[str, Any]]` | Serialized steps (clicks, types, etc.) |
| `created_at` | `datetime` | Creation time |
| `meta` | `dict[str, Any]` | e.g. `target_url`, `tags`, `notes`, `step_count` |

| Method | Returns | Description |
|--------|---------|-------------|
| `to_dict()` | `dict[str, Any]` | JSON-serializable dict |
| `from_dict(data)` | `WardrobeSkill` | classmethod; expects `created_at` ISO string |

---

## Recorder API (`src/recorder.py`)

### `record_new_skill`

```text
record_new_skill(
    name: str,
    target_url: str,
    backend: str = DEFAULT_BACKEND,
    duration_seconds: int = DEFAULT_RECORD_DURATION,
    tags: Optional[list[str]] = None,
    notes: Optional[str] = None,
) -> WardrobeSkill
```

| Parameter | Description |
|-----------|-------------|
| `name` | Skill name |
| `target_url` | Page opened for recording |
| `backend` | `"playwright"` or `"selenium"` (see `src/config.py` defaults) |
| `duration_seconds` | Recording window |
| `tags` / `notes` | Stored in `skill.meta` |

**Returns**: Built `WardrobeSkill` after `save_skill`.

**Errors**: Propagates from backend `get_backend` / `record_session` (browser/driver failures).

---

### `replay_skill_by_name`

```text
replay_skill_by_name(name: str, backend: Optional[str] = None) -> None
```

Loads skill by `name`; uses `backend` override if given, else skill’s stored backend. Prints and **returns early** if `load_skill` returns `None` (not found, ambiguous name, or missing file).

**Errors**: Backend replay failures propagate from `replay_skill`.

---

### `show_skills_library`

```text
show_skills_library(backend_filter: Optional[str] = None) -> None
```

Prints human-readable listing; uses `list_skills(filter_backend=backend_filter)`. No return value.

---

## Skills store API (`src/skills_store.py`)

### `save_skill`

```text
save_skill(skill: WardrobeSkill) -> Path
```

Writes `{slug}.{backend}.json` under `SKILLS_DIR` and updates `skills_index.json`.

**Returns**: Path to saved JSON file.

---

### `load_skill`

```text
load_skill(name: str, backend: Optional[str] = None) -> Optional[WardrobeSkill]
```

**Returns**: `WardrobeSkill` or **`None`** if not found, ambiguous multi-backend match without `backend`, or missing JSON file (also prints diagnostics).

---

### `list_skills`

```text
list_skills(filter_backend: Optional[str] = None) -> list[WardrobeSkill]
```

Loads each index entry via `load_skill`; skips failures implicitly.

---

### `import_skill_file`

```text
import_skill_file(
    file_path: str | Path,
    backend_override: Optional[str] = None,
    name_override: Optional[str] = None,
) -> WardrobeSkill
```

Imports external JSON (e.g. Chrome extension export), normalizes `chrome_extension` → `selenium` when appropriate, calls `save_skill`, returns skill.

**Raises**: `FileNotFoundError` if `file_path` does not exist.

---

## Environment variables (`src/config.py`)

| Variable | Default | Effect |
|----------|---------|--------|
| `WARDROBE_DEFAULT_BACKEND` | `playwright` | Default recorder backend name |
| `WARDROBE_SKILLS_DIR` | `<module>/skills` | Skill JSON + index location |
| `WARDROBE_RECORD_DURATION` | `15` | Default recording seconds |
| `WARDROBE_HEADLESS` | `false` | Headless browser when truthy |
| `WARDROBE_SLOW_MO` | `0` | Slow-motion ms for operations |

---

## Integration

- **Backends**: `backends/` — `get_backend(name)` used by recorder (not re-exported at package root).
- **CLI**: `python -m modules.infrastructure.wardrobe_ide` — see `README.md`.
- **Dependencies**: `requirements.txt` (Playwright, Selenium, etc.).

---

## Non-goals (current layer)

- No remote task queue or WRE wiring in this INTERFACE scope.
- `delete_skill` in store is **NotImplementedError** if called.

---

*Generated for WSP 11 traceability; ground truth is source under `src/`.*
