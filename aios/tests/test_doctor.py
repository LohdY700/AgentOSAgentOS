from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aios_core.doctor import run_doctor


class DoctorTests(unittest.TestCase):
    def test_doctor_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            guard = root / "guard.json"
            store = root / "store.json"
            guard.write_text(json.dumps({"mode": "strict", "allowed": ["python3"]}), encoding="utf-8")
            store.write_text(
                json.dumps({"path": "data/events.jsonl", "max_lines": 10, "keep_last": 5, "prune_check_every": 2}),
                encoding="utf-8",
            )

            out = run_doctor(root, guard, store)
            self.assertTrue(out["ok"])


if __name__ == "__main__":
    unittest.main()
