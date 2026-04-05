from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aios_core.approval import classify_action, load_policy


class ApprovalTests(unittest.TestCase):
    def test_classify_actions(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "policy.json"
            p.write_text(
                json.dumps(
                    {
                        "tiers": {
                            "tier1_auto": {"actions": ["run_tests"]},
                            "tier2_owner": {"actions": ["sudo_command"]},
                        }
                    }
                ),
                encoding="utf-8",
            )
            policy = load_policy(p)

            d1 = classify_action("run_tests", policy)
            self.assertTrue(d1.auto_approved)
            self.assertEqual(d1.tier, "tier1_auto")

            d2 = classify_action("sudo_command", policy)
            self.assertFalse(d2.auto_approved)
            self.assertEqual(d2.tier, "tier2_owner")

            d3 = classify_action("unknown_action", policy)
            self.assertFalse(d3.auto_approved)
            self.assertEqual(d3.tier, "tier2_owner")


if __name__ == "__main__":
    unittest.main()
