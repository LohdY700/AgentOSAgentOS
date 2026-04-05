from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from aios_core.bus import EventBus
from aios_core.guard import GuardConfig, ProcessGuard


class GuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_learning_mode_writes_candidates_file(self) -> None:
        bus = EventBus()
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "learn.txt"
            guard = ProcessGuard(
                GuardConfig(allowed=set(), mode="learning", learning_output=out),
                bus,
            )
            unknown = await guard.watch_once()
            await bus.stop()

            self.assertTrue(out.exists())
            content = out.read_text(encoding="utf-8")
            self.assertGreaterEqual(len(unknown), 1)
            self.assertTrue(len(content.strip()) > 0)


if __name__ == "__main__":
    unittest.main()
