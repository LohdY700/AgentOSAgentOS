from __future__ import annotations

import unittest

from aios_core.conversation_quality import rubric_score, build_daily_rubric_review


class ConversationRubricTests(unittest.TestCase):
    def test_rubric_score_basic(self) -> None:
        text = "Dạ sếp, em đã làm xong ✅\n- Đã cập nhật Mission Control\n- Bước tiếp: chạy test"
        out = rubric_score(text)
        self.assertEqual(out["max"], 10)
        self.assertGreaterEqual(out["total"], 7)
        self.assertTrue(out["pass"])

    def test_daily_review_picks_low_scores(self) -> None:
        rows = [
            {"role": "assistant", "text": "ok", "created_at": "t1"},
            {"role": "assistant", "text": "Dạ sếp, em đã làm xong.\n- Đã xử lý\n- Bước tiếp theo...", "created_at": "t2"},
            {"role": "user", "text": "irrelevant", "created_at": "t3"},
        ]
        out = build_daily_rubric_review(rows, limit=1)
        self.assertTrue(out["ok"])
        self.assertEqual(len(out["items"]), 1)
        self.assertEqual(out["items"][0]["text"], "ok")


if __name__ == "__main__":
    unittest.main()
