from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from aios_core.wiki_pipeline import wiki_ingest, wiki_build_index, wiki_export_slide, wiki_search, wiki_answer


class WikiPipelineTests(unittest.TestCase):
    def test_ingest_index_slide(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "config").mkdir(parents=True, exist_ok=True)
            (root / "config" / "wiki-pipeline.json").write_text(
                '{"wiki_dir":"wiki","inbox_path":"data/wiki-inbox.jsonl","index_path":"data/wiki-index.json"}',
                encoding="utf-8",
            )

            a = wiki_ingest(root, title="My Story", content="Hello wiki", tags=["story"])
            self.assertTrue(a.get("ok"))

            b = wiki_build_index(root)
            self.assertTrue(b.get("ok"))
            self.assertEqual(b.get("count"), 1)

            c = wiki_export_slide(root, slug="my-story")
            self.assertTrue(c.get("ok"))
            self.assertIn("slides", c.get("path", ""))

            s = wiki_search(root, query="hello", limit=3)
            self.assertTrue(s.get("ok"))
            self.assertGreaterEqual(len(s.get("items", [])), 1)

            qa = wiki_answer(root, question="hello", limit=2)
            self.assertTrue(qa.get("ok"))
            self.assertIn("-", str(qa.get("answer", "")))


if __name__ == "__main__":
    unittest.main()
