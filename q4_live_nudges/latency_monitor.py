"""
Q4 Live Nudges — Latency Monitor
==================================
Measures and reports end-to-end latency for the live nudge pipeline.

Latency Stages Measured:
  1. ASR Latency           — Audio chunk receipt → transcript segment ready
  2. Signal Extraction     — Transcript segment → detected signals
  3. Nudge Generation      — Detected signals → nudge emitted
  4. End-to-End (E2E)      — Audio chunk → nudge displayed

Statistics Computed:
  - P50 (median) latency per stage
  - P95 (95th percentile) latency per stage
  - P99 latency per stage
  - Mean and standard deviation
  - Min / Max per stage
  - SLA compliance check (target: E2E P95 < 1500ms)
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Latency Stage
# ---------------------------------------------------------------------------

class LatencyStage:
    ASR = "asr"
    SIGNAL_EXTRACTION = "signal_extraction"
    NUDGE_GENERATION = "nudge_generation"
    END_TO_END = "end_to_end"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class LatencySample:
    """A single latency measurement for one pipeline event."""
    stage: str
    value_ms: float
    timestamp: float = field(default_factory=time.perf_counter)
    session_id: str = ""
    event_id: str = ""


@dataclass
class StageStats:
    """Computed statistics for a single latency stage."""
    stage: str
    count: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    mean_ms: float
    std_ms: float
    min_ms: float
    max_ms: float
    sla_target_ms: Optional[float] = None
    sla_compliant: Optional[bool] = None

    def format(self) -> str:
        lines = [
            f"  Stage      : {self.stage.upper()}",
            f"  Samples    : {self.count}",
            f"  P50        : {self.p50_ms:.1f}ms",
            f"  P95        : {self.p95_ms:.1f}ms",
            f"  P99        : {self.p99_ms:.1f}ms",
            f"  Mean±Std   : {self.mean_ms:.1f}ms ± {self.std_ms:.1f}ms",
            f"  Min / Max  : {self.min_ms:.1f}ms / {self.max_ms:.1f}ms",
        ]
        if self.sla_target_ms is not None:
            status = "✅ PASS" if self.sla_compliant else "❌ FAIL"
            lines.append(f"  SLA Target : < {self.sla_target_ms:.0f}ms P95 → {status}")
        return "\n".join(lines)


@dataclass
class LatencyReport:
    """Complete latency report for a full streaming session."""
    session_id: str
    total_duration_s: float
    total_samples: int
    stages: Dict[str, StageStats]
    sla_targets_ms: Dict[str, float]
    overall_sla_compliant: bool
    generated_at: float = field(default_factory=time.perf_counter)

    def format(self) -> str:
        lines = [
            f"{'='*65}",
            f"  LATENCY REPORT | Session: {self.session_id}",
            f"  Duration: {self.total_duration_s:.1f}s | Samples: {self.total_samples}",
            f"{'='*65}",
        ]
        for stage_name, stats in self.stages.items():
            lines.append(f"\n{'─'*65}")
            lines.append(stats.format())

        overall = "✅ ALL SLA TARGETS MET" if self.overall_sla_compliant else "❌ SLA VIOLATIONS DETECTED"
        lines.append(f"\n{'='*65}")
        lines.append(f"  Overall SLA Status: {overall}")
        lines.append(f"{'='*65}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Latency Monitor
# ---------------------------------------------------------------------------

class LatencyMonitor:
    """
    Real-time latency monitor for the live nudge pipeline.

    Records latency samples per stage and computes P50/P95/P99 statistics
    on demand.

    SLA Targets:
        ASR              : P95 < 800ms
        Signal Extraction: P95 < 200ms
        Nudge Generation : P95 < 100ms
        End-to-End       : P95 < 1500ms

    Usage:
        monitor = LatencyMonitor(session_id="call-001")
        monitor.record(LatencyStage.ASR, 245.3)
        monitor.record(LatencyStage.END_TO_END, 1100.0)
        report = monitor.generate_report()
    """

    SLA_TARGETS_MS: Dict[str, float] = {
        LatencyStage.ASR: 800.0,
        LatencyStage.SIGNAL_EXTRACTION: 200.0,
        LatencyStage.NUDGE_GENERATION: 100.0,
        LatencyStage.END_TO_END: 1500.0,
    }

    def __init__(self, session_id: str = "") -> None:
        import uuid as _uuid
        self.session_id = session_id or str(_uuid.uuid4())[:8]
        self._samples: Dict[str, List[float]] = {
            stage: [] for stage in [
                LatencyStage.ASR,
                LatencyStage.SIGNAL_EXTRACTION,
                LatencyStage.NUDGE_GENERATION,
                LatencyStage.END_TO_END,
            ]
        }
        self._start_time = time.perf_counter()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(self, stage: str, value_ms: float) -> None:
        """Record a latency sample for a given pipeline stage."""
        if stage in self._samples:
            self._samples[stage].append(value_ms)

    def record_asr(self, value_ms: float) -> None:
        self.record(LatencyStage.ASR, value_ms)

    def record_signal_extraction(self, value_ms: float) -> None:
        self.record(LatencyStage.SIGNAL_EXTRACTION, value_ms)

    def record_nudge_generation(self, value_ms: float) -> None:
        self.record(LatencyStage.NUDGE_GENERATION, value_ms)

    def record_e2e(self, value_ms: float) -> None:
        self.record(LatencyStage.END_TO_END, value_ms)

    def generate_report(self) -> LatencyReport:
        """Compute statistics and generate a full LatencyReport."""
        duration_s = time.perf_counter() - self._start_time
        total_samples = sum(len(v) for v in self._samples.values())
        stage_stats: Dict[str, StageStats] = {}

        overall_compliant = True
        for stage, values in self._samples.items():
            if not values:
                continue

            p50 = self._percentile(values, 50)
            p95 = self._percentile(values, 95)
            p99 = self._percentile(values, 99)
            mean = statistics.mean(values)
            std = statistics.stdev(values) if len(values) >= 2 else 0.0

            sla_target = self.SLA_TARGETS_MS.get(stage)
            sla_compliant = (p95 <= sla_target) if sla_target else None

            if sla_compliant is False:
                overall_compliant = False

            stage_stats[stage] = StageStats(
                stage=stage,
                count=len(values),
                p50_ms=round(p50, 2),
                p95_ms=round(p95, 2),
                p99_ms=round(p99, 2),
                mean_ms=round(mean, 2),
                std_ms=round(std, 2),
                min_ms=round(min(values), 2),
                max_ms=round(max(values), 2),
                sla_target_ms=sla_target,
                sla_compliant=sla_compliant,
            )

        return LatencyReport(
            session_id=self.session_id,
            total_duration_s=round(duration_s, 2),
            total_samples=total_samples,
            stages=stage_stats,
            sla_targets_ms=dict(self.SLA_TARGETS_MS),
            overall_sla_compliant=overall_compliant,
        )

    def get_current_p95(self, stage: str) -> Optional[float]:
        """Get the current P95 latency for a stage (live monitoring)."""
        values = self._samples.get(stage, [])
        if len(values) < 5:
            return None
        return self._percentile(values, 95)

    def is_sla_at_risk(self, stage: str, threshold_pct: float = 0.90) -> bool:
        """
        Check if a stage is approaching its SLA limit.
        Returns True if current P95 is above threshold_pct of SLA target.
        """
        p95 = self.get_current_p95(stage)
        if p95 is None:
            return False
        sla_target = self.SLA_TARGETS_MS.get(stage)
        if sla_target is None:
            return False
        return p95 >= sla_target * threshold_pct

    # ------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _percentile(values: List[float], pct: int) -> float:
        """Compute the pct-th percentile of a sorted list."""
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        k = (pct / 100) * (n - 1)
        lower = int(k)
        upper = min(lower + 1, n - 1)
        fractional = k - lower
        return sorted_vals[lower] + fractional * (sorted_vals[upper] - sorted_vals[lower])
