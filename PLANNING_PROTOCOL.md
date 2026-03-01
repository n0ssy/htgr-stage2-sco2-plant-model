# Research-First Planning Protocol

This project requires a strict sequence for all major changes:

## Step 1: Research
- Inspect current implementation and related outputs.
- Cross-check assumptions against primary references (RR docs + technical sources).
- Capture findings and risks.

## Step 2: Plan
- Produce a decision-complete plan including:
  - objective and scope
  - interface/type changes
  - data flow and formulas
  - test cases and acceptance criteria
  - rollback/risk notes
- Iterate with reviewer until assumptions are locked.

## Step 3: Implement
- Make modular commits by workstream.
- Keep changes scoped and traceable.
- Update task and session ledgers.

## Step 4: Validate
- Run targeted tests and scenario checks.
- Export scenario-tagged outputs.
- Gate on:
  - conversion checks
  - metadata tags
  - reproducible FoM values

## Step 5: Handoff
- Update:
  - `TASKS_TBC.md`
  - `PARALLEL_SESSION_LEDGER.md`
  - canonical output index
- Note unresolved blockers explicitly.
