from __future__ import annotations

import json
from pathlib import Path

from .guard import GuardConfig


def load_guard_config(path: str | Path) -> GuardConfig:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    allowed = set(data.get("allowed", []))
    poll_sec = float(data.get("poll_sec", 2.0))
    mode = str(data.get("mode", "strict")).lower()
    learning_output = data.get("learning_output")
    learning_path = Path(learning_output) if learning_output else None
    return GuardConfig(allowed=allowed, poll_sec=poll_sec, mode=mode, learning_output=learning_path)
