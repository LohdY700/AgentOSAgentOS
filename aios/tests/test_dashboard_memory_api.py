from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

from http.server import ThreadingHTTPServer

from aios_core.dashboard import make_handler


class DashboardMemoryApiTests(unittest.TestCase):
    def _start_server(self, root: Path, guard: Path, store_cfg: Path) -> tuple[ThreadingHTTPServer, threading.Thread, int]:
        handler = make_handler(root, guard, store_cfg)
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        return server, t, int(server.server_address[1])

    def _request(self, port: int, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
        conn = HTTPConnection("127.0.0.1", port, timeout=5)
        raw = b""
        headers = {}
        if body is not None:
            raw = json.dumps(body).encode("utf-8")
            headers = {"Content-Type": "application/json", "Content-Length": str(len(raw))}
        conn.request(method, path, body=raw if raw else None, headers=headers)
        resp = conn.getresponse()
        payload = json.loads(resp.read().decode("utf-8"))
        conn.close()
        return resp.status, payload

    def test_memory_add_and_search_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "config").mkdir(parents=True, exist_ok=True)

            guard = root / "guard.json"
            store_cfg = root / "store.json"
            guard.write_text(json.dumps({"mode": "strict", "allowed": ["python3"]}), encoding="utf-8")
            store_cfg.write_text(json.dumps({"path": "data/events.jsonl"}), encoding="utf-8")
            (root / "config" / "memory-backend.json").write_text(
                json.dumps({"backend": "local", "fallback": "local", "local_path": "data/memory-local.jsonl"}),
                encoding="utf-8",
            )

            server, thread, port = self._start_server(root, guard, store_cfg)
            try:
                code_add, add_payload = self._request(
                    port,
                    "POST",
                    "/api/memory/add",
                    {"text": "sếp thích cafe đá", "metadata": {"kind": "preference"}},
                )
                self.assertEqual(code_add, 200)
                self.assertTrue(add_payload.get("ok"))
                self.assertEqual(add_payload.get("backend"), "local")

                code_search, search_payload = self._request(port, "GET", "/api/memory/search?q=cafe&limit=5&kind=preference")
                self.assertEqual(code_search, 200)
                self.assertTrue(search_payload.get("ok"))
                self.assertEqual(search_payload.get("backend"), "local")
                self.assertEqual(search_payload.get("filters", {}).get("kind"), "preference")
                items = search_payload.get("items", [])
                self.assertGreaterEqual(len(items), 1)
                self.assertIn("cafe", str(items[0].get("text", "")).lower())

                code_health, health_payload = self._request(port, "GET", "/api/memory/health")
                self.assertEqual(code_health, 200)
                self.assertTrue(health_payload.get("ok"))
                self.assertEqual(health_payload.get("active"), "local")

                code_auto, auto_payload = self._request(port, "GET", "/api/memory/search?q=s%E1%BA%BFp%20th%C3%ADch%20g%C3%AC&limit=5")
                self.assertEqual(code_auto, 200)
                self.assertTrue(auto_payload.get("ok"))
                self.assertTrue(auto_payload.get("auto_filter"))
                self.assertEqual(auto_payload.get("filters", {}).get("kind"), "preference")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_memory_add_requires_text(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "config").mkdir(parents=True, exist_ok=True)

            guard = root / "guard.json"
            store_cfg = root / "store.json"
            guard.write_text(json.dumps({"mode": "strict", "allowed": ["python3"]}), encoding="utf-8")
            store_cfg.write_text(json.dumps({"path": "data/events.jsonl"}), encoding="utf-8")
            (root / "config" / "memory-backend.json").write_text(
                json.dumps({"backend": "local", "fallback": "local", "local_path": "data/memory-local.jsonl"}),
                encoding="utf-8",
            )

            server, thread, port = self._start_server(root, guard, store_cfg)
            try:
                code_add, add_payload = self._request(port, "POST", "/api/memory/add", {"text": ""})
                self.assertEqual(code_add, 400)
                self.assertFalse(add_payload.get("ok"))
                self.assertIn("text is required", str(add_payload.get("error", "")))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
