"""Central local model selection and path resolution.

This module provides one place to map task roles to local models, so model
upgrades do not require touching many modules.

Role-Based Architecture:
    Roles are stable capability contracts. Models are fluid candidates.

    Roles resolved by this module:
        triage   - fast validation/classification (<10ms target)
        general  - synthesis, reasoning, non-code tasks
        code     - resident coding, refactoring, test generation
        asr      - speech-to-text transcription (Cohere Transcribe 2B default)
        tts      - text-to-speech synthesis (Qwen3-TTS default)

    Roles resolved elsewhere (NOT in this module):
        vision   - ui_tars_bridge.py (UI_TARS_PATH env var)

    Policy-only (not auto-resolved anywhere):
        architect_escalation - bounded high-compute path (explicit policy)

    Future roles (not yet implemented):
        social_copy          - marketing/engagement text
        research             - web/paper research

    Promotion Path:
        1. Train a local model on codebase patterns
        2. Set LOCAL_MODEL_CODE_PATH or LOCAL_MODEL_CODE_DIR to trained model
        3. Role resolution automatically picks it up
        4. No repo-wide rewrites needed

    The system selects by role, not by model name. Current defaults are
    configurable via environment variables and can be swapped without
    touching code that requests roles.
"""

from __future__ import annotations

import fnmatch
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


DEFAULT_LOCAL_MODEL_ROOT = Path("E:/LM_studio/models/local")
HOLOINDEX_MODEL_ROOT = Path("E:/HoloIndex/models")

# Task roles -> default model folders under LOCAL_MODEL_ROOT
MODEL_DIR_DEFAULTS: Dict[str, str] = {
    "triage": "gemma-270m",
    "general": "qwen3.5-4b",
    "code": "qwen-coder-7b",
    "asr": "cohere-transcribe-2b",
    "tts": "qwen3-tts",
}

# Role-specific env vars:
# - *_PATH supports direct file path or model directory path
# - *_DIR supports directory path only
ROLE_ENV_VARS: Dict[str, Tuple[str, str]] = {
    "triage": ("LOCAL_MODEL_TRIAGE_PATH", "LOCAL_MODEL_TRIAGE_DIR"),
    "general": ("LOCAL_MODEL_GENERAL_PATH", "LOCAL_MODEL_GENERAL_DIR"),
    "code": ("LOCAL_MODEL_CODE_PATH", "LOCAL_MODEL_CODE_DIR"),
    "asr": ("LOCAL_MODEL_ASR_PATH", "LOCAL_MODEL_ASR_DIR"),
    "tts": ("LOCAL_MODEL_TTS_PATH", "LOCAL_MODEL_TTS_DIR"),
}

# Backward-compatible env aliases currently used around the repo.
ROLE_ENV_ALIASES: Dict[str, Tuple[str, ...]] = {
    "triage": ("HOLO_GEMMA_MODEL",),
    "general": (),
    "code": ("HOLO_QWEN_MODEL",),
    "asr": (),
    "tts": (),
}

# Legacy file fallbacks (kept for compatibility while migrating).
LEGACY_FILE_FALLBACKS: Dict[str, List[Path]] = {
    "triage": [
        Path("E:/HoloIndex/models/gemma-3-270m-it-Q4_K_M.gguf"),
        Path("E:/LLM_Models/gemma-3-270m-it.gguf"),
    ],
    "general": [],
    "code": [
        Path("E:/HoloIndex/models/qwen-coder-1.5b.gguf"),
        Path("E:/LLM_Models/qwen-coder-1.5b.gguf"),
    ],
    "asr": [
        HOLOINDEX_MODEL_ROOT / "cohere-transcribe-2b",
    ],
    "tts": [
        HOLOINDEX_MODEL_ROOT / "qwen3-tts",
    ],
}

ROLE_GGUF_PATTERNS: Dict[str, List[str]] = {
    "triage": ["*gemma*270m*.gguf", "*gemma*.gguf", "*.gguf"],
    "general": ["*qwen*3.5*4b*.gguf", "*qwen*35*4b*.gguf", "*qwen*3*4b*.gguf", "*qwen*4b*.gguf", "*.gguf"],
    "code": ["*qwen*coder*7b*.gguf", "*coder*7b*.gguf", "*.gguf"],
    "asr": ["*cohere*transcribe*.gguf", "*transcribe*.gguf", "*.gguf"],
    "tts": ["*qwen*tts*.gguf", "*tts*.gguf", "*.gguf"],
}

# Default placeholder names used only if no file can be discovered.
ROLE_DEFAULT_FILENAMES: Dict[str, str] = {
    "triage": "gemma-270m.gguf",
    "general": "qwen3.5-4b.gguf",
    "code": "qwen-coder-7b.gguf",
    "asr": "cohere-transcribe-2b.gguf",
    "tts": "qwen3-tts.gguf",
}


@dataclass(frozen=True)
class ModelSelection:
    """Resolved local model selection."""

    role: str
    path: Path
    exists: bool
    source: str


def _get_env_path(name: str) -> Optional[Path]:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return Path(value)


def _env_truthy(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "y", "on"}


def legacy_fallback_enabled() -> bool:
    """Return True when legacy fallback model paths are enabled."""
    return _env_truthy("LOCAL_MODEL_ENABLE_LEGACY_FALLBACK", "0")


def get_local_model_root() -> Path:
    """Return configured local model root directory."""
    return _get_env_path("LOCAL_MODEL_ROOT") or DEFAULT_LOCAL_MODEL_ROOT


def get_role_model_dir(role: str) -> Path:
    """Return the role-specific model directory."""
    if role not in MODEL_DIR_DEFAULTS:
        raise ValueError(f"Unknown model role: {role}")
    _, dir_var = ROLE_ENV_VARS[role]
    explicit_dir = _get_env_path(dir_var)
    if explicit_dir:
        return explicit_dir
    return get_local_model_root() / MODEL_DIR_DEFAULTS[role]


def _ranked_gguf_files(model_dir: Path, role: str) -> List[Path]:
    if not model_dir.exists() or not model_dir.is_dir():
        return []

    try:
        files = [p for p in model_dir.rglob("*.gguf") if p.is_file()]
    except OSError:
        return []

    if not files:
        return []

    files.sort(key=lambda p: p.stat().st_size, reverse=True)
    patterns = ROLE_GGUF_PATTERNS.get(role, ["*.gguf"])

    for pattern in patterns:
        matched = [p for p in files if fnmatch.fnmatch(p.name.lower(), pattern.lower())]
        if matched:
            return matched

    return files


def _resolve_candidate(candidate: Path, role: str) -> Optional[Path]:
    if candidate.is_file():
        return candidate
    if candidate.is_dir():
        ranked = _ranked_gguf_files(candidate, role)
        if ranked:
            return ranked[0]
    return None


def _build_candidates(role: str) -> List[Tuple[Path, str]]:
    path_var, dir_var = ROLE_ENV_VARS[role]
    candidates: List[Tuple[Path, str]] = []

    explicit_path = _get_env_path(path_var)
    if explicit_path:
        candidates.append((explicit_path, path_var))

    explicit_dir = _get_env_path(dir_var)
    if explicit_dir:
        candidates.append((explicit_dir, dir_var))

    for alias in ROLE_ENV_ALIASES.get(role, ()):
        alias_path = _get_env_path(alias)
        if alias_path:
            candidates.append((alias_path, alias))

    candidates.append((get_role_model_dir(role), "LOCAL_MODEL_ROOT/default"))

    if legacy_fallback_enabled():
        for legacy_path in LEGACY_FILE_FALLBACKS.get(role, []):
            candidates.append((legacy_path, "legacy_fallback"))

    return candidates


def resolve_model_selection(role: str) -> ModelSelection:
    """Resolve best-available model file for a role."""
    if role not in MODEL_DIR_DEFAULTS:
        raise ValueError(f"Unknown model role: {role}")

    unresolved_fallback: Optional[ModelSelection] = None

    for candidate, source in _build_candidates(role):
        resolved = _resolve_candidate(candidate, role)
        if resolved and resolved.exists():
            return ModelSelection(role=role, path=resolved, exists=True, source=source)

        if unresolved_fallback is None:
            if candidate.suffix.lower() == ".gguf":
                unresolved_fallback = ModelSelection(
                    role=role,
                    path=candidate,
                    exists=False,
                    source=source,
                )
            elif candidate.is_dir() or str(candidate).lower().endswith(("/", "\\")):
                unresolved_fallback = ModelSelection(
                    role=role,
                    path=candidate / ROLE_DEFAULT_FILENAMES[role],
                    exists=False,
                    source=source,
                )

    if unresolved_fallback is not None:
        return unresolved_fallback

    model_dir = get_role_model_dir(role)
    return ModelSelection(
        role=role,
        path=model_dir / ROLE_DEFAULT_FILENAMES[role],
        exists=False,
        source="default_placeholder",
    )


def resolve_model_path(role: str) -> Path:
    """Convenience helper returning just the resolved model path."""
    return resolve_model_selection(role).path


def resolve_triage_model_path() -> Path:
    """Return triage model path (Gemma 270M default)."""
    return resolve_model_path("triage")


def resolve_general_model_path() -> Path:
    """Return general model path (Qwen3.5 4B default)."""
    return resolve_model_path("general")


def resolve_code_model_path() -> Path:
    """Return coding model path (Qwen Coder 7B default)."""
    return resolve_model_path("code")


def resolve_asr_model_path() -> Path:
    """Return ASR model path (Cohere Transcribe 2B default)."""
    return resolve_model_path("asr")


def resolve_tts_model_path() -> Path:
    """Return TTS model path (Qwen3-TTS default)."""
    return resolve_model_path("tts")


def get_model_selections() -> Dict[str, ModelSelection]:
    """Return resolved model selections for all roles."""
    return {role: resolve_model_selection(role) for role in MODEL_DIR_DEFAULTS}


def _cli() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Show centralized local model routing (triage/general/code)."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output routing as JSON.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any role model path is missing.",
    )
    args = parser.parse_args()

    selections = get_model_selections()
    if args.json:
        payload = {
            role: {
                "path": str(selection.path),
                "exists": selection.exists,
                "source": selection.source,
            }
            for role, selection in selections.items()
        }
        print(json.dumps(payload, indent=2))
    else:
        for role, selection in selections.items():
            status = "OK" if selection.exists else "MISSING"
            print(f"{role:7} {status:8} {selection.path}  ({selection.source})")

    if args.strict and any(not selection.exists for selection in selections.values()):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
