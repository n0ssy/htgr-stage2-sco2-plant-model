# AI Onboarding Hub

Use this as the first file for any new AI session.

## Goal
- Fast, safe onboarding across sessions.
- Parallel execution without overlap.
- Research-first planning before implementation.
- Full audit trail from task claim to output artifact.

## Read Order (Mandatory)
1. `SESSION_HANDBOOK.md`
2. `TASKS_TBC.md`
3. `PARALLEL_SESSION_LEDGER.md`
4. `PLANNING_PROTOCOL.md`
5. `PR_TRACKER.md`

## 60-Second Startup
1. Check current branch:
   - `git branch --show-current`
2. Check current status:
   - `git status --short`
3. Read active tasks in `TASKS_TBC.md`.
4. Claim one task in `PARALLEL_SESSION_LEDGER.md`.
5. Start in research mode for major work.

## Parallel Session Rules
1. No file edits before task claim.
2. One session owns one task set and file set at a time.
3. If overlap is unavoidable, split by file/function and record it.
4. Always add handoff notes before ending a session.

## Required Workflow (Major Changes)
1. Research:
   - inspect existing implementation
   - verify assumptions against RR docs/literature
2. Plan:
   - decision-complete plan with APIs, tests, acceptance gates
   - reviewer lock before coding
3. Implement:
   - modular commits
   - preserve scenario-tag metadata
4. Validate:
   - scenario run checks
   - conversion checks
   - reproducibility checks
5. Handoff:
   - update task board and session ledger
   - list changed files + commit hash

## Canonical Scenario IDs
- `S0_BASE_30MW_OPONLY` (headline)
- `S1_36MW_OPONLY` (sensitivity)
- `S2_30MW_FUELDISP` (sensitivity)
- `S3_36MW_FUELDISP` (optional sensitivity)

## Canonical Output Pack
- Location: `outputs/canonical_pack/`
- Minimum expected files:
  - `canonical_pack_index.json`
  - `scenarios/*.json`
  - `fom_summary_with_uncertainty.csv`
  - `assumptions_register.csv`
  - `teammate_number_reconciliation.csv`
  - `teammate_delta_table.csv`
  - `architecture_compliance_matrix.csv`
  - `limitations_register.csv`
  - `constraint_margin_table.csv`
  - `equation_sheet.md`

## Team Scope Locks
1. HTGR-only scope.
2. Headline FoM uses `operational_only`.
3. Baseline is `30 MWth`.
4. `36 MWth` is sensitivity only.

## Source of Truth
- RR docs in `source docs/`
- Assumptions and tasks in `TASKS_TBC.md`
- Active ownership in `PARALLEL_SESSION_LEDGER.md`

## Session Templates
- New session prompt: `docs/ai/NEW_SESSION_PROMPT.md`
- Task card: `docs/ai/TASK_CARD_TEMPLATE.md`
- Handoff note: `docs/ai/HANDOFF_TEMPLATE.md`
