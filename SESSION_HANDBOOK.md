# Session Handoff Handbook (Parallel AI Workflow)

This file is the entry point for any new AI session working in this repo.

## Purpose
- Keep multiple AI sessions synchronized.
- Prevent duplicate/conflicting edits.
- Enforce research-first planning before implementation.
- Keep an auditable trail of assumptions, tasks, and outputs.

## Ground Rules (Mandatory)
1. Before major implementation, perform targeted research and produce a plan.
2. Do not implement major code changes until the plan is reviewed and locked.
3. Claim work in `PARALLEL_SESSION_LEDGER.md` before editing.
4. Update `TASKS_TBC.md` after each meaningful step.
5. Use scenario tags in outputs:
   - `S0_BASE_30MW_OPONLY` (headline)
   - `S1_36MW_OPONLY` (sensitivity)
   - `S2_30MW_FUELDISP` (sensitivity)
   - `S3_36MW_FUELDISP` (optional sensitivity)

## Current Delivery Policy
- HTGR-only scope.
- Headline FoM boundary: `operational_only`.
- Baseline reactor case: `30 MWth`.
- `36 MWth` is sensitivity only.

## Session Startup Checklist
1. Read this file.
2. Read `TASKS_TBC.md`.
3. Claim a task in `PARALLEL_SESSION_LEDGER.md`.
4. Confirm no overlap with active sessions.
5. If task is major:
   - run research,
   - draft a plan section in the ledger,
   - only then implement.
6. Commit changes with modular scope and clear messages.

## Session Close Checklist
1. Update `TASKS_TBC.md` status and notes.
2. Update `PARALLEL_SESSION_LEDGER.md` with:
   - files changed,
   - commit hash,
   - blockers and next steps.
3. Ensure outputs are scenario-tagged and reproducible.

## Canonical Output Location
- `outputs/canonical_pack/`
- Required artifacts include scenario JSONs, assumptions register, delta table, and compliance/limitations tables.

## Source-of-Truth Docs
- `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/source docs/Rolls Royce Fission Energy Project 25-26.pdf`
- `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/source docs/RR-UES_Final_Deliverables_Guidance.pdf`
- `TASKS_TBC.md`
- `PARALLEL_SESSION_LEDGER.md`
