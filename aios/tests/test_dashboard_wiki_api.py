from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

from http.server import ThreadingHTTPServer

from aios_core.dashboard import make_handler


class DashboardWikiApiTests(unittest.TestCase):
    def _start_server(self, root: Path, guard: Path, store_cfg: Path):
        handler = make_handler(root, guard, store_cfg)
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        return server, t, int(server.server_address[1])

    def _request(self, port: int, method: str, path: str, body: dict | None = None):
        conn = HTTPConnection("127.0.0.1", port, timeout=5)
        headers = {}
        raw = b""
        if body is not None:
            raw = json.dumps(body).encode("utf-8")
            headers = {"Content-Type": "application/json", "Content-Length": str(len(raw))}
        conn.request(method, path, body=raw if raw else None, headers=headers)
        resp = conn.getresponse()
        data = json.loads(resp.read().decode("utf-8"))
        conn.close()
        return resp.status, data

    def test_wiki_ingest_api(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "config").mkdir(parents=True, exist_ok=True)
            (root / "config" / "wiki-pipeline.json").write_text(
                '{"wiki_dir":"wiki","inbox_path":"data/wiki-inbox.jsonl","index_path":"data/wiki-index.json"}',
                encoding="utf-8",
            )
            guard = root / "guard.json"
            store_cfg = root / "store.json"
            guard.write_text(json.dumps({"mode": "strict", "allowed": ["python3"]}), encoding="utf-8")
            store_cfg.write_text(json.dumps({"path": "data/events.jsonl"}), encoding="utf-8")

            server, thread, port = self._start_server(root, guard, store_cfg)
            try:
                code, payload = self._request(port, "POST", "/api/wiki/ingest", {
                    "title": "Tam Cam",
                    "content": "Noi dung truyen",
                    "tags": "fairy,vn"
                })
                self.assertEqual(code, 200)
                self.assertTrue(payload.get("ok"))
                self.assertIn("wiki/tam-cam.md", str(payload.get("path", "")))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
