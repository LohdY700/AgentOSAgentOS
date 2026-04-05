from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ApprovalDecision:
    action: str
    tier: str
    auto_approved: bool


def load_policy(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def classify_action(action: str, policy: dict) -> ApprovalDecision:
    t1 = set(policy.get("tiers", {}).get("tier1_auto", {}).get("actions", []))
    t2 = set(policy.get("tiers", {}).get("tier2_owner", {}).get("actions", []))

    if action in t2:
        return ApprovalDecision(action=action, tier="tier2_owner", auto_approved=False)
    if action in t1:
        return ApprovalDecision(action=action, tier="tier1_auto", auto_approved=True)
    # unknown defaults to owner approval (safe default)
    return ApprovalDecision(action=action, tier="tier2_owner", auto_approved=False)
