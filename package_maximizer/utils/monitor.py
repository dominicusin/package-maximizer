"""`utils/monitor.py` — мониторинг ресурсов процесса во время решения.

Предоставляет класс :class:`ResourceMonitor`, который измеряет:

* ``wall_time`` — реальное прошедшее время (time.perf_counter);
* ``cpu_user`` / ``cpu_system`` / ``cpu_children_*`` — процессорное время
  (psutil ``Process.cpu_times``);
* ``rss_mb`` / ``vms_mb`` — текущее и пиковое потребление RSS памяти процесса;
* ``num_threads`` / ``pid``.

Монитор предназначен для обёртки вокруг вычислительных этапов пакетного
решателя (бенчмарки, процессоры решений, CLI-команды ``maximize``/``export``),
чтобы давать системно-структурную оценку затрат ресурсов на больших графах.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Generator

import psutil

__all__ = ["ResourceMonitor", "ResourceSnapshot", "capture_monitor"]


@dataclass
class ResourceSnapshot:
    """Снимок ресурсов в произвольной точке."""

    wall_time: float
    cpu_user: float
    cpu_system: float
    cpu_children_user: float
    cpu_children_system: float
    rss_mb: float
    vms_mb: float
    num_threads: int
    pid: int

    @property
    def total_cpu_s(self) -> float:
        return self.cpu_user + self.cpu_system

    @property
    def peak_rss_mb(self) -> float:
        return self.rss_mb


@dataclass
class ResourceMonitor:
    """Измерение ресурсов процесса за временной интервал."""

    process: psutil.Process | None = None
    start_wall: float = 0.0
    start_cpu_user: float = 0.0
    start_cpu_system: float = 0.0
    start_cpu_children_user: float = 0.0
    start_cpu_children_system: float = 0.0
    peak_rss: float = 0.0

    def __post_init__(self) -> None:
        self.process = psutil.Process() if self.process is None else self.process
        self._reset()

    def _reset(self) -> None:
        self.start_wall = time.perf_counter()
        proc = self.process
        if proc is not None:
            try:
                ct = proc.cpu_times()
                self.start_cpu_user = ct.user
                self.start_cpu_system = ct.system
                self.start_cpu_children_user = ct.children_user
                self.start_cpu_children_system = ct.children_system
            except (psutil.Error, AttributeError):
                self.start_cpu_user = 0.0
                self.start_cpu_system = 0.0
                self.start_cpu_children_user = 0.0
                self.start_cpu_children_system = 0.0
        else:
            self.start_cpu_user = 0.0
            self.start_cpu_system = 0.0
            self.start_cpu_children_user = 0.0
            self.start_cpu_children_system = 0.0
        self.peak_rss = 0.0

    def _safe_sample(self) -> ResourceSnapshot:
        if self.process is None:
            return ResourceSnapshot(
                wall_time=0.0,
                cpu_user=0.0,
                cpu_system=0.0,
                cpu_children_user=0.0,
                cpu_children_system=0.0,
                rss_mb=0.0,
                vms_mb=0.0,
                num_threads=0,
                pid=-1,
            )
        try:
            ct = self.process.cpu_times()
            rss = self.process.memory_info().rss / (1024 * 1024)
            self.peak_rss = max(self.peak_rss, rss)
            return ResourceSnapshot(
                wall_time=time.perf_counter() - self.start_wall,
                cpu_user=ct.user - self.start_cpu_user,
                cpu_system=ct.system - self.start_cpu_system,
                cpu_children_user=ct.children_user - self.start_cpu_children_user,
                cpu_children_system=ct.children_system - self.start_cpu_children_system,
                rss_mb=rss,
                vms_mb=self.process.memory_info().vms / (1024 * 1024),
                num_threads=self.process.num_threads(),
                pid=self.process.pid,
            )
        except (psutil.Error, AttributeError) as exc:
            logger = logging.getLogger(__name__)
            logger.warning("ResourceMonitor: cannot sample process: %s", exc)
            return ResourceSnapshot(
                wall_time=time.perf_counter() - self.start_wall,
                cpu_user=0.0,
                cpu_system=0.0,
                cpu_children_user=0.0,
                cpu_children_system=0.0,
                rss_mb=0.0,
                vms_mb=0.0,
                num_threads=0,
                pid=self.process.pid if self.process else -1,
            )

    def snapshot(self) -> ResourceSnapshot:
        """Сделать снимок и сбросить таймер."""
        snap = self._safe_sample()
        self._reset()
        return snap

    @contextmanager
    def track(self):
        """Контекстный менеджер: измеряет `with` блок и возвращает снимок."""
        self._reset()
        try:
            yield self
        finally:
            self.snapshot()

    def to_dict(self) -> dict[str, Any]:
        """Превратить измерение в отчёт (JSON-совместимый)."""
        sample = self._safe_sample()
        return {
            "pid": self.process.pid if self.process else -1,
            "peak_rss_mb": round(self.peak_rss, 3),
            "rss_mb": round(sample.rss_mb, 3),
            "wall_time_s": round(sample.wall_time, 6),
            "cpu_user_s": round(sample.cpu_user, 6),
            "cpu_system_s": round(sample.cpu_system, 6),
            "cpu_total_s": round(sample.total_cpu_s, 6),
            "num_threads": sample.num_threads,
        }


def capture_monitor(
    func: Callable[..., Any], *args, **kwargs
) -> tuple[Any, ResourceMonitor]:
    """Вызвать ``func`` и вернуть (результат, ResourceMonitor)."""
    monitor = ResourceMonitor()
    try:
        result = func(*args, **kwargs)
    finally:
        monitor.snapshot()
    return result, monitor
