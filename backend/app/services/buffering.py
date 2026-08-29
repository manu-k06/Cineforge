import collections
import logging
import time
from typing import Deque, Optional, Tuple

from app.config import settings
from app.models.buffering import (
    BufferHealthState,
    PrefetchAction,
    SessionBufferingMetrics,
)

logger = logging.getLogger("cineforge.buffering")


class ThroughputEstimator:
    """Estimates real-time MTProto download throughput using a sliding window of recent chunk download samples."""

    def __init__(self, window_size: int = 10, default_bps: int = settings.MEASURED_SOURCE_THROUGHPUT_BPS):
        self.window_size = window_size
        self.default_bps = default_bps
        self._samples: Deque[Tuple[int, float]] = collections.deque(maxlen=window_size)
        self.total_downloaded_bytes: int = 0

    def record_sample(self, byte_count: int, elapsed_seconds: float) -> None:
        """Record a completed chunk download measurement."""
        self.total_downloaded_bytes += byte_count
        if elapsed_seconds > 0.001 and byte_count > 0:
            self._samples.append((byte_count, elapsed_seconds))

    def get_estimated_throughput_bps(self) -> int:
        """Calculate weighted average throughput in bits/sec from recent samples, or fallback to default baseline."""
        if not self._samples:
            return self.default_bps

        total_bytes = sum(b for b, _ in self._samples)
        total_time = sum(t for _, t in self._samples)

        if total_time <= 0:
            return self.default_bps

        return int((total_bytes * 8) / total_time)


class BufferHealthEngine:
    """Evaluates playback viability, buffer drain rates, health states, and adaptive prefetch actions."""

    @staticmethod
    def evaluate_buffering(
        session_id: str,
        downloaded_bytes: int,
        buffered_bytes: int,
        max_buffer_bytes: int,
        download_throughput_bps: int,
        playback_bitrate_bps: Optional[int],
        margin: float = settings.MEDIA_SUSTAINABILITY_MARGIN,
    ) -> SessionBufferingMetrics:
        """Evaluate buffer duration, health state, stall risk, and prefetch strategy for a streaming session."""
        if not playback_bitrate_bps or playback_bitrate_bps <= 0:
            # Fallback if bitrate is unknown
            health = BufferHealthState.HEALTHY if buffered_bytes > 0 else BufferHealthState.STALLED
            return SessionBufferingMetrics(
                session_id=session_id,
                downloaded_bytes=downloaded_bytes,
                buffered_bytes=buffered_bytes,
                buffered_seconds=None,
                download_throughput_bps=download_throughput_bps,
                playback_bitrate_bps=None,
                playback_drain_rate_bps=None,
                net_buffer_growth_rate_bps=None,
                buffer_health=health,
                time_to_stall_seconds=None,
                sustainable=None,
                prefetch_recommended=buffered_bytes < max_buffer_bytes,
                prefetch_action=PrefetchAction.NORMAL_PREFETCH if buffered_bytes > 0 else PrefetchAction.AGGRESSIVE_PREFETCH,
                recommended_prefetch_chunks=2 if buffered_bytes > 0 else 4,
            )

        # 1. Calculate buffer duration in seconds
        buffered_seconds = round((buffered_bytes * 8) / playback_bitrate_bps, 2)
        playback_drain_rate_bps = playback_bitrate_bps
        net_growth_bps = download_throughput_bps - playback_drain_rate_bps

        # 2. Sustainability check
        required_bps = int(playback_bitrate_bps * margin)
        sustainable = download_throughput_bps >= required_bps

        # 3. Time to stall calculation
        time_to_stall: Optional[float] = None
        if net_growth_bps < 0 and buffered_bytes > 0:
            # Buffer is draining during playback
            time_to_stall = round((buffered_bytes * 8) / abs(net_growth_bps), 2)

        # 4. State classification
        if buffered_bytes == 0 or buffered_seconds < 2.0:
            health = BufferHealthState.STALLED
        elif buffered_seconds < 10.0:
            health = BufferHealthState.CRITICAL
        elif buffered_seconds < 30.0:
            health = BufferHealthState.LOW
        else:
            health = BufferHealthState.HEALTHY

        # 5. Adaptive Prefetch Decision Mechanism
        if health == BufferHealthState.STALLED:
            prefetch_rec = True
            prefetch_act = PrefetchAction.AGGRESSIVE_PREFETCH
            rec_chunks = 4
        elif health == BufferHealthState.CRITICAL:
            prefetch_rec = True
            if time_to_stall is not None and time_to_stall < 8.0:
                prefetch_act = PrefetchAction.STALL_WARNING
            else:
                prefetch_act = PrefetchAction.AGGRESSIVE_PREFETCH
            rec_chunks = 4
        elif health == BufferHealthState.LOW:
            prefetch_rec = True
            prefetch_act = PrefetchAction.AGGRESSIVE_PREFETCH
            rec_chunks = 3
        else:
            # HEALTHY state: Check if buffer is nearly full or holds >= 60s
            is_buffer_full = buffered_bytes >= int(0.90 * max_buffer_bytes)
            has_ample_buffer = buffered_seconds >= 60.0

            if (is_buffer_full or has_ample_buffer) and net_growth_bps >= 0:
                prefetch_rec = False
                prefetch_act = PrefetchAction.PAUSE_PREFETCH
                rec_chunks = 0
            else:
                prefetch_rec = True
                prefetch_act = PrefetchAction.NORMAL_PREFETCH
                rec_chunks = settings.MEDIA_PREFETCH_CHUNKS_AHEAD

        return SessionBufferingMetrics(
            session_id=session_id,
            downloaded_bytes=downloaded_bytes,
            buffered_bytes=buffered_bytes,
            buffered_seconds=buffered_seconds,
            download_throughput_bps=download_throughput_bps,
            playback_bitrate_bps=playback_bitrate_bps,
            playback_drain_rate_bps=playback_drain_rate_bps,
            net_buffer_growth_rate_bps=net_growth_bps,
            buffer_health=health,
            time_to_stall_seconds=time_to_stall,
            sustainable=sustainable,
            prefetch_recommended=prefetch_rec,
            prefetch_action=prefetch_act,
            recommended_prefetch_chunks=rec_chunks,
        )


buffering_engine = BufferHealthEngine()
