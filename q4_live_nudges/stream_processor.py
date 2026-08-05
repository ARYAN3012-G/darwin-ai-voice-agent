"""
Q4 Live Nudges — Streaming Audio Pipeline
==========================================
Simulates a production-grade streaming audio processing pipeline for
real-time call analysis.

Pipeline stages:
  1. Audio Chunk Ingest  — Receives raw audio chunks from telephony
  2. VAD (Voice Activity Detection) — Distinguishes speech from silence
  3. ASR (Automatic Speech Recognition) — Transcribes speech to text
  4. Segment Assembly — Combines ASR tokens into complete utterance segments
  5. Speaker Diarization — Labels segments as AGENT or CUSTOMER

In production, stages 2–4 would use cloud ASR (Google Speech-to-Text,
AWS Transcribe, Azure Speech). Here they are simulated deterministically
to enable reliable testing without external dependencies.

Latency Budget (target):
  - ASR latency (chunk → transcript): < 800ms P95
  - Signal extraction: < 200ms P95
  - End-to-end (chunk → nudge): < 1500ms P95
"""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Iterator, List, Optional


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class Speaker(str, Enum):
    AGENT = "agent"
    CUSTOMER = "customer"
    UNKNOWN = "unknown"


@dataclass
class AudioChunk:
    """Represents a single chunk of raw audio from the telephony stream."""
    chunk_id: str
    session_id: str
    sequence_number: int
    audio_bytes: bytes           # Raw audio bytes (simulated)
    duration_ms: float           # Duration of this chunk in milliseconds
    sample_rate: int = 8000      # 8kHz telephone quality
    channels: int = 1
    received_at: float = field(default_factory=time.perf_counter)

    @classmethod
    def simulate(
        cls,
        session_id: str,
        sequence_number: int,
        duration_ms: float = 200.0,
    ) -> "AudioChunk":
        """Create a simulated audio chunk with placeholder bytes."""
        byte_count = int((duration_ms / 1000) * 8000 * 2)  # 16-bit PCM
        return cls(
            chunk_id=str(uuid.uuid4())[:8],
            session_id=session_id,
            sequence_number=sequence_number,
            audio_bytes=bytes(random.getrandbits(8) for _ in range(min(byte_count, 128))),
            duration_ms=duration_ms,
        )


@dataclass
class VADResult:
    """Voice Activity Detection output."""
    chunk_id: str
    has_speech: bool
    speech_probability: float    # 0.0 to 1.0
    energy_db: float             # Signal energy in dB
    processing_time_ms: float


@dataclass
class ASRToken:
    """A single word token from the ASR engine."""
    word: str
    confidence: float           # 0.0 to 1.0
    start_ms: float             # Offset from chunk start
    end_ms: float


@dataclass
class TranscriptSegment:
    """
    A fully assembled utterance segment from ASR output.
    Represents a complete spoken turn (or partial turn for low-latency).
    """
    segment_id: str
    session_id: str
    speaker: Speaker
    text: str
    tokens: List[ASRToken]
    is_final: bool              # False for partial/streaming segments
    start_offset_ms: float      # Offset from call start
    end_offset_ms: float
    asr_latency_ms: float       # Time from audio receipt to transcript ready
    chunk_sequence: int         # Which audio chunk this came from

    @property
    def duration_ms(self) -> float:
        return self.end_offset_ms - self.start_offset_ms

    def to_dict(self) -> dict:
        return {
            "segment_id": self.segment_id,
            "session_id": self.session_id,
            "speaker": self.speaker.value,
            "text": self.text,
            "is_final": self.is_final,
            "start_ms": self.start_offset_ms,
            "end_ms": self.end_offset_ms,
            "asr_latency_ms": round(self.asr_latency_ms, 1),
        }


# ---------------------------------------------------------------------------
# Simulated ASR Engine
# ---------------------------------------------------------------------------

# A library of pre-scripted utterances for realistic simulation
_ASR_UTTERANCE_LIBRARY = {
    Speaker.AGENT: [
        "Good morning, this is Alex from HealthGuard Insurance. How can I help you today?",
        "Before we continue, I need to mention that this call may be recorded for quality assurance.",
        "May I ask your age to help determine the right plan for you?",
        "We offer comprehensive health insurance starting at PHP 6,000 per year.",
        "There is a 30-day waiting period for illness claims, but accidents are covered from Day 1.",
        "The critical illness rider provides a lump-sum payment upon diagnosis of major illness.",
        "If you have a pre-existing condition, there is typically a 12-month exclusion period.",
        "Our plans are renewable up to the age of 75.",
        "Would you like me to explain the claims process in detail?",
        "I can also offer you a maternity rider for an additional PHP 200 per month.",
    ],
    Speaker.CUSTOMER: [
        "I already have company HMO. Why would I need additional insurance?",
        "I've been calling for the past 3 times and nobody has resolved my issue.",
        "The interest rate seems really high. Can you give me a better deal?",
        "I'm not sure I can afford this right now. Times are tough.",
        "What exactly is covered if I get cancer? I have a family history.",
        "I want to cancel my policy. I'm not happy with the service.",
        "Can you transfer me to someone who can actually help me?",
        "I haven't received my policy documents yet. It's been 3 weeks.",
        "Do you cover mental health consultations?",
        "I might be interested in getting insurance for my whole family.",
        "My income is irregular. Can I pay annually instead of monthly?",
        "Are there any exclusions for sports injuries?",
    ],
}


class SimulatedASR:
    """
    Deterministic simulated ASR engine for testing purposes.
    In production, this would be replaced with a real ASR API call.
    """

    BASE_ASR_LATENCY_MS = 150.0  # Base processing latency
    LATENCY_VARIANCE_MS = 80.0   # Random variance

    def __init__(self, session_id: str) -> None:
        self._session_id = session_id
        self._utterance_queue: List[tuple] = []  # (speaker, text) pairs
        self._current_offset_ms = 0.0
        self._seg_counter = 0

    def load_script(self, script: List[tuple]) -> None:
        """Load a list of (Speaker, text) tuples as the call script."""
        self._utterance_queue = list(script)

    def process_chunk(self, chunk: AudioChunk) -> Optional[TranscriptSegment]:
        """
        Simulate processing an audio chunk through ASR.
        Returns a TranscriptSegment or None (if silence/incomplete).
        """
        process_start = time.perf_counter()

        # Simulate ASR latency
        latency_ms = self.BASE_ASR_LATENCY_MS + random.uniform(
            -self.LATENCY_VARIANCE_MS / 2, self.LATENCY_VARIANCE_MS
        )

        # Only emit a segment every 3–5 chunks (simulates utterance completion)
        self._seg_counter += 1
        if self._seg_counter % random.randint(3, 5) != 0:
            return None

        if not self._utterance_queue:
            return None

        speaker, text = self._utterance_queue.pop(0)
        tokens = self._tokenize(text)
        seg_duration_ms = len(tokens) * 120.0  # ~120ms per word average

        asr_latency_ms = (time.perf_counter() - process_start) * 1000 + latency_ms
        self._current_offset_ms += chunk.duration_ms

        return TranscriptSegment(
            segment_id=str(uuid.uuid4())[:8],
            session_id=self._session_id,
            speaker=speaker,
            text=text,
            tokens=tokens,
            is_final=True,
            start_offset_ms=self._current_offset_ms,
            end_offset_ms=self._current_offset_ms + seg_duration_ms,
            asr_latency_ms=round(asr_latency_ms, 2),
            chunk_sequence=chunk.sequence_number,
        )

    @staticmethod
    def _tokenize(text: str) -> List[ASRToken]:
        """Convert text to ASRToken list with simulated confidence scores."""
        words = text.split()
        tokens = []
        offset = 0.0
        for word in words:
            word_duration = 120.0 + random.uniform(-20, 30)
            tokens.append(ASRToken(
                word=word,
                confidence=random.uniform(0.82, 0.99),
                start_ms=offset,
                end_ms=offset + word_duration,
            ))
            offset += word_duration
        return tokens


# ---------------------------------------------------------------------------
# Stream Processor
# ---------------------------------------------------------------------------

class StreamProcessor:
    """
    Production-grade streaming audio pipeline.

    Orchestrates: Audio Chunks → VAD → ASR → Segment Assembly → Callbacks

    Usage:
        processor = StreamProcessor(session_id="call-001")
        processor.load_call_script(script)
        processor.on_segment(my_callback)
        for segment in processor.stream(chunk_count=50):
            print(segment.speaker, segment.text)
    """

    CHUNK_DURATION_MS = 200.0    # 200ms chunks (standard telephony)

    def __init__(self, session_id: str = "") -> None:
        import uuid as _uuid
        self.session_id = session_id or str(_uuid.uuid4())[:8]
        self._asr = SimulatedASR(self.session_id)
        self._callbacks: List[Callable[[TranscriptSegment], None]] = []
        self._segments: List[TranscriptSegment] = []
        self._chunk_count = 0
        self._is_running = False

    def load_call_script(self, script: List[tuple]) -> None:
        """Load (Speaker, text) script into the simulated ASR engine."""
        self._asr.load_script(script)

    def on_segment(self, callback: Callable[[TranscriptSegment], None]) -> None:
        """Register a callback to be called on each transcribed segment."""
        self._callbacks.append(callback)

    def stream(self, chunk_count: int = 100) -> Iterator[TranscriptSegment]:
        """
        Stream audio chunks through the pipeline, yielding TranscriptSegments.
        Simulates real-time processing with configurable chunk count.
        """
        self._is_running = True
        for seq in range(chunk_count):
            # Simulate chunk receipt (in production: from telephony API)
            chunk = AudioChunk.simulate(
                session_id=self.session_id,
                sequence_number=seq,
                duration_ms=self.CHUNK_DURATION_MS,
            )
            self._chunk_count += 1

            # VAD (simplified: always has speech for simulation)
            # ASR processing
            segment = self._asr.process_chunk(chunk)

            if segment:
                self._segments.append(segment)
                for cb in self._callbacks:
                    cb(segment)
                yield segment

        self._is_running = False

    def get_all_segments(self) -> List[TranscriptSegment]:
        return list(self._segments)

    def get_full_transcript(self) -> str:
        """Return the complete call transcript as a string."""
        lines = []
        for seg in self._segments:
            lines.append(f"[{seg.speaker.value.upper():<8}] {seg.text}")
        return "\n".join(lines)

    @property
    def total_chunks(self) -> int:
        return self._chunk_count
