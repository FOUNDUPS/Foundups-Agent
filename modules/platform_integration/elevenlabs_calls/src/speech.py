"""Explicit local microphone trigger for a previously prepared request."""
from contextlib import redirect_stdout
import re
import sys
import unicodedata


def is_call_trigger(text: str) -> bool:
    normalized = unicodedata.normalize("NFKC", text).strip().lower()
    normalized = re.sub(r"[.!。！]+$", "", normalized).strip()
    return normalized in {"make this call", "0102 make this call", "この電話をかけて"}


def listen_once(language: str = "en", backend: str = "whisper") -> str:
    # Reuse owned capture and STT contracts; don't start the general RedDog REPL.
    from modules.infrastructure.cli.src.openclaw_voice import (
        CohereTranscribeBackend, WhisperSTTBackend, record_until_silence,
    )
    recognizer = (CohereTranscribeBackend(language=language) if backend == "cohere"
                  else WhisperSTTBackend(language=language))
    with redirect_stdout(sys.stderr):
        if not recognizer.available():
            raise ValueError("Selected local STT is unavailable; install the speech requirements/model")
        audio = record_until_silence(max_duration=8, announce=False,
                                     suppress_no_speech_log=True)
        if audio is None:
            raise ValueError("No microphone speech captured; no call submitted")
        text = recognizer.transcribe(audio)
    if not text:
        raise ValueError("No speech recognized; no call submitted")
    return text
