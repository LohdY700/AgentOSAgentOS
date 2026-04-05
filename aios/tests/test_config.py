from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aios_core.config import load_guard_config


class ConfigTests(unittest.TestCase):
    def test_load_guard_config(self) -> None:
        payload = {"allowed": ["python3", "bash"], "poll_sec": 1.5}
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "guard.json"
            p.write_text(json.dumps(payload), encoding="utf-8")

            cfg = load_guard_config(p)
            self.assertEqual(cfg.allowed, {"python3", "bash"})
            self.assertEqual(cfg.poll_sec, 1.5)


if __name__ == "__main__":
    unittest.main()
