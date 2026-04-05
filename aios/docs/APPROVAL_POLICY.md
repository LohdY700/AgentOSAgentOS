# Approval Policy (2-Tier)

## Goal
Reduce owner dependency while preserving safety.

## Tier 1 — Agent Auto-Approve
Low-risk, reversible operations:
- read logs / inspect status
- run test/benchmark/doctor
- generate docs/reports
- non-critical guard tuning

## Tier 2 — Owner Approval Required
High-impact or sensitive operations:
- sudo/system-level commands
- security policy hardening changes
- deploy to production
- release tag/push decisions
- external messaging/webhooks
- secret/token/access-control changes

## Pre-Approval Window
Owner can grant temporary pre-approval for selected Tier-2 actions.
- Recommended max window: 120 minutes
- Every action still logged with reason/context

## Audit Requirements
For every Tier-2 action:
- action name
- requested by (agent/user)
- reason
- timestamp
- approval status (approved/denied)

## Quick API Check
Dashboard server exposes policy check endpoint:

```bash
curl "http://127.0.0.1:8787/api/approval/check?action=sudo_command"
```

Response includes `tier` and `auto_approved`.
