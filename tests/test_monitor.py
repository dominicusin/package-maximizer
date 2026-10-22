"""Tests for monitor module coverage."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
import psutil

from package_maximizer.utils import monitor


class TestResourceSnapshot:
    def test_total_cpu_s_property(self):
        snap = monitor.ResourceSnapshot(
            wall_time=1.0,
            cpu_user=1.5,
            cpu_system=0.5,
            cpu_children_user=0.0,
            cpu_children_system=0.0,
            rss_mb=10.0,
            vms_mb=20.0,
            num_threads=1,
            pid=1234,
        )
        assert snap.total_cpu_s == 2.0
        assert snap.peak_rss_mb == 10.0

    def test_peak_rss_mb_property(self):
        snap = monitor.ResourceSnapshot(
            wall_time=1.0,
            cpu_user=0.0,
            cpu_system=0.0,
            cpu_children_user=0.0,
            cpu_children_system=0.0,
            rss_mb=100.0,
            vms_mb=200.0,
            num_threads=5,
            pid=1,
        )
        assert snap.peak_rss_mb == 100.0


class TestResourceMonitor:
    def test_snapshot_with_real_process(self):
        mon = monitor.ResourceMonitor()
        snap = mon.snapshot()
        assert isinstance(snap, monitor.ResourceSnapshot)
        assert snap.pid == mon.process.pid
        assert snap.wall_time >= 0
        assert snap.num_threads >= 1
        assert snap.total_cpu_s >= 0

    def test_snapshot_resets_timer(self):
        mon = monitor.ResourceMonitor()
        # Initial snapshot
        snap1 = mon.snapshot()
        # Second snapshot should have wall_time >= 0 (timer was reset)
        snap2 = mon.snapshot()
        assert snap2.wall_time >= 0
        assert snap1.wall_time >= 0

    def test_to_dict(self):
        mon = monitor.ResourceMonitor()
        snap = mon.snapshot()
        data = mon.to_dict()
        assert isinstance(data, dict)
        assert "pid" in data
        assert "peak_rss_mb" in data
        assert "rss_mb" in data
        assert "wall_time_s" in data
        assert "cpu_user_s" in data
        assert "cpu_system_s" in data
        assert "cpu_total_s" in data
        assert "num_threads" in data
        assert data["pid"] == mon.process.pid
        assert data["peak_rss_mb"] >= 0
        assert data["rss_mb"] >= 0
        assert data["wall_time_s"] >= 0
        assert data["cpu_user_s"] >= 0
        assert data["cpu_system_s"] >= 0
        assert data["cpu_total_s"] >= 0
        assert data["num_threads"] >= 1

    @patch("package_maximizer.utils.monitor.psutil")
    def test_with_none_process(self, mock_psutil):
        mock_psutil.Process.return_value = None
        mon = monitor.ResourceMonitor()
        snap = mon.snapshot()
        assert snap.pid == -1
        assert snap.cpu_user == 0.0
        assert snap.cpu_system == 0.0
        assert snap.cpu_children_user == 0.0
        assert snap.cpu_children_system == 0.0
        assert snap.rss_mb == 0.0
        assert snap.vms_mb == 0.0
        assert snap.num_threads == 0

    @patch("package_maximizer.utils.monitor.psutil")
    def test_sample_with_psutil_error(self, mock_psutil):
        mock_psutil.Process.return_value = MagicMock()
        mock_proc = mock_psutil.Process.return_value
        mock_proc.cpu_times.side_effect = psutil.Error("test")
        mock_proc.memory_info.side_effect = psutil.Error("test")
        # Make psutil.Error accessible to the code under test
        mock_psutil.Error = psutil.Error

        mon = monitor.ResourceMonitor()
        snap = mon.snapshot()

        assert snap.wall_time >= 0
        assert snap.cpu_user == 0.0
        assert snap.cpu_system == 0.0
        assert snap.cpu_children_user == 0.0
        assert snap.cpu_children_system == 0.0
        assert snap.rss_mb == 0.0
        assert snap.vms_mb == 0.0
        assert snap.num_threads == 0
        assert snap.pid == mon.process.pid

    def test_track_context_manager(self):
        mon = monitor.ResourceMonitor()
        with mon.track():
            time.sleep(0.01)
        snap = mon.snapshot()
        assert snap.wall_time >= 0


class TestCaptureMonitor:
    def test_capture_monitor_returns_result_and_monitor(self):
        def dummy_fn(x, y):
            return x + y

        result, mon = monitor.capture_monitor(dummy_fn, 1, 2)
        assert result == 3
        assert isinstance(mon, monitor.ResourceMonitor)

    def test_capture_monitor_with_exception(self):
        def failing_fn():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            monitor.capture_monitor(failing_fn)
