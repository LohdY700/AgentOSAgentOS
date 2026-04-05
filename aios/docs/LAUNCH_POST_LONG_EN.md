# Long Launch Post (EN)

I just shipped **AIOS v0.1.0** — an experiment in building an **AI-native runtime/OS direction**.

Instead of treating AI as a layer added on top later, I’m exploring the opposite: designing the runtime environment so agents can operate naturally from day one.

## What’s in v0.1.0?
- ~65MB ISO
- ~5s boot
- Event-first runtime (push events over polling)
- Process guard with two modes:
  - `learning` for baseline discovery
  - `strict` for anomaly alerts

## Phase-1 technical foundation
- Canonical event envelope
- In-memory event bus with retry + dead-letter + basic idempotency
- Benchmark/report pipeline
- Unit tests for reliability-critical paths
- CI to keep iteration quality high

## Why this direction?
In agent systems, constant polling quickly becomes expensive and noisy. Event-first flows are often cleaner, more reactive, and easier to reason about in terms of state transitions.

AIOS is still early, but the priorities are clear:
1) make it run,
2) make it measurable,
3) make it explainable,
4) make it improvable.

If you’re building agent infra / edge runtime / embedded AI, I’d love to connect.

#AIOS #BuildInPublic #AIAgents #Linux #Buildroot
