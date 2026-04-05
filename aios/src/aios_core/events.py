from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any
import json
import uuid


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class Event:
    id: str
    type: str
    source: str
    timestamp: str
    payload: dict[str, Any]
    trace_id: str

    @classmethod
    def create(cls, event_type: str, source: str, payload: dict[str, Any], trace_id: str | None = None) -> "Event":
        return cls(
            id=str(uuid.uuid4()),
            type=event_type,
            source=source,
            timestamp=utc_now_iso(),
            payload=payload,
            trace_id=trace_id or str(uuid.uuid4()),
        )

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)
