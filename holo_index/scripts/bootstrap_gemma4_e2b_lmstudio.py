#!/usr/bin/env python3
"""
Bootstrap Gemma 4 E2B (2.3B) GGUF for Foundups local runtime.

Gemma 4 E2B is Google's on-device multimodal model (text+image+audio).
  - 2.3B effective parameters (5.1B with embeddings)
  - 128K context window, 35 layers
  - Q4_K_M quantization: ~3.46 GB (fits RTX 2060 6GB)

Workflow:
  1) Download model to E:/HoloIndex/models/gemma4-e2b
  2) Mirror model into LM Studio local dir
  3) Try LM Studio API load (may fail if gemma4 arch unsupported)
  4) Optionally verify via llama_cpp Python fallback
  5) Optionally run a smoke chat completion

Requirements:
  - huggingface_hub (pip install huggingface_hub)
  - requests
  - llama_cpp (optional, for fallback verification)

Known compatibility:
  - Requires llama.cpp b8648+ for gemma4 architecture
  - LM Studio 0.4.8 may show "unknown model architecture 'gemma4'"
  - llama_cpp Python 0.2.69 may need update for gemma4 support
  - lmstudio-community/gemma-4-E2B-it-GGUF also available as alternate repo
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from huggingface_hub import hf_hub_download


DEFAULT_REPO_ID = "bartowski/google_gemma-4-E2B-it-GGUF"
DEFAULT_FILENAME = "google_gemma-4-E2B-it-Q4_K_M.gguf"
ALTERNATE_REPO_ID = "lmstudio-community/gemma-4-E2B-it-GGUF"
ALTERNATE_FILENAME = "gemma-4-E2B-it-Q4_K_M.gguf"

MODEL_FOLDER = "gemma4-e2b"


def _resolve_holo_model_root() -> Path:
    explicit = os.getenv("HOLO_MODEL_ROOT", "").strip()
    if explicit:
        return Path(explicit).expanduser()
    holo_ssd = os.getenv("HOLO_SSD_PATH", "E:/HoloIndex").strip() or "E:/HoloIndex"
    return Path(holo_ssd).expanduser() / "models"


def _resolve_lm_local_dir() -> Path:
    explicit = os.getenv("LOCAL_MODEL_GEMMA4_DIR", "").strip()
    if explicit:
        return Path(explicit).expanduser()
    local_root = os.getenv("LOCAL_MODEL_ROOT", "E:/LM_studio/models/local").strip()
    return Path(local_root).expanduser() / MODEL_FOLDER


def _lm_base_url() -> str:
    port = int(os.getenv("LM_STUDIO_PORT", "1234"))
    return f"http://127.0.0.1:{port}"


def _download_model(repo_id: str, filename: str, dst_dir: Path) -> Path:
    dst_dir.mkdir(parents=True, exist_ok=True)
    target = dst_dir / filename
    if target.exists():
        size_gb = target.stat().st_size / (1024 ** 3)
        print(f"[OK] Model already present: {target} ({size_gb:.2f} GB)")
        return target

    print(f"[DOWNLOAD] {repo_id}/{filename}")
    print("           This may take 5-15 minutes depending on bandwidth...")
    downloaded = hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        local_dir=str(dst_dir),
        local_dir_use_symlinks=False,
    )
    downloaded_path = Path(downloaded)
    size_gb = downloaded_path.stat().st_size / (1024 ** 3)
    print(f"[OK] Downloaded: {downloaded_path} ({size_gb:.2f} GB)")
    return downloaded_path


def _mirror_into_lmstudio(src_file: Path, lm_dir: Path) -> Path:
    lm_dir.mkdir(parents=True, exist_ok=True)
    dst_file = lm_dir / src_file.name

    if dst_file.exists():
        if dst_file.stat().st_size == src_file.stat().st_size:
            print(f"[OK] LM Studio model already mirrored: {dst_file}")
            return dst_file
        dst_file.unlink()

    try:
        os.link(src_file, dst_file)
        print(f"[OK] Created hardlink for LM Studio: {dst_file}")
        return dst_file
    except OSError:
        shutil.copy2(src_file, dst_file)
        print(f"[OK] Copied model for LM Studio: {dst_file}")
        return dst_file


def _get_models(base_url: str, timeout_s: float = 5.0) -> List[Dict[str, Any]]:
    resp = requests.get(f"{base_url}/v1/models", timeout=timeout_s)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("data", [])
    return items if isinstance(items, list) else []


def _find_loaded_model(models: List[Dict[str, Any]], needle: str = "gemma-4") -> Optional[str]:
    for item in models:
        model_id = str(item.get("id", "")).strip()
        if needle in model_id.lower() or "gemma4" in model_id.lower():
            return model_id
    return None


def _request_model_load(base_url: str, model_id: str, filename: str) -> bool:
    endpoints = ("/v1/models/load", "/api/v0/models/load", "/api/models/load")
    payloads = (
        {"model": model_id, "file": filename},
        {"model": model_id},
        {"id": model_id, "file": filename},
    )
    for endpoint in endpoints:
        for payload in payloads:
            try:
                resp = requests.post(f"{base_url}{endpoint}", json=payload, timeout=20)
                if resp.status_code in (200, 201, 202):
                    print(f"[OK] Load request accepted via {endpoint}: {payload}")
                    return True
            except requests.RequestException:
                continue
    return False


def _wait_for_loaded_model(base_url: str, timeout_s: float = 120.0) -> Optional[str]:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            models = _get_models(base_url, timeout_s=5.0)
            loaded = _find_loaded_model(models)
            if loaded:
                return loaded
        except requests.RequestException:
            pass
        time.sleep(2.0)
    return None


def _smoke_chat(base_url: str, model_id: str) -> bool:
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": "Reply with OK only."}],
        "temperature": 0.0,
        "max_tokens": 8,
    }
    try:
        resp = requests.post(f"{base_url}/v1/chat/completions", json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        print(f"[SMOKE] Response: {content or '<empty>'}")
        return bool(content)
    except requests.RequestException as exc:
        print(f"[WARN] Smoke test failed: {type(exc).__name__}: {exc}")
        return False


def _verify_llama_cpp(model_path: Path) -> bool:
    """Verify model loads via llama_cpp Python (fallback inference path)."""
    try:
        from llama_cpp import Llama
    except ImportError:
        print("[SKIP] llama_cpp not installed — cannot verify via Python fallback.")
        return False

    print("[VERIFY] Attempting llama_cpp Python load...")
    old_stdout = old_stderr = devnull = None
    try:
        old_stdout, old_stderr = os.dup(1), os.dup(2)
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)

        llm = Llama(
            model_path=str(model_path),
            n_ctx=512,
            n_threads=2,
            n_gpu_layers=0,
            verbose=False,
        )
    except Exception as exc:
        if old_stdout is not None:
            os.dup2(old_stdout, 1)
            os.dup2(old_stderr, 2)
            os.close(devnull)
        print(f"[WARN] llama_cpp load failed: {type(exc).__name__}: {exc}")
        print("       This likely means llama_cpp 0.2.69 does not support gemma4 arch.")
        print("       Upgrade: pip install --upgrade llama-cpp-python")
        return False
    finally:
        if old_stdout is not None:
            try:
                os.dup2(old_stdout, 1)
                os.dup2(old_stderr, 2)
                os.close(devnull)
            except OSError:
                pass

    print("[OK] llama_cpp loaded model successfully!")

    try:
        response = llm(
            "Reply with OK only.",
            max_tokens=8,
            temperature=0.0,
        )
        text = response["choices"][0]["text"].strip()
        print(f"[VERIFY] Inference test: {text or '<empty>'}")
        del llm
        return True
    except Exception as exc:
        print(f"[WARN] Inference test failed: {type(exc).__name__}: {exc}")
        del llm
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap Gemma 4 E2B model for LM Studio / llama_cpp."
    )
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID, help="Hugging Face repo id.")
    parser.add_argument("--filename", default=DEFAULT_FILENAME, help="GGUF filename.")
    parser.add_argument(
        "--use-lmstudio-community",
        action="store_true",
        help="Use lmstudio-community repo instead of bartowski.",
    )
    parser.add_argument(
        "--download-root",
        default=str(_resolve_holo_model_root()),
        help="Root directory for Holo model downloads.",
    )
    parser.add_argument(
        "--folder",
        default=MODEL_FOLDER,
        help="Model folder name under --download-root.",
    )
    parser.add_argument(
        "--lm-dir",
        default=str(_resolve_lm_local_dir()),
        help="LM Studio local model directory for mirror/link.",
    )
    parser.add_argument(
        "--model-id",
        default=os.getenv("GEMMA4_MODEL_ID", DEFAULT_REPO_ID),
        help="LM Studio model id for /models/load.",
    )
    parser.add_argument("--download-only", action="store_true", help="Only download, skip LM Studio steps.")
    parser.add_argument("--skip-mirror", action="store_true", help="Do not mirror model into LM Studio dir.")
    parser.add_argument("--skip-load", action="store_true", help="Do not request model load in LM Studio.")
    parser.add_argument("--smoke", action="store_true", help="Run chat-completion smoke test after load.")
    parser.add_argument("--verify-llama-cpp", action="store_true", help="Verify via llama_cpp Python (fallback path).")
    args = parser.parse_args()

    if args.use_lmstudio_community:
        args.repo_id = ALTERNATE_REPO_ID
        args.filename = ALTERNATE_FILENAME

    download_root = Path(args.download_root).expanduser()
    model_dir = download_root / args.folder
    lm_dir = Path(args.lm_dir).expanduser()
    base_url = _lm_base_url()

    print("=" * 72)
    print("Gemma 4 E2B Bootstrap")
    print("=" * 72)
    print(f"Model        : Gemma 4 E2B (2.3B params, multimodal)")
    print(f"Quantization : Q4_K_M (~3.46 GB)")
    print(f"Download dir : {model_dir}")
    print(f"LM Studio dir: {lm_dir}")
    print(f"LM Studio API: {base_url}")
    print(f"Repo         : {args.repo_id}")
    print(f"File         : {args.filename}")
    print()

    # Step 1: Download
    try:
        src_file = _download_model(args.repo_id, args.filename, model_dir)
    except Exception as exc:
        print(f"[ERROR] Download failed: {type(exc).__name__}: {exc}")
        if not args.use_lmstudio_community:
            print("[HINT] Try --use-lmstudio-community for alternate repo.")
        return 1

    # Step 2: Mirror
    if not args.skip_mirror:
        _mirror_into_lmstudio(src_file, lm_dir)

    if args.download_only:
        print("[DONE] Download-only mode complete.")
        return 0

    # Step 3: LM Studio load
    lm_loaded = False
    try:
        models = _get_models(base_url)
        loaded = _find_loaded_model(models)
        if loaded:
            print(f"[OK] LM Studio already has Gemma 4 E2B loaded: {loaded}")
            lm_loaded = True
        elif args.skip_load:
            print("[SKIP] --skip-load set; not requesting LM Studio load.")
        else:
            print("[LOAD] Requesting LM Studio model load...")
            accepted = _request_model_load(base_url, args.model_id, args.filename)
            if not accepted:
                print("[WARN] LM Studio did not accept load request.")
                print("       Possible cause: gemma4 architecture not supported in LM Studio 0.4.8.")
                print("       Workaround: Update LM Studio or use --verify-llama-cpp for Python fallback.")
            else:
                loaded = _wait_for_loaded_model(base_url, timeout_s=120.0)
                if loaded:
                    print(f"[OK] LM Studio loaded model: {loaded}")
                    lm_loaded = True
                else:
                    print("[WARN] LM Studio did not report model as loaded within timeout.")
                    print("       Check LM Studio UI for architecture compatibility errors.")
    except requests.RequestException as exc:
        print(f"[WARN] LM Studio API unavailable: {type(exc).__name__}: {exc}")
        print("       Start LM Studio and enable the local server first.")

    # Step 4: Smoke test (if loaded)
    if args.smoke and lm_loaded and loaded:
        _smoke_chat(base_url, loaded)

    # Step 5: llama_cpp fallback verification
    if args.verify_llama_cpp:
        _verify_llama_cpp(src_file)

    # Summary
    print()
    print("=" * 72)
    print("Summary")
    print("=" * 72)
    print(f"Model file    : {src_file}")
    print(f"LM Studio     : {'LOADED' if lm_loaded else 'NOT LOADED (may need update for gemma4 arch)'}")
    print()
    if not lm_loaded:
        print("Next steps if LM Studio fails to load:")
        print("  1. Update LM Studio to latest version (needs llama.cpp b8648+)")
        print("  2. Or use llama_cpp Python: pip install --upgrade llama-cpp-python")
        print("  3. Or load via lms CLI: lms load gemma4-e2b")
        print()
    print("[DONE] Gemma 4 E2B bootstrap complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
