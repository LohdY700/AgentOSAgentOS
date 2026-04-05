from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from aios_core.conversation_quality import FeedbackStore, quality_summary


class ConversationQualityTests(unittest.TestCase):
    def test_feedback_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = FeedbackStore(Path(td) / "feedback.jsonl")
            store.add("good", "nice")
            store.add("bad", "too long")
            rows = store.list_recent()
            self.assertEqual(len(rows), 2)
            s = quality_summary(rows)
            self.assertEqual(s["total"], 2)
            self.assertEqual(s["good"], 1)
            self.assertEqual(s["bad"], 1)
            self.assertEqual(s["score"], 50.0)


if __name__ == "__main__":
    unittest.main()
