# Risk Levels

## L1 (Low)
No privileged access, easy rollback.
Examples: tests, metrics, docs.
Default: auto-approve.

## L2 (Medium)
Can affect behavior but usually recoverable.
Examples: guard allowlist tuning, runtime config updates.
Default: auto-approve with logging; escalate if uncertain.

## L3 (High)
Privileged, external, or hard-to-rollback.
Examples: sudo commands, secrets, production deploy, access-control changes.
Default: owner approval required.
