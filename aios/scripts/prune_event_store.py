#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def prune_jsonl(path: Path, keep_last: int) -> dict[str, int | str]:
    if keep_last < 1:
        raise ValueError("keep_last must be >= 1")

    if not path.exists():
        return {"store": str(path), "before": 0, "after": 0}

    lines = path.read_text(encoding="utf-8").splitlines()
    before = len(lines)
    kept = lines[-keep_last:]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(("\n".join(kept) + ("\n" if kept else "")), encoding="utf-8")
    return {"store": str(path), "before": before, "after": len(kept)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Prune AIOS JSONL event store")
    parser.add_argument("--path", default="data/events.jsonl", help="path to jsonl store")
    parser.add_argument("--keep-last", type=int, default=1000, help="number of latest rows to keep")
    args = parser.parse_args()

    result = prune_jsonl(Path(args.path), args.keep_last)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
