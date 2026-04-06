from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

from http.server import ThreadingHTTPServer

from aios_core.dashboard import make_handler


class DashboardMissionApiTests(unittest.TestCase):
    def _start_server(self, root: Path, guard: Path, store_cfg: Path) -> tuple[ThreadingHTTPServer, threading.Thread, int]:
        handler = make_handler(root, guard, store_cfg)
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        return server, t, int(server.server_address[1])

    def _request(self, port: int, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
        conn = HTTPConnection("127.0.0.1", port, timeout=5)
        headers = {}
        raw = b""
        if body is not None:
            raw = json.dumps(body).encode("utf-8")
            headers = {"Content-Type": "application/json", "Content-Length": str(len(raw))}
        conn.request(method, path, body=raw if raw else None, headers=headers)
        resp = conn.getresponse()
        payload = json.loads(resp.read().decode("utf-8"))
        conn.close()
        return resp.status, payload

    def test_mission_status_and_note(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            guard = root / "guard.json"
            store_cfg = root / "store.json"
            guard.write_text(json.dumps({"mode": "strict", "allowed": ["python3"]}), encoding="utf-8")
            store_cfg.write_text(json.dumps({"path": "data/events.jsonl"}), encoding="utf-8")

            server, thread, port = self._start_server(root, guard, store_cfg)
            try:
                code, payload = self._request(port, "GET", "/api/mission/status")
                self.assertEqual(code, 200)
                self.assertTrue(payload.get("ok"))
                self.assertIn("state", payload)
                self.assertIn("team", payload.get("state", {}))

                code2, payload2 = self._request(port, "POST", "/api/mission/note", {"note": "đã chốt sprint"})
                self.assertEqual(code2, 200)
                self.assertTrue(payload2.get("ok"))

                _, payload3 = self._request(port, "GET", "/api/mission/status")
                notes = payload3.get("state", {}).get("notes", [])
                self.assertGreaterEqual(len(notes), 1)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
