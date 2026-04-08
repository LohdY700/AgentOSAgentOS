from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
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
from .conversation_quality import FeedbackStore, quality_summary, build_daily_rubric_review
from .memory_backend import load_memory_backend
from .mission_control_assets import MISSION_CONTROL_HTML, MISSION_CONTROL_JS
from .story_tts import synth_story_audio, StoryTtsError
from .wiki_pipeline import wiki_ingest, wiki_search, wiki_answer


def _now_vn_iso() -> str:
    return datetime.now(ZoneInfo("Asia/Bangkok")).isoformat()


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


def _memory_health(root_dir: Path) -> dict[str, Any]:
    mem = load_memory_backend(root_dir)
    backend = mem.backend
    store_path = ""
    items = None

    if hasattr(backend, "path"):
        p = Path(getattr(backend, "path"))
        store_path = str(p)
        if p.exists():
            items = len([x for x in p.read_text(encoding="utf-8").splitlines() if x.strip()])
        else:
            items = 0
    elif hasattr(backend, "index_dir"):
        idx = Path(getattr(backend, "index_dir"))
        store_path = str(idx)
        if idx.exists():
            items = len(list(idx.glob("*.pkl"))) + len(list(idx.glob("*.faiss")))
        else:
            items = 0

    return {
        "ok": True,
        "requested": mem.requested,
        "active": mem.active,
        "fallback_used": mem.fallback_used,
        "init_ms": round(float(mem.init_ms), 2),
        "cache_hit": bool(mem.cache_hit),
        "store_path": store_path,
        "items": items,
        "note": mem.note,
    }


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
    mem_health = _memory_health(root_dir)

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
            "init_ms": round(float(mem.init_ms), 2),
            "cache_hit": bool(mem.cache_hit),
        },
        "memory_health": mem_health,
        "progress": {
            "recent_commits": len(_mission_recent_commits(root_dir, limit=50)),
            "mission_notes": len(_load_mission_state(root_dir).get("notes", [])),
            "learning_notes": len(notes_recent),
            "chat_examples": len(chat_recent),
        },
    }




def _suggest_memory_filters(query: str) -> dict[str, str]:
    q = query.strip().lower()
    if not q:
        return {}
    if any(k in q for k in ["tiến độ", "status", "đang làm", "kế hoạch"]):
        return {"kind": "task"}
    if any(k in q for k in ["thích", "xưng hô", "phong cách", "preference"]):
        return {"kind": "preference"}
    if any(k in q for k in ["quy trình", "cách làm", "followup", "meeting", "proposal", "skill"]):
        return {"kind": "skill"}
    if any(k in q for k in ["policy", "compliance", "quy định"]):
        return {"source": "policy"}
    return {}




def _gpon_status(target_ip: str = "192.168.1.1") -> dict[str, Any]:
    import re
    import socket
    import urllib.request

    out: dict[str, Any] = {"ok": True, "target": target_ip}

    # hostname (reverse DNS best-effort)
    try:
        host, _, _ = socket.gethostbyaddr(target_ip)
        out["hostname"] = host
    except Exception:
        out["hostname"] = ""

    # ping
    try:
        p = subprocess.run(["ping", "-c", "2", "-W", "2", target_ip], capture_output=True, text=True, timeout=8)
        out["ping_ok"] = p.returncode == 0
        out["ping"] = (p.stdout or p.stderr)[-800:]
    except Exception as exc:  # noqa: BLE001
        out["ping_ok"] = False
        out["ping"] = str(exc)

    # route-selected interface (the one actually used to reach target)
    out["route_dev"] = ""
    try:
        route_line = subprocess.check_output(["ip", "route", "get", target_ip], text=True, timeout=5).strip().splitlines()[0]
        mdev = re.search(r"\bdev\s+(\S+)", route_line)
        if mdev:
            out["route_dev"] = mdev.group(1)
    except Exception:
        pass

    # arp/neigh (parse mac + interface)
    out["neighbors"] = []
    try:
        raw = subprocess.check_output(["ip", "neigh", "show", target_ip], text=True, timeout=5).strip()
        out["neighbor"] = raw
        for line in [x.strip() for x in raw.splitlines() if x.strip()]:
            mac = ""
            dev = ""
            state = ""
            m = re.search(r"lladdr\s+([0-9a-f:]{17})", line, flags=re.I)
            if m:
                mac = m.group(1)
            d = re.search(r"\bdev\s+(\S+)", line)
            if d:
                dev = d.group(1)
            st = re.search(r"\b(REACHABLE|STALE|DELAY|FAILED|INCOMPLETE|PERMANENT)\b", line)
            if st:
                state = st.group(1)
            # only keep neighbor on the route-selected interface when available
            if out["route_dev"] and dev and dev != out["route_dev"]:
                continue
            out["neighbors"].append({"dev": dev, "mac": mac, "state": state, "raw": line})
    except Exception:
        out["neighbor"] = ""

    # TCP 80 reachability
    try:
        sock = socket.create_connection((target_ip, 80), timeout=3)
        sock.close()
        out["tcp80"] = True
    except Exception:
        out["tcp80"] = False

    # HTTP headers (best effort)
    try:
        req = urllib.request.Request(f"http://{target_ip}", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
            out["http_status"] = int(getattr(resp, "status", 0) or 0)
            out["http_server"] = str(resp.headers.get("Server", ""))
            out["http_title_hint"] = str(resp.headers.get("WWW-Authenticate", ""))
    except Exception as exc:  # noqa: BLE001
        out["http_status"] = 0
        out["http_error"] = str(exc)

    return out




def _wifi_scan_status(iface: str = "wlp1s0") -> dict[str, Any]:
    import re
    out: dict[str, Any] = {"ok": True, "iface": iface, "items": []}
    try:
        raw = subprocess.check_output(
            ["nmcli", "-t", "--escape", "no", "-f", "SSID,BSSID,FREQ,SIGNAL,SECURITY", "dev", "wifi", "list", "ifname", iface],
            text=True,
            timeout=10,
        )
        rows = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            ln = line.strip()
            m = re.match(r"^(.*?):((?:[0-9A-Fa-f]{2}\\:){5}[0-9A-Fa-f]{2}):(.*?):(.*?):(.*)$", ln)
            if not m:
                continue
            ssid = m.group(1)
            bssid = m.group(2).replace("\\:", ":")
            freq = m.group(3)
            signal = m.group(4)
            security = m.group(5)
            band = "unknown"
            try:
                f = int(freq)
                if 2400 <= f <= 2500:
                    band = "2.4GHz"
                elif 4900 <= f <= 5900:
                    band = "5GHz"
                elif 5925 <= f <= 7125:
                    band = "6GHz"
            except Exception:
                pass
            rows.append({
                "ssid": ssid,
                "bssid": bssid,
                "freq_mhz": freq,
                "band": band,
                "signal": signal,
                "security": security,
            })
        out["items"] = rows
    except Exception as exc:  # noqa: BLE001
        out["ok"] = False
        out["error"] = str(exc)
    return out


def _mission_path(root_dir: Path) -> Path:
    return root_dir / "data" / "mission-control.json"


def _mission_backup_path(root_dir: Path) -> Path:
    return root_dir / "data" / "mission-control.backup.json"


def _default_mission_state() -> dict[str, Any]:
    return {
        "title": "AIOS Mission Control",
        "updated_at": _now_vn_iso(),
        "team": [
            {"name": "Su", "role": "Lead/Orchestrator", "status": "active"},
            {"name": "Behavior Trainer", "role": "Behavior Spec/Dataset/Rubric", "status": "active"},
            {"name": "Memory/Core Agent", "role": "Memory engine + benchmark + doctor", "status": "planned"},
            {"name": "Dashboard/API Agent", "role": "API + dashboard + integration tests", "status": "planned"},
            {"name": "Docs/Release Agent", "role": "Release notes + demo + launch posts", "status": "active"},
        ],
        "lanes": [
            {"name": "Behavior", "items": [
                {"task": "Integrate rubric into daily feedback loop", "status": "todo"},
                {"task": "Add quick-score template (5 criteria)", "status": "todo"}
            ]},
            {"name": "Memory/Core", "items": [
                {"task": "Metadata-aware memory search", "status": "todo"},
                {"task": "Add /api/memory/health", "status": "todo"}
            ]},
            {"name": "Dashboard/API", "items": [
                {"task": "Show memory health + latency card", "status": "todo"},
                {"task": "Integration test for filtered search", "status": "todo"}
            ]},
            {"name": "Docs/Release", "items": [
                {"task": "Update docs for metadata search", "status": "todo"},
                {"task": "Troubleshooting playbook", "status": "todo"}
            ]},
        ],
        "notes": [],
        "blockers": [],
    }


def _load_mission_state(root_dir: Path) -> dict[str, Any]:
    path = _mission_path(root_dir)
    bak = _mission_backup_path(root_dir)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        if bak.exists():
            try:
                data = json.loads(bak.read_text(encoding="utf-8"))
                path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                return data
            except Exception:
                pass
        state = _default_mission_state()
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        return state
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data
    except Exception:
        if bak.exists():
            try:
                data = json.loads(bak.read_text(encoding="utf-8"))
                path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                return data
            except Exception:
                pass
        return _default_mission_state()


def _save_mission_state(root_dir: Path, state: dict[str, Any]) -> None:
    path = _mission_path(root_dir)
    bak = _mission_backup_path(root_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        try:
            shutil.copy2(path, bak)
        except Exception:
            pass

    state["updated_at"] = _now_vn_iso()
    payload = json.dumps(state, ensure_ascii=False, indent=2)
    path.write_text(payload, encoding="utf-8")

    # keep backup in sync after successful write
    try:
        bak.write_text(payload, encoding="utf-8")
    except Exception:
        pass


def _mission_recent_commits(root_dir: Path, limit: int = 8) -> list[dict[str, str]]:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(root_dir), "log", f"-n{max(1, limit)}", "--pretty=%h|%s|%ci"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return []
    rows: list[dict[str, str]] = []
    for line in out.splitlines():
        if "|" not in line:
            continue
        h, subj, dt = (line.split("|", 2) + ["", "", ""])[:3]
        rows.append({"hash": h.strip(), "subject": subj.strip(), "date": dt.strip()})
    return rows


def _mission_artifacts(root_dir: Path, limit: int = 20) -> list[dict[str, str]]:
    docs = root_dir / "docs"
    if not docs.exists():
        return []
    rows = sorted(docs.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)
    out: list[dict[str, str]] = []
    for f in rows[: max(1, limit)]:
        out.append({"name": f.name, "path": str(f.relative_to(root_dir))})
    return out


def build_mission_snapshot(root_dir: Path) -> dict[str, Any]:
    state = _load_mission_state(root_dir)
    if "blockers" not in state:
        state["blockers"] = []
    return {
        "ok": True,
        "state": state,
        "kpi": _mission_kpi(root_dir, state),
        "commits": _mission_recent_commits(root_dir),
        "artifacts": _mission_artifacts(root_dir),
    }



def _mission_kpi(root_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    commits = _mission_recent_commits(root_dir, limit=50)
    lanes = list(state.get("lanes", []))
    all_items: list[dict[str, Any]] = []
    for lane in lanes:
        all_items.extend(list(lane.get("items", [])))

    done = sum(1 for x in all_items if str(x.get("status", "")).lower() == "done")
    in_progress = sum(1 for x in all_items if str(x.get("status", "")).lower() == "in_progress")
    blocked = sum(1 for x in all_items if str(x.get("status", "")).lower() == "blocked")
    todo = sum(1 for x in all_items if str(x.get("status", "")).lower() == "todo")

    return {
        "tasks_total": len(all_items),
        "done": done,
        "in_progress": in_progress,
        "blocked": blocked,
        "todo": todo,
        "commits_24h_hint": min(len(commits), 24),
        "notes": len(state.get("notes", [])),
        "blockers": len(state.get("blockers", [])),
    }


def _mission_write_daily_report(root_dir: Path, state: dict[str, Any]) -> Path:
    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    out = root_dir / "docs" / f"MISSION_REPORT_{now.strftime('%Y-%m-%d')}.md"
    kpi = _mission_kpi(root_dir, state)

    lines = [
        f"# Mission Report — {now.strftime('%Y-%m-%d %H:%M')} (Asia/Bangkok)",
        "",
        "## KPI",
        f"- tasks_total: {kpi['tasks_total']}",
        f"- done: {kpi['done']}",
        f"- in_progress: {kpi['in_progress']}",
        f"- blocked: {kpi['blocked']}",
        f"- todo: {kpi['todo']}",
        f"- mission_notes: {kpi['notes']}",
        f"- blockers: {kpi['blockers']}",
        "",
        "## Lanes",
    ]
    for lane in state.get("lanes", []):
        lines.append(f"### {lane.get('name', 'lane')}")
        for it in lane.get("items", []):
            lines.append(f"- [{it.get('status','todo')}] {it.get('task','')}")
        lines.append("")

    blockers = state.get("blockers", [])
    lines.append("## Blockers")
    if blockers:
        for b in blockers:
            lines.append(f"- [{b.get('status','open')}] {b.get('text','')} ({b.get('created_at','')})")
    else:
        lines.append("- none")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out

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

        def _send_audio_mp3(self, data: bytes, code: int = 200) -> None:
            self.send_response(code)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

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
            if parsed.path == "/api/conversation/rubric-review":
                q = parse_qs(parsed.query)
                limit = int((q.get("limit", ["5"])[0] or "5"))
                ex_store = ChatExampleStore(root_dir / "data" / "chat-examples.jsonl")
                rows = ex_store.list_recent(limit=200)
                self._send_json(build_daily_rubric_review(rows, limit=limit))
                return
            if parsed.path == "/api/memory/health":
                self._send_json(_memory_health(root_dir))
                return
            if parsed.path == "/api/memory/search":
                q = parse_qs(parsed.query)
                query = str((q.get("q", [""])[0] or "")).strip()
                limit = int((q.get("limit", ["5"])[0] or "5"))
                if not query:
                    self._send_json({"ok": False, "error": "missing q"}, code=400)
                    return
                filters: dict[str, str] = {}
                for key in ("kind", "role", "source"):
                    v = str((q.get(key, [""])[0] or "")).strip()
                    if v:
                        filters[key] = v
                auto_filters = _suggest_memory_filters(query) if not filters else {}
                applied_filters = filters or auto_filters
                mem = load_memory_backend(root_dir)
                self._send_json(
                    {
                        "ok": True,
                        "backend": mem.active,
                        "filters": applied_filters,
                        "auto_filter": bool(auto_filters),
                        "items": mem.backend.search(query, limit=limit, metadata_filters=applied_filters),
                    }
                )
                return
            if parsed.path == "/api/wiki/search":
                q = parse_qs(parsed.query)
                query = str((q.get("q", [""])[0] or "")).strip()
                limit = int((q.get("limit", ["5"])[0] or "5"))
                self._send_json(wiki_search(root_dir, query=query, limit=limit))
                return
            if parsed.path == "/api/wiki/qa":
                q = parse_qs(parsed.query)
                question = str((q.get("q", [""])[0] or "")).strip()
                limit = int((q.get("limit", ["3"])[0] or "3"))
                self._send_json(wiki_answer(root_dir, question=question, limit=limit))
                return
            if parsed.path == "/api/mission/status":
                self._send_json(build_mission_snapshot(root_dir))
                return
            if parsed.path == "/mission-control.js":
                self.send_response(200)
                self.send_header("Content-Type", "application/javascript; charset=utf-8")
                self.send_header("Cache-Control", "no-store, max-age=0")
                self.send_header("Pragma", "no-cache")
                body = MISSION_CONTROL_JS.encode("utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if parsed.path == "/mission-control":
                mc_ver = str(int(datetime.now(timezone.utc).timestamp()))
                html = MISSION_CONTROL_HTML.replace("__MC_VER__", mc_ver)
                self._send_html(html)
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
            if parsed.path == "/api/gpon/status":
                self._send_json(_gpon_status("192.168.1.1"))
                return
            if parsed.path == "/api/wifi/scan":
                self._send_json(_wifi_scan_status("wlp1s0"))
                return
            if parsed.path in ("/story-reader", "/story-reader/index.html"):
                story_path = root_dir.parent / "story-audio-reader" / "index.html"
                if story_path.exists():
                    self._send_html(story_path.read_text(encoding="utf-8"))
                else:
                    self._send_html("<h1>Story Reader not found</h1><p>Expected at ../story-audio-reader/index.html</p>")
                return
            if parsed.path in ("/wiki-search", "/wiki-search/index.html"):
                self._send_html(WIKI_SEARCH_HTML)
                return
            if parsed.path in ("/gpon", "/gpon/index.html"):
                self._send_html(GPON_HTML)
                return
            if parsed.path in ("/wifi-scan", "/wifi-scan/index.html"):
                self._send_html(WIFI_SCAN_HTML)
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
            if parsed.path == "/api/story/tts":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                    body = json.loads(raw)
                    text = str(body.get("text", "")).strip()
                    voice_key = str(body.get("voice", "bac")).strip().lower() or "bac"
                    if not text:
                        self._send_json({"ok": False, "error": "text is required"}, code=400)
                        return
                    audio = synth_story_audio(root_dir, text=text[:4000], voice_key=voice_key)
                    self._send_audio_mp3(audio)
                except StoryTtsError as exc:
                    self._send_json({"ok": False, "error": str(exc)}, code=400)
                except Exception as exc:  # noqa: BLE001
                    self._send_json({"ok": False, "error": str(exc)}, code=500)
                return
            if parsed.path == "/api/wiki/ingest":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                    body = json.loads(raw)
                    title = str(body.get("title", "")).strip()
                    content = str(body.get("content", "")).strip()
                    tags = body.get("tags", []) or []
                    if not title or not content:
                        self._send_json({"ok": False, "error": "title and content are required"}, code=400)
                        return
                    if isinstance(tags, str):
                        tags = [x.strip() for x in tags.split(",") if x.strip()]
                    out = wiki_ingest(root_dir, title=title, content=content, tags=list(tags))
                    self._send_json(out)
                except Exception as exc:  # noqa: BLE001
                    self._send_json({"ok": False, "error": str(exc)}, code=500)
                return
            if parsed.path == "/api/mission/note":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                    body = json.loads(raw)
                    note = str(body.get("note", "")).strip()
                    if not note:
                        self._send_json({"ok": False, "error": "note is required"}, code=400)
                        return
                    state = _load_mission_state(root_dir)
                    notes = list(state.get("notes", []))
                    notes.append({"text": note, "created_at": _now_vn_iso()})
                    state["notes"] = notes[-100:]
                    _save_mission_state(root_dir, state)
                    self._send_json({"ok": True})
                except Exception as exc:  # noqa: BLE001
                    self._send_json({"ok": False, "error": str(exc)}, code=500)
                return
            if parsed.path == "/api/mission/task-status":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                    body = json.loads(raw)
                    lane_name = str(body.get("lane", "")).strip()
                    task = str(body.get("task", "")).strip()
                    status = str(body.get("status", "")).strip().lower()
                    if status not in ("todo", "in_progress", "blocked", "done"):
                        self._send_json({"ok": False, "error": "invalid status"}, code=400)
                        return
                    state = _load_mission_state(root_dir)
                    changed = False
                    for lane in state.get("lanes", []):
                        if lane_name and str(lane.get("name", "")) != lane_name:
                            continue
                        for it in lane.get("items", []):
                            if str(it.get("task", "")).strip() == task:
                                it["status"] = status
                                changed = True
                                break
                        if changed:
                            break
                    if not changed:
                        self._send_json({"ok": False, "error": "task not found"}, code=404)
                        return
                    _save_mission_state(root_dir, state)
                    self._send_json({"ok": True})
                except Exception as exc:  # noqa: BLE001
                    self._send_json({"ok": False, "error": str(exc)}, code=500)
                return
            if parsed.path == "/api/mission/blocker":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                    body = json.loads(raw)
                    action = str(body.get("action", "add")).strip().lower()
                    state = _load_mission_state(root_dir)
                    blockers = list(state.get("blockers", []))
                    if action == "add":
                        text = str(body.get("text", "")).strip()
                        if not text:
                            self._send_json({"ok": False, "error": "text is required"}, code=400)
                            return
                        blockers.append({"id": str(len(blockers) + 1), "text": text, "status": "open", "created_at": _now_vn_iso()})
                    elif action == "resolve":
                        bid = str(body.get("id", "")).strip()
                        found = False
                        for b in blockers:
                            if str(b.get("id", "")) == bid:
                                b["status"] = "resolved"
                                b["resolved_at"] = _now_vn_iso()
                                found = True
                                break
                        if not found:
                            self._send_json({"ok": False, "error": "blocker not found"}, code=404)
                            return
                    else:
                        self._send_json({"ok": False, "error": "invalid action"}, code=400)
                        return
                    state["blockers"] = blockers[-100:]
                    _save_mission_state(root_dir, state)
                    self._send_json({"ok": True})
                except Exception as exc:  # noqa: BLE001
                    self._send_json({"ok": False, "error": str(exc)}, code=500)
                return
            if parsed.path == "/api/mission/daily-report":
                try:
                    state = _load_mission_state(root_dir)
                    out = _mission_write_daily_report(root_dir, state)
                    notes = list(state.get("notes", []))
                    notes.append({"text": f"Daily report generated: {out.name}", "created_at": _now_vn_iso()})
                    state["notes"] = notes[-100:]
                    _save_mission_state(root_dir, state)
                    self._send_json({"ok": True, "path": str(out.relative_to(root_dir))})
                except Exception as exc:  # noqa: BLE001
                    self._send_json({"ok": False, "error": str(exc)}, code=500)
                return
            self._send_json({"error": "not found"}, code=404)

        def log_message(self, fmt: str, *args):
            return

    return Handler


def run_dashboard(host: str, port: int, root_dir: Path, guard_config_path: Path, store_config_path: Path) -> None:
    cfg_path = root_dir / "config" / "memory-backend.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    lc = cfg.get("langchain", {}) if isinstance(cfg, dict) else {}
    preload = bool(lc.get("preload_on_startup", True))
    if preload:
        mem = load_memory_backend(root_dir)
        print(
            f"memory backend ready: requested={mem.requested} active={mem.active} "
            f"fallback={mem.fallback_used} init_ms={mem.init_ms:.2f} cache_hit={mem.cache_hit}"
        )

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
  <a href='/mission-control' style='margin-left:8px'>Open Mission Control</a>
  <a href='/story-reader' style='margin-left:8px'>Open Story Audio Reader</a>
  <a href='/wiki-search' style='margin-left:8px'>Open Wiki Search & QA</a>
  <a href='/gpon' style='margin-left:8px'>Open GPon</a>
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
    <div id='memory-health' style='margin-top:6px;color:#444'>Loading...</div>
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

function updateLifeMeta(eventCount, progress) {
  const p = progress || {};
  const xp = (eventCount || 0) + (Number(p.recent_commits || 0) * 30) + (Number(p.mission_notes || 0) * 20) + (Number(p.learning_notes || 0) * 15) + (Number(p.chat_examples || 0) * 10);
  const seg = Math.min(24, 1 + Math.floor(xp / 80));
  life.targetLen = seg;
  const stage = seg <= 3 ? 'head-only' : (seg <= 10 ? 'growing' : 'evolved');
  document.getElementById('life-stage').innerHTML = '<b>Stage:</b> ' + stage;
  document.getElementById('life-length').innerHTML = '<b>Length:</b> ' + seg + ' | <b>XP:</b> ' + Math.round(xp);
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
  updateLifeMeta((data && data.store && data.store.events) || 0, (data && data.progress) || {});
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
  const mh = data.memory_health || {};
  document.getElementById('memory-brief').textContent =
    'Requested: ' + (mb.requested || 'local') + ' | Active: ' + (mb.active || 'local') + (mb.fallback_used ? ' (fallback)' : '') + (mb.note ? ' | Note: ' + mb.note : '');
  document.getElementById('memory-health').textContent =
    'Init: ' + (mh.init_ms ?? '-') + ' ms | Cache: ' + ((mh.cache_hit) ? 'hit' : 'miss') + ' | Items: ' + (mh.items ?? '-') + (mh.store_path ? (' | Store: ' + mh.store_path) : '');

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


WIKI_SEARCH_HTML = """<!doctype html>
<html lang='vi'><head>
<meta charset='utf-8'/><meta name='viewport' content='width=device-width, initial-scale=1'/>
<title>Wiki Search & QA</title>
<style>
body{font-family:system-ui,sans-serif;max-width:920px;margin:24px auto;padding:0 12px}
input,button{padding:8px} .card{border:1px solid #ddd;border-radius:10px;padding:12px;margin-top:10px}
pre{white-space:pre-wrap}
</style></head><body>
<h1>🔎 Wiki Search & QA</h1>
<p><a href='/'>⬅ Dashboard</a> · <a href='/wifi-scan'>WiFi Scan</a></p>
<div class='card'>
  <input id='q' style='width:65%' placeholder='Nhập câu hỏi hoặc từ khóa...' />
  <button onclick='runSearch()'>Search</button>
  <button onclick='runQA()'>Ask QA</button>
</div>
<div class='card'><h3>Search results</h3><div id='searchOut'></div></div>
<div class='card'><h3>QA answer</h3><pre id='qaOut'>...</pre></div>
<script>
async function runSearch(){
 const q=encodeURIComponent((document.getElementById('q').value||'').trim());
 const r=await fetch('/api/wiki/search?q='+q+'&limit=6'); const d=await r.json();
 const out=document.getElementById('searchOut'); out.innerHTML='';
 (d.items||[]).forEach(it=>{ const div=document.createElement('div'); div.innerHTML='<b>'+it.title+'</b><br><small>'+it.path+'</small><br>'+it.snippet; out.appendChild(div); out.appendChild(document.createElement('hr')); });
 if(!(d.items||[]).length) out.textContent='Không có kết quả.';
}
async function runQA(){
 const q=encodeURIComponent((document.getElementById('q').value||'').trim());
 const r=await fetch('/api/wiki/qa?q='+q+'&limit=3'); const d=await r.json();
 document.getElementById('qaOut').textContent=d.answer||JSON.stringify(d,null,2);
}
</script></body></html>"""


GPON_HTML = """<!doctype html>
<html lang='vi'><head>
<meta charset='utf-8'/><meta name='viewport' content='width=device-width, initial-scale=1'/>
<title>GPon Monitor</title>
<style>
:root{--bg:#0b1020;--card:#121a33;--line:#283359;--txt:#e9eefc;--muted:#9fb0de;--ok:#22c55e;--bad:#ef4444}
body{font-family:system-ui,sans-serif;max-width:980px;margin:24px auto;padding:0 12px;background:var(--bg);color:var(--txt)}
a{color:#9cc0ff}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;margin-top:12px;box-shadow:0 6px 20px rgba(0,0,0,.2)}
.row{display:grid;grid-template-columns:repeat(2,minmax(220px,1fr));gap:10px}
.k{font-size:12px;color:var(--muted);margin-bottom:4px}
.v{font-size:16px;font-weight:700}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:700}
.ok{background:rgba(34,197,94,.15);color:#86efac}
.bad{background:rgba(239,68,68,.15);color:#fca5a5}
button{padding:8px 12px;border:1px solid var(--line);border-radius:10px;background:#1a2447;color:var(--txt);cursor:pointer}
ul{margin:0;padding-left:18px;color:var(--muted)}
</style>
</head><body>
<h1>📡 GPon</h1>
<p><a href='/'>⬅ Dashboard</a> · <a href='/wifi-scan'>WiFi Scan</a></p>
<div class='card'>
  <button onclick='refreshNow()'>Kiểm tra lại</button>
  <span id='badge' class='badge' style='margin-left:8px'>...</span>
  <p id='sum' style='color:var(--muted)'>Đang tải...</p>
  <div class='row'>
    <div><div class='k'>Hostname</div><div id='hostname' class='v'>-</div></div>
    <div><div class='k'>Route Interface</div><div id='routeDev' class='v'>-</div></div>
    <div><div class='k'>HTTP Server</div><div id='httpSrv' class='v'>-</div></div>
    <div><div class='k'>HTTP Status</div><div id='httpSt' class='v'>-</div></div>
  </div>
</div>
<div class='card'>
  <h3 style='margin-top:0'>MAC đang route tới gateway</h3>
  <ul id='macList'></ul>
</div>
<script>
async function refreshNow(){
 const r=await fetch('/api/gpon/status'); const d=await r.json();
 const ping = d.ping_ok ? 'OK' : 'FAIL';
 const badge=document.getElementById('badge');
 badge.textContent = 'Ping ' + ping;
 badge.className = 'badge ' + (d.ping_ok ? 'ok':'bad');
 document.getElementById('sum').textContent = `Target: ${d.target} | TCP80: ${d.tcp80?'OPEN':'CLOSED'} | Last update: ${new Date().toLocaleTimeString()}`;
 document.getElementById('hostname').textContent = d.hostname || '-';
 document.getElementById('routeDev').textContent = d.route_dev || '-';
 document.getElementById('httpSrv').textContent = d.http_server || '-';
 document.getElementById('httpSt').textContent = (d.http_status || 0);
 const ul=document.getElementById('macList'); ul.innerHTML='';
 const arr=(d.neighbors||[]);
 if(!arr.length){ const li=document.createElement('li'); li.textContent='Không có dữ liệu MAC'; ul.appendChild(li); }
 arr.forEach(n=>{ const li=document.createElement('li'); li.textContent=`${n.dev||'-'} → ${n.mac||'-'} [${n.state||'-'}]`; ul.appendChild(li); });
}
refreshNow(); setInterval(refreshNow, 15000);
</script></body></html>"""


WIFI_SCAN_HTML = """<!doctype html>
<html lang='vi'><head>
<meta charset='utf-8'/><meta name='viewport' content='width=device-width, initial-scale=1'/>
<title>WiFi Scan</title>
<style>body{font-family:system-ui,sans-serif;max-width:980px;margin:24px auto;padding:0 12px}table{width:100%;border-collapse:collapse}th,td{border:1px solid #ddd;padding:8px;font-size:14px}th{background:#f4f4f4}button{padding:8px 12px}</style>
</head><body>
<h1>📶 WiFi Scan</h1>
<p><a href='/'>⬅ Dashboard</a> · <a href='/gpon'>GPon</a></p>
<p><button onclick='scan()'>Quét lại</button> <span id='status'>...</span></p>
<table><thead><tr><th>SSID</th><th>BSSID (MAC)</th><th>Band</th><th>Freq</th><th>Signal</th><th>Security</th></tr></thead><tbody id='rows'></tbody></table>
<script>
async function scan(){
 const st=document.getElementById('status'); st.textContent='Đang quét...';
 const r=await fetch('/api/wifi/scan'); const d=await r.json();
 const tb=document.getElementById('rows'); tb.innerHTML='';
 if(!d.ok){ st.textContent='Lỗi: '+(d.error||'scan failed'); return; }
 (d.items||[]).forEach(it=>{
   const tr=document.createElement('tr');
   tr.innerHTML=`<td>${it.ssid||''}</td><td>${it.bssid||''}</td><td>${it.band||''}</td><td>${it.freq_mhz||''}</td><td>${it.signal||''}</td><td>${it.security||''}</td>`;
   tb.appendChild(tr);
 });
 st.textContent='Xong: '+(d.items||[]).length+' mạng';
}
scan(); setInterval(scan,20000);
</script></body></html>"""
