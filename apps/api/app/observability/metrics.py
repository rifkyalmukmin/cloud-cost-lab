"""Application metrics for observability.

Tracks key operational metrics for SLI/SLO monitoring.
Uses an in-memory metrics store (production would use Prometheus or Cloud Monitoring).
"""

import time
from collections import defaultdict
from threading import Lock


class Metrics:
    """Thread-safe in-memory metrics store."""

    def __init__(self):
        self._counters: dict[str, int] = defaultdict(int)
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._gauges: dict[str, float] = {}
        self._lock = Lock()

    def increment(self, name: str, value: int = 1, labels: dict | None = None) -> None:
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] += value

    def observe(self, name: str, value: float, labels: dict | None = None) -> None:
        key = self._make_key(name, labels)
        with self._lock:
            self._histograms[key].append(value)

    def set_gauge(self, name: str, value: float, labels: dict | None = None) -> None:
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = value

    def get_counter(self, name: str, labels: dict | None = None) -> int:
        key = self._make_key(name, labels)
        with self._lock:
            return self._counters.get(key, 0)

    def get_histogram(self, name: str, labels: dict | None = None) -> dict:
        key = self._make_key(name, labels)
        with self._lock:
            values = self._histograms.get(key, [])
            if not values:
                return {"count": 0, "sum": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}
            sorted_vals = sorted(values)
            count = len(sorted_vals)
            return {
                "count": count,
                "sum": round(sum(sorted_vals), 4),
                "avg": round(sum(sorted_vals) / count, 4),
                "p50": round(sorted_vals[int(count * 0.5)], 4),
                "p95": round(sorted_vals[min(int(count * 0.95), count - 1)], 4),
                "p99": round(sorted_vals[min(int(count * 0.99), count - 1)], 4),
            }

    def get_gauge(self, name: str, labels: dict | None = None) -> float:
        key = self._make_key(name, labels)
        with self._lock:
            return self._gauges.get(key, 0.0)

    def get_all(self) -> dict:
        with self._lock:
            return {
                "counters": dict(self._counters),
                "histograms": {k: self._summarize_histogram(v) for k, v in self._histograms.items()},
                "gauges": dict(self._gauges),
            }

    def _summarize_histogram(self, values: list[float]) -> dict:
        if not values:
            return {"count": 0, "sum": 0, "avg": 0}
        return {
            "count": len(values),
            "sum": round(sum(values), 4),
            "avg": round(sum(values) / len(values), 4),
        }

    def _make_key(self, name: str, labels: dict | None) -> str:
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._histograms.clear()
            self._gauges.clear()


metrics = Metrics()
