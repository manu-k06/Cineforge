import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from app.models.buffering import BufferHealthState, PrefetchAction
from app.services.buffering import BufferHealthEngine, ThroughputEstimator
from app.services.stream_session import MediaChunkCache, MediaStreamSession


class TestMilestoneB8Buffering(unittest.TestCase):
    """Test suite for Milestone B8: Playback Viability & Buffering Layer."""

    def setUp(self):
        self.engine = BufferHealthEngine()
        self.session_id = "test-b8-session-uuid"
        self.bitrate = 1_013_226  # ~1.01 Mbps (Inception probed bitrate)
        self.max_buffer_bytes = 16 * 1024 * 1024  # 16 MB

    def test_01_buffer_duration_calculation(self):
        """1. Verify buffered duration calculation in seconds from buffered bytes and bitrate."""
        # 4 MB buffered at ~1.013 Mbps bitrate
        buffered_bytes = 4 * 1024 * 1024  # 4,194,304 bytes = 33,554,432 bits
        metrics = self.engine.evaluate_buffering(
            session_id=self.session_id,
            downloaded_bytes=buffered_bytes,
            buffered_bytes=buffered_bytes,
            max_buffer_bytes=self.max_buffer_bytes,
            download_throughput_bps=1_050_000,
            playback_bitrate_bps=self.bitrate,
        )
        expected_sec = round((buffered_bytes * 8) / self.bitrate, 2)  # ~33.12s
        self.assertEqual(metrics.buffered_seconds, expected_sec)
        self.assertEqual(metrics.playback_drain_rate_bps, self.bitrate)

    def test_02_throughput_estimation(self):
        """2. Verify dynamic throughput sliding window estimator."""
        estimator = ThroughputEstimator(window_size=5, default_bps=1_000_000)
        # Fallback when empty
        self.assertEqual(estimator.get_estimated_throughput_bps(), 1_000_000)

        # Record 2 chunks of 512 KB in 4.0 seconds (1 MB in 8.0s = 1,048,576 bps)
        estimator.record_sample(524288, 4.0)
        estimator.record_sample(524288, 4.0)
        self.assertEqual(estimator.total_downloaded_bytes, 1048576)
        self.assertEqual(estimator.get_estimated_throughput_bps(), 1048576)

    def test_03_playback_drain_rate_and_net_growth(self):
        """3. Verify playback drain rate and net growth/drain rate."""
        throughput = 1_500_000
        metrics = self.engine.evaluate_buffering(
            session_id=self.session_id,
            downloaded_bytes=2097152,
            buffered_bytes=2097152,
            max_buffer_bytes=self.max_buffer_bytes,
            download_throughput_bps=throughput,
            playback_bitrate_bps=self.bitrate,
        )
        self.assertEqual(metrics.playback_drain_rate_bps, self.bitrate)
        self.assertEqual(metrics.net_buffer_growth_rate_bps, throughput - self.bitrate)
        # When throughput exceeds bitrate, time to stall is None
        self.assertIsNone(metrics.time_to_stall_seconds)

    def test_04_healthy_buffer_state(self):
        """4. Verify HEALTHY buffer state (>= 30s buffered)."""
        # 8 MB buffered at 1.01 Mbps = ~66.2s
        buffered_bytes = 8 * 1024 * 1024
        metrics = self.engine.evaluate_buffering(
            session_id=self.session_id,
            downloaded_bytes=buffered_bytes,
            buffered_bytes=buffered_bytes,
            max_buffer_bytes=self.max_buffer_bytes,
            download_throughput_bps=1_200_000,
            playback_bitrate_bps=self.bitrate,
        )
        self.assertEqual(metrics.buffer_health, BufferHealthState.HEALTHY)
        self.assertGreaterEqual(metrics.buffered_seconds, 30.0)

    def test_05_low_buffer_state(self):
        """5. Verify LOW buffer state (10s <= duration < 30s)."""
        # 2 MB buffered at 1.01 Mbps = ~16.5s
        buffered_bytes = 2 * 1024 * 1024
        metrics = self.engine.evaluate_buffering(
            session_id=self.session_id,
            downloaded_bytes=buffered_bytes,
            buffered_bytes=buffered_bytes,
            max_buffer_bytes=self.max_buffer_bytes,
            download_throughput_bps=1_050_000,
            playback_bitrate_bps=self.bitrate,
        )
        self.assertEqual(metrics.buffer_health, BufferHealthState.LOW)
        self.assertTrue(10.0 <= metrics.buffered_seconds < 30.0)
        self.assertTrue(metrics.prefetch_recommended)
        self.assertEqual(metrics.prefetch_action, PrefetchAction.AGGRESSIVE_PREFETCH)

    def test_06_critical_buffer_state(self):
        """6. Verify CRITICAL buffer state (2s <= duration < 10s)."""
        # 512 KB buffered at 1.01 Mbps = ~4.14s
        buffered_bytes = 524288
        metrics = self.engine.evaluate_buffering(
            session_id=self.session_id,
            downloaded_bytes=buffered_bytes,
            buffered_bytes=buffered_bytes,
            max_buffer_bytes=self.max_buffer_bytes,
            download_throughput_bps=900_000,  # Draining
            playback_bitrate_bps=self.bitrate,
        )
        self.assertEqual(metrics.buffer_health, BufferHealthState.CRITICAL)
        self.assertLess(metrics.buffered_seconds, 10.0)
        self.assertTrue(metrics.prefetch_recommended)
        self.assertIsNotNone(metrics.time_to_stall_seconds)

    def test_07_stall_detection(self):
        """7. Verify STALLED state detection (0 bytes or < 2s)."""
        metrics = self.engine.evaluate_buffering(
            session_id=self.session_id,
            downloaded_bytes=0,
            buffered_bytes=0,
            max_buffer_bytes=self.max_buffer_bytes,
            download_throughput_bps=1_050_000,
            playback_bitrate_bps=self.bitrate,
        )
        self.assertEqual(metrics.buffer_health, BufferHealthState.STALLED)
        self.assertEqual(metrics.buffered_seconds, 0.0)
        self.assertTrue(metrics.prefetch_recommended)
        self.assertEqual(metrics.recommended_prefetch_chunks, 4)

    def test_08_sustainability_assessment(self):
        """8. Verify sustainable vs non-sustainable throughput comparison."""
        # Sustainable: speed >= bitrate * 1.15
        sustainable_speed = int(self.bitrate * 1.20)
        met_sust = self.engine.evaluate_buffering(
            session_id=self.session_id,
            downloaded_bytes=4194304,
            buffered_bytes=4194304,
            max_buffer_bytes=self.max_buffer_bytes,
            download_throughput_bps=sustainable_speed,
            playback_bitrate_bps=self.bitrate,
            margin=1.15,
        )
        self.assertTrue(met_sust.sustainable)

        # Unsustainable: speed < bitrate * 1.15
        unsustainable_speed = int(self.bitrate * 1.04)
        met_unsust = self.engine.evaluate_buffering(
            session_id=self.session_id,
            downloaded_bytes=4194304,
            buffered_bytes=4194304,
            max_buffer_bytes=self.max_buffer_bytes,
            download_throughput_bps=unsustainable_speed,
            playback_bitrate_bps=self.bitrate,
            margin=1.15,
        )
        self.assertFalse(met_unsust.sustainable)

    def test_09_adaptive_prefetch_action_scaling(self):
        """9. Verify adaptive prefetch recommendation & chunk scaling."""
        # Case A: Buffer is full (>90%) with healthy buffer (>60s) -> PAUSE_PREFETCH, 0 chunks
        full_buffer = int(0.95 * self.max_buffer_bytes)
        met_pause = self.engine.evaluate_buffering(
            session_id=self.session_id,
            downloaded_bytes=full_buffer,
            buffered_bytes=full_buffer,
            max_buffer_bytes=self.max_buffer_bytes,
            download_throughput_bps=1_500_000,
            playback_bitrate_bps=self.bitrate,
        )
        self.assertFalse(met_pause.prefetch_recommended)
        self.assertEqual(met_pause.prefetch_action, PrefetchAction.PAUSE_PREFETCH)
        self.assertEqual(met_pause.recommended_prefetch_chunks, 0)

        # Case B: Buffer is LOW -> AGGRESSIVE_PREFETCH, 3 chunks
        low_buffer = 2 * 1024 * 1024
        met_low = self.engine.evaluate_buffering(
            session_id=self.session_id,
            downloaded_bytes=low_buffer,
            buffered_bytes=low_buffer,
            max_buffer_bytes=self.max_buffer_bytes,
            download_throughput_bps=1_050_000,
            playback_bitrate_bps=self.bitrate,
        )
        self.assertTrue(met_low.prefetch_recommended)
        self.assertEqual(met_low.prefetch_action, PrefetchAction.AGGRESSIVE_PREFETCH)
        self.assertEqual(met_low.recommended_prefetch_chunks, 3)

    def test_10_media_stream_session_buffering_integration(self):
        """10. Verify MediaStreamSession.get_buffering_metrics integration."""
        mock_reader = MagicMock()
        mock_reader.get_file_size.return_value = 1125702788
        mock_reader.get_mime_type.return_value = "video/x-matroska"
        mock_reader.get_file_name.return_value = "Inception.mkv"
        mock_reader.get_video_metadata.return_value = MagicMock(duration_seconds=8888.06)

        session = MediaStreamSession(session_id="integration-test-session", reader=mock_reader, max_buffer_mb=16)
        # Put 2 chunks into cache
        session.cache.put(0, b"0" * 524288)
        session.cache.put(1, b"1" * 524288)
        session.throughput_estimator.record_sample(1048576, 8.0)

        metrics = session.get_buffering_metrics()
        self.assertEqual(metrics.session_id, "integration-test-session")
        self.assertEqual(metrics.buffered_bytes, 1048576)
        self.assertAlmostEqual(metrics.buffered_seconds, 8.28, delta=0.5)
        self.assertIn(metrics.buffer_health, [BufferHealthState.CRITICAL, BufferHealthState.LOW])


if __name__ == "__main__":
    unittest.main()
