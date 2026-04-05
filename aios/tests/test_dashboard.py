from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aios_core.dashboard import build_snapshot
from aios_core.events import Event
from aios_core.event_store import JsonlEventStore


class DashboardTests(unittest.TestCase):
    def test_build_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            guard = root / "guard.json"
            store_cfg = root / "store.json"
            guard.write_text(json.dumps({"mode": "strict", "allowed": ["python3"]}), encoding="utf-8")
            store_cfg.write_text(json.dumps({"path": "data/events.jsonl"}), encoding="utf-8")

            store = JsonlEventStore(root / "data" / "events.jsonl")
            store.append("system", Event.create("system.boot", "test", {"ok": True}))

            snap = build_snapshot(root, guard, store_cfg)
            self.assertTrue(snap["doctor"]["ok"])
            self.assertEqual(snap["store"]["events"], 1)
            self.assertGreaterEqual(len(snap["agents"]), 1)
            self.assertIn("status", snap["agents"][0])


if __name__ == "__main__":
    unittest.main()
