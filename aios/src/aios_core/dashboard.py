from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .doctor import run_doctor
from .event_store import JsonlEventStore
from .store_config import load_event_store_config


def build_snapshot(root_dir: Path, guard_config_path: Path, store_config_path: Path) -> dict[str, Any]:
    doctor = run_doctor(root_dir, guard_config_path, store_config_path)

    cfg = load_event_store_config(store_config_path)
    store_path = cfg.path if cfg.path.is_absolute() else root_dir / cfg.path
    store = JsonlEventStore(store_path, max_lines=cfg.max_lines, keep_last=cfg.keep_last, prune_check_every=cfg.prune_check_every)
    rows = list(store.replay())

    topics: dict[str, int] = {}
    recent: list[dict[str, Any]] = []
    for topic, event in rows:
        topics[topic] = topics.get(topic, 0) + 1
        recent.append({
            "topic": topic,
            "type": event.type,
            "source": event.source,
            "timestamp": event.timestamp,
            "payload": event.payload,
        })

    recent = recent[-20:]

    return {
        "doctor": doctor,
        "store": {
            "path": str(store_path),
            "events": len(rows),
            "topics": topics,
            "recent": recent,
        },
    }


def make_handler(root_dir: Path, guard_config_path: Path, store_config_path: Path):
    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, payload: dict[str, Any], code: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, html: str) -> None:
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802
            if self.path == "/api/status":
                self._send_json(build_snapshot(root_dir, guard_config_path, store_config_path))
                return
            if self.path in ("/", "/index.html"):
                self._send_html(DASHBOARD_HTML)
                return
            self._send_json({"error": "not found"}, code=404)

        def log_message(self, fmt: str, *args):
            return

    return Handler


def run_dashboard(host: str, port: int, root_dir: Path, guard_config_path: Path, store_config_path: Path) -> None:
    server = ThreadingHTTPServer((host, port), make_handler(root_dir, guard_config_path, store_config_path))
    print(f"AIOS dashboard running at http://{host}:{port}")
    server.serve_forever()


DASHBOARD_HTML = """<!doctype html>
<html>
<head>
  <meta charset='utf-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1' />
  <title>AIOS Dashboard</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 24px; max-width: 900px; }
    .ok { color: #0a7d2c; font-weight: 700; }
    .bad { color: #b42318; font-weight: 700; }
    .card { border: 1px solid #ddd; border-radius: 12px; padding: 12px; margin: 10px 0; }
    pre { background: #f7f7f8; padding: 10px; border-radius: 8px; overflow:auto; }
    button { padding: 8px 12px; border-radius: 8px; border: 1px solid #ccc; background: #fff; cursor: pointer; }
  </style>
</head>
<body>
  <h1>AIOS Dashboard</h1>
  <p id='health'>Loading...</p>
  <button onclick='refresh()'>Refresh</button>

  <div class='card'>
    <h3>Store Summary</h3>
    <pre id='store'></pre>
  </div>

  <div class='card'>
    <h3>Recent Events (last 20)</h3>
    <pre id='recent'></pre>
  </div>

<script>
async function refresh() {
  const res = await fetch('/api/status');
  const data = await res.json();
  const ok = data.doctor?.ok;
  const el = document.getElementById('health');
  el.className = ok ? 'ok' : 'bad';
  el.textContent = ok ? '✅ Healthy' : '⚠️ Warning';

  document.getElementById('store').textContent = JSON.stringify({
    path: data.store.path,
    events: data.store.events,
    topics: data.store.topics,
    checks: data.doctor.checks,
  }, null, 2);

  document.getElementById('recent').textContent = JSON.stringify(data.store.recent, null, 2);
}
refresh();
</script>
</body>
</html>
"""
