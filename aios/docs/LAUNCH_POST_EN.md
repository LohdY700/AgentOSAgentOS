# Launch Post (EN)

I just shipped **AIOS v0.1.0** — an experiment in building an **AI-native OS runtime**:

- ~65MB ISO
- ~5s boot
- Event-first architecture (push events over polling)
- Process guard with `learning -> strict` hardening flow

This phase focuses on the runtime foundation:
- Canonical event envelope
- Event bus with retry + dead-letter + basic idempotency
- Process anomaly guard
- Benchmark/report pipeline + CI

The repo now includes:
- 2-minute demo script
- Architecture doc
- Known limitations (explicitly documented)
- Release checklist

Early stage, but the direction is clear: **AI agents need environments designed for them from first principles.**

#AIOS #BuildInPublic #AIAgents #Linux #Buildroot
