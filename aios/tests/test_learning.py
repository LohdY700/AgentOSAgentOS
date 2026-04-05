from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from aios_core.learning import LearningInbox


class LearningTests(unittest.TestCase):
    def test_add_and_list_recent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            inbox = LearningInbox(Path(td) / "learning.jsonl")
            inbox.add("https://example.com/a", "first")
            inbox.add("https://example.com/b", "second")
            rows = inbox.list_recent(limit=10)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[-1]["url"], "https://example.com/b")


if __name__ == "__main__":
    unittest.main()
