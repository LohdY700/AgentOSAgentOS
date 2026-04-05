#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STRICT_CFG = ROOT / "config" / "guard-allowlist.json"
LEARN_FILE = ROOT / "config" / "guard-learning-candidates.txt"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_candidates(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def main() -> None:
    cfg = load_json(STRICT_CFG)
    current = set(cfg.get("allowed", []))
    candidates = load_candidates(LEARN_FILE)

    if not candidates:
        print("No learning candidates found. Nothing to merge.")
        return

    merged = sorted(current | candidates)
    cfg["allowed"] = merged
    save_json(STRICT_CFG, cfg)

    print(f"Merged {len(candidates)} candidates into allowlist.")
    print(f"allowlist size: {len(merged)}")


if __name__ == "__main__":
    main()
