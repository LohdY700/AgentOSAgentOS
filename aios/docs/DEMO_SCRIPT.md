# AIOS 2-Minute Demo Script

## Goal
Show AIOS as an AI-native, event-first OS runtime: fast, lightweight, and safe-by-default.

## Setup
```bash
cd aios
```

## 1) Run quick benchmark (30s)
```bash
make bench
```
- Explain: event throughput, p95 latency, guard alerts, idle memory.

## 2) Generate markdown report (20s)
```bash
make report
sed -n '1,40p' docs/BENCHMARK_LATEST.md
```
- Explain: reproducible benchmark artifact for sharing.

## 3) Learning mode demo (40s)
```bash
make learning
sed -n '1,30p' config/guard-learning-candidates.txt
```
- Explain: learning mode discovers candidate process list without noisy anomaly spam.

## 4) Merge candidates into strict allowlist (20s)
```bash
python3 scripts/merge_allowlist.py
sed -n '1,80p' config/guard-allowlist.json
```
- Explain: controlled promotion from learning output to strict policy.

## 5) Final strict run (10s)
```bash
make demo
```
- Explain: strict mode emits anomalies only for unknown process names.

## Talking points
- 65MB ISO, ~5s boot, AI-ready runtime
- Event push architecture over polling
- Guard supports `learning -> strict` hardening flow
- Benchmark and report are reproducible
