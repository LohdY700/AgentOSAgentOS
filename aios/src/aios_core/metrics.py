from __future__ import annotations

from dataclasses import dataclass, field
from statistics import quantiles


@dataclass(slots=True)
class Metrics:
    event_throughput: int = 0
    agent_restart_count: int = 0
    guard_alert_count: int = 0
    memory_idle_mb: float = 0.0
    _event_latencies_ms: list[float] = field(default_factory=list)

    def record_event_latency(self, latency_ms: float) -> None:
        self.event_throughput += 1
        self._event_latencies_ms.append(latency_ms)

    @property
    def event_latency_p95(self) -> float:
        if not self._event_latencies_ms:
            return 0.0
        if len(self._event_latencies_ms) == 1:
            return self._event_latencies_ms[0]
        # n=100 quantiles -> index 94 == p95 cutoff bucket end
        return quantiles(self._event_latencies_ms, n=100)[94]

    def snapshot(self) -> dict[str, float | int]:
        return {
            "event_throughput": self.event_throughput,
            "event_latency_p95": round(self.event_latency_p95, 2),
            "agent_restart_count": self.agent_restart_count,
            "guard_alert_count": self.guard_alert_count,
            "memory_idle_mb": round(self.memory_idle_mb, 2),
        }
