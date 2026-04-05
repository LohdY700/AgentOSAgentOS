from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aios_core.doctor import run_doctor, doctor_exit_code


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
            names = {str(c.get("name")) for c in out.get("checks", [])}
            self.assertIn("memory_backend", names)
            self.assertIn("memory_rw", names)
            self.assertEqual(doctor_exit_code(root, guard, store), 0)

    def test_doctor_exit_code_nonzero_on_bad_config(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            guard = root / "guard.json"
            store = root / "store.json"
            guard.write_text("{bad-json", encoding="utf-8")
            store.write_text(json.dumps({"path": "data/events.jsonl"}), encoding="utf-8")

            self.assertEqual(doctor_exit_code(root, guard, store), 1)


if __name__ == "__main__":
    unittest.main()
