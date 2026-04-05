from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from aios_core.event_store import JsonlEventStore
from aios_core.events import Event


class EventStoreTests(unittest.TestCase):
    def test_append_and_replay(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = JsonlEventStore(Path(td) / "events.jsonl")
            e1 = Event.create("system.boot", "test", {"ok": True})
            e2 = Event.create("security.process.anomaly", "test", {"process": "x"})
            store.append("system", e1)
            store.append("security", e2)

            rows = list(store.replay())
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0][0], "system")
            self.assertEqual(rows[1][0], "security")

    def test_auto_prune_when_exceeding_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "events.jsonl"
            store = JsonlEventStore(p, max_lines=5, keep_last=3, prune_check_every=1)

            for i in range(7):
                store.append("system", Event.create("tick", "test", {"i": i}))

            lines = p.read_text(encoding="utf-8").splitlines()
            self.assertLessEqual(len(lines), 5)
            rows = list(store.replay())
            self.assertLessEqual(len(rows), 5)


if __name__ == "__main__":
    unittest.main()
