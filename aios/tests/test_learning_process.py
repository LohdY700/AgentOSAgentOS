from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aios_core.learning import LearningInbox
from aios_core import learning_process


class LearningProcessTests(unittest.TestCase):
    def test_process_learning_inbox_writes_notes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inbox = LearningInbox(root / "data" / "learning-inbox.jsonl")
            inbox.add("https://example.com", "seed")

            def fake_fetch(url: str, max_chars: int = 700):
                return "Example Domain", "This domain is for use in illustrative examples"

            orig = learning_process.fetch_and_summarize
            learning_process.fetch_and_summarize = fake_fetch
            try:
                out = learning_process.process_learning_inbox(root, limit=5)
            finally:
                learning_process.fetch_and_summarize = orig

            self.assertTrue(out["ok"])
            self.assertEqual(out["written"], 1)

            notes = (root / "data" / "learning-notes.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(notes), 1)
            row = json.loads(notes[0])
            self.assertEqual(row["title"], "Example Domain")


if __name__ == "__main__":
    unittest.main()
