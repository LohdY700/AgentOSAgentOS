# AIOS v0.1.3 (Draft Release Notes)

## Highlights
- Dashboard UX improved for non-technical users:
  - Added action buttons: **Run Health Check** and **Run Benchmark**.
  - Added **Copy Public Status** button for quick share text.
  - Added **What to do now** guidance card.
  - Store/Recent panels now default to friendly summaries with optional JSON expand.
- Added approval decision API:
  - `GET /api/approval/check?action=<action_name>`
  - returns `tier` + `auto_approved`.
- Added 2-tier approval framework docs + config and dashboard summary.

## Why this matters
This release shifts AIOS from engineering-only visibility toward human-friendly operation,
while keeping governance explicit via policy checks and approval tiers.

## Suggested demo
1. `make dashboard`
2. open `http://127.0.0.1:8787`
3. click **Run Health Check**
4. click **Run Benchmark**
5. check policy with:
   `curl "http://127.0.0.1:8787/api/approval/check?action=sudo_command"`
