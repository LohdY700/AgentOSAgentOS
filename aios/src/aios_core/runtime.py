from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AgentPolicy:
    name: str
    timeout_sec: int = 10
    restart_on_failure: bool = True


class AgentRunner:
    def __init__(self, policy: AgentPolicy) -> None:
        self.policy = policy
        self.restart_count = 0

    async def run(self, agent_fn):
        while True:
            try:
                await asyncio.wait_for(agent_fn(), timeout=self.policy.timeout_sec)
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning("agent %s crashed: %s", self.policy.name, exc)
                if not self.policy.restart_on_failure:
                    raise
                self.restart_count += 1
                await asyncio.sleep(0.2)
