from __future__ import annotations

import json
from pathlib import Path

from .config import load_guard_config
from .store_config import load_event_store_config
from .memory_backend import load_memory_backend


def run_doctor(root_dir: Path, guard_config_path: Path, store_config_path: Path) -> dict[str, object]:
    checks: list[dict[str, object]] = []

    # guard config
    try:
        g = load_guard_config(guard_config_path)
        checks.append({"name": "guard_config", "ok": True, "mode": g.mode, "allowed": len(g.allowed)})
    except Exception as exc:  # noqa: BLE001
        checks.append({"name": "guard_config", "ok": False, "error": str(exc)})

    # store config
    try:
        s = load_event_store_config(store_config_path)
        store_path = s.path if s.path.is_absolute() else root_dir / s.path
        checks.append(
            {
                "name": "store_config",
                "ok": True,
                "path": str(store_path),
                "max_lines": s.max_lines,
                "keep_last": s.keep_last,
                "prune_check_every": s.prune_check_every,
            }
        )

        # writable probe
        store_path.parent.mkdir(parents=True, exist_ok=True)
        probe = store_path.parent / ".doctor-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        checks.append({"name": "store_writable", "ok": True})
    except Exception as exc:  # noqa: BLE001
        checks.append({"name": "store_config", "ok": False, "error": str(exc)})

    # memory backend
    try:
        mem = load_memory_backend(root_dir)
        checks.append(
            {
                "name": "memory_backend",
                "ok": True,
                "requested": mem.requested,
                "active": mem.active,
                "fallback_used": mem.fallback_used,
                "note": mem.note,
            }
        )

        probe_text = "doctor-memory-probe"
        mem.backend.add(probe_text, {"kind": "doctor_probe"})
        probe_out = mem.backend.search("doctor-memory-probe", limit=1)
        checks.append({"name": "memory_rw", "ok": len(probe_out) >= 1, "backend": mem.active})
    except Exception as exc:  # noqa: BLE001
        checks.append({"name": "memory_backend", "ok": False, "error": str(exc)})

    ok = all(bool(c.get("ok")) for c in checks)
    return {"ok": ok, "checks": checks}


def render_doctor_json(root_dir: Path, guard_config_path: Path, store_config_path: Path) -> str:
    return json.dumps(run_doctor(root_dir, guard_config_path, store_config_path), ensure_ascii=False)


def doctor_exit_code(root_dir: Path, guard_config_path: Path, store_config_path: Path) -> int:
    result = run_doctor(root_dir, guard_config_path, store_config_path)
    return 0 if bool(result.get("ok")) else 1
