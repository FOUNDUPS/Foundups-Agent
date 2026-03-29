#!/usr/bin/env python3
"""
Download Qwen3-TTS 1.7B GGUF for local text-to-speech.

Model: mradermacher/Qwen3-1.7B-Multilingual-TTS-GGUF
Size: ~1.2GB (Q4_K_M) or ~2GB (Q8_0)
Use case: Local TTS with voice cloning capability

Target: LOCAL_MODEL_TTS_DIR/Qwen3-1.7B-Multilingual-TTS-Q4_K_M.gguf

WSP: Audio provider registry (shared_utilities)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from huggingface_hub import hf_hub_download


REPO_ID = "mradermacher/Qwen3-1.7B-Multilingual-TTS-GGUF"

# Available quantizations (size in MB):
# Q2_K: 889, Q3_K_S: 978, Q3_K_M: 1050, Q3_K_L: 1110
# IQ4_XS: 1130, Q4_K_S: 1170, Q4_K_M: 1220 (recommended)
# Q5_K_S: 1340, Q5_K_M: 1370, Q6_K: 1530
# Q8_0: 1980 (best quality), F16: 3720

DEFAULT_QUANT = "Q4_K_M"
FILENAME_TEMPLATE = "Qwen3-1.7B-Multilingual-TTS.{quant}.gguf"


def _resolve_tts_dir() -> Path:
    """Resolve TTS model directory from env or defaults."""
    explicit = os.getenv("LOCAL_MODEL_TTS_DIR", "").strip()
    if explicit:
        return Path(explicit)
    default_root = os.getenv("LOCAL_MODEL_ROOT", "E:/LM_studio/models/local")
    return Path(default_root) / "qwen3-tts"


def download_qwen3_tts(quant: str = DEFAULT_QUANT) -> Path:
    """
    Download Qwen3-TTS GGUF model.

    Args:
        quant: Quantization level (Q4_K_M, Q8_0, etc.)

    Returns:
        Path to downloaded model file.
    """
    filename = FILENAME_TEMPLATE.format(quant=quant)
    local_dir = _resolve_tts_dir()

    print("=" * 70)
    print(f"Downloading Qwen3-TTS 1.7B ({quant})")
    print("=" * 70)
    print(f"Repo: {REPO_ID}")
    print(f"File: {filename}")
    print(f"Target: {local_dir}")
    print()

    local_dir.mkdir(parents=True, exist_ok=True)
    target = local_dir / filename

    if target.exists():
        size_mb = target.stat().st_size / (1024 * 1024)
        print(f"[OK] Model already present: {target} ({size_mb:.1f} MB)")
        return target

    print(f"[DOWNLOAD] Fetching from Hugging Face...")
    downloaded = hf_hub_download(
        repo_id=REPO_ID,
        filename=filename,
        local_dir=str(local_dir),
        local_dir_use_symlinks=False,
    )
    downloaded_path = Path(downloaded)
    size_mb = downloaded_path.stat().st_size / (1024 * 1024)
    print(f"[OK] Downloaded: {downloaded_path} ({size_mb:.1f} MB)")
    return downloaded_path


def create_ollama_modelfile(gguf_path: Path) -> Path:
    """
    Create Ollama Modelfile for custom model loading.

    Args:
        gguf_path: Path to downloaded GGUF file.

    Returns:
        Path to created Modelfile.
    """
    modelfile_path = gguf_path.parent / "Modelfile"
    content = f"""# Qwen3-TTS 1.7B for Ollama
# Created by holo_index/scripts/download_qwen3_tts.py

FROM {gguf_path.name}

# TTS-specific parameters
PARAMETER temperature 0.7
PARAMETER top_p 0.9

TEMPLATE \"\"\"{{{{ .Prompt }}}}\"\"\"
"""
    modelfile_path.write_text(content)
    print(f"[OK] Created Modelfile: {modelfile_path}")
    return modelfile_path


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Download Qwen3-TTS 1.7B GGUF for local TTS"
    )
    parser.add_argument(
        "--quant",
        default=DEFAULT_QUANT,
        choices=["Q2_K", "Q3_K_S", "Q3_K_M", "Q3_K_L", "IQ4_XS",
                 "Q4_K_S", "Q4_K_M", "Q5_K_S", "Q5_K_M", "Q6_K", "Q8_0", "F16"],
        help=f"Quantization level (default: {DEFAULT_QUANT})"
    )
    parser.add_argument(
        "--ollama",
        action="store_true",
        help="Create Ollama Modelfile for custom model loading"
    )
    args = parser.parse_args()

    try:
        path = download_qwen3_tts(quant=args.quant)
        print()
        print(f"[SUCCESS] TTS model ready at: {path}")
        print()

        if args.ollama:
            modelfile = create_ollama_modelfile(path)
            print()
            print("Ollama setup:")
            print(f"  cd {path.parent}")
            print(f"  ollama create qwen3-tts -f Modelfile")
            print(f"  ollama run qwen3-tts")
            print()

        print("Next steps:")
        print("  1. Verify: python -c \"from modules.infrastructure.shared_utilities.local_model_selection import resolve_tts_model_path; print(resolve_tts_model_path())\"")
        print("  2. For LM Studio: Load GGUF directly from the model directory")
        print("  3. For Ollama: Use --ollama flag to create Modelfile, then 'ollama create'")
        print("  4. Test with TTS backend (future integration)")
        return 0
    except Exception as e:
        print(f"[ERROR] Download failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
