from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aios_core.second_brain import index_second_brain, search_second_brain


class SecondBrainTests(unittest.TestCase):
    def test_index_and_search_local_vault(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "config").mkdir(parents=True, exist_ok=True)
            vault = root / "vault"
            vault.mkdir(parents=True, exist_ok=True)
            (vault / "note1.md").write_text("# RAG\nSu dung metadata filter cho retriever", encoding="utf-8")
            (vault / "note2.md").write_text("# Obsidian\nSecond brain local index", encoding="utf-8")

            (root / "config" / "second-brain.json").write_text(
                json.dumps(
                    {
                        "vault_path": "vault",
                        "patterns": ["**/*.md"],
                        "max_chunk_chars": 600,
                        "min_chunk_chars": 20,
                        "push_to_memory_backend": False,
                        "index_path": "data/second-brain-index.jsonl",
                    }
                ),
                encoding="utf-8",
            )

            out = index_second_brain(root)
            self.assertTrue(out.get("ok"))
            self.assertEqual(out.get("files"), 2)
            self.assertGreaterEqual(int(out.get("chunks", 0)), 2)

            s = search_second_brain(root, query="metadata", limit=5)
            self.assertTrue(s.get("ok"))
            items = s.get("items", [])
            self.assertGreaterEqual(len(items), 1)
            self.assertIn("metadata", str(items[0].get("text", "")).lower())


if __name__ == "__main__":
    unittest.main()
