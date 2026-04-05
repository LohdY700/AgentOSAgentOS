from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .doctor import run_doctor
from .event_store import JsonlEventStore
from .store_config import load_event_store_config
from .approval import load_policy, classify_action


def _parse_iso(ts: str) -> datetime:
    # supports standard isoformat and trailing Z
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _agent_status(last_seen: datetime, now: datetime) -> str:
    age_sec = (now - last_seen).total_seconds()
    if age_sec <= 30:
        return "active"
    if age_sec <= 300:
        return "idle"
    return "down"


def build_snapshot(root_dir: Path, guard_config_path: Path, store_config_path: Path) -> dict[str, Any]:
    doctor = run_doctor(root_dir, guard_config_path, store_config_path)

    approval_cfg_path = root_dir / "config" / "approval-policy.json"
    approval_policy = load_policy(approval_cfg_path) if approval_cfg_path.exists() else {"tiers": {}}

    cfg = load_event_store_config(store_config_path)
    store_path = cfg.path if cfg.path.is_absolute() else root_dir / cfg.path
    store = JsonlEventStore(store_path, max_lines=cfg.max_lines, keep_last=cfg.keep_last, prune_check_every=cfg.prune_check_every)
    rows = list(store.replay())

    topics: dict[str, int] = {}
    recent: list[dict[str, Any]] = []
    agent_index: dict[str, dict[str, Any]] = {}
    now = datetime.now(timezone.utc)

    for topic, event in rows:
        topics[topic] = topics.get(topic, 0) + 1
        recent.append(
            {
                "topic": topic,
                "type": event.type,
                "source": event.source,
                "timestamp": event.timestamp,
                "payload": event.payload,
            }
        )

        src = event.source or "unknown"
        item = agent_index.setdefault(
            src,
            {
                "name": src,
                "events": 0,
                "last_type": None,
                "last_seen": None,
                "status": "down",
            },
        )
        item["events"] += 1
        item["last_type"] = event.type
        item["last_seen"] = event.timestamp

    # derive status
    for item in agent_index.values():
        last_seen_raw = item.get("last_seen")
        if last_seen_raw:
            last_seen = _parse_iso(str(last_seen_raw))
            item["status"] = _agent_status(last_seen, now)

    recent = recent[-20:]
    agents = sorted(agent_index.values(), key=lambda x: (x["status"], -int(x["events"])))

    t1 = approval_policy.get("tiers", {}).get("tier1_auto", {}).get("actions", [])
    t2 = approval_policy.get("tiers", {}).get("tier2_owner", {}).get("actions", [])

    return {
        "doctor": doctor,
        "approval": {
            "tier1_count": len(t1),
            "tier2_count": len(t2),
            "preapproval_enabled": bool(approval_policy.get("preapproval", {}).get("enabled", False)),
            "preapproval_max_minutes": int(approval_policy.get("preapproval", {}).get("maxWindowMinutes", 0)),
        },
        "store": {
            "path": str(store_path),
            "events": len(rows),
            "topics": topics,
            "recent": recent,
        },
        "agents": agents,
    }


def run_health_check(root_dir: Path, guard_config_path: Path, store_config_path: Path) -> dict[str, Any]:
    return run_doctor(root_dir, guard_config_path, store_config_path)


def run_benchmark_once(root_dir: Path, guard_config_path: Path, store_config_path: Path) -> dict[str, Any]:
    cmd = [
        sys.executable,
        "-m",
        "aios_core.cli",
        "--guard-config",
        str(guard_config_path),
        "--store-config",
        str(store_config_path),
        "benchmark",
    ]
    out = subprocess.check_output(cmd, cwd=str(root_dir), text=True)
    return json.loads(out.strip().splitlines()[-1])


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
            parsed = urlparse(self.path)
            if parsed.path == "/api/status":
                self._send_json(build_snapshot(root_dir, guard_config_path, store_config_path))
                return
            if parsed.path == "/api/approval/check":
                q = parse_qs(parsed.query)
                action = (q.get("action", [""])[0] or "").strip()
                if not action:
                    self._send_json({"ok": False, "error": "missing action query param"}, code=400)
                    return
                policy_path = root_dir / "config" / "approval-policy.json"
                policy = load_policy(policy_path) if policy_path.exists() else {"tiers": {}}
                decision = classify_action(action, policy)
                self._send_json(
                    {
                        "ok": True,
                        "action": decision.action,
                        "tier": decision.tier,
                        "auto_approved": decision.auto_approved,
                    }
                )
                return
            if parsed.path in ("/", "/index.html"):
                self._send_html(DASHBOARD_HTML)
                return
            self._send_json({"error": "not found"}, code=404)

        def do_POST(self):  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/api/run/doctor":
                self._send_json(run_health_check(root_dir, guard_config_path, store_config_path))
                return
            if parsed.path == "/api/run/benchmark":
                try:
                    self._send_json({"ok": True, "benchmark": run_benchmark_once(root_dir, guard_config_path, store_config_path)})
                except Exception as exc:  # noqa: BLE001
                    self._send_json({"ok": False, "error": str(exc)}, code=500)
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
    body { font-family: system-ui, sans-serif; margin: 24px; max-width: 980px; }
    .ok { color: #0a7d2c; font-weight: 700; }
    .bad { color: #b42318; font-weight: 700; }
    .card { border: 1px solid #ddd; border-radius: 12px; padding: 12px; margin: 10px 0; }
    pre { background: #f7f7f8; padding: 10px; border-radius: 8px; overflow:auto; }
    button { padding: 8px 12px; border-radius: 8px; border: 1px solid #ccc; background: #fff; cursor: pointer; }
    table { width: 100%; border-collapse: collapse; }
    th, td { text-align: left; padding: 8px; border-bottom: 1px solid #eee; font-size: 14px; }
    .pill { border-radius: 999px; padding: 2px 8px; font-size: 12px; font-weight: 700; display: inline-block; }
    .active { background:#e8f7ee; color:#0a7d2c; }
    .idle { background:#fff5e6; color:#9a6700; }
    .down { background:#fdecec; color:#b42318; }
  </style>
</head>
<body>
  <h1>AIOS Dashboard</h1>
  <p id='health'>Loading...</p>
  <button onclick='refresh()'>Refresh</button>
  <button onclick='runHealthCheck()'>Run Health Check</button>
  <button onclick='runBenchmark()'>Run Benchmark</button>
  <div id='action-result' style='margin-top:8px;color:#444;'></div>

  <div class='card'>
    <h3>Active Agents</h3>
    <table>
      <thead><tr><th>Agent</th><th>Status</th><th>Events</th><th>Last Event Type</th><th>Last Seen</th></tr></thead>
      <tbody id='agents'></tbody>
    </table>
  </div>

  <div class='card'>
    <h3>Approval Policy</h3>
    <div id='approval-brief'>Loading...</div>
  </div>

  <div class='card'>
    <h3>Store Summary</h3>
    <div id='store-brief'>Loading...</div>
    <button onclick='toggleStoreRaw()'>Xem chi tiết JSON</button>
    <pre id='store' style='display:none'></pre>
  </div>

  <div class='card'>
    <h3>Recent Events (last 20)</h3>
    <div id='recent-brief'>Loading...</div>
    <button onclick='toggleRecentRaw()'>Xem chi tiết JSON</button>
    <pre id='recent' style='display:none'></pre>
  </div>

<script>
function statusPill(s) {
  const c = (s === 'active') ? 'active' : (s === 'idle' ? 'idle' : 'down');
  return `<span class="pill ${c}">${s}</span>`;
}

function toggleStoreRaw() {
  const el = document.getElementById('store');
  el.style.display = (el.style.display === 'none') ? 'block' : 'none';
}

function toggleRecentRaw() {
  const el = document.getElementById('recent');
  el.style.display = (el.style.display === 'none') ? 'block' : 'none';
}

async function runHealthCheck() {
  const res = await fetch('/api/run/doctor', { method: 'POST' });
  const data = await res.json();
  document.getElementById('action-result').textContent = data.ok ? '✅ Health check OK' : '⚠️ Health check warning';
  await refresh();
}

async function runBenchmark() {
  const res = await fetch('/api/run/benchmark', { method: 'POST' });
  const data = await res.json();
  if (!data.ok) {
    document.getElementById('action-result').textContent = '⚠️ Benchmark failed: ' + (data.error || 'unknown');
    return;
  }
  const b = data.benchmark || {};
  document.getElementById('action-result').textContent = `✅ Benchmark done | p95: ${b.event_latency_p95} ms | throughput: ${b.event_throughput}`;
  await refresh();
}

async function refresh() {
  const res = await fetch('/api/status');
  const data = await res.json();
  const ok = data.doctor?.ok;
  const el = document.getElementById('health');
  el.className = ok ? 'ok' : 'bad';
  el.textContent = ok ? '✅ Healthy' : '⚠️ Warning';

  const tbody = document.getElementById('agents');
  tbody.innerHTML = '';
  for (const a of (data.agents || [])) {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${a.name}</td><td>${statusPill(a.status)}</td><td>${a.events}</td><td>${a.last_type || ''}</td><td>${a.last_seen || ''}</td>`;
    tbody.appendChild(tr);
  }

  const ap = data.approval || {};
  document.getElementById('approval-brief').textContent =
    `Tier1 auto: ${ap.tier1_count || 0} | Tier2 owner: ${ap.tier2_count || 0} | Pre-approval: ${ap.preapproval_enabled ? 'ON' : 'OFF'} (${ap.preapproval_max_minutes || 0}m)`;

  const storeSummary = {
    path: data.store.path,
    events: data.store.events,
    topics: data.store.topics,
  };
  document.getElementById('store-brief').textContent =
    `Events: ${data.store.events} | Topics: ${Object.keys(data.store.topics || {}).length}`;
  document.getElementById('store').textContent = JSON.stringify({
    ...storeSummary,
    checks: data.doctor.checks,
  }, null, 2);

  const recentCount = (data.store.recent || []).length;
  document.getElementById('recent-brief').textContent = `Hiển thị ${recentCount} events gần nhất`;
  document.getElementById('recent').textContent = JSON.stringify(data.store.recent, null, 2);
}
refresh();
</script>
</body>
</html>
"""
