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


if __name__ == "__main__":
    unittest.main()
