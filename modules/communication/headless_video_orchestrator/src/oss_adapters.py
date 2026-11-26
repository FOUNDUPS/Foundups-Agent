"""
Open-source adapter wrappers for external video automation tools.

These adapters are optional and only run if the repos are present locally.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


class ExternalToolError(Exception):
    """Raised when an external tool invocation fails."""


def _resolve_repo_path(env_key: str, default_path: str) -> Path:
    raw = os.getenv(env_key, "").strip() or default_path
    return Path(raw)


def _find_latest_short(repo_path: Path) -> Optional[Path]:
    candidates = sorted(repo_path.glob("*_short.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def run_ai_shorts_generator(
    *,
    input_ref: str,
    output_dir: str = "memory/video_lab/clips",
    auto_approve: bool = True,
    repo_path: Optional[str] = None,
) -> Path:
    """
    Run SamurAIGPT/AI-Youtube-Shorts-Generator against a URL or local file.

    Returns the copied output path in output_dir.
    """
    if not input_ref:
        raise ExternalToolError("input_ref is required (YouTube URL or local file)")

    repo = Path(repo_path) if repo_path else _resolve_repo_path(
        "AI_SHORTS_REPO_PATH",
        "external_research/AI-Youtube-Shorts-Generator",
    )
    main_py = repo / "main.py"
    if not main_py.exists():
        raise ExternalToolError(f"AI shorts generator not found at {main_py}")

    cmd = [sys.executable, "main.py"]
    if auto_approve:
        cmd.append("--auto-approve")
    cmd.append(input_ref)

    try:
        subprocess.run(
            cmd,
            cwd=str(repo),
            capture_output=True,
            check=True,
            timeout=600,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        stderr = e.stderr.decode(errors="ignore") if getattr(e, "stderr", None) else str(e)
        raise ExternalToolError(f"AI shorts generator failed: {stderr}") from e

    latest = _find_latest_short(repo)
    if not latest:
        raise ExternalToolError("No *_short.mp4 output found in repo root")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / latest.name
    shutil.copy2(latest, dest)
    return dest
