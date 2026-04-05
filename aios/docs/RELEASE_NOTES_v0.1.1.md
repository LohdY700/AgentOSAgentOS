# AIOS v0.1.1 (Patch Notes)

## Focus
Noise reduction and guard policy hardening for strict mode.

## What changed
- Added **guard prefix allowlist** support (`allowed_prefixes`).
- Updated guard config loader to parse prefix policies.
- Added `kworker/` prefix in default strict/learning configs to absorb dynamic kernel worker names.
- Expanded tests:
  - guard prefix filtering behavior
  - config parsing for `allowed_prefixes`

## Impact
After baseline learning + merge + prefix policy:
- strict-mode unknown process count reduced from ~231 to **0** in current environment.
- guard alert noise significantly reduced while keeping strict detection enabled.

## Files touched
- `src/aios_core/guard.py`
- `src/aios_core/config.py`
- `config/guard-allowlist.json`
- `config/guard-learning.json`
- `tests/test_guard.py`
- `tests/test_config.py`

## Verification
```bash
cd aios
make test
make demo
```
Expected:
- tests pass
- strict demo reports `unknown_process_count: 0` (environment-dependent)
