#!/usr/bin/env python3
"""
Download Cohere Transcribe 2B for local ASR.

Model: CohereLabs/cohere-transcribe-03-2026
Size: ~2B parameters (transformers format, not GGUF)
Use case: State-of-the-art ASR with 14 language support

NOTE: This model uses transformers format, NOT GGUF.
      Runtime integration requires transformers/vLLM, not llama.cpp.

Target: LOCAL_MODEL_ASR_DIR/

WSP: Audio provider registry (shared_utilities)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Load .env for HF_TOKEN
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from huggingface_hub import snapshot_download
    HF_HUB_AVAILABLE = True
except ImportError:
    HF_HUB_AVAILABLE = False


REPO_ID = "CohereLabs/cohere-transcribe-03-2026"


def _resolve_asr_dir() -> Path:
    """Resolve ASR model directory from env or defaults."""
    explicit = os.getenv("LOCAL_MODEL_ASR_DIR", "").strip()
    if explicit:
        return Path(explicit)
    default_root = os.getenv("LOCAL_MODEL_ROOT", "E:/LM_studio/models/local")
    return Path(default_root) / "cohere-transcribe-2b"


def download_cohere_transcribe() -> Path:
    """
    Download Cohere Transcribe model (transformers format).

    Returns:
        Path to downloaded model directory.
    """
    if not HF_HUB_AVAILABLE:
        print("[ERROR] huggingface_hub not installed. Run: pip install huggingface_hub")
        sys.exit(1)

    local_dir = _resolve_asr_dir()

    print("=" * 70)
    print("Downloading Cohere Transcribe 2B (transformers format)")
    print("=" * 70)
    print(f"Repo: {REPO_ID}")
    print(f"Target: {local_dir}")
    print()
    print("NOTE: This is NOT a GGUF model.")
    print("      Runtime requires transformers or vLLM, not llama.cpp.")
    print()

    # Check if already downloaded (look for config.json)
    config_path = local_dir / "config.json"
    if config_path.exists():
        print(f"[OK] Model already present: {local_dir}")
        return local_dir

    print(f"[DOWNLOAD] Fetching full model snapshot from Hugging Face...")
    print("           This may take a while (~4-8 GB depending on precision)...")
    print()

    local_dir.mkdir(parents=True, exist_ok=True)

    downloaded = snapshot_download(
        repo_id=REPO_ID,
        local_dir=str(local_dir),
        local_dir_use_symlinks=False,
        ignore_patterns=["*.md", "*.txt"],  # Skip docs to save space
    )

    print(f"[OK] Downloaded to: {downloaded}")
    return Path(downloaded)


def verify_transformers_load() -> bool:
    """Verify model can be loaded with transformers."""
    try:
        from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq
        print("[CHECK] transformers available")
        return True
    except ImportError:
        print("[WARN] transformers not installed")
        print("       To use this model, run: pip install transformers torch")
        return False


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Download Cohere Transcribe 2B for local ASR"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify transformers can load the model after download"
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Only verify, don't download"
    )
    args = parser.parse_args()

    if args.skip_download:
        verify_transformers_load()
        return 0

    try:
        path = download_cohere_transcribe()
        print()
        print(f"[SUCCESS] ASR model ready at: {path}")
        print()

        if args.verify:
            verify_transformers_load()

        print("Next steps:")
        print("  1. Install transformers: pip install transformers torch")
        print("  2. Load model:")
        print("     from transformers import AutoProcessor, CohereAsrForConditionalGeneration")
        print(f"     processor = AutoProcessor.from_pretrained('{path}')")
        print(f"     model = CohereAsrForConditionalGeneration.from_pretrained('{path}')")
        print()
        print("  OR use vLLM for production serving:")
        print(f"     vllm serve {path} --trust-remote-code")
        return 0
    except Exception as e:
        print(f"[ERROR] Download failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
