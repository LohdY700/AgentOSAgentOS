# Known Limitations (Phase 1)

This project is currently a Phase-1 skeleton. Known limitations are intentional and documented below.

## 1) In-memory Event Bus
- No persistence across process restarts.
- No distributed transport yet.
- Single-process assumptions in current implementation.

## 2) Idempotency Scope
- Idempotency uses in-memory `seen_ids` only.
- Not durable across restarts.

## 3) Guard Signal Quality
- Process-name based detection only (`ps comm`).
- Can produce false positives in strict mode.
- No signature/hash/parent-chain validation yet.

## 4) Metrics Scope
- Current metrics are local and ephemeral.
- No Prometheus/OpenTelemetry exporter yet.

## 5) Security Model (Early)
- Guard is detection-oriented, not a full prevention engine.
- No seccomp/cgroup policy enforcement in this phase.

## 6) Test Coverage
- Unit tests cover critical bus paths and config loading.
- Integration/system tests are still minimal.

## 7) Packaging/Distribution
- Python runtime scaffold is present; not yet fully packaged as a deployable service bundle.

---

These limitations are acceptable for current objective: prove event-first AI-native runtime flow quickly and safely.
