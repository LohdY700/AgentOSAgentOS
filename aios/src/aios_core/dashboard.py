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
from .learning import LearningInbox
from .learning_process import process_learning_inbox
from .conversation_data import ChatExampleStore
from .conversation_quality import FeedbackStore, quality_summary
from .memory_backend import load_memory_backend


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

    learning = LearningInbox(root_dir / "data" / "learning-inbox.jsonl")
    learning_recent = learning.list_recent(limit=10)

    notes_path = root_dir / "data" / "learning-notes.jsonl"
    notes_recent: list[dict[str, Any]] = []
    if notes_path.exists():
        for line in notes_path.read_text(encoding="utf-8").splitlines()[-20:]:
            if not line.strip():
                continue
            try:
                notes_recent.append(json.loads(line))
            except Exception:
                pass

    insights: list[str] = []
    for row in reversed(notes_recent):
        title = str(row.get("title", "")).strip()
        summary = str(row.get("summary", "")).strip()
        if title and title not in insights:
            insights.append(title)
        elif summary:
            insights.append(summary[:90])
        if len(insights) >= 3:
            break

    chat_store = ChatExampleStore(root_dir / "data" / "chat-examples.jsonl")
    chat_recent = chat_store.list_recent(limit=10)

    feedback_store = FeedbackStore(root_dir / "data" / "conversation-feedback.jsonl")
    feedback_recent = feedback_store.list_recent(limit=100)
    feedback_stat = quality_summary(feedback_recent)

    mem = load_memory_backend(root_dir)

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
        "learning": {
            "count": len(learning_recent),
            "recent": learning_recent,
            "notes_count": len(notes_recent),
            "notes_recent": notes_recent,
            "insights": insights,
        },
        "conversation": {
            "examples_count": len(chat_recent),
            "recent": chat_recent,
            "feedback": feedback_stat,
        },
        "memory_backend": {
            "requested": mem.requested,
            "active": mem.active,
            "fallback_used": mem.fallback_used,
            "note": mem.note,
        },
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
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, html: str) -> None:
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Pragma", "no-cache")
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
            if parsed.path == "/api/learn/list":
                q = parse_qs(parsed.query)
                limit = int((q.get("limit", ["20"])[0] or "20"))
                inbox = LearningInbox(root_dir / "data" / "learning-inbox.jsonl")
                self._send_json({"ok": True, "items": inbox.list_recent(limit=limit)})
                return
            if parsed.path == "/api/chat-examples/list":
                q = parse_qs(parsed.query)
                limit = int((q.get("limit", ["20"])[0] or "20"))
                store = ChatExampleStore(root_dir / "data" / "chat-examples.jsonl")
                self._send_json({"ok": True, "items": store.list_recent(limit=limit)})
                return
            if parsed.path == "/api/conversation/quality":
                store = FeedbackStore(root_dir / "data" / "conversation-feedback.jsonl")
                rows = store.list_recent(limit=200)
                self._send_json({"ok": True, "summary": quality_summary(rows), "recent": rows[-20:]})
                return
            if parsed.path == "/api/memory/search":
                q = parse_qs(parsed.query)
                query = str((q.get("q", [""])[0] or "")).strip()
                limit = int((q.get("limit", ["5"])[0] or "5"))
                if not query:
                    self._send_json({"ok": False, "error": "missing q"}, code=400)
                    return
                mem = load_memory_backend(root_dir)
                self._send_json({"ok": True, "backend": mem.active, "items": mem.backend.search(query, limit=limit)})
                return
            if parsed.path == "/app.js":
                self.send_response(200)
                self.send_header("Content-Type", "application/javascript; charset=utf-8")
                self.send_header("Cache-Control", "no-store, max-age=0")
                self.send_header("Pragma", "no-cache")
                body = DASHBOARD_JS.encode("utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
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
            if parsed.path == "/api/learn/add":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                    body = json.loads(raw)
                    url = str(body.get("url", "")).strip()
                    note = str(body.get("note", "")).strip()
                    if not url:
                        self._send_json({"ok": False, "error": "url is required"}, code=400)
                        return
                    inbox = LearningInbox(root_dir / "data" / "learning-inbox.jsonl")
                    item = inbox.add(url, note)
                    self._send_json({"ok": True, "item": {"url": item.url, "note": item.note, "created_at": item.created_at}})
                except Exception as exc:  # noqa: BLE001
                    self._send_json({"ok": False, "error": str(exc)}, code=500)
                return
            if parsed.path == "/api/learn/process":
                try:
                    self._send_json(process_learning_inbox(root_dir, limit=5))
                except Exception as exc:  # noqa: BLE001
                    self._send_json({"ok": False, "error": str(exc)}, code=500)
                return
            if parsed.path == "/api/chat-examples/add":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                    body = json.loads(raw)
                    role = str(body.get("role", "assistant")).strip()
                    text = str(body.get("text", "")).strip()
                    if role not in ("user", "assistant"):
                        self._send_json({"ok": False, "error": "role must be user|assistant"}, code=400)
                        return
                    if not text:
                        self._send_json({"ok": False, "error": "text is required"}, code=400)
                        return
                    store = ChatExampleStore(root_dir / "data" / "chat-examples.jsonl")
                    ex = store.add(role, text)
                    mem = load_memory_backend(root_dir)
                    mem.backend.add(text=ex.text, metadata={"kind": "chat_example", "role": ex.role})
                    self._send_json({"ok": True, "item": {"role": ex.role, "text": ex.text, "created_at": ex.created_at}, "memory_backend": mem.active})
                except Exception as exc:  # noqa: BLE001
                    self._send_json({"ok": False, "error": str(exc)}, code=500)
                return
            if parsed.path == "/api/conversation/feedback":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                    body = json.loads(raw)
                    label = str(body.get("label", "")).strip().lower()
                    note = str(body.get("note", "")).strip()
                    store = FeedbackStore(root_dir / "data" / "conversation-feedback.jsonl")
                    fb = store.add(label, note)
                    self._send_json({"ok": True, "item": {"label": fb.label, "note": fb.note, "created_at": fb.created_at}})
                except Exception as exc:  # noqa: BLE001
                    self._send_json({"ok": False, "error": str(exc)}, code=500)
                return
            if parsed.path == "/api/memory/add":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                    body = json.loads(raw)
                    text = str(body.get("text", "")).strip()
                    metadata = body.get("metadata", {}) or {}
                    if not text:
                        self._send_json({"ok": False, "error": "text is required"}, code=400)
                        return
                    mem = load_memory_backend(root_dir)
                    mem.backend.add(text=text, metadata=metadata)
                    self._send_json({"ok": True, "backend": mem.active})
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
    .life-wrap { display:flex; gap:14px; align-items:center; flex-wrap:wrap; }
    canvas#life-canvas { background:#0b1220; border-radius:12px; border:1px solid #1f2a44; }
    .life-note { font-size:14px; color:#444; }
  </style>
</head>
<body>
  <h1>AIOS Dashboard</h1>
  <p id='health'>Loading...</p>
  <button onclick='refresh()'>Refresh</button>
  <button onclick='runHealthCheck()'>Run Health Check</button>
  <button onclick='runBenchmark()'>Run Benchmark</button>
  <button onclick='copyPublicStatus()'>Copy Public Status</button>
  <div id='action-result' style='margin-top:8px;color:#444;'></div>

  <div class='card'>
    <h3>What to do now</h3>
    <ul id='next-steps'>
      <li>Đang tải gợi ý...</li>
    </ul>
  </div>

  <div class='card'>
    <h3>Chat Training Examples</h3>
    <div style='display:flex;gap:8px;flex-wrap:wrap'>
      <select id='chat-role' style='padding:8px;border:1px solid #ddd;border-radius:8px;'>
        <option value='user'>user</option>
        <option value='assistant' selected>assistant</option>
      </select>
      <input id='chat-text' placeholder='Ví dụ câu hội thoại...' style='flex:1;min-width:320px;padding:8px;border:1px solid #ddd;border-radius:8px;' />
      <button onclick='addChatExample()'>Add Chat Example</button>
    </div>
    <div style='display:flex;gap:8px;margin-top:8px;'>
      <button onclick="sendConversationFeedback('good')">👍 Good</button>
      <button onclick="sendConversationFeedback('bad')">👎 Bad</button>
      <input id='feedback-note' placeholder='ghi chú ngắn (tuỳ chọn)' style='flex:1;min-width:220px;padding:8px;border:1px solid #ddd;border-radius:8px;' />
    </div>
    <div id='chat-result' style='margin-top:8px;color:#444;'></div>
    <div id='chat-brief' style='margin-top:8px;color:#444;'>Đang tải...</div>
    <div id='chat-quality' style='margin-top:6px;color:#444;'>Quality: đang tải...</div>
  </div>

  <div class='card'>
    <h3>Learning Inbox</h3>
    <div style='display:flex;gap:8px;flex-wrap:wrap'>
      <input id='learn-url' placeholder='Dán link để AIOS học' style='flex:1;min-width:280px;padding:8px;border:1px solid #ddd;border-radius:8px;' />
      <input id='learn-note' placeholder='Ghi chú (tuỳ chọn)' style='flex:1;min-width:220px;padding:8px;border:1px solid #ddd;border-radius:8px;' />
      <button onclick='addLearningLink()'>Add Link</button>
      <button onclick='processLearningNow()'>Learn Now</button>
    </div>
    <div id='learn-result' style='margin-top:8px;color:#444;'></div>
    <div id='learn-brief' style='margin-top:8px;color:#444;'>Đang tải...</div>
    <div style='margin-top:8px;'><b>Top 3 insights hôm nay</b></div>
    <ul id='learn-insights'>
      <li>Đang tổng hợp insight...</li>
    </ul>
  </div>

  <div class='card'>
    <h3>AIOS Life Pulse</h3>
    <div class='life-wrap'>
      <canvas id='life-canvas' width='320' height='180'></canvas>
      <div>
        <div id='life-stage'><b>Stage:</b> head-only</div>
        <div id='life-length'><b>Length:</b> 1</div>
        <div class='life-note'>Chú rắn sẽ dài ra theo số event tích lũy — càng học, càng lớn.</div>
      </div>
    </div>
  </div>

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
    <h3>Memory Backend</h3>
    <div id='memory-brief'>Loading...</div>
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

<script src='/app.js'></script>

</body>
</html>
"""


DASHBOARD_JS = """
function statusPill(s) {
  const c = (s === 'active') ? 'active' : (s === 'idle' ? 'idle' : 'down');
  return '<span class="pill ' + c + '">' + s + '</span>';
}

function toggleStoreRaw() {
  const el = document.getElementById('store');
  el.style.display = (el.style.display === 'none') ? 'block' : 'none';
}

function toggleRecentRaw() {
  const el = document.getElementById('recent');
  el.style.display = (el.style.display === 'none') ? 'block' : 'none';
}

const life = { angle: 0, targetLen: 1, currentLen: 1 };
let lastSnapshot = null;

function drawLife() {
  const canvas = document.getElementById('life-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const w = canvas.width, h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  // tiny world
  ctx.fillStyle = '#111a2e';
  ctx.fillRect(0, 0, w, h);
  ctx.strokeStyle = '#20304f';
  ctx.beginPath();
  ctx.arc(w/2, h/2, 62, 0, Math.PI * 2);
  ctx.stroke();

  life.currentLen += (life.targetLen - life.currentLen) * 0.08;
  const segs = Math.max(1, Math.round(life.currentLen));
  const radius = 62;

  for (let i = segs - 1; i >= 0; i--) {
    const a = life.angle - i * 0.22;
    const x = w/2 + Math.cos(a) * radius;
    const y = h/2 + Math.sin(a) * radius;
    const r = (i === 0) ? 8 : 6;
    ctx.fillStyle = (i === 0) ? '#7ee787' : '#3fb950';
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
  }

  life.angle += 0.03;
  requestAnimationFrame(drawLife);
}

function updateLifeMeta(eventCount) {
  // every 100 events grows 1 segment, cap at 24 for readability
  const seg = Math.min(24, 1 + Math.floor((eventCount || 0) / 100));
  life.targetLen = seg;
  const stage = seg <= 2 ? 'head-only' : (seg <= 8 ? 'growing' : 'evolved');
  document.getElementById('life-stage').innerHTML = '<b>Stage:</b> ' + stage;
  document.getElementById('life-length').innerHTML = '<b>Length:</b> ' + seg;
}

function renderNextSteps(data) {
  const steps = [];
  const ok = !!(data && data.doctor && data.doctor.ok);
  const guardAlerts = Number((data && data.store && data.store.topics && data.store.topics.security) || 0);
  const totalEvents = Number((data && data.store && data.store.events) || 0);

  if (ok) {
    steps.push('✅ Hệ thống đang ổn định.');
  } else {
    steps.push('⚠️ Hệ thống có cảnh báo, nên bấm Run Health Check.');
  }

  if (guardAlerts > 0) {
    steps.push('🔎 Có ' + guardAlerts + ' security events, nên xem mục Recent Events.');
  } else {
    steps.push('🛡️ Chưa thấy cảnh báo security mới.');
  }

  if (totalEvents < 100) {
    steps.push('📈 Chạy Run Benchmark để tạo thêm tín hiệu theo dõi.');
  } else {
    steps.push('🌱 AIOS đang tích lũy dữ liệu tốt, có thể tiếp tục theo dõi theo ngày.');
  }

  const ul = document.getElementById('next-steps');
  ul.innerHTML = '';
  for (const s of steps) {
    const li = document.createElement('li');
    li.textContent = s;
    ul.appendChild(li);
  }
}

function buildPublicStatusText(data) {
  const ok = !!(data && data.doctor && data.doctor.ok);
  const events = Number((data && data.store && data.store.events) || 0);
  const security = Number((data && data.store && data.store.topics && data.store.topics.security) || 0);
  const agents = ((data && data.agents) || []).length;
  return [
    'AIOS Status Snapshot',
    '- Health: ' + (ok ? 'Healthy' : 'Warning'),
    '- Active Agents tracked: ' + agents,
    '- Total events: ' + events,
    '- Security events: ' + security,
    '- Time: ' + new Date().toLocaleString(),
  ].join('\\n');
}

async function copyPublicStatus() {
  if (!lastSnapshot) {
    document.getElementById('action-result').textContent = '⚠️ Chưa có dữ liệu, bấm Refresh trước.';
    return;
  }
  const text = buildPublicStatusText(lastSnapshot);
  try {
    await navigator.clipboard.writeText(text);
    document.getElementById('action-result').textContent = '✅ Đã copy status tóm tắt.';
  } catch {
    document.getElementById('action-result').textContent = '⚠️ Copy thất bại, trình duyệt chặn clipboard.';
  }
}

async function addChatExample() {
  const role = document.getElementById('chat-role').value;
  const textEl = document.getElementById('chat-text');
  const text = (textEl.value || '').trim();
  if (!text) {
    document.getElementById('chat-result').textContent = '⚠️ Vui lòng nhập nội dung hội thoại.';
    return;
  }
  const res = await fetch('/api/chat-examples/add', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role: role, text: text })
  });
  const data = await res.json();
  if (!data.ok) {
    document.getElementById('chat-result').textContent = '⚠️ Add thất bại: ' + (data.error || 'unknown');
    return;
  }
  document.getElementById('chat-result').textContent = '✅ Đã thêm chat example.';
  textEl.value = '';
  await refresh();
}

async function sendConversationFeedback(label) {
  const noteEl = document.getElementById('feedback-note');
  const note = (noteEl.value || '').trim();
  const res = await fetch('/api/conversation/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ label: label, note: note })
  });
  const data = await res.json();
  if (!data.ok) {
    document.getElementById('chat-result').textContent = '⚠️ Feedback lỗi: ' + (data.error || 'unknown');
    return;
  }
  document.getElementById('chat-result').textContent = '✅ Đã ghi feedback ' + label + '.';
  noteEl.value = '';
  await refresh();
}

async function addLearningLink() {
  const urlEl = document.getElementById('learn-url');
  const noteEl = document.getElementById('learn-note');
  const url = (urlEl.value || '').trim();
  const note = (noteEl.value || '').trim();
  if (!url) {
    document.getElementById('learn-result').textContent = '⚠️ Vui lòng nhập URL.';
    return;
  }
  const res = await fetch('/api/learn/add', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url: url, note: note })
  });
  const data = await res.json();
  if (!data.ok) {
    document.getElementById('learn-result').textContent = '⚠️ Add thất bại: ' + (data.error || 'unknown');
    return;
  }
  document.getElementById('learn-result').textContent = '✅ Đã thêm link vào Learning Inbox.';
  urlEl.value = '';
  noteEl.value = '';
  await refresh();
}

async function processLearningNow() {
  const res = await fetch('/api/learn/process', { method: 'POST' });
  const data = await res.json();
  if (!data.ok) {
    document.getElementById('learn-result').textContent = '⚠️ Learn failed: ' + (data.error || 'unknown');
    return;
  }
  document.getElementById('learn-result').textContent = '✅ Learn done | processed: ' + data.processed + ' | written: ' + data.written;
  await refresh();
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
  document.getElementById('action-result').textContent = '✅ Benchmark done | p95: ' + b.event_latency_p95 + ' ms | throughput: ' + b.event_throughput;
  await refresh();
}

async function refresh() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    lastSnapshot = data;
    renderNextSteps(data);
    const ok = !!(data && data.doctor && data.doctor.ok);
  updateLifeMeta((data && data.store && data.store.events) || 0);
  const el = document.getElementById('health');
  el.className = ok ? 'ok' : 'bad';
  el.textContent = ok ? '✅ Healthy' : '⚠️ Warning';

  const tbody = document.getElementById('agents');
  tbody.innerHTML = '';
  for (const a of (data.agents || [])) {
    const tr = document.createElement('tr');
    tr.innerHTML = '<td>' + a.name + '</td><td>' + statusPill(a.status) + '</td><td>' + a.events + '</td><td>' + (a.last_type || '') + '</td><td>' + (a.last_seen || '') + '</td>';
    tbody.appendChild(tr);
  }

  const ap = data.approval || {};
  document.getElementById('approval-brief').textContent =
    'Tier1 auto: ' + (ap.tier1_count || 0) + ' | Tier2 owner: ' + (ap.tier2_count || 0) + ' | Pre-approval: ' + (ap.preapproval_enabled ? 'ON' : 'OFF') + ' (' + (ap.preapproval_max_minutes || 0) + 'm)';

  const mb = data.memory_backend || {};
  document.getElementById('memory-brief').textContent =
    'Requested: ' + (mb.requested || 'local') + ' | Active: ' + (mb.active || 'local') + (mb.fallback_used ? ' (fallback)' : '') + (mb.note ? ' | Note: ' + mb.note : '');

  const convo = data.conversation || {};
  const cr = convo.recent || [];
  const lastChat = cr.length ? (cr[cr.length - 1].role + ': ' + cr[cr.length - 1].text.slice(0, 60)) : 'chưa có ví dụ';
  document.getElementById('chat-brief').textContent = 'Examples: ' + (convo.examples_count || 0) + ' | Mới nhất: ' + lastChat;
  const fb = convo.feedback || {};
  document.getElementById('chat-quality').textContent = 'Quality score: ' + (fb.score || 0) + '% | Good: ' + (fb.good || 0) + ' | Bad: ' + (fb.bad || 0) + ' | Total: ' + (fb.total || 0);

  const learn = data.learning || {};
  const lr = learn.recent || [];
  const latest = lr.length ? lr[lr.length - 1].url : 'chưa có link';
  document.getElementById('learn-brief').textContent = 'Inbox: ' + (learn.count || 0) + ' link | Learned notes: ' + (learn.notes_count || 0) + ' | Mới nhất: ' + latest;

  const insightList = document.getElementById('learn-insights');
  insightList.innerHTML = '';
  const insights = learn.insights || [];
  if (!insights.length) {
    const li = document.createElement('li');
    li.textContent = 'Chưa có insight, hãy thêm link rồi bấm Learn Now.';
    insightList.appendChild(li);
  } else {
    for (const s of insights.slice(0, 3)) {
      const li = document.createElement('li');
      li.textContent = s;
      insightList.appendChild(li);
    }
  }

  const storeSummary = {
    path: data.store.path,
    events: data.store.events,
    topics: data.store.topics,
  };
  document.getElementById('store-brief').textContent =
    'Events: ' + data.store.events + ' | Topics: ' + Object.keys(data.store.topics || {}).length;
  document.getElementById('store').textContent = JSON.stringify({
    ...storeSummary,
    checks: data.doctor.checks,
  }, null, 2);

    const recentCount = (data.store.recent || []).length;
    document.getElementById('recent-brief').textContent = 'Hiển thị ' + recentCount + ' events gần nhất';
    document.getElementById('recent').textContent = JSON.stringify(data.store.recent, null, 2);
  } catch (err) {
    document.getElementById('health').className = 'bad';
    document.getElementById('health').textContent = '⚠️ Dashboard load error';
    document.getElementById('action-result').textContent = 'Lỗi tải dữ liệu: ' + ((err && err.message) || err);
  }
}
drawLife();
refresh();
setInterval(refresh, 15000);
"""
