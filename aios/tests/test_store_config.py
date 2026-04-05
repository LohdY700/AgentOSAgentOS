from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aios_core.store_config import load_event_store_config


class StoreConfigTests(unittest.TestCase):
    def test_load_event_store_config(self) -> None:
        payload = {
            "path": "data/custom-events.jsonl",
            "max_lines": 777,
            "keep_last": 111,
            "prune_check_every": 33,
        }
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "store.json"
            p.write_text(json.dumps(payload), encoding="utf-8")
            cfg = load_event_store_config(p)

            self.assertEqual(str(cfg.path), "data/custom-events.jsonl")
            self.assertEqual(cfg.max_lines, 777)
            self.assertEqual(cfg.keep_last, 111)
            self.assertEqual(cfg.prune_check_every, 33)


if __name__ == "__main__":
    unittest.main()
