from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from aios_core.conversation_data import ChatExampleStore


class ConversationDataTests(unittest.TestCase):
    def test_add_and_list_recent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = ChatExampleStore(Path(td) / "chat.jsonl")
            store.add("user", "hello")
            store.add("assistant", "hi")
            rows = store.list_recent(limit=10)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[-1]["role"], "assistant")


if __name__ == "__main__":
    unittest.main()
