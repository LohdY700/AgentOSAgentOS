# AIOS Release Checklist (v0.x)

## 1) Stability
- [ ] `make test` pass
- [ ] `make bench` returns valid JSON
- [ ] `make report` generates `docs/BENCHMARK_LATEST.md`
- [ ] Guard strict mode emits anomalies as expected
- [ ] Guard learning mode writes candidates file

## 2) Security & Policy
- [ ] `config/guard-allowlist.json` reviewed
- [ ] learning candidates merged intentionally (no blind merge)
- [ ] Dead-letter behavior verified

## 3) Demo Readiness
- [ ] Run `docs/DEMO_SCRIPT.md` once end-to-end
- [ ] Prepare latest benchmark snippet for sharing
- [ ] Confirm key talking points: 65MB / ~5s / event-first / learning->strict

## 4) Repository Hygiene
- [ ] No cache artifacts committed
- [ ] README updated with latest commands
- [ ] Commit history clean and understandable

## 5) Public Launch
- [ ] Tag release: `v0.x.y`
- [ ] Add release notes (what changed, known limits)
- [ ] Share benchmark + architecture summary
