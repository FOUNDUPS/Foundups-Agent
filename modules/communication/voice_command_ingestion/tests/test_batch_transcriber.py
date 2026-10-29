import numpy as np
from dataclasses import dataclass

from modules.communication.voice_command_ingestion import (
    BatchTranscriber,
    TranscriptSegment,
    STTEvent,
)


@dataclass
class DummyChunk:
    audio: np.ndarray
    sample_rate: int
    timestamp_ms: int
    duration_sec: float


class DummySTT:
    def __init__(self, text="hello", confidence=0.9):
        self.text = text
        self.confidence = confidence

    def transcribe(self, audio, sample_rate=16000):
        return STTEvent(
            text=self.text,
            is_final=True,
            start_ms=0,
            end_ms=1000,
            confidence=self.confidence,
        )


def test_transcribe_video_yields_segments(tmp_path):
    transcriber = BatchTranscriber(output_dir=str(tmp_path))
    transcriber._stt = DummySTT(text="hello")

    chunks = [
        DummyChunk(
            audio=np.zeros(16000, dtype=np.float32),
            sample_rate=16000,
            timestamp_ms=30000,
            duration_sec=30.0,
        )
    ]

    segments = list(transcriber.transcribe_video(
        video_id="abc123",
        title="Test Title",
        audio_chunks=chunks,
    ))

    assert len(segments) == 1
    segment = segments[0]
    assert segment.video_id == "abc123"
    assert segment.title == "Test Title"
    assert segment.timestamp_sec == 30.0
    assert segment.end_sec == 60.0
    assert segment.text == "hello"
    assert segment.url == "https://youtu.be/abc123?t=30"


def test_save_transcripts_jsonl(tmp_path):
    transcriber = BatchTranscriber(output_dir=str(tmp_path))
    segments = [
        TranscriptSegment(
            video_id="vid001",
            title="Example",
            timestamp_sec=12.0,
            end_sec=15.0,
            text="hello world",
            confidence=0.95,
            url="https://youtu.be/vid001?t=12",
        )
    ]

    count = transcriber.save_transcripts_jsonl(segments, "out.jsonl")
    assert count == 1
    payload = (tmp_path / "out.jsonl").read_text(encoding="utf-8").strip()
    assert '"video_id": "vid001"' in payload
    assert '"text": "hello world"' in payload
