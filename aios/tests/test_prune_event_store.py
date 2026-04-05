from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from prune_event_store import prune_jsonl


class PruneEventStoreTests(unittest.TestCase):
    def test_prune_keeps_last_n(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "events.jsonl"
            p.write_text("a\nb\nc\nd\n", encoding="utf-8")

            out = prune_jsonl(p, keep_last=2)
            self.assertEqual(out["before"], 4)
            self.assertEqual(out["after"], 2)
            self.assertEqual(p.read_text(encoding="utf-8"), "c\nd\n")


if __name__ == "__main__":
    unittest.main()
